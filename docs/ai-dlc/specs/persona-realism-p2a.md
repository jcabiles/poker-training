# Spec — P2a: Street-aware refactor + river polarization (THE keystone)

> Slice of `docs/ai-dlc/roadmap/persona-realism.md` (NOW slice P2a, W2). Reference: doc-12 §2.4/§9.2.
> **Stacks on `feat/persona-realism-p1`** (needs A1's `_CALL_BASE[AIR]`=0.08 + the re-anchored bands). One slice → one PR.

## Goal (one line)
Thread a `street` argument through the postflop sampler so the **river is polarized** — medium made hands
(one-pair class) never RAISE, air never CALLs — fixing M2+M7 ("maniac over-calls / raises one pair on the
river") for **all six personas**, with a default that keeps every existing caller **byte-identical** and the
range estimator kept in **parity** with the live policy.

## Files to touch (exact — one owner each)
| File | Change | Owner ticket |
|---|---|---|
| `backend/app/domain/personas_postflop.py` | add `street` kwarg + river polarization (default byte-identical) | Q1 |
| `backend/app/domain/table/play.py` | live loop opts in — pass `state.street` at the sampler call | Q2 |
| `backend/app/domain/table/range_estimate.py` | estimator opts in — pass `ctx.street` at `:278` (parity) | Q2 |
| `backend/tests/test_personas_postflop.py` | default-off byte-identity + river-polarization tests | Q3 |
| `backend/tests/test_range_estimate.py` | live-vs-estimator river parity test | Q3 |
| `backend/tests/{test_personas.py, test_coverage_baseline.py, ...}` + `coverage_baseline.json` | re-anchor bands + re-record (opt-in moved the stream) | Q4 |

## The change

### Q1 — `street` kwarg + river polarization *(personas_postflop.py)*
- Add `street: Street | None = None` (import `Street` from `app.domain.spot` — already the source of
  `ActionType`/`Card`/`LegalAction`, so domain purity holds). **Default `None` = today's behavior exactly** —
  do NOT auto-derive street from `len(board)` (that would break byte-identity for the ~16 direct callers).
- When `street is Street.RIVER`, apply polarization to the **RAISE action merit only** (betting a medium hand
  is fine — a thin value bet; only *raising* it is off-archetype):
  - For a **non-bluff** made hand in **{MIDDLE_PAIR, TOP_PAIR, OVERPAIR_TPTK}**, floor the RAISE merit to
    **0.0** in BOTH the facing branch (the `RAISE` entry, `:486-492`) and the matched-with-option branch
    (`CHECK+RAISE`, where `agg_action is RAISE`). Leave the `BET` action (`CHECK+BET`) untouched. **Boundary
    decision (Codex-Sol F7): OVERPAIR_TPTK IS floored** — river raises come only from `TWO_PAIR_PLUS+` or the
    bluff cell (matches the north-star; a TPTK river raise is thin value that only folds out worse).
    **Known coarse compromise (refuter F2):** `OVERPAIR_TPTK` MERGES a bare overpair (higher equity, a
    borderline-legit polarizing raise for a maniac/LAG) with TPTK — the merged bucket can't distinguish them
    without the kicker/relative-nut split, which is **N4 (NEXT)**. Flooring the whole rung is the defensible
    coarse call under that constraint; the finer overpair-keeps-raising treatment is explicitly deferred to N4.
  - **Air CALL ≈0 on the river:** for a bluff-cell hand (`AIR`/`ACE_HIGH`, draw NONE — always NONE on the
    river) facing a bet, floor the CALL merit to **0.0** (air folds or bluff-raises, never calls). This is the
    river-specific gate P1's A1 deliberately deferred.
- **Do NOT** add any new `rng` draw — the action draw stays the FIRST `rng.choices` (range_estimate + capture
  rngs key on that). Flooring is a merit-value change before the existing normalize/choices, nothing else.
- **Ordering (refuter F4):** apply the river floor to the base `entries` merits **before** the SPR-commit boost
  pass (`:508-521`) — a floored 0 survives `0 × _COMMIT_AGG_BOOST = 0`. State this so a future edit to either
  mechanism can't silently break the "0×3=0" invariant.

### Q2 — live loop + estimator opt-in *(play.py + range_estimate.py)*
- `play.py`: thread `state.street` from `bot_decision` (`:170` scope) → `_postflop_decision` (`:128`) →
  `sample_postflop_decision(..., street=street)` (`:132`). Postflop only (guarded by the existing
  `state.street is Street.PREFLOP` early-return at `:170`, so street is always flop/turn/river here).
- `range_estimate.py`: pass `street=ctx.street` at the `:278` call (`_Ctx` already carries `.street`). This is
  the **non-negotiable parity fix** (doc-12 §6.3 / Codex-Sol F1): the estimator replays the SAME polarized
  policy, so the villain-range reveal (R1) reads the true river distribution, not the stale streetless one.

### Q3 — tests *(test_personas_postflop.py + test_range_estimate.py)*
- **⚠️ Thread `street` into the in-file closed-loop harness (refuter F1 — HIGH):** `test_personas_postflop.py`
  has its OWN duplicate `_postflop_decision`/`_play_hand` helper (`:1012`) that calls `sample_postflop_decision`
  **without** `street=` — separate from `play.py`'s real path. Left as-is, the in-file population/WTSD bands run
  STREETLESS and never exercise river polarization (the keystone could ship untested by those bands). Thread the
  decision's street (derive from `len(board)`) into that local helper so the closed-loop bands measure the
  polarized behavior. (The coverage/limper/mw-funnel belts already import the real `play.py` path, so Q2a
  covers them.)
- **Default-off byte-identity (refuter F3 — stronger idiom):** use the `_CaptureWeights`/`_exact_dist` capture-rng
  idiom (`:527-538`) to assert the **exact normalized merit-weight dicts are identical** with `street=None` vs
  the pre-P2a code, for MIDDLE_PAIR/TOP_PAIR/OVERPAIR_TPTK/AIR-CALL spots — not just `same_seed` action equality
  (which can coincide even if weights differ).
- **River polarization:** maniac river MIDDLE_PAIR raise-freq ≈0 (was ~38%), TOP_PAIR ≈0 (was ~54%),
  OVERPAIR_TPTK raise ≈0; LAG/TAG one-pair river raise ≈0; river raises only from `TWO_PAIR_PLUS+`/bluff-cell;
  air river CALL ≈0. Turn/flop behavior unchanged (assert a TURN one-pair spot still raises → proves only
  `street=River` floors).
- **Estimator parity:** on a fixed river spot, the estimator's recovered action distribution
  (`_postflop_action_dist` via the capture rng) **equals** the live policy's distribution (same capture on
  `sample_postflop_decision(..., street=River)`). This is the R1-truthfulness guarantee.

### Q4 — re-anchor *(bands + coverage)*
Opting in `play.py` changes villain river play → the population harness stream shifts. Re-anchor moved bands
(levers-first, in-file justification), re-record the **operational** `coverage_baseline.json`, and **report
the cumulative graded-coverage delta vs the immutable `coverage_baseline.persona-realism-start.json`**. Note:
the ONE authoritative combined population re-anchor is **W5** (after P4) — P2a's re-record is operational (CI
green) + cumulative-delta reported, not the final anchor.

