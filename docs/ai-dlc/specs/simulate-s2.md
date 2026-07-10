# Delta spec — Simulate S2: hand engine (betting, side pots, showdown, chip conservation)

> Slice S2 of `docs/ai-dlc/roadmap/simulate-table.md` (Track A, W2). Contract map:
> `docs/ai-dlc/contracts/simulate-s2.md`. Interview 2026-07-10: raw-shuffle RNG suite;
> raise-to semantics, public `best7` alias, POST-blind history, float-tolerance conservation
> all frozen at Gate 1.

**Goal (one line):** a pure-domain 9-max NLHE hand state machine in
`backend/app/domain/table/engine.py` — blinds through showdown with side pots and chip
conservation — surfacing legal actions in Practice's exact `LegalAction` shape, plus the RNG
statistical suite deferred from S1. Domain-only: zero wire/UI/persona changes.

## Frozen interface (makers implement EXACTLY this)

```python
# backend/app/domain/table/engine.py  (new; purity-allowlist entry required)

class SeatState(BaseModel):
    seat: int                      # 0-8
    position: Position             # from positions_for_button(button_seat)[seat]
    stack_bb: float                # chips behind (not yet invested)
    invested_street_bb: float      # put in THIS street (resets each street)
    invested_total_bb: float       # put in this hand (never resets)
    status: PlayerStatus           # IN / FOLDED / ALLIN
    hole_cards: tuple[Card, Card]

class Pot(BaseModel):
    amount_bb: float
    eligible_seats: list[int]      # seats that can win it (side-pot layering)

class HandState(BaseModel):
    button_seat: int
    street: Street                 # PREFLOP → FLOP → TURN → RIVER
    board: list[Card]              # REVEALED cards only: 0/3/4/5 by street
    full_board: list[Card]         # all 5 from DealtHand (internal; never serialized)
    seats: list[SeatState]         # len 9, index = seat
    to_act_seat: int | None        # None ⇒ betting closed / hand over
    current_bet_bb: float          # highest invested_street_bb this street
    min_raise_to_bb: float         # legal minimum raise-TO amount
    last_full_raise_bb: float      # size of last full raise increment (min-raise rule)
    action_history: list[HistoryAction]   # existing model; POST entries for blinds
    hand_over: bool

class SeatDelta(BaseModel):
    seat: int
    delta_bb: float                # net chips won/lost this hand (2dp)

class Settlement(BaseModel):
    pots: list[Pot]
    winners_by_pot: list[list[int]]  # parallel to pots; ties split
    deltas: list[SeatDelta]          # len 9, sums to 0.0 (±0.01 per rounding rule)
    showdown_seats: list[int]        # seats whose hands were compared ([] on fold-out)

def start_hand(dealt: DealtHand, button_seat: int, stacks_bb: list[float]) -> HandState
def legal_actions(state: HandState) -> list[LegalAction]     # for state.to_act_seat
def apply(state: HandState, decision: Decision) -> HandState  # pure: returns NEW state
def settle(state: HandState) -> Settlement                    # only when hand_over
```

```python
# backend/app/domain/equity.py — one line, no behavior change:
best7 = _best7   # public alias; docstring: 7-card list[str] → comparable strength tuple
```

`table/__init__.py` re-exports the new public names alongside the existing three.

## Rules (frozen semantics)

1. **Blinds + initial state:** `start_hand` posts SB 0.5 / BB 1.0 as `ActionType.POST`
   entries in `action_history` with `amount_bb` absolute (0.5, 1.0); `invested_street_bb`
   reflects posts; **POST does not count as having acted.** Initial betting state:
   `current_bet_bb = 1.0`, `last_full_raise_bb = 1.0`, `min_raise_to_bb = 2.0` (min open =
   2.0-to). Resolves S1 carry-forward "Pot 0bb". First to act preflop = seat
   `(button_seat + 3) % 9` (UTG); postflop = first seat with `status == IN` clockwise from
   SB. Any `stacks_bb[i]` below that seat's blind obligation → `ValueError` (unreachable
   today: flat 100bb + auto-rebuy).
2. **Amount semantics:** `Decision.size_bb` for RAISE/BET = **raise-TO / bet-TO total** for
   the street. `Decision` arriving with `size_bb=None` (size_fraction-only, valid per the
   model validator) → `ValueError("engine requires size_bb")` — size_fraction unsupported
   in S2; illegal-action test covers it. `LegalAction` CALL `min_bb` = **incremental**
   chips to add (net of `invested_street_bb`) — the existing repo convention (contract 4);
   frozen because `faced_bet_bucket` derives SRS signatures from it.
   `HistoryAction.amount_bb` = absolute chips moved by that action (increment actually paid).
