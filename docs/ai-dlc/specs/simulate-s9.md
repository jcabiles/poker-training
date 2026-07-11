# Delta spec — Simulate S9: hero plays (session persistence, stacks, ledger)

> Slice S9 of `docs/ai-dlc/roadmap/simulate-table.md` (Track E, W4 — strictly after S4:
> full hands need the postflop bots). Contract scan 2026-07-10 (agent report folded in).
> Interview decisions 2026-07-10: **full mid-hand restore** (persist live `HandState`,
> resume the exact decision point) · **defer `sim_decision` to S10** (S9 ships
> `sim_session` + `sim_seat` + `sim_hand` only; no per-decision rows, no grading).

**Goal (one line):** turn the Simulate tab into a **playable, persistent** 9-max session —
hero acts via predetermined-sizing buttons, bots act (instantly, no pacing yet), stacks
carry over, busts auto-rebuy to 100BB, a per-seat net-BB ledger tracks P&L, and a browser
reload restores the **exact live decision point** — with **no grading** (that is S10).

## Two invariants that shape the whole slice

1. **Bots resolve synchronously ⇒ persisted state is always at a hero-decision boundary or
   hand-over — never mid-bot-sequence.** The server advances all bots up to the hero's turn
   (or hand end) *within a single request*, then persists `HandState`. Restore therefore
   never resumes a half-played bot street. This is what makes full mid-hand restore
   tractable.
2. **Hero-only wire privacy is structural and must be re-earned per new response shape.**
   `PlayerState` has no `hole_cards` field (can't leak). `HandState.seats[i].hole_cards`
   holds **all 9** hands and is **server-side only** — like `full_board` and the seed.
   Every wire view is built field-by-field from a rehydrated `HandState`; the ONLY hole
   cards on the wire are `hero.hole_cards` plus, at showdown, the `showdown_seats`' cards.
   Folded villains are never revealed. No endpoint ever returns `state_json` or a raw
   `HandState`.

## Frozen interface

### Domain play-loop — `app/domain/table/play.py` (NEW, pure; add
`'app.domain.table.play'` to `test_domain_purity.py` allowlist)

Productionizes the bot-driving helpers that already exist in
`tests/test_personas_postflop.py` (`_preflop_facing`, `_preflop_decision`,
`_postflop_decision`, `_live_opponents`, `_play_hand`) — **mirror the PER-DECISION logic
EXACTLY** (preflop raise size = `la.min_bb`; bots min-raise; postflop threads
`current_bet_to=state.current_bet_bb`; do NOT invent iso-sizing or the S3/S4 persona
calibration breaks). The one change vs `_play_hand`: stop at the hero seat instead of
sampling it. **Parity is per-DECISION, not per-hand:** given the same `(state, seat, pack,
rng)`, `bot_decision` must return the same `Decision` the harness's `_preflop_decision`/
`_postflop_decision` would. A full-hand playout of `advance_to_hero` will NOT match
`_play_hand` on the same seed — production skips the hero's RNG draw, so the bot RNG stream
diverges from the harness's the moment the hero is not the last actor to close a street.
This is by design; never assert full-hand parity.

```python
LINEUP: tuple[VillainType, ...]  # fixed composition, 8 bots: PASSIVE_FISH, PASSIVE_FISH,
                                 # TAG, TAG, CALLING_STATION, NIT, LAG, MANIAC
def assign_lineup(rng: random.Random) -> dict[int, VillainType]:
    """Shuffle LINEUP across the 8 non-hero seats (1..8); seat 0 is the hero (absent)."""

@dataclass(frozen=True)
class ActionEvent:            # safe to serialize (NO hole cards)
    seat: int
    position: Position
    action: ActionType
    amount_bb: float
    street: Street

def bot_decision(state: HandState, seat: int, pack: PersonaPack,
                 rng: random.Random) -> Decision:
    """One bot seat's action: preflop via _preflop_facing + sample_preflop_action (+ the
    min_bb sizing wrap), postflop via sample_postflop_decision threading
    current_bet_to=state.current_bet_bb and opponents=_live_opponents(state, seat)."""

def advance_to_hero(state: HandState, seat_personas: dict[int, PersonaPack],
                    hero_seat: int, rng: random.Random) -> tuple[HandState, list[ActionEvent]]:
    """Apply bot actions (via engine.apply — pure) until to_act_seat == hero_seat OR
    hand_over. Returns the advanced state + ordered events. Never applies a hero action.
    Guard against non-termination (mirror the harness's guard<500)."""
```

### Persistence — `app/db/models.py` + Alembic `0009_sim_tables` (down_revision "0008")

Three additive tables (S9 is the **sole** Alembic owner this wave; head 0008 → 0009).
Owner_id sentinel `''` (migration 0006 pattern). `rng_seed` stored as **str** (256-bit,
overflows SQLite INTEGER). `state_json` is the **first** text-blob column in the codebase —
holds `HandState.model_dump_json()` (all hole cards, server-side only).

