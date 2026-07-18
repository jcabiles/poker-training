# N4a contract map — postflop barrel sizing grades (read-only scan, 2026-07-17, post-N3)

N4 split into **N4a (barrels)** + N4b (facing-raises). This maps N4a. Anchors verified live against HEAD (main, incl. N1/N2/N3).

## Aggressor bet graders already grade by size — just need the additive sizing verdict + correct sizes
- `backend/app/domain/postflop.py`: `grade_cbet` (445-552, `_match` at 515), `grade_turn_barrel` (1052-1159, `_match` at 1123), `grade_river_barrel` (1376-1488, `_match` at 1452). All THREE build two BET `ActionEval`s (small/big) from `_bet_sizes(spot)` (438-442, reads `spot.legal_actions` BET `min_bb`) and resolve the chosen by size via `_match` (555-564). **Correctness already reflects the size choice.** N4a ADDS an isolated `sizing_correctness` (optimal = hero's chosen size is the higher-merit/frequency BET eval; acceptable = the lower; None = single-size or non-bet). Additive — `correctness`/`per_action` unchanged.
- `_match` (555-564): CHECK/BET only, `min(bet_evals, key=abs(size-target))`. Reusable as-is for reading the chosen bet eval.

## The barrel-size bug (N4a fixes)
- `grade_map_postflop.py::_barrel_spot` (268-310): hard-codes `small=round(0.33*pot,1)` / `big=round(0.75*pot,1)` (281-282) — copied from `map_flop_cbet` (93-94) but SHARED by `map_turn_barrel` (359-385) and `map_river_barrel` (421-451). Per RES-B (`docs/ai-dlc/research/RES-B-bet-sizing.md:144-145`): **turn barrel = 0.5/0.75 pot; river = 0.5/1.0 pot** — two different pairs, neither is the flop's 0.33/0.75. So today's turn/river barrels are silently GRADED against wrong sizes (pre-existing correctness bug). Fix: parameterize `_barrel_spot` with the per-street pair.
- Third divergent source: `sim_session.py::_hero_postflop_size_bb` uses `HERO_NODE_SIZE["turn_barrel"]=0.67`/`["river_value"]=0.75` (`table/sizing.py:26-27`) as the single DISPLAYED size — and there is NO two-size hero offer for barrels today (`_hero_legal_actions` only special-cases the flop c-bet via `_is_flop_cbet_node`/`_hero_cbet_legal_actions`, 328-350/441-472).

## Two-size emission = the MAPPER (not an inject)
- Postflop grading: `apply_hero_action` (606-669) → `map_decision_point` (626) → `_inject_two_sizes` (628, **preflop-only-gated at :388, no-ops postflop**) → `evaluate` (631) → grader reads `spot.legal_actions`. So the **mapper is the source of truth for graded sizes** (`map_flop_cbet` already emits two BETs, 126-130). N4a's `_barrel_spot` already emits two BETs — just with the wrong fractions.
- **Display parity (the #1 risk):** N4a adds `_is_turn_barrel_node`/`_is_river_barrel_node` + `_hero_turn_barrel_legal_actions`/`_hero_river_barrel_legal_actions` in `sim_session.py` (mirror `_hero_cbet_legal_actions`), deriving from the SAME fraction source as `_barrel_spot`. Put the RES-B fractions in ONE const (e.g. `table/sizing.py`) imported by both the mapper (graded) and sim_session (displayed). Docstring invariant already stated at `sim_session.py:338-341`.

## Reuse from N3 (no re-spec)
- `EvaluationResult.sizing_correctness` (`evaluation.py:69`); `SimDecision.sizing_correctness` col (migration 0011, `models.py:111`); `GradeView.sizing_correctness` (`schemas/simulate.py:52`, wired `sim_session.py:217,264-266`); FE sub-note (`types.ts:252`, `SimTable.tsx:298`, `SimRecap.tsx:85-87`). **N4a only makes the postflop bet graders POPULATE the field** — flow to `_sim_decision_row` (264-266) is identical to preflop. **No migration, no schema, no FE.** (Note: the flop c-bet retrofit means the c-bet will now ALSO show the "· size" sub-note — intended consistency.)

## Hash pins + invariants
- Pins are on `spot_signature()`/`_postflop_signature()` (`test_signature.py:203-208,264-267,301,304-307`), hashing Spot structure (`srs.py:48-68,107-163`) — NOT grader `per_action`/`EvaluationResult`. `sizing_correctness` on `EvaluationResult` is never hashed → additive-safe. **Do NOT change the CALL leg `min_bb`** (feeds `faced_bet_bucket`, `srs.py:71-104`) — N4a only changes the BET small/big fractions, not CALL. `TAXONOMY_VERSION==5` (`leaks.py:15`) untouched. `test_postflop.py` has no byte-exact numeric goldens (structural/directional only) — the barrel-size fix (0.33/0.75→RES-B) is safe as long as directional assertions hold; re-run + adjust any barrel test that asserted a specific 0.33/0.75-derived value.
- HU-only: mappers gate `len(live)!=2 → None` (`map_flop_cbet:48-50`, `_hu_srp_preflop:156-158`) — barrels inherit. Multiway stays "no baseline yet."
- Anti-tell: bot sizing (`personas_postflop.py`) untouched — N4a only changes HERO offers + grading.

## N4a files touched
- `backend/app/domain/postflop.py` — additive `sizing_correctness` on `grade_cbet`/`grade_turn_barrel`/`grade_river_barrel` (shared `_bet_sizing_verdict` helper).
- `backend/app/domain/table/grade_map_postflop.py` — `_barrel_spot` parameterized to RES-B pairs.
- `backend/app/domain/table/sizing.py` — new `BARREL_SIZES` fraction const (single source for graded + displayed).
- `backend/app/services/sim_session.py` — turn/river barrel two-size display helpers + `_hero_legal_actions` wiring.
- `backend/tests/test_postflop.py` (+ sizing-verdict + barrel-size tests), new `backend/tests/test_sim_postflop_sizing.py` (e2e: barrel hand → `sizing_correctness` persists, displayed==graded).
- **NOT touched:** `evaluation.py`/`models.py`/`schemas`/migrations/FE (reuse N3); the 4 facing graders + new mappers (that's N4b); `personas*`, `srs.py`.

## Risks N4a must respect
1. **Displayed≠graded** — single fraction source for both paths (highest-risk repeat bug).
2. **Distinctness** — two bet sizes clamped to `[min,max]`, 1-dp, distinct or fallback to one (R3/N3 lesson).
3. **Hash pins** — don't touch CALL leg / signature inputs; sizing verdict additive.
4. **Pin/goldens** — the barrel-size fix may shift a barrel test that hard-coded 0.33/0.75 values; re-run test_postflop.py, adjust directional expectations only.
5. **c-bet retrofit** — adding `sizing_correctness` to `grade_cbet` must NOT alter its `correctness`/`per_action` (R3 tests stay green).
