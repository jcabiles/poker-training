# Spec — Phase 2d: Equity-Backed Range Advantage

> **STATUS: investigated → reverted → deferred to Phase 3.** Bounded Monte-Carlo over heuristic ranges does not recover a stable range-advantage signal (see the OUTCOME note in `../tickets/phase-2d-equity-backed.md` for the measured failure of all three metrics). The positional heuristic was retained. This spec is preserved as the design record + the plan to revive once solver tables exist.


> Delta spec for **Phase 2d** only. Builds on 2a/2b/2c. Replaces the positional+texture range-advantage *heuristic* inside the two flop graders (`grade_cbet`, `grade_vs_cbet`) with **real range-vs-range equity**, computed by the existing equity engine behind the unchanged `StrategyProvider`. Pays down the "not equity-backed" caveat repeated since 2a. STOP at the plan gate — no code until approved.

## Goal
Flop c-bet + vs-c-bet grading derive `range advantage` from the **actual equity of the aggressor's range vs the defender's range on the actual board**, not a positional rule. No new drill type, UI, migration, or signature change — a contained swap behind the provider (the architecture's whole point).

## Key decisions (perf + determinism + refuter fixes)
- **Range advantage is HAND-INDEPENDENT** (refuter blocker 1 fix + the conceptually-correct choice). Range advantage is a property of *the two ranges + the board* — NOT of hero's specific hole cards (the actual hand is already handled separately by `_hand_category`). So **dead = `set(board)` only**; hero's actual cards are NOT used in the equity. This (a) removes `hero_cards` from the computation and cache key entirely → no stale-cache-per-hand bug, and (b) lets the cache hit across every hero hand on the same board+ranges (big win for review/repeated archetypes).
- **Monte-Carlo range-vs-range, bounded.** Per-pair enumeration (combos² × runouts) is the perf bomb that got this deferred. Instead sample N≈**1000** triples `(hero_combo, villain_combo, runout)` uniformly (mutually disjoint + disjoint from the board), evaluate with the 2a `equity.py` 7-card evaluator, average → the aggressor's range equity in [0,1]. O(N), not O(combos²). **Pre-filter both ranges' combos against the board ONCE, before the loop** (no per-iter `combos_for_range`).
- **Empty-range guard → 0.5, NOT 0.0** (refuter blocker 2). The 2a `equity_vs_range` returns `0.0` on an empty villain range — that would map to `"villain"`. The new function must check `if not hero_combos or not villain_combos: return 0.5` BEFORE the loop (neutral), and must NOT delegate empty-handling to `equity_vs_range`.
- **Deterministic seed via a fixed digest** (refuter blocker 3). Seed a private `random.Random` from `int(hashlib.sha256(canonical.encode()).hexdigest()[:8], 16)` over a canonical `f"{'/'.join(board)}|{hero_range}|{villain_range}"` — NOT Python's salted `hash()` and NOT `sum(ord)` (which collides on character permutations). Mirrors the existing `srs.py` digest pattern.
- **Cached, bounded.** `functools.lru_cache(maxsize=256)` on a pure `_range_vs_range_equity(hero_range, villain_range, board_tuple, iters, seed)` (all hashable; hero_cards intentionally absent). 
- **Called once per grade.** `grade_*` runs only on `/drill/grade` (one human action). `_rebuild_postflop` (2c) builds spots but does **not** grade (confirmed — it only constructs candidates), so the review path stays cheap. ~1000 iters ≈ the equity-quiz cost (<~200ms); acceptable for a single call.
- **Graceful fallback.** If `hero_range`/`villain_range` is missing (defensive — built spots always set them), fall back to the positional `range_advantage` / `range_advantage_defender`. No crash, no behavior change for range-less spots.

## In scope
1. **`domain/postflop.py::range_vs_range_equity(hero_range, villain_range, board, iters=1000, seed=0) -> float`** (the cached, hand-independent core): pre-filter both ranges' combos against `set(board)` once; **return 0.5 if either filtered range is empty**; else MC over `iters` triples `(hero_combo, villain_combo disjoint, runout disjoint)` using `equity._best7`; win=1, tie=0.5; deterministic for `seed`. `lru_cache(maxsize=256)`-wrapped (args: ranges, `tuple(board)`, iters, seed).
2. **`domain/postflop.py::range_advantage_eq(aggressor_range, defender_range, board, seed) -> str`**: returns `"hero"|"villain"|"neutral"` (aggressor's view, matching the `range_advantage` contract consumed by `_merits`). Thresholds on `eq`: `eq >= HI → "hero"`, `eq <= LO → "villain"`, else `"neutral"`. `HI/LO` finalized in the build against the anchor equities (the refuter's analysis estimates A-high-dry ≈ 0.55–0.60 aggressor and 8♥7♥6♣ ≈ 0.42–0.47 aggressor, so ~0.53/0.47 should separate cleanly; the build will **print the measured equities** and pin thresholds with margin).
3. **`grade_cbet`**: compute `adv` via `range_advantage_eq(hero_range, villain_range, board, seed)` when both ranges are set; else the positional `range_advantage`. `_merits` and everything downstream are UNCHANGED (they consume the `adv` string).
4. **`grade_vs_cbet`**: the aggressor is the c-bettor (`villain_range`), the defender is hero (`hero_range`). Compute aggressor equity via `range_vs_range_equity(villain_range, hero_range, board, …)`; map to the defender-view label the grader expects (`"defender"|"aggressor"|"neutral"`): high aggressor equity → `"aggressor"`, low → `"defender"`. Fallback to `range_advantage_defender` when ranges are missing. `_merits_vs_cbet` UNCHANGED.
5. **Determinism seed helper** (`_adv_seed(board, hero_range, villain_range)`): `int(hashlib.sha256(f"{'/'.join(board)}|{hero_range}|{villain_range}".encode()).hexdigest()[:8], 16)` — fixed digest (NOT salted `hash()`, NOT `sum(ord)` which collides on permutations).

## Contract changes
- None to `Spot`, `spot_signature`, DB, or the provider interface. `EvaluationResult` shape unchanged. The positional `range_advantage` / `range_advantage_defender` remain (now the fallback path) and keep their tests.
- `rationale_tags`/`explanation` may note "equity-backed" but the structure is unchanged.

## Out of scope (deferred)
- Turn / river / check-raise-as-aggressor · multiway · solver tables · equity-backed grading of anything beyond the flop range-advantage signal (the hand-category merits stay heuristic) · mastery-gating · squeeze.

## Constraints
Live/simplified · grading stays behind the composite `StrategyProvider` · domain pure (no web/DB) · **bounded** equity (≤~1000 iters/grade) with its **own seeded RNG** + `lru_cache` · **deterministic** grading · no new migration · no new deps (`RUN-THESE-COMMANDS.md` target: none) · CSS unaffected.

## Verify-by
1. `pytest` green incl:
   - **`range_vs_range_equity`**: a nut-heavy range vs a weak range on a dry board → clearly >0.5; two identical ranges → ≈0.5 (±MC noise); deterministic for a fixed seed (two calls equal); **returns exactly 0.5 when a range is empty after board filtering** (not 0.0); a **perf guard** (one call < ~200ms at the iter cap); the test **prints the measured anchor equities** so threshold drift is visible in future refactors.
   - **`range_advantage_eq` anchors**: A-high dry board, preflop-raiser range vs caller range → `"hero"` (aggressor edge); low connected board (8♥7♥6♣) → `"villain"`/`"neutral"` (defender catches up). Same boards as the 2a/2b positional anchors, now equity-driven.
   - **graders unchanged behavior**: the 2a/2b anchor tests still pass with equity-backed `adv` — strong hand bets/raises, air on a dry aggressor board checks/folds, etc. (retune `HI/LO` if an anchor flips; document the final thresholds).
   - **determinism**: grading the same spot twice yields identical `EvaluationResult` (freqs + EVs).
   - **fallback**: a spot with `hero_range=None` grades via the positional path without error.
   - 2a/2b/2c + preflop suites all still green; `spot_signature` byte-identical.
2. Backend boots; a flop grade returns within budget; all existing modes/quizzes/review unaffected.
3. Frontend unchanged; `vite build` + `tsc` clean.
4. `scripts/verify.sh` green (existing probes; grading still works end-to-end).
