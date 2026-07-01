# Tickets — Phase 2d: Equity-Backed Range Advantage

Spec: `docs/ai-dlc/specs/phase-2d-equity-backed.md`. 2 tickets — surgical (almost entirely `domain/postflop.py`, behind the unchanged provider). All 3 refuter fixes baked into the spec (hand-independent equity → no stale cache; empty→0.5; sha256 seed).

> **OUTCOME: NOT SHIPPED — investigated, then reverted; deferred to Phase 3 (solver).** Building T1 surfaced that equity-backed range advantage is not reliably computable from bounded Monte-Carlo over the heuristic ranges. Three metrics were measured and all failed:
> - **mean range-vs-range equity** — flat ~0.49–0.52 on every board (wide-vs-condensed ranges average to ~0.5); no signal.
> - **strong-combo share** — range-width-biased; rated A♠K♦2♣ as *defender* edge (wrong) because the wide PFR range has many whiffed combos.
> - **top-of-range strength** — width-robust but noisy/unstable at usable sample sizes (a run gave A-K-Q → *defender* and 7-6-2 → *aggressor*, both backwards) and cost ~300–500ms/grade.
>
> Root cause: range advantage is an equity-*distribution* + EV property solvers compute over the full game tree; a flop MC over simplified ranges can't recover it stably. The **positional+texture heuristic was kept** (sound, stable, instant, passes all anchors). The equity engine stays in use for the quizzes. True equity/solver-backed range advantage → **Phase 3 solver tables** (the swappable `StrategyProvider` already supports the swap). User decision (2026-06-29): revert + defer.
>
> Kept from this session (unrelated, good): the **FeedbackPanel** polish (per-action bet size shown + space before "best").

## DAG / waves
```
T1 ─ T2
```
- W1: **T1** (equity core + grader wiring + calibration, all in postflop.py)
- W2: **T2** (verify + docs)

---

### T1 — Equity-backed range advantage
In `domain/postflop.py`:
- `_adv_seed(board, hero_range, villain_range)` — sha256-digest int (not salted `hash`/`sum(ord)`).
- `range_vs_range_equity(hero_range, villain_range, board, iters=1000, seed=0)` — `lru_cache(maxsize=256)`; pre-filter both ranges' combos vs `set(board)` ONCE; **return 0.5 if either filtered range empty**; MC over `iters` `(hero_combo, villain_combo, runout)` triples via `equity._best7`; deterministic per seed.
- `range_advantage_eq(aggressor_range, defender_range, board, seed) -> "hero"|"villain"|"neutral"` — threshold `eq` on tuned `HI/LO`.
- Wire `grade_cbet` (aggressor = hero_range) and `grade_vs_cbet` (aggressor = villain_range; map high→`"aggressor"`, low→`"defender"`) to use the equity label when both ranges are set; **fallback** to the positional `range_advantage` / `range_advantage_defender` when missing. `_merits` / `_merits_vs_cbet` UNCHANGED.
- **Calibrate** `HI/LO`: print the measured anchor equities, pin thresholds with margin so the 2a/2b anchors keep their labels.
- **Owns:** `domain/postflop.py`, `tests/test_postflop.py`.
- **Done when:** equity core tests pass (nut>weak; identical≈0.5; empty→0.5; deterministic; perf <~200ms; printed anchor equities); `range_advantage_eq` anchors (A-high-dry→`hero`, 8♥7♥6♣→`villain`/`neutral`); **all existing 2a/2b grader anchors still pass** with equity-backed `adv`; grading is deterministic (same spot twice → identical result); `hero_range=None` falls back without error; positional functions + their tests retained.

### T2 — Verify + docs
- **Owns:** `scripts/verify.sh` (confirm grading still end-to-end; no probe change needed), `README.md`, roadmap/ticket status, project memory.
- **Depends:** T1.
- **Done when:** full `pytest` green; `verify.sh` → `BACKEND VERIFY OK`; `vite build`+`tsc` clean (frontend untouched); live Playwright: a flop spot still grades sanely (now equity-backed) with no console errors; docs updated.

---

## Notes
- Riskiest: **T1 calibration** — real range-vs-range equities cluster near 0.5; if an anchor refuses to separate, widen iters or accept `neutral` and let `_merits` carry it (document). The threshold choice is empirical, made against printed equities, not guessed.
- No `Spot`/signature/DB/UI/contract change. Turn/river/check-raise-as-aggressor stay deferred (2e+).