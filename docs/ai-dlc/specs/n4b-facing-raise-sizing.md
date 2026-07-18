# N4b — facing-raise sizing grades (delta spec)

Roadmap: `docs/ai-dlc/roadmap/simulate-table.md` Epic 3, second half of the N4 split (N4a = barrels, shipped #48). Contracts: `docs/ai-dlc/contracts/n4b-facing-raise-sizing.md`. Interview locked 2026-07-18 (Gate 1 confirmed): **full scope** — flop facing mappers included, RES-B forks, Practice reconciled, texture-aware verdict everywhere.

## Goal (one line)
When hero faces a bet or check-raise (flop/turn/river, HU), offer TWO raise sizes, grade the size choice into the existing `sizing_correctness` field with a texture-aware verdict, and open Simulate's first flop facing-node grading via two new mappers — backend-only, no migration, no FE.

## Design decisions (locked)

### D1 — Raise-size forks: one shared constant, selected by check-raise-ness
New const in `backend/app/domain/table/sizing.py` (single source for graded + displayed + Practice):

```python
FACING_RAISE_MULTS: dict[str, tuple[float, float]] = {
    "check_raise": (2.5, 3.5),  # hero check-raises the FLOP c-bet — RES-B :148 (flop-scoped research)
    "raise":       (2.5, 3.0),  # every other facing raise / re-raise — RES-B :149
}
```
Multipliers apply to the faced bet/raise-to amount: `small = round(m_small * bet, 1)`, `big = round(m_big * bet, 1)`. Clamp rule (refuter LOW, mirrors `_barrel_two_sizes` exactly): clamp each leg to `min(computed, hero_remaining)`, then **big ≤ small after clamp → collapse to one leg**; keep `_faced_bet_spot`'s existing None-if-hero-can't-afford gate keyed on the SMALL leg. Pair selection: `check_raise` **iff street is FLOP and hero checked earlier this street** (the vs-c-bet check-raise); ALL other facing raises — flop re-raise over a check-raise, and all turn/river raises — use `raise` (2.5×/3.0×). Rationale (refuter MED): RES-B's 2.5×/3.5× row is explicitly "Check-raise (flop)"; extrapolating it to turn/river is unresearched, and the 3.0× big leg keeps turn/river `per_action` RAISE values byte-identical to today's flat 3×. NOTE the corrected RES-B mapping: 2.5×/3.5× is for MAKING a check-raise, NOT re-raising over one.

### D2 — Mapper emission: `_faced_bet_spot` emits two RAISE legs (ATOMIC WITH D4)
`grade_map_postflop.py::_faced_bet_spot` (321-364) parameterized: replaces the single `round(3*bet,1)` RAISE leg (:336, :358) with two RAISE `LegalAction`s from D1 (small first, big second; D1 clamp/collapse rule). **CALL leg untouched for existing callers** (`min_bb = bet`, feeds `faced_bet_bucket` — signature-frozen). Signature is provably RAISE-leg-blind (contracts §4) — safe.
**HARD SEQUENCING CONSTRAINT (refuter HIGH-2): D2 must NOT land without D4 in the same change.** The graders' current first-leg `next(...)` grab would silently return the small leg and change `per_action`'s RAISE `size_bb`. Ship D2+D4 as one atomic ticket, with a regression test asserting a two-RAISE spot grades against the leg nearest `decision.size_bb` (not list order). Pinned tests `test_grade_map_turn_river.py:252-256,296-300` (single 3×-leg lists) and `test_postflop.py:353` update in the same change — intentional, expected churn.

### D3 — Two NEW flop facing mappers + dispatcher widening
- `map_flop_vs_cbet` — HU SRP, villain (postflop aggressor) has bet the flop, hero to act facing it → `NodeContext.VS_CBET` spot via `_faced_bet_spot`. If hero checked before the bet → check_raise mults; else raise mults.
- `map_flop_vs_check_raise` — hero c-bet the flop, villain raised, hero faces the raise → `NodeContext.VS_CHECK_RAISE`; hero's re-raise uses "raise" mults with sizing base = villain's raise-to. **CALL leg is INCREMENTAL (refuter HIGH-1):** hero already invested the c-bet this street, so `CALL.min_bb = raise_to − hero_cbet` — NOT raise-to. (Full raise-to would corrupt `_faced_call_and_pot`'s pot-odds price in `grade_vs_check_raise` (postflop.py:877), display the wrong call amount, and double-subtract hero's bet in `faced_bet_bucket` (srs.py:83-104) — misfiled SRS buckets.) Implementation: generalize `_faced_bet_spot` with a separate `call_amt` param (default = `bet`, existing callers unchanged); this mapper passes `bet=raise_to` (sizing base) + `call_amt=raise_to − hero_cbet` — same convention `build_check_raise_spot` pins at `scenarios.py:575`. Required test: `CALL.min_bb == raise_to − cbet`.
- Gates mirror existing discipline: HU only (`len(live)!=2 → None`), canonical recognizable line, else `None` ("no baseline yet" — never a wrong grade). Dispatcher `grade_map.py:44-45` widens: flop → first non-None of `map_flop_cbet` → `map_flop_vs_cbet` → `map_flop_vs_check_raise`.
- These route to the EXISTING, tested `grade_vs_cbet` / `grade_vs_check_raise` (already wired in `PostflopHeuristicProvider`) — first time reachable from live Simulate.

### D4 — Grader generalization: sizing verdict is an OVERLAY, not per-size eval surgery (ATOMIC WITH D2)
The 4 facing graders (`grade_vs_cbet` :743, `grade_vs_check_raise` :932, `grade_vs_turn_bet` :1259, `grade_vs_river_bet` :1595) keep a SINGLE RAISE `ActionEval` and the size-blind action match — action `correctness` and `ev_bb` stay byte-identical (no frequency splitting, no action-verdict drift risk). The RAISE eval's `size_bb` build changes from first-leg `next(...)` to **the BIG leg** (`max` of RAISE legs' `min_bb`): on turn/river facing nodes big = 3.0× = today's flat 3×, so existing `per_action` values are byte-identical; on the flop nodes the value is new coverage anyway. This replacement of the first-leg grab is the D2-atomicity fix — regression test required (two-leg spot → RAISE eval `size_bb` == big leg, sizing verdict resolves by nearest leg).
**Intentional design divergence from N4a (refuter MED, documented):** `_bet_sizing_verdict` is merit/frequency-driven because the bet graders compute distinct per-size merits (`m_small`/`m_big`). The facing graders' `_merits_vs_*` return ONE scalar raise merit — no per-size raise merits exist, and inventing them risks exactly the action-verdict drift this design avoids. So the raise verdict is a **texture-rule overlay** (the RES-B guidance applied directly), NOT a merit comparison. This is deliberate, not accidental asymmetry.
New pure helper in `postflop.py`:

