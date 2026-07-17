# N3 — Preflop sizing grades · ticket DAG

Spec: `docs/ai-dlc/specs/n3-preflop-sizing-grades.md` · Contracts: `docs/ai-dlc/contracts/n3-preflop-sizing-grades.md`
**Backend + migration + FE.** Verify: `./scripts/verify.sh` · `cd backend && ruff check .` · `cd frontend && npm run typecheck && npm run build`.

| # | Ticket | Owned files | Depends | Done-condition |
|---|--------|-------------|---------|----------------|
| **T1** | Schema + migration | `app/domain/evaluation.py` (additive field), `app/db/models.py`, `backend/alembic/versions/0011_*.py` | — | `EvaluationResult.sizing_correctness` + `SimDecision.sizing_correctness` (nullable); migration `0011` up/down clean, existing rows read back unchanged; `verify.sh` green |
| **T2** | Grader fix + sizing verdict | `app/domain/grading.py`, `backend/tests/test_grading.py` | T1 | Eval-build emits one `ActionEval` per legal RAISE (kills the `sizes` collision) + `_match()` by nearest size; sizing verdict (smallest raise = optimal, bigger = acceptable, else null); **17 existing tests byte-green** + new strict-superset, standard-vs-shove direction, two-RAISE-match tests; domain purity green |
| **T3** | Two-size injection + persistence | `app/services/sim_session.py`, `app/schemas/simulate.py` | T1, T2 | `_preflop_two_sizes` helper (+ short-stack single-RAISE fallback); **graded-spot rewrite in `apply_hero_action`** (RFI/VS_RFI/BLIND_DEFENSE only) + display path `_hero_legal_actions`; write `sizing_correctness`; `_grade_view`+`GradeView` field; **sim-level e2e test: RFI hand → `sizing_correctness` persists**; chart/Practice assert single-RAISE |
| **T4** | FE two-raise UX + verdict display | `frontend/src/api/types.ts`, `src/lib/decisions.ts`, `src/components/simulate/SimActionBar.tsx`, `SimRecap.tsx`, `SimTable.tsx` | T3 | `GradeView` mirror; RAISE two-size branch + new keyboard key (not F/C/R/K/B/V); both raises reachable; recap/badge show sizing sub-note in coach mode; typecheck+build green |
| **T5** | Verify + design-review | — (review only) | T1–T4 | `verify.sh`+ruff+typecheck+build green; **N1 dashboard denominator byte-unchanged** assert; design-review two-raise UI + sizing verdict both themes |

## Acceptance criteria highlights
- **T1** — additive nullable column only; migration head 0010→0011; `down` drops the column; no backfill. `EvaluationResult` new field defaults `None` (Practice/non-raise unaffected).
- **T2** — the collision fix is BOTH sides: eval-build iterates `spot.legal_actions` (one eval per RAISE with its `size_bb`) AND `_match()` picks nearest size. When ≤1 RAISE legal, output is byte-identical to today's `next(...)` (Practice + 4-bet+). Sizing verdict is self-contained (reads `spot.legal_actions`: hero matched smallest raise → OPTIMAL, bigger → ACCEPTABLE, single/non-raise → None). Stays pure.
- **T3** — the **graded-spot rewrite lives in `apply_hero_action`** (after `map_decision_point`, before `evaluate`), NOT in `map_preflop`/`build_spot` (keeps chart + Practice single-RAISE). Same `_preflop_two_sizes` helper feeds display + graded (parity). Fallback to single RAISE when sizes can't be made distinct within `[min_bb, eff_bb]`. The e2e test must play a real RFI hand through `apply_hero_action` and assert the persisted `sizing_correctness` — proving the feature engages beyond unit tests (refuter HIGH).
- **T4** — new raise key distinct from `F/C/R/K/B/V`; label "Raise small/big ${bb}bb"; both mouse + keyboard reachable. Sizing sub-note additive, tone via `tierOf`, gated by N2 coach mode.
- **T5** — assert `street_report` `total_decisions`/`graded` numerically identical on a fixed DB before/after; design-review both themes.

## Sequencing
Backend is a mostly-sequential chain: **T1 → T2 → T3 → T4 → T5**. T2 and T3 both depend on T1's `EvaluationResult` field; T3 depends on T2's grader output; T4 depends on T3's `GradeView` field. `sim_session.py` (T3) is a single-owner hotspot. **Limited parallelism** — a single implementer sequential, or a thin wave (T1 alone → T2 → T3 → T4 → T5), fits better than a wide fan-out. Migration + Practice-shared grader = verify hard at each step.
