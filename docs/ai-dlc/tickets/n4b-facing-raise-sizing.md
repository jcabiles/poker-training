# N4b — facing-raise sizing grades · ticket DAG

Spec: `docs/ai-dlc/specs/n4b-facing-raise-sizing.md` · Contracts: `docs/ai-dlc/contracts/n4b-facing-raise-sizing.md`
**Backend-only — no migration, no schema, no FE (reuses N3 plumbing).** Verify: `./scripts/verify.sh` · `cd backend && ruff check .` · `cd frontend && npm run typecheck && npm run build` (FE unchanged, must stay green).

| # | Ticket | Owned files | Depends | Done-condition |
|---|--------|-------------|---------|----------------|
| **T1** | ATOMIC: `FACING_RAISE_MULTS` + two-RAISE-leg emission + grader big-leg build | `app/domain/table/sizing.py`, `app/domain/table/grade_map_postflop.py` (`_faced_bet_spot` only), `app/domain/postflop.py` (RAISE-eval builds only), `backend/tests/test_grade_map_turn_river.py`, `backend/tests/test_postflop.py` | — | Const per spec D1 (check_raise flop-only 2.5/3.5, raise 2.5/3.0); `_faced_bet_spot` emits two legs (clamp→collapse rule) + new `call_amt` param (default `bet`, existing callers byte-identical); all 4 graders build RAISE eval from **BIG leg** (`max`), not first-leg `next(...)`; **turn/river `per_action` RAISE `size_bb` unchanged at `round(3*bet,1)`** (regression test); pinned tests updated; `verify.sh` green |
| **T2** | Texture-overlay `_raise_sizing_verdict` | `app/domain/postflop.py`, `backend/tests/test_postflop.py` | T1 | Pure helper per spec D4: None unless RAISE + two distinct legs + chosen merit >0; dry→small optimal / wet→big optimal / medium→both acceptable; nearest-leg match on `decision.size_bb`; wired into all 4 facing graders' `EvaluationResult`; **action `correctness`/`ev_bb` byte-unchanged**; purity green |
| **T3** | Flop facing mappers + dispatcher widening | `app/domain/table/grade_map_postflop.py` (new mappers), `app/domain/table/grade_map.py`, new `backend/tests/test_grade_map_flop_facing.py` | T1 | `map_flop_vs_cbet` (hero-checked→check_raise mults, else raise mults) + `map_flop_vs_check_raise` (sizing base `raise_to`, **`CALL.min_bb == raise_to − cbet`** — required test); HU + canonical gates, else None; dispatcher = first non-None of cbet→vs_cbet→vs_check_raise; multiway/non-canonical still None; signature pins green |
| **T4** | Simulate two-size display + parity | `app/services/sim_session.py`, `backend/tests/test_sim_postflop_sizing.py` | T1, T3 | `_is_facing_raise_node` gated on mapper non-None; `_facing_two_sizes` from `FACING_RAISE_MULTS` + same faced amount/rounding/clamp as mapper; wired ahead of generic fallback, preflop branch untouched; e2e facing hand → two sizes offered → `sizing_correctness` persists; **short-stack displayed==graded parity** |
| **T5** | Practice onto shared constant | `app/domain/scenarios.py`, any drill/scenario test asserting `3*cbet` | T1 | `build_vs_cbet_spot` → 3.5× (check_raise big); `build_check_raise_spot` → 3.0× via const (**value unchanged**, incremental `call_amt` convention intact); drills stay single-size; tests green |
| **T6** | Verify + design-review | — (review only) | T1–T5 | `verify.sh`+ruff+typecheck+build green; refuter-on-diff; design-review (coach mode, both themes): two raise buttons at a facing node + "size:" sub-note on recap |

## Acceptance highlights
- **T1 is the refuter-HIGH-2 fix**: mapper two-leg emission and grader big-leg build are ONE change — never split. Big leg = 3.0× on turn/river keeps `per_action` byte-identical.
- **T3 carries refuter-HIGH-1**: the incremental CALL leg for the check-raise mapper (`raise_to − cbet`), matching `scenarios.py:575`'s convention — pot-odds, EV, and `faced_bet_bucket` all depend on it.
- **T2's divergence from N4a's merit-based verdict is intentional and documented** (spec D4) — texture-rule overlay because no per-size raise merits exist.
- **T4 mirrors `_barrel_two_sizes` discipline exactly** — same fraction source, mapper-non-None gate, collapse fallback.

## Sequencing
**T1 → T2 → T3 → T4 → T5 → T6** (T5 can slot anywhere after T1). File overlaps (`postflop.py` T1/T2, `grade_map_postflop.py` T1/T3) make this a sequential single-agent build, not waves.
