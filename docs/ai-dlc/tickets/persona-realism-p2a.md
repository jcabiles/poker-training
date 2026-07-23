# Tickets — P2a: Street-aware refactor + river polarization

> From `docs/ai-dlc/specs/persona-realism-p2a.md`. Wave DAG for `/parallel-waves`. One file = one owner.
> Fan-in each wave: fresh `refuter` (maker ≠ checker) + narrow verify. Stacks on `feat/persona-realism-p1`.

## Wave DAG
- **Wave 1** (foundation, byte-identical default → breaks nothing): Q1
- **Wave 2** (opt-in, parallel disjoint engine files): Q2a ‖ Q2b
- **Wave 3** (all tests + re-anchor, single owner of test files): Q3

Models: Q1 heavy-worker·opus · Q2a/Q2b implementer·sonnet · Q3 heavy-worker·opus. No Fable, no Terra.

---

### Q1 — `street` kwarg + river polarization *(backend/app/domain/personas_postflop.py)*
Add `street: Street | None = None` to `sample_postflop_decision` (import `Street` from `app.domain.spot`).
**Default None reproduces today's behavior byte-for-byte** — do NOT auto-derive from `len(board)`. When
`street is Street.RIVER`:
- Floor the **RAISE** action merit to `0.0` for a **non-bluff** made hand in `{MIDDLE_PAIR, TOP_PAIR,
  OVERPAIR_TPTK}` — in BOTH the facing `RAISE` entry (`:486-492`) and the matched `CHECK+RAISE` branch
  (`agg_action is RAISE`). Do NOT touch the `BET` action (thin river value bets stay legal).
- Floor the **CALL** merit to `0.0` for a bluff-cell hand (`AIR`/`ACE_HIGH`, draw NONE) facing a bet.
No new `rng` draw (flooring is a pre-normalize merit edit; action draw stays the first `rng.choices`).
**Done:** direct callers (no `street=`) byte-identical (existing `test_personas_postflop.py` still green after
Q1 alone); domain purity green; `ruff` clean. Owns only this file. Do NOT opt in any caller (that's Q2).

### Q2a — live loop opt-in *(backend/app/domain/table/play.py)*
Thread `state.street` from `bot_decision` (`:170`) → `_postflop_decision` (`:128`, add a `street` param) →
`sample_postflop_decision(..., street=street)` (`:132`). Postflop-only (the `:170` preflop early-return
guarantees street ∈ {flop,turn,river}).
**Done:** `play.py` passes `street`; imports/signature clean; `ruff` clean. Owns only this file. (Population
tests will drift — re-anchored in Q3, NOT here.)

### Q2b — estimator parity opt-in *(backend/app/domain/table/range_estimate.py)*
Pass `street=ctx.street` at the `sample_postflop_decision` call (`:278`). `_Ctx` already carries `.street`.
**Done:** estimator passes `street`; `ruff` clean. Owns only this file. (Non-negotiable parity fix — the
reveal feature must replay the polarized policy.)

### Q3 — tests + re-anchor *(test_personas_postflop.py, test_range_estimate.py, test_personas.py, test_coverage_baseline.py, test_limper_coverage_belt.py, test_mw_funnel_belt.py, backend/tests/data/coverage_baseline.json)*
- **⚠️ Thread `street` into the in-file harness (refuter F1 — HIGH):** `test_personas_postflop.py` has a
  DUPLICATE `_postflop_decision`/`_play_hand` helper (`:1012`) calling the sampler with NO `street=`. Thread the
  decision's street (derive from `len(board)`) into it so the in-file population/WTSD bands actually exercise
  river polarization — else the keystone ships untested by those bands.
- **New — default-off byte-identity (refuter F3):** use the `_CaptureWeights` capture-rng idiom (`:527-538`) to
  assert **exact normalized merit-weight dicts** are identical with `street=None` for MP/TP/OVERPAIR/AIR-CALL
  spots — stronger than `same_seed` action equality.
- **New — river polarization** (in `test_personas_postflop.py`): maniac river MP raise ≈0 (was ~38%), TP ≈0
  (~54%), OVERPAIR_TPTK raise ≈0; LAG/TAG one-pair river raise ≈0; air river CALL ≈0; **turn/flop behavior
  unchanged** (assert a TURN one-pair spot still raises → proves only River floors).
- **New — estimator parity** (in `test_range_estimate.py`): on a fixed river spot the estimator's recovered
  action distribution == the live policy's (both via capture rng, `street=River`).
- **Re-anchor** any population/belt band moved by the `play.py` opt-in (levers-first, in-file justification);
  re-record operational `coverage_baseline.json`; **report cumulative graded-coverage delta vs the immutable
  snapshot**. Re-verify empirically (2-3 suite runs); treat `test_persona_postflop_bands[lag/maniac]` as
  wall-clock-flaky (don't chase). Do NOT touch `coverage_baseline.persona-realism-start.json`.
- **Guardrail pins stay green untouched** — if monotonicity/α-ceiling/anti-sizing-tell/bluff-ordering/
  aggression-cap/domain-purity fails, STOP and report (real regression, not a re-anchor).
**Done:** `./scripts/verify.sh` → `BACKEND VERIFY OK`; `ruff` clean; polarization + parity tests green;
cumulative-delta reported.

---
## Fan-in (orchestrator, each wave)
`refuter` on the wave diff + narrow verify. Wave-3 gets a final refuter to confirm no re-anchor hides a
regression + that parity genuinely holds. Only verified + reviewed advances; commit per wave; PR at the end.
