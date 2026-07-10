# Delta spec — Simulate S1: table walking skeleton

> Slice S1 of `docs/ai-dlc/roadmap/simulate-table.md` (mark `[x]` there when Verify-by passes).
> Contract scan: `docs/ai-dlc/contracts/simulate-s1.md`. PRD: `docs/ai-dlc/prd/simulate-table.md` (§8 RNG grounding).
> Gate decisions (2026-07-10): reuse PokerTable · hero cards only on the wire · no board shown in S1.

**Goal (one line):** a "Simulate" tab that deals seed-reproducible 9-max hands — 9 seats,
hero hole cards, dealer button rotating each hand — with no betting, chips, or persistence.

## API contract (FROZEN before fan-out — all three tickets build to this)

```
POST /api/v1/simulate/session                 → 200 SimulateSessionResponse
POST /api/v1/simulate/session/{session_id}/hand → 200 SimulateHandView | 404 {"detail": "session not found"}
```

```python
# schemas/simulate.py (thin wrappers; domain Pydantic models ARE the wire contract)
class SimulateHandView(BaseModel):
    hand_no: int                 # 1-based, increments per hand
    players: list[PlayerState]   # exactly 9, one per Position, stack_bb=100, is_hero on hero's
    hero: Hero                   # position + hole_cards (the ONLY hole cards on the wire) + stack_bb=100

class SimulateSessionResponse(BaseModel):
    session_id: str              # uuid4 hex
    hand: SimulateHandView
```

Wire privacy: villain hole cards and the 5-card board are dealt server-side but NEVER
serialized in S1 (no field for them). The RNG seed is logged server-side
(`logger.info("simulate hand seed session=%s hand=%s seed=%s", ...)`) and kept on the
in-memory hand record — not on the wire (seed ⇒ full deck derivable).

Errors: unknown `session_id` → `raise HTTPException(status_code=404, detail="session not found")`.
First error-response precedent in this API — keep it exactly this simple.

## Behavior

- **Deal:** per hand, `seed = secrets.randbits(256)`; `rng = random.Random(seed)`;
  `deck = [r + s for r in RANKS for s in SUITS]` (mirror `equity.py:24`); `rng.shuffle(deck)`;
  pop 18 hole cards (2 per seat, hero included) then 5 board cards. No hand-rolled shuffle.
- **Seats/rotation:** 9 fixed seats, hero always seat 0 (FE hero-centering handles display).
  Session holds a button seat index; hand 1 places the button at a random seat
  (`secrets.randbelow(9)` at session create); each subsequent hand advances it one seat.
  Positions derive from the button clockwise in the frozen order
  `BTN, SB, BB, UTG, UTG1, UTG2, LJ, HJ, CO` mapped onto seats — every emitted
  `Position.value` is a member of the FE `RING` (contract A3/C5) and exactly one player is
  `BTN` per hand (dealer chip contract A4).
- **Session state:** module-level `dict[str, SimSession]` in `api/v1/simulate.py`
  (mirrors the `drill.py:56-60` singleton precedent). Lost on restart — accepted.
- **FE:** new `SimulateView` renders the existing `PokerTable` via a **synthetic-Spot
  adapter** (refuter finding: `PokerTable`'s sole prop is a full `Spot` and it dereferences
  `spot.game.stakes.sb` / `spot.board` / `spot.pot_bb` etc. unguarded — a bare
  `players`/`hero` payload neither typechecks nor runs). The adapter lives ENTIRELY inside
  `SimulateView.tsx` (PokerTable.tsx is NOT touched) and builds a `Spot` object from the
  response with these pinned values: `players`/`hero` from the wire · `game.stakes = {sb: 0.5,
  bb: 1}` (BB units) · `game.table_size = 9` · `board = []` · `pot_bb = 0` ·
  `effective_stack_bb = 100` · `node_context = []` · `action_history = []` ·
  `legal_actions = []` · `to_act = hero.position` · `limper_count = 0` · street preflop ·
  any remaining required `Spot` fields per `types.ts` get the neutral literal that
  typechecks (optional fields omitted). Villains render face-down via the existing
  `faceDown` union (contract C6). SimulateView adds a hand counter + "Next hand" button.
  View registered at all 4 points (`View` union + `VIEW_IDS` in `hashRoute.ts`; `VIEWS` +
  an explicit render branch in `App.tsx` — must NOT fall into the `QuizPanel` else).
  Session created lazily on first visit; session id held in component state (a reload
  starts a new session — fine in S1).