```python
class SimSession(SQLModel, table=True):     # __tablename__ = "sim_session"
    id: str            = Field(primary_key=True)          # uuid4 hex
    owner_id: str      = Field(default="", index=True)    # '' sentinel
    button_seat: int
    hand_no: int
    status: str        = Field(default="active")          # "active" | "ended"
    created_at: datetime

class SimSeat(SQLModel, table=True):        # __tablename__ = "sim_seat"; 9 rows/session
    session_id: str    = Field(primary_key=True, foreign_key="sim_session.id")
    seat_index: int    = Field(primary_key=True)          # 0..8 (composite PK)
    is_hero: bool
    persona_type: str | None                              # VillainType value; None = hero
    stack_bb: float                                       # carry-over current stack
    buyins_bb: float                                      # cumulative chips brought in

class SimHand(SQLModel, table=True):        # __tablename__ = "sim_hand"
    id: int | None     = Field(default=None, primary_key=True)   # autoincrement
    session_id: str    = Field(foreign_key="sim_session.id", index=True)
    hand_no: int
    button_seat: int
    rng_seed: str                                          # persisted per R1
    status: str        = Field(default="in_progress")     # "in_progress" | "complete"
    state_json: str | None = None                          # serialized live HandState
    created_at: datetime
```

### Session service — `app/services/sim_session.py` (NEW; DB-touching, outside domain purity)

Returns **view objects** the API layer serializes (privacy-scrubbed; see below). Signatures
frozen so the API ticket (T2) authors against them:

```python
def create_session(db: Session, owner_id: str = "") -> SessionView
def restore_session(db: Session, session_id: str, owner_id: str = "") -> SessionView | None
    # None => 404 (preserves the existing 404 contract the FE special-cases)
def apply_hero_action(db: Session, session_id: str, decision: Decision,
                      owner_id: str = "") -> SessionView            # raises on illegal/not-hero-turn
def deal_next_hand(db: Session, session_id: str, owner_id: str = "") -> SessionView
def leave_session(db: Session, session_id: str, owner_id: str = "") -> None
```

**Bot-action RNG lifecycle (deal vs actions are SEPARATE streams).** The deal uses
`random.Random(int(rng_seed))` (R1 — reproducible, `rng_seed` persisted). Bot ACTIONS use a
DIFFERENT rng: the service constructs a **fresh `random.Random(secrets.randbits(256))` for
each `advance_to_hero` call**. Rationale: a naive `random.Random(rng_seed)` re-seeded per
request would replay the identical draw sequence on every street (degenerate, correlated bot
play — a bug invisible to chip-conservation/restore/parity tests). Consequence: **bot actions
are intentionally NOT reproducible from `rng_seed`** (only the deal and the pre-first-hero-
action street are); full-hand replay is a **Later** item that would need a persisted action
log — out of S9 scope. Restore is unaffected: bots' results are already baked into the
persisted `state_json`; restore never re-runs bots.

Behavior:
- **create:** mint id; random `button_seat`; `assign_lineup` over seats 1..8 (hero = seat 0);
  9 `SimSeat` rows (stack 100, buyins 100); deal hand 1 (seed = `secrets.randbits(256)`,
  logged), `start_hand(stacks=[per-seat carry])`, `advance_to_hero`, persist `SimHand`
  (`state_json`, status in_progress unless already over).
- **apply_hero_action:** load in-progress `SimHand`, rehydrate `HandState`, assert
  `to_act_seat == hero_seat` and the decision is in `legal_actions` (else `ValueError`),
  `apply`, then `advance_to_hero`. If `hand_over`: `settle`, apply `deltas` to each
  `SimSeat.stack_bb`, **auto-rebuy** any seat with `stack_bb < 1.0` up to 100.0
  (`buyins_bb += 100.0 - stack_before`; then `stack_bb = 100.0`), mark hand complete,
  persist final `state_json`. Persist the new `state_json` either way. **Round `stack_bb`
  and `buyins_bb` to 2dp on every settlement/rebuy write** (engine's `round(x, 2)`
  convention — keeps `net_bb` free of IEEE-754 display noise).
- **deal_next_hand:** require the current hand `complete` (else no-op/idempotent);
  `button_seat = (button_seat+1) % 9`; `hand_no += 1`; deal with **carry-over stacks** from
  `SimSeat`; `start_hand`, `advance_to_hero`, new `SimHand` row.
- **leave_session:** `status = "ended"` (session no longer restorable → 404 on restore).

### Wire schemas — `app/schemas/simulate.py` (extend) + `SessionView` shape

`SessionView` (service-side) carries everything; the API scrubs to these wire models
(Maker C mirrors field names verbatim in `types.ts`):