## Out of scope (P2a)
- No scare-card term / bluff-mass decay / give-up (P2b). No turn polarization (only river). No stickiness
  split (P3). No preflop kwargs (P4). No `_FOLD_BASE`/price-logic change. No new merit tables.
- No grader touch (`grade_map*`, `postflop.py` graders, `spot_signature()`, `TAXONOMY_VERSION` frozen).
- No M4/kicker split to resolve the OVERPAIR boundary — it's a coarse policy gate (decision made above).

## Constraints (inherited invariants — doc-12 §6.3)
- Domain purity; results freq+EV; strategy in content data (this is engine mechanics, shared — no persona
  numbers added).
- **Action draw stays the FIRST `rng.choices`** — no new randomness; flooring is pre-normalize merit edits.
- **Default = today's behavior** (mirror `is_aggressor=False`) until the live loop/estimator opt in.
- Pins stay green: monotonicity, α-ceiling, anti-sizing-tell, bluff-ordering, aggression-cap, domain-purity.
  (River flooring touches RAISE/air-CALL merit on the river only — verify the flop/turn-calibrated pins,
  which key on non-river spots, are untouched.)

## Verify-by (end-to-end)
1. **Default-off:** `test_personas_postflop.py` byte-identical for callers that pass no `street=` (verified: no
   `street=` at the ~16 direct call sites).
2. **Street-on (via play.py AND range_estimate.py):** maniac river MP raise ≈0 (was 38%), TP ≈0 (was 54%),
   OVERPAIR_TPTK raise ≈0, LAG/TAG one-pair river raise ≈0, air river call ≈0 (regenerate §9.2 dist);
   **estimator-parity test green** (recovered river dist == live river dist).
3. `./scripts/verify.sh` → `BACKEND VERIFY OK`; `ruff check .` clean; bands re-anchored + `coverage_baseline.json`
   re-recorded + cumulative-delta reported vs the immutable snapshot.
