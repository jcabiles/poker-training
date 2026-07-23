# Tickets — P1: Persona correctness patch

> From `docs/ai-dlc/specs/persona-realism-p1.md`. Wave DAG for `/parallel-waves`. One file = one owner.
> Fan-in gate each wave: fresh `refuter` (maker ≠ checker) + `./scripts/verify.sh` green + `ruff` clean.

## Wave DAG
- **Wave 1** (parallel — disjoint source files): T1, T2, T3, T4
- **Wave 2** (after content settled): T5
- **Wave 3** (after all source + validator): T6

Model/agent per ticket: T1 implementer·sonnet · T2 heavy-worker·opus · T3 mechanic·sonnet ·
T4 implementer·sonnet · T5 implementer·sonnet · T6 heavy-worker·opus. **No Fable, no Terra** (domain
logic/content, not agentic tooling).

---

### T1 — B1 station premium unopened *(content/personas/calling_station.json)*
Replace the `fold` leg in BOTH `unopened` premium mixes (`AA, KK, AKs`) with `limp`
(`{ "raise": 0.5, "limp": 0.5 }`, zero fold weight).
**Done:** grep shows no `fold` weight in any station `unopened` mix; a test asserts station never folds
`AA/KK/AKs` unopened. Owns only this file.

### T2 — maniac bundle: M3 + N4/N5 + N3 *(content/personas/maniac.json)*
*(M1 aggression edit DROPPED from P1 — refuter F1; do NOT touch `postflop.aggression`, leave it 15.0.)*
- **M3:** delete `limp` mix from every `unopened` node except `SB`.
- **N4/N5:** `sizing.threebet_mult` 5.5 → 3.3.
- **N3 (behavioral rebuild, refuter F4):** rebuild `vs_4bet` (+ modestly `vs_3bet`). LAG vs_4bet
  (`content/personas/lag.json`) = `QQ+, AKs` shove + `A5s` partial. A plain combo-superset is ALREADY true and
  is NOT the fix — you must make maniac jam **lighter + trappier**: (a) add ≥3 `5bet_shove` bluff combos LAG
  never shoves (e.g. `A3s, A2s, 55, 66` at partial weight); (b) split `AA`/`KK` out of the pure-shove `QQ+`
  into a partial `call` (trap) leg. No cross-mix combo overlaps in any node.
**Done:** `postflop.aggression` unchanged (15.0); no non-SB unopened limp mix; `threebet_mult == 3.3`; a test
proves (a) ≥3 maniac `5bet_shove` combos with zero LAG shove weight AND (b) nonzero maniac AA/KK `call` weight.
Owns only this file. **Report the preflop mixes you changed** (for T6's re-anchor). Expect
`test_limper_coverage_belt.py`/baseline drift — re-anchored in T6, NOT here.

### T3 — M3 lag *(content/personas/lag.json)*
Delete the `limp` mix (`limp 0.7 / fold 0.3`) from every `unopened` node except `SB`.
**Done:** no non-SB unopened limp mix in lag; `ruff`/schema load clean. Owns only this file.

### T4 — A1 shared air-call base *(backend/app/domain/personas_postflop.py)*
`_CALL_BASE[StrengthBucket.AIR]` 0.25 → 0.08. Update the adjacent calibration comment to note the
street-neutral base-drop rationale + that the river-zero gate is deferred to P2a. **No river/street logic.**
**Done:** value is 0.08; domain-purity test green; `personas_postflop.py` imports unchanged. Owns only this
file. (Expect `test_personas_postflop.py` + population-band deltas — those are re-anchored in T6, NOT here.)

### T5 — N2 overlap validator *(backend/tests/test_content.py; may edit packs for residual overlaps)*
Add `test_no_overlapping_combos_within_node`: for every pack × preflop node, expand each mix's combos and
assert the sets are pairwise-disjoint; include a synthetic overlapping pack the validator **rejects**. Fix
any residual real overlaps surfaced in the packs (sole owner of packs at this wave).
**Done:** validator passes on all six real packs; rejects the synthetic overlap; `verify.sh` green for
`test_content.py`. **If it edits any pack to remove a residual overlap, list the exact combos removed** — those
are baseline-moving (refuter F5) and must feed T6's re-anchor justification.

### T6 — re-anchor bands + baselines *(test_personas_postflop.py, test_coverage_baseline.py, test_personas.py, test_limper_coverage_belt.py, backend/tests/data/coverage_baseline.json)*
Re-run the population/statistical harness; re-anchor any bands moved by **A1 (air-call drop)**, the
**content-driven preflop-range shifts (B1/M3/N3 AND T5's residual-overlap pack fixes — refuter F5)**,
**levers-first, with in-file justification comments**. Specifically:
- `test_coverage_baseline.py`: the villain seats are real packs, so preflop+A1 changes drift the hand stream →
  `total` changes → **re-record `coverage_baseline.json`** (deliberate; per its `_record()` path).
- `test_limper_coverage_belt.py` (**refuter F2 — was omitted**): `_PRE_M3_FIRES` pins EXACT organic fire counts
  driven by all personas' real policy + `calling_station` hero proxy → B1/M3/N3 drift them. **Re-measure at the
  pinned seed and update `_PRE_M3_FIRES` with an in-file justification comment**; keep the `_WANT_*`/`_WANT_BB`
  ≥1 assertions satisfied.
- Verify anti-sizing-tell + bluff-ordering pins still hold (A1 touches CALL, not the bluff path).
- **Report the cumulative graded-coverage delta vs `coverage_baseline.persona-realism-start.json`** and
  adjudicate any loss in the PR body. Do NOT touch the immutable snapshot.
**Done:** `./scripts/verify.sh` → `BACKEND VERIFY OK`; `ruff` clean; cumulative-delta line reported; all P1
pass/fail bullets in the spec satisfied.

---
## Fan-in verification (orchestrator, each wave)
`refuter` on the wave diff (contract breaks / regressions / missed edge cases) **and** `./scripts/verify.sh`
+ `ruff`. A red gate blocks the next wave. Only verified + reviewed work advances; commit per wave.