3. **Legal-action shapes (Practice precedent), three cases:**
   - unopened street → `[CHECK, BET(min_bb=1.0-to, max_bb=stack-to)]`
   - facing chips → `[FOLD, CALL(min_bb=incremental), RAISE(min_bb=min_raise_to_bb,
     max_bb=all-in-TO)]`
   - **matched-but-holds-option** (e.g. BB in a limped pot: `invested_street_bb ==
     current_bet_bb` but seat hasn't acted) → `[CHECK, RAISE(min_bb=min_raise_to_bb,
     max_bb=all-in-TO)]` — never `CALL(min_bb=0)`, never `BET`.
   When all-in-TO < `min_raise_to_bb`, RAISE is offered as the jam encoding
   `RAISE(min_bb=all-in-TO, max_bb=all-in-TO)` (precedent `scenarios.py:248`) — `min_bb`
   must never exceed `max_bb`. `apply` accepts ANY size in `[min_bb, max_bb]` for
   raises/bets (persona sizings, S4), not just an offered value.
4. **All-in:** never a new ActionType — CALL/RAISE capped at stack sets
   `status = PlayerStatus.ALLIN`. **Incomplete-raise rule (increment comparison):** an
   all-in raise-TO where `(allin_to − current_bet_bb) < last_full_raise_bb` is incomplete —
   it does NOT reopen action for seats that have already acted this street. After it:
   `current_bet_bb = allin_to`; `min_raise_to_bb` and `last_full_raise_bb` UNCHANGED.
   "Already acted this street" is derived from `action_history` (entries for this street
   with `action != POST`, positions unique per seat) — no extra state field. A seat that
   already acted and faces only an incomplete raise gets `[FOLD, CALL]` (no RAISE) — the
   fourth legal-action shape. A complete raise sets `last_full_raise_bb = allin_to −
   current_bet_bb` (the increment), `current_bet_bb = allin_to`, `min_raise_to_bb =
   current_bet_bb + last_full_raise_bb`, and reopens action.
5. **Street advance:** betting closes when every seat with `status == IN` has matched
   `current_bet_bb` and acted this street; engine reveals `full_board[:3]` / `[:4]` /
   `[:5]`, resets `invested_street_bb = 0` and `current_bet_bb = 0`, sets
   `min_raise_to_bb = 1.0` and `last_full_raise_bb = 1.0` (first BET of `b` then sets
   `last_full_raise_bb = b`, `min_raise_to_bb = 2b`). If ≤1 IN seat can act (others
   folded/all-in), remaining streets auto-reveal and the hand runs out to settlement.
6. **Fold-out:** last unfolded seat wins uncontested; `showdown_seats = []`; hole cards of
   others never compared. An uncalled top-layer bet returns to its bettor.
7. **Side pots:** standard layering by ascending `invested_total_bb` of all-in seats,
   folded contributors' chips staying in as dead money; each pot's `eligible_seats` =
   contributors not folded. Showdown per pot via `best7(hole + board)` tuple comparison;
   equal tuples split equally.
8. **Rounding — conservation by construction:** internal arithmetic unrounded floats. At
   settlement, per pot: round each winner's share DOWN to 2dp, then assign the pot's
   residual to the remainder winner — the eligible winner minimizing
   `(seat − button_seat − 1) % 9` (SB-first, button-last). Rounded payouts sum exactly to
   the rounded pot, so `sum(d.delta_bb for d in deltas) == 0.0` EXACTLY (test asserts
   equality within float epsilon 1e-9, not ±0.01).
9. **Illegal actions:** `apply` raises `ValueError` with a specific message: wrong action
   type for the current shape, size outside `[min_bb, max_bb]`, `size_bb=None` on
   BET/RAISE, RAISE after an incomplete raise by a no-reopen seat, act on finished hand.
   (Wrong-seat is impossible — action always applies to `to_act_seat`.)
10. **RNG:** engine itself is deterministic given inputs — takes NO rng. Randomized
    playout tests inject their own seeded `random.Random` (repo convention, contract 10).

## RNG statistical suite (deferred from S1)

New `backend/tests/test_rng_suite.py`, seeded `random.Random(20260710)`, unmarked:
- **200k raw shuffles** of the same 52-card list `deal_hand` shuffles (import the deck
  constant; call `rng.shuffle` directly — same code path, no model construction):
  card×position chi-square over the first 18 dealt slots (52×18 table, p > 0.001), plus
  pocket-pair rate 5.88% and suited rate 23.53% over the implied 9 hands per shuffle,
  tolerance ±0.3pp (binomial 3σ at n=1.8M hands ≈ ±0.05pp; ±0.3pp is generous).
- **5k full `deal_hand` calls** proving the wrapper preserves distribution (pair/suited
  rates within ±1.5pp) and no duplicate cards within any deal.
- Runtime budget: whole file < 10s; report measured runtime in the ticket close-out.

## Other tests (property + scripted)

- Chip-conservation property: ≥2k random-policy playouts (uniform legal action, seeded rng);
  every hand: `sum(delta) == 0 ±0.01`, no negative stacks, every all-in seat's delta bounded
  by their investment.
- Scripted side-pot scenarios settle exactly: 3-way with two all-ins at different amounts;
  split main pot + sole side-pot winner; incomplete-raise reopening case; fold-out;
  BB walk-through (everyone folds to BB).
- Illegal-action rejection cases.
- Purity: `tests/test_domain_purity.py` allowlist += `'app.domain.table.engine'`.

## Files

`backend/app/domain/table/engine.py` (new) · `backend/app/domain/table/__init__.py`
(re-exports) · `backend/app/domain/equity.py` (alias line only) ·
`backend/tests/test_engine.py` (new) · `backend/tests/test_rng_suite.py` (new) ·
`backend/tests/test_domain_purity.py` (one allowlist string).

## Out of scope (S2 no-gos)

No API/wire/schema/FE changes (S9) · no persona logic (S4) — random-policy playouts suffice ·
no straddles/antes/rake · no changes to `deck.py` internals (pinned-seed test) · no grading
shapes — engine does settlement, never correctness/freq/EV · no DB/Alembic.

## Verify-by

`cd backend && pytest -q` fully green including new suites (report test_rng_suite.py
runtime); scripted side-pot cases assert exact amounts; conservation property over ≥2k
playouts; illegal actions raise; `tests/test_table.py` pinned-seed test UNCHANGED and green;
domain-purity green with the new entry; ruff clean; `./scripts/verify.sh` → BACKEND VERIFY OK.