```python
_raise_sizing_verdict(spot, decision, texture, chosen_eval) -> Correctness | None
```
- `None` unless: hero's action is RAISE, spot has TWO distinct RAISE legs, and `chosen_eval` merit > 0 (no "size:" sub-note beside a raise-blunder — N4a rule).
- Texture-aware (everywhere, per Gate 1): flop-texture `wetness` (graders already hold the flop `Texture` for all streets):
  - `dry` → small leg optimal, big acceptable (pot-controlled raise)
  - `wet` → big leg optimal, small acceptable (deny equity)
  - `medium` → both acceptable (no forced optimal on a neutral board)
- Hero's leg = nearest of the two RAISE `min_bb` to `decision.size_bb` (same nearest-size rule as `_match`).
- Wired additively into all 4 facing graders' `EvaluationResult(..., sizing_correctness=...)`. Single-leg spots (short-stack collapse, pre-N4b flows) → `None`, exactly today's behavior.

### D5 — Simulate two-size display + parity
`sim_session.py`: new `_is_facing_raise_node(state)` gate — non-None from the corresponding `map_vs_*`/`map_flop_vs_*` mapper (grade-gated, like `_is_turn_barrel_node`) — plus `_facing_two_sizes(...)` mirroring `_barrel_two_sizes`: same `FACING_RAISE_MULTS` + same faced-bet amount + same rounding/clamp/collapse as `_faced_bet_spot` ⇒ displayed==graded by construction. Wire into `_hero_legal_actions` (485-524) ahead of the generic single-size fallback (:513-522); preflop RAISE branch (506-512) untouched. `HERO_NODE_SIZE["raise"]` path remains the fallback for unmapped facing nodes.