## Files / interfaces to touch (and nothing else)

| Ticket | Files |
|---|---|
| T1 domain | `backend/app/domain/table/{__init__,deck}.py` (new) · `backend/tests/test_table.py` (new) · `backend/tests/test_domain_purity.py` (allowlist += `app.domain.table.deck` — the precise module, not the bare package; contract C4) |
| T2 API | `backend/app/schemas/simulate.py` (new) · `backend/app/api/v1/simulate.py` (new) · `backend/app/api/v1/__init__.py` (include_router) · `backend/tests/test_simulate_api.py` (new) |
| T3 FE | `frontend/src/lib/hashRoute.ts` · `frontend/src/App.tsx` · `frontend/src/components/SimulateView.tsx` (new) · `frontend/src/api/client.ts` · `frontend/src/api/types.ts` |

Domain interface (frozen for T2): `deal_hand(rng: random.Random) -> DealtHand` where
`DealtHand` (Pydantic, in `deck.py`) has `hole_cards: list[tuple[Card, Card]]` (len 9, seat
order) and `board: list[Card]` (len 5); plus `positions_for_button(button_seat: int) -> list[Position]`
(len 9, **indexed by seat**: element `i` is seat `i`'s position). Cards are the existing
`Card = str` alias from `domain/spot.py`.

**Indexing pinned by worked example (T1 implements, T2 consumes — must match exactly):**
`positions_for_button(0) == [BTN, SB, BB, UTG, UTG1, UTG2, LJ, HJ, CO]` — seat 0 is the
button when `button_seat == 0`; `positions_for_button(2)[2] == BTN`, and seat 3 is then SB
(clockwise = ascending seat index, wrapping mod 9). T2 zips `hole_cards[i]` with
`positions_for_button(button_seat)[i]` to build seat `i`'s `PlayerState`; hero is seat 0
always, so hero's position = `positions_for_button(button_seat)[0]`.

`SimSession` (module-internal to T2, NOT frozen — reviewers expect no spec match): minimally
`button_seat: int`, `hand_no: int`; anything else is T2's judgment.

## Out of scope (S1 no-gos)

No betting/actions/blinds/chips beyond the constant 100BB display · no personas (seats show
positions only) · no board reveal · no DB writes, models, or Alembic migrations (touching
`alembic/versions/` is a scope violation) · no keyboard shortcuts for simulate · no RNG
statistical suite (S2) · no reuse of or changes to `drill.py`'s `_RNG` · no `spot_signature()`
or grader/provider code paths.

## Constraints (from profile invariants)

Domain purity: `domain/table/` imports nothing from fastapi/starlette/sqlmodel/sqlalchemy
(test-enforced once allowlisted) · CSS values from design tokens only; AA contrast + visible
focus both themes · `types.ts` hand-maintained, field-for-field with `schemas/simulate.py` ·
strategy stays in `content/` (S1 adds none) · may push/PR on `feat/*` branches; never main.

## Verify-by (end-to-end)

1. `./scripts/verify.sh` → `BACKEND VERIFY OK`. Pytest auto-discovers the new
   `test_table.py` + `test_simulate_api.py` (verify.sh's boot-probe only exercises
   drill/stats/health routes — simulate coverage comes from pytest, not the probe; verify.sh
   itself is out of scope). Required tests: fixed-seed test (known seed ⇒ exact expected
   18+5 cards), uniqueness (52 distinct, no repeats within a hand), rotation test (button
   advances one seat per hand; every hand exactly one BTN; all Position values valid;
   worked-example indexing asserted), 404 on unknown session, response carries no villain
   cards and no board (assert fields absent), purity test green with the new allowlist entry.
2. `cd frontend && npm run typecheck && npm run build` — clean.
3. Manual probe: `./scripts/serve.sh start` → open `#/simulate` → a hand renders (9 seats,
   hero cards face-up, villains face-down, one dealer chip) → "Next hand" deals a new hand
   with the button moved one seat → reload restores the Simulate view (hash route).