```python
class SeatView(BaseModel):          # per seat, all 9
    seat_index: int
    position: str
    persona_type: str | None        # badge; None for hero
    is_hero: bool
    stack_bb: float
    status: str                     # IN / FOLDED / ALLIN
    invested_street_bb: float       # this street's commitment (for chips-in-front display)
    net_bb: float                   # stack_bb - buyins_bb (ledger)

class ShowdownSeatView(BaseModel):  # ONLY for settlement.showdown_seats
    seat_index: int
    hole_cards: tuple[str, str]
    delta_bb: float

class SimulateHandView(BaseModel):  # REPLACES the S1 shape (superset)
    hand_no: int
    button_seat: int
    street: str
    board: list[str]                # REVEALED cards only (never full_board)
    pot_bb: float
    seats: list[SeatView]
    hero: Hero                      # hero.hole_cards — the only in-hand hole cards
    to_act_seat: int | None
    is_hero_turn: bool
    legal_actions: list[LegalAction]     # populated only when is_hero_turn
    events: list[EventView]              # bot actions since the last hero decision
    hand_over: bool
    showdown: list[ShowdownSeatView]     # [] until hand_over; folded villains never listed

class EventView(BaseModel):
    seat_index: int; position: str; action: str; amount_bb: float; street: str

class SessionView(BaseModel):       # top-level response
    session_id: str
    hand: SimulateHandView
```

### API — `app/api/v1/simulate.py` (rewrite the two S1 endpoints + add three)

- `POST /simulate/session` → `SessionView` (create)
- `GET  /simulate/session/{id}` → `SessionView` (**restore**; 404 if missing/ended)
- `POST /simulate/session/{id}/action` body `Decision` → `SessionView` (hero acts)
- `POST /simulate/session/{id}/hand` → `SessionView` (deal next; keeps the S1 path name)
- `POST /simulate/session/{id}/leave` → 204
All use `Depends(get_session)`. 404 uses the existing `HTTPException(404, "session not
found")` shape. Illegal hero action → `HTTPException(400, ...)`. `owner_id=""` (no auth).

### Frontend — `SimulateView.tsx` + `components/simulate/*` + `types.ts` + `client.ts`
+ tokens/css (Maker C, ux-ui-designer; App.tsx single-owner this wave)

- Replace the fake `toSpot()` neutral-value adapter with the real `SimulateHandView`
  (board, pot, per-seat persona badge + stack + status + chips-in-front). `PokerTable.tsx`
  stays the render primitive; the adapter maps the new view onto it (villain cards absent).
- **Hero action bar:** reuse Practice's predetermined-sizing pattern
  (`lib/decisions.ts::legalDecisions` + `DecisionBar` shape) driven by
  `hand.legal_actions` — fold/check/call/bet/raise buttons at engine-provided sizes; **no
  free-form input.** Shown only when `is_hero_turn`. Posts `Decision` to `/action`.
- **Bots act instantly** (S9 = no pacing; S11 owns delays): after a hero action, render the
  resulting view; `events` may be shown as a static list/log (no animation).
- **Ledger panel:** per-seat `net_bb`.
- **Hand-over:** show `showdown` (revealed seats + deltas) + a "Deal next hand" control
  (auto-deal deferred to S11); recap/verdicts are S10 (none here).
- **Reload restore:** persist `session_id` in `localStorage` on create; on mount, if present
  `GET /session/{id}` → render the restored decision point; on 404 clear it and start fresh
  (preserve the existing `isSessionNotFound` recovery). "Leave table" → `POST /leave`,
  clear storage, start fresh.
- `types.ts`: hand-mirror every new field (no generation). `client.ts`: `getSession`,
  `postHeroAction`, `postNextHand`, `leaveSession`. Tokens-only CSS, AA contrast + visible
  focus **both themes**; `design-reviewer` pass required.

## Out of scope (S9 no-gos)

No grading / verdicts / badges-per-decision / recap `why` (S10) · no `sim_decision` table
(S10) · no attempt recording / `source` column (S10) · no SRS writes ever · no pacing /
delays / auto-deal / speed setting (S11) · no multi-session list · no persona-aware
anything · no `services/review.py` or grader/provider/srs edits (that's S8's file set) · no
straddles/antes/rake.

## Verify-by

`play.py` bot loop matches the `test_personas_postflop.py` reference logic (parity, no
calibration drift — refuter diffs them); `./scripts/verify.sh` → BACKEND VERIFY OK;
migration 0009 up/down clean, existing rows read back unchanged; **manual**: `#/simulate`
deals → play a hand to showdown → fold mid-hand → **reload mid-hand restores the exact
decision point** → bust triggers rebuy + ledger reflects buy-ins → "Leave table" ends it;
no wire payload ever contains a non-hero, non-showdown seat's hole cards (privacy test);
`cd frontend && npm run typecheck && npm run build` green; `design-reviewer` acceptable
(AA contrast + focus both themes); ruff clean; domain-purity green (with
`app.domain.table.play` added).