### D6 — Practice reconciled onto the shared constant (single-size stays)
`scenarios.py` builders import `FACING_RAISE_MULTS` and use the BIG fork (drills stay one raise size):
- `build_vs_cbet_spot` (:488): hero's check-raise `3*cbet` → `3.5*cbet` (**behavior change** — the check-raise fork's big).
- `build_check_raise_spot` (:576): hero's re-raise `3*raise_to` → `3.0*raise_to` (**value unchanged**, now sourced from the const; keep its incremental `call_amt` convention :575 intact).
Practice stays single-size, single-eval — no drill UI change.

## Files to touch
`backend/app/domain/table/sizing.py` · `backend/app/domain/table/grade_map_postflop.py` · `backend/app/domain/table/grade_map.py` · `backend/app/domain/postflop.py` · `backend/app/services/sim_session.py` · `backend/app/domain/scenarios.py` · tests: `backend/tests/test_postflop.py`, `backend/tests/test_grade_map_turn_river.py`, new `backend/tests/test_grade_map_flop_facing.py`, `backend/tests/test_sim_postflop_sizing.py` (extend), any scenarios/drill test asserting `3*cbet`.

## Out of scope
Multiway (stays "no baseline yet") · bot/villain sizing (`personas_postflop.py` — anti-tell, untouched) · hero-barrels-then-gets-raised turn/river nodes (no grader exists — N5) · FE changes (existing generic "size:" sub-note renders raise verdicts as-is; verify only) · schema/migration (0011 column reused) · texture classifier changes · preflop paths · `spot_signature()`/`_postflop_signature()`/`TAXONOMY_VERSION`.

## Constraints
Domain purity (test-enforced) · results freq+EV never boolean · signatures frozen (CALL leg `min_bb` untouched; RAISE legs verified un-hashed) · strict superset: every currently-graded flow that N4b doesn't intentionally change stays byte-identical (action verdicts NEVER move — only `sizing_correctness` may newly populate; flop hands that mapped `None` and still have no canonical line stay `None`) · displayed==graded from one constant · Alembic: none needed.

## Build-phase findings folded (2026-07-18)
- **Refuter-on-diff HIGH:** `_faced_bet_spot` affordability keyed on chips-behind, but the check-raise-defense hero already has the c-bet invested — raise-TO ceiling is now `invested_street_bb + stack_bb` (byte-identical for zero-invested callers; mid-stack facing-check-raise nodes no longer silently un-map). Pinned by two mid-stack tests.
- **Design-review HIGH (reachability):** bots size bets `round(f*pot, 2)` but `_is_canonical_bet` demanded the 1-dp canonical value within 1e-6 — so every villain-bet-gated facing mapper (incl. the pre-existing R5 `map_vs_turn_bet`/`map_vs_river_bet`) was DEAD in live play. Fixed with a 0.06bb fraction-recognition tolerance (`_CANON_BET_TOL`); pinned by `test_bot_rounded_cbet_maps`. Headless probe: 20 two-raise facing offers / 3000 hands with an all-tag lineup (0 before the fix). **Residual reachability limits are pre-existing ecosystem gates, deferred to N5:** loose default persona mix makes HU pots rare (155/217 BB flop facing nodes were multiway), oversized persona opens (3.5/4.0/4.5) rejected by the R5 open band, and BB-defense content exists only vs UTG/CO/BTN openers.
- **Design-review LOW:** clamped big raise leg floors to 1dp so paired button labels share precision.

## Verify-by
`./scripts/verify.sh` green (incl. purity + signature pins) · `cd backend && ruff check .` · `cd frontend && npm run typecheck && npm run build` (FE untouched, must stay green) · e2e: a Simulate hand reaching a facing node offers two raise sizes, hero raises, `sizing_correctness` persists on the `SimDecision` and returns in `GradeView` · parity test: offered sizes == graded legs incl. short-stack collapse · **refuter-mandated tests:** `map_flop_vs_check_raise` `CALL.min_bb == raise_to − cbet`; two-leg spot → RAISE eval `size_bb` == big leg + verdict resolves nearest-leg; turn/river `per_action` RAISE `size_bb` unchanged at `round(3*bet,1)` · flop dispatcher test: vs-c-bet and vs-check-raise hands now grade; multiway/non-canonical still `None` · Practice: `build_vs_cbet_spot` at 3.5×, `build_check_raise_spot` unchanged at 3.0× · design-review (coach mode, both themes): two raise buttons at a facing node + "size:" sub-note on recap.
