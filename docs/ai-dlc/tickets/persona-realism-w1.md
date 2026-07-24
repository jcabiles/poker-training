# Tickets — persona-realism W1

Spec: `docs/ai-dlc/specs/persona-realism-w1.md`. All on ONE branch
`feat/persona-realism-w1`, three serial commits (shared hotspot
`personas_postflop.py` = single owner ⇒ NO parallelism), ONE PR at end.

DAG: **T1 (W0-a helper, already merged) → A → B → C**. A/B/C are serial (same
file), each commit leaves the suite green.

---

### A — River one-pair BET floor (MIDDLE_PAIR only)
- **Owns:** `backend/app/domain/personas_postflop.py`,
  `backend/tests/test_personas_postflop.py`.
- **Do:** add `_RIVER_BET_FLOOR = (MIDDLE_PAIR,)`; floor the unopened river BET
  merit to 0.0 for that bucket in the non-bluff aggressive path. **SPLIT the named
  test** `test_river_check_raise_branch_floored_bet_untouched` — MIDDLE_PAIR
  unopened river BET now asserts `P(BET)==0`; TOP_PAIR + OVERPAIR keep the
  byte-identical-to-streetless assertion (theory H1; sanctioned unit-assertion edit).
- **Acceptance:** MIDDLE_PAIR unopened river BET → `P(BET)==0`; TOP_PAIR +
  OVERPAIR_TPTK river BET → `P(BET)>0`; MIDDLE_PAIR flop/turn BET unchanged.
- **Done-condition:** `cd backend && source .venv/bin/activate && python -m pytest
  -q tests/test_personas_postflop.py` green incl. the split assertions; ruff clean.
- **No-gos:** no raise-floor edit; no band re-anchor; MIDDLE_PAIR only.

### B — faced_frac increment fix (ENGINE-ONLY) (depends: W0-a helper)
- **Owns:** `backend/app/domain/personas_postflop.py`,
  `backend/app/domain/table/play.py`,
  `backend/tests/test_personas_postflop.py`.
  (**NOT** `range_estimate.py` — estimator numerator is structurally 0, fix inert;
  **NOT** the harness wrapper — separate path, stays legacy → bands byte-identical.)
- **Do:** append trailing `latest_aggressor_contribution_bb` param (default None =
  legacy formula, **no `*` separator**); new-formula branch on the exact
  pre-aggression pot; fix the backwards comment (OVERSTATES, drop "Epic-4"); wire
  the engine via `pot_before_current_aggression(state.action_history,
  state.street)`. Estimator + harness UNTOUCHED.
- **Acceptance:** existing faced_frac/fresh-raiser tests byte-identical; NEW
  self-re-raise fold-less test (straddle spot, exact weights); NEW back-raise test;
  NEW fresh-raise byte-identity test; NEW engine-wiring assertion.
- **Done-condition:** `python -m pytest -q tests/test_personas_postflop.py`;
  full `python -m pytest -q` (879 baseline) + domain-purity + node-trace green;
  ruff clean.
- **No-gos:** no fresh-aggression change; no estimator/harness edit; no rng-draw
  insertion; no sizing edit.

### C — Multiway made-value tightening
- **Owns:** `backend/app/domain/personas_postflop.py`,
  `backend/tests/test_personas_postflop.py`.
- **Do:** add `_MW_VALUE_DAMP=0.8` / `_MW_VALUE_CAP=3` /
  `_MW_VALUE_BUCKETS=(TOP_PAIR, MIDDLE_PAIR)`; apply the capped geometric damp to
  made-value agg_merit in the unopened non-bluff path.
- **Acceptance:** monotone test via EXACT captured P(BET) weights (not sampled
  counts) non-increasing over opponents 1→4, plateau ≥4; HU byte-identical;
  node-trace multiway spot well-formed. Gated `agg_action is ActionType.BET`.
- **Done-condition:** `python -m pytest -q tests/test_personas_postflop.py` green
  incl. monotone + HU-identity tests; ruff clean.
- **No-gos:** no move at HU; no 5+way magnitude; direction only (no level assertion).

### D — Whole-wave verify + PR
- **Do:** full `ruff check . && pytest -q` green; open ONE PR
  `feat/persona-realism-w1` with the three commits; mark W1-a/b/c `[x]` in the
  roadmap ONLY after the PR's pass/fail checks actually pass (no roadmap edits in
  the slice commits — coverage-delta discipline).
- **Done-condition:** PR open, CI green, roadmap slice boxes checked.
