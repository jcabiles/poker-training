# N4a — Barrel sizing grades · ticket DAG

Spec: `docs/ai-dlc/specs/n4a-barrel-sizing-grades.md` · Contracts: `docs/ai-dlc/contracts/n4a-barrel-sizing-grades.md`
**Backend-only — no migration, no schema, no FE (reuses N3 plumbing).** Verify: `./scripts/verify.sh` · `cd backend && ruff check .` · `cd frontend && npm run typecheck && npm run build` (FE unchanged, must stay green).

| # | Ticket | Owned files | Depends | Done-condition |
|---|--------|-------------|---------|----------------|
| **T1** | Correct barrel sizes + street-aware canonical-bet gate | `app/domain/table/sizing.py`, `app/domain/table/grade_map_postflop.py`, `backend/tests/test_grade_map_turn_river.py` | — | `POSTFLOP_BET_FRACS` (flop 0.33/0.75, turn 0.5/0.75, river 0.5/1.0); `_barrel_spot` uses it; `_is_canonical_bet`/`_check_bet`/`_check_bet_call` street-aware; **turn barrel at 0.5 pot → river still maps** (integration test); mock helpers updated; `verify.sh` green |
| **T2** | Additive barrel/c-bet sizing verdict | `app/domain/postflop.py`, `backend/tests/test_postflop.py` | T1 | `_bet_sizing_verdict` (higher-merit BET = OPTIMAL, other = ACCEPTABLE; **None when both BET merits ≤0** — no verdict beside a bet-blunder); populated in `grade_cbet`/`grade_turn_barrel`/`grade_river_barrel`; **`correctness`/`per_action`/`ev_bb` byte-unchanged** (R3 c-bet + pins green); purity green |
| **T3** | Barrel two-size display + parity | `app/services/sim_session.py`, new `backend/tests/test_sim_postflop_sizing.py` | T1, T2 | `_is_turn/river_barrel_node` + `_hero_turn/river_barrel_legal_actions` from `POSTFLOP_BET_FRACS`; **distinctness fallback (collapse→one) + gate on `map_*_barrel` non-None**; e2e (barrel hand → `sizing_correctness` persists) + **short-stack display==grade parity** |
| **T4** | Verify + design-review | — (review only) | T1–T3 | `verify.sh`+ruff+typecheck+build green; design-review the barrel two-size UI + the sizing sub-note (now also on the flop c-bet) both themes, coach mode |

## Acceptance highlights
- **T1** — flop entry stays 0.33/0.75 (no flop-c-bet size change). The canonical-bet gate is the refuter-HIGH fix: without it, a 0.5-pot turn barrel orphans the river mapper. CALL leg untouched (signature-safe). Re-run `test_postflop.py`/`test_signature.py`; adjust ONLY barrel assertions tied to old 0.33/0.75 numerics (directional expectations unchanged).
- **T2** — additive only. `sizing_correctness` derives from the two BET evals' merit/frequency (verified distinct per hand by the refuter). None when hero didn't bet, single-size, or both bet merits clamp to 0. The `grade_cbet` retrofit means the flop c-bet now shows a "· size" sub-note too (intended consistency) — its action verdict must not move.
- **T3** — do NOT blind-mirror `_hero_cbet_legal_actions` (it lacks the fallback + grading-gate). Same fraction source + pot + non-None gate + fallback as the graded path ⇒ parity by construction. Short-stack test proves one-size-both-sides.
- **T4** — maker≠checker design-reviewer; default is real-play, so flip to Coach; reach a turn/river barrel to see two sizes + the sub-note.

## Sequencing
**T1 → T2 → T3 → T4**, mostly sequential (T2 needs T1's correct graded sizes; T3 needs both). `grade_map_postflop.py` (T1) and `postflop.py` (T2) and `sim_session.py` (T3) are distinct files but logically chained. Small-medium, backend-only → **single implementer/heavy-worker sequential** fits; verify hard at each step (hash pins + the canonical-bet-gate regression).
