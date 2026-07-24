# W2 tickets — persona identity + EV correctness

Spec: `docs/ai-dlc/specs/persona-realism-w2.md`. One branch `feat/persona-realism-w2`, one PR. Build serial in order; each ticket is a commit.

Owned hotspot (single-owner, serial): `backend/app/domain/personas_postflop.py`, `backend/tests/test_personas_postflop.py`.

---

## T1 — W2-a schema: two optional levers on `PersonaPostflop`
**Files:** `backend/app/domain/content/models.py`.
**Do:** add `call_looseness: float | None = Field(default=None, gt=0.0)` and `size_elasticity: float | None = Field(default=None, ge=0.0)` to `PersonaPostflop` (note: elasticity allows 0 = size-blind; looseness must be >0 like stickiness). Docstring each: "optional; falls back to `stickiness` when unset (default-off byte-identity)".
**Done:** existing persona JSON all still validate (`load_persona_packs()` succeeds); a pack with neither set parses with both `None`.
**Acceptance:** `python -c "from app.domain.personas import load_persona_packs; load_persona_packs()"` clean; a unit asserts unset → `None`.

## T2 — W2-a wiring: split the two uses of `stickiness` in the sampler
**Files:** `backend/app/domain/personas_postflop.py`.
**Do:** at the top of the decision body resolve `looseness = pf.call_looseness if pf.call_looseness is not None else pf.stickiness`. Compute the price exponent with the legacy/opt-in branch (reviewer #1 — crash + direction fix): `size_elasticity is None` → `exponent = _PRICE_SENSITIVITY * pf.stickiness ** (-_PRICE_STICKINESS_DAMP)` (legacy, byte-identical); else → `exponent = _PRICE_SENSITIVITY * pf.size_elasticity` (DIRECT; 0 → flat, higher → steeper). Change `_price_factor` to accept the resolved exponent (`_price_factor(faced_frac, exponent)`) OR add a sibling — either way un-opted-in callers stay byte-identical. Replace the call-merit `* pf.stickiness` → `* looseness`. Update the STICKINESS_DAMP comment block to describe the split + the two exponent branches. **KEEP the α buckets** (continuous reformulation descoped, reviewer #2).
**Done:** a persona with neither lever set samples a byte-identical decision stream vs pre-T2, verified on captured normalized weights (not informal).
**Acceptance:** `test_elasticity_split_default_off_byte_identical` (unset pack, fixed seed, captured normalized weights + decision identical); `test_size_elasticity_zero_is_size_flat` (elasticity 0.0 does NOT raise, price factor equal across all size buckets); existing suite green pre-content-edit.

## T3 — W2-a monotonicity pins rewritten onto new levers
**Files:** `backend/tests/test_personas_postflop.py`.
**Do:** rewrite `test_monotonicity_stickiness_never_lowers_call_freq` to build `high` via `update={"call_looseness": ...}` ONLY — leave `stickiness` (hence the elasticity fallback) unchanged between base/high so the fold-side price factor is held constant and the assertion isolates the call axis (reviewer #9) — assert call-freq non-decreasing. Add `test_size_elasticity_steeper_fold_vs_bigger_size` (higher `size_elasticity` ⇒ larger fold-rate gap OVERBET-vs-SMALL). Keep the α-ceiling / price-monotone pins.
**Done:** both monotonicity properties hold on the new levers.
**Acceptance:** the two monotonicity tests pass.

## T4 — W2-a content: unlock station/fish identity
**Files:** `content/personas/calling_station.json`, `content/personas/passive_fish.json` (others only if a clear gain).
**Do:** station `size_elasticity ≈ 0.0` (size-blind) + `call_looseness` ≈ its current stickiness (or higher); fish higher `size_elasticity` + moderate `call_looseness`. Ground each value in the D4 curve target, not vibes. Leave nit/tag/lag/maniac unset (byte-identical) unless a value is justified.
**Done:** station D4 fold-curve roughly flat SMALL→OVERBET; fish D4 curve rises steeply.
**Acceptance:** `test_station_fold_curve_flat` + `test_fish_fold_curve_steep` (D4-style sweep) pass.

## T5 — W2-a fixture re-record (station/fish opt-in moves the stream)
**Files:** `backend/tests/data/coverage_baseline.json`, `backend/tests/test_coverage_baseline.py`, `backend/tests/test_limper_coverage_belt.py`, the golden AF/WTSD dict in `test_personas_postflop.py`.
**Do:** re-record each fixture that moves; add a W2-a docstring note (why: station/fish elasticity opt-in changes their faced-size fold decisions → shared-rng displacement). Bands frozen. **Per-persona guard (reviewer #8):** before overwriting, regenerate + diff old-vs-new restricted to un-opted-in personas (neither lever set) and assert that subset byte-identical FIRST. Verify coverage ratio holds vs the immutable start floor; verify every limper `_WANT_*` shape still fires.
**Done:** all three fixtures pass on the re-recorded values; ratio held.
**Acceptance:** `test_coverage_never_regresses`, limper belt, golden AF/WTSD all green.

## T6 — W2-b pure helpers only (no behavior change — reviewer #5 atomicity)
**Files:** `backend/app/domain/personas_postflop.py`.
**Do:** add ONLY the pure helpers + their unit tests, no wiring into the decision path yet: `_draw_equity(draw, board)` (rule-of-4-and-2, street derived from `len(board)`: STRONG 0.36 flop / 0.18 turn; WEAK 0.16 / 0.08; river/len5 → not applicable, draw is NONE) and a `_value_commit_threshold(faced_frac)` returning `faced_frac / (1 + 2*faced_frac)`. No change to `sample_postflop_decision`.
**Done:** helpers exist + unit-tested; the full decision suite is BYTE-IDENTICAL (helpers unused → zero behavior change this commit).
**Acceptance:** `test_draw_equity_proxy` (values + street-from-board) + `test_value_commit_threshold` (0.429 at faced_frac=3, 1/3 at faced_frac=1) pass; existing suite unchanged.

## T7 — W2-b apply the commit/draw gate ATOMICALLY (directional, F\* dropped)
**Files:** `backend/app/domain/personas_postflop.py`.
**Do:** restructure the SPR-commit block (lines ~577-588) from the single uniform list-transform into: (1) resolve `e` — `1.0` for `_RUNG[bucket] ≥ OVERPAIR_TPTK` (made-hand bypass — keep the EXISTING zero-fold/agg-boost transform UNCHANGED, no draw damp, reviewer #6), else `_draw_equity(draw, board)`; (2) compute `threshold = _value_commit_threshold(faced_frac)`; (3) if `e ≥ threshold` → zero fold (value-committed); (4) else (below T1, draw side) → do NOT zero fold (existing price-aware fold merit stands) and damp the draw CALL/RAISE bonus by commitment `c` (B5b). Fold merit is left to the existing price machinery — **no forced-F\*** (owner decision). Note `faced_frac` is only defined on the facing branch; guard the unopened path (no fold entry → nothing to gate).
**Done:** made ≥OVERPAIR commit byte-identical; STRONG draw vs 3×-pot overbet can fold; naked WEAK draw stacks off less.
**Acceptance:** `test_madehand_commit_byte_identical`, `test_strong_draw_potcommitted_still_jams`, `test_strong_draw_vs_overbet_can_fold` (fold prob > 0 and > pot-committed case), `test_weak_draw_stops_stacking_off` all pass.

## T8 — W2-b fixture re-record (commit-path change moves the stream)
**Files:** same fixture set as T5.
**Do:** re-record whatever the commit/draw-gate change moves; add a W2-b docstring note. Bands frozen; ratio invariant held; limper `_WANT_*` shapes still fire.
**Done:** all three fixtures green on re-recorded values.
**Acceptance:** coverage + limper + golden green.

## T9 — roadmap check-off + verify sweep
**Files:** `docs/ai-dlc/roadmap/persona-realism.md`, `MEMORY.md`.
**Do:** mark W2-a / W2-b `[x]` with ✅ shipped notes once pass/fail actually passes. `./scripts/verify.sh` + `ruff check .` + typecheck-if-touched. Update MEMORY persona line: W2 shipped.
**Done:** full suite green, ruff clean, roadmap + memory updated.
**Acceptance:** `./scripts/verify.sh` green; ruff clean.

---

## Review dispositions (refuter + Codex Sol fan-in, folded 2026-07-24)
Both reviewers returned **REVISE**, no cross-reviewer conflict. All findings folded:
1. **`size_elasticity=0` crash + direction reversal** (both, HIGH) — FOLDED into T2: opt-in uses DIRECT exponent `SENSITIVITY * size_elasticity` (0=flat, higher=steeper); unset keeps legacy inverse. `0**-0.15 ZeroDivisionError` avoided. New elasticity-0 unit test.
2. **Continuous-price byte-identity risk** (Codex, HIGH) — DESCOPED: keep α buckets. T2 updated.
3. **T1 risk model** (Codex, MED) — SCOPED to a faced-price call-commit proxy via existing `faced_frac`; `threshold = faced_frac/(1+2·faced_frac)`; labeled heuristic not jam-solve. T6/T7.
4. **F\* conflation** (both, HIGH) — **owner decision: drop forced-F\***, directional own-action policy below T1. Spec W2-b rewritten; T7.
5. **Serial half-state** (both, MED) — T6 = pure helpers only (byte-identical); T7 = whole W2-b behavior atomically.
6. **Overpair-with-draw byte-identity** (Codex, MED) — made ≥OVERPAIR fully bypasses W2-b (e=1, no damp). T7.
7. **Non-executable pass/fails + `_draw_equity(street=None)`** (Codex, MED) — all pass/fails rewritten as seeded numeric inequalities; street derived from `len(board)`. Spec + T2/T3/T6/T7.
8. **Re-record masking** (refuter, MED) — per-persona byte-identity diff before overwrite. T5/T8 + spec Fixtures.
9. **Monotonicity confound** (refuter, LOW) — hold `stickiness` constant across base/high. T3.
