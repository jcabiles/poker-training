# N4a — Postflop barrel sizing grades (turn/river barrels + flop c-bet consistency)

**Status:** spec (Gate-2 pending) · **Roadmap slice:** Epic 3 · N4a (N4 split → N4a barrels / N4b facing-raises; supersedes R3b postflop half, barrel part) · **Consumes:** RES-B · **Appetite:** ~1 small-medium epic (backend-only, no migration). · **Codex dual-review:** no (sandbox — Claude `refuter` only).

## 1. Goal / outcome-link
Sizing is graded only on the flop c-bet (R3). N4a extends it to **turn/river barrels**: hero gets two size options and a **separate size verdict**, and the barrels are graded against the **correct RES-B sizes** (fixing a pre-existing bug where they're graded against flop 0.33/0.75). The sizing-verdict half of the north-star, for postflop bets.

## 2. Locked interview decisions (2026-07-17)
- **Split:** N4 → **N4a (barrels, this slice)** + **N4b (facing-raises, next)**. Cleanly separable (no shared function bodies).
- **Separate size verdict** (not blended): the three aggressor bet graders (`grade_turn_barrel`, `grade_river_barrel`, + **retrofit `grade_cbet`** for consistency) populate an **additive `sizing_correctness`** — OPTIMAL if hero's chosen BET size is the higher-merit (higher-frequency) of the two, else ACCEPTABLE; None when single-size or hero didn't bet. **The action `correctness`/`per_action` are UNCHANGED** (additive → hash-pin safe). Reuses N3's `sizing_correctness` column/field/FE — no migration, no schema, no FE work. (The flop c-bet will now also show the "· size" sub-note — intended consistency.)
- **Sizes = RES-B pairs:** turn barrel **0.5/0.75 pot**, river **0.5/1.0 pot**. Replace `_barrel_spot`'s hard-coded 0.33/0.75. Live in ONE fraction const feeding both graded + displayed.
- **Parity:** one size source → both the graded spot (`_barrel_spot`) and the displayed hero offer (`sim_session`). Two sizes clamped to `[min,max]`, 1-dp, distinct or fallback to one.
- HU-only (multiway → no baseline); anti-tell/`spot_signature()`/`TAXONOMY_VERSION==5` intact.

## 3. Contract map (full map in `contracts/n4a-barrel-sizing-grades.md`)
- Aggressor bet graders already grade size via two BET evals + `_match` (`postflop.py`: `grade_cbet` 445-552, `grade_turn_barrel` 1052-1159, `grade_river_barrel` 1376-1488; `_match` 555-564; `_bet_sizes` 438-442). N4a adds the isolated sizing verdict.
- `_barrel_spot` (`grade_map_postflop.py:268-310`) hard-codes 0.33/0.75 (281-282), shared by `map_turn_barrel`/`map_river_barrel` → the bug.
- Two-size emission = the MAPPER (`_inject_two_sizes` is preflop-only, `sim_session.py:388`). Display parity via new barrel helpers in `sim_session.py` (mirror `_hero_cbet_legal_actions` 333-350).
- Reuse N3: `EvaluationResult.sizing_correctness` (`evaluation.py:69`), `SimDecision.sizing_correctness`/migration 0011, `GradeView.sizing_correctness` (`schemas/simulate.py:52`), FE sub-note (`SimRecap.tsx:85-87`). Write path `_sim_decision_row` (264-266) identical to preflop.
- Pins on `spot_signature()` (`test_signature.py`), not grader output; CALL leg untouched.

## 4. Changes (backend-only — no migration, no schema, no FE)
### 4a. Street-keyed fraction source (`table/sizing.py`)
- Add `POSTFLOP_BET_FRACS: dict[str, tuple[float, float]] = {"flop": (0.33, 0.75), "turn": (0.5, 0.75), "river": (0.5, 1.0)}` (pot fractions). **Single source of truth for offered sizes, graded sizes, AND the canonical-bet recognition gate** (below). Flop stays 0.33/0.75 (unchanged — flop c-bet sizes don't move); only turn/river get the RES-B fix.

### 4b. Fix the graded barrel sizes (`grade_map_postflop.py`)
- Parameterize `_barrel_spot` to take the street (or the pair) instead of hard-coding 0.33/0.75; `map_turn_barrel` uses `POSTFLOP_BET_FRACS["turn"]`, `map_river_barrel` uses `["river"]`. Emit two BET `LegalAction`s clamped to `[min,max]`, 1-dp, distinct (or one on collapse). CALL leg unchanged.

### 4b′. Make the canonical-bet gate street-aware (refuter HIGH — MANDATORY)
- `_BET_FRACS`/`_is_canonical_bet`/`_check_bet`/`_check_bet_call` (`grade_map_postflop.py:143-144`+) currently validate a prior-street bet against the flop-only `(0.33, 0.75)`. Since the turn barrel now offers 0.5 pot, `map_river_barrel`/`map_vs_river_bet` (which re-verify the prior TURN bet via `_check_bet_call(state, Street.TURN, ...)`) would reject a 0.5-pot turn bet → the river silently becomes **unmappable** (a live regression). **Fix:** make `_is_canonical_bet(size, pot, street)` (and its callers) validate against `POSTFLOP_BET_FRACS[street]` — so a canonical TURN bet is 0.5 OR 0.75 pot, a FLOP bet 0.33 OR 0.75, a RIVER bet 0.5 OR 1.0. This unifies the offered/graded/recognized sizes on ONE source. **New test: play a turn barrel at the new 0.5 size through `apply_hero_action`, assert the subsequent river decision still MAPS (not silently None).** The existing `test_grade_map_turn_river.py` mock helpers hard-code the turn leg at 0.33 — update them to the new turn fractions (else they mask this).

### 4c. Additive sizing verdict (`postflop.py`)
- New `_bet_sizing_verdict(bet_evals, chosen_eval) -> Correctness | None`: with ≥2 BET evals, OPTIMAL if `chosen_eval` is the max-frequency (merit) BET eval, else ACCEPTABLE; None if <2 BET evals or hero didn't bet.
- **No verdict when betting wasn't reasonable (refuter LOW):** if BOTH BET frequencies clamp to 0 (air/weak hand where betting itself is a mistake — both merits non-positive), return **None**, NOT a tie-break to OPTIMAL. Prevents a "· size: Best" sub-note printing beside an action verdict of "Blunder." (A genuine tie between two POSITIVE-merit sizes → OPTIMAL.)
- Call it in `grade_cbet`, `grade_turn_barrel`, `grade_river_barrel`, attach to `EvaluationResult.sizing_correctness`. **Do NOT change `correctness`/`per_action`/`ev_bb`** — purely additive.

### 4d. Displayed two-size offer for barrels (`sim_session.py`) — with real parity (refuter MED)
- New `_is_turn_barrel_node`/`_is_river_barrel_node` + `_hero_turn_barrel_legal_actions`/`_hero_river_barrel_legal_actions`, using `POSTFLOP_BET_FRACS` + the current pot. Wire into `_hero_legal_actions`' if/elif chain (append-only).
- **Do NOT blindly mirror `_hero_cbet_legal_actions`** — it lacks a distinctness fallback and its display gate is independent of the grading gate (a latent divergence). The barrel helpers must: (1) **explicit distinctness fallback** — collapse to ONE `LegalAction` when the two sizes clamp equal (short stack), mirroring `_preflop_two_sizes` (`sim_session.py:360-377`); (2) **gate on grading** — only offer two sizes when `map_turn_barrel`/`map_river_barrel`(state, HERO_SEAT) is non-None (so display never offers two sizes on a spot grading bailed to None, e.g. `hero_remaining < big`). Displayed == graded by construction (same fractions + pot + same non-None gate + same fallback). A short-stack barrel parity test is required.

## 5. Pass/fail
- Hero barreling turn/river sees **two** size options; the recap/badge shows the action verdict **and** a "· size: Best/OK" sub-note (coach mode); the sizing verdict is OPTIMAL for the higher-merit size, ACCEPTABLE for the other; persisted to `sim_decision.sizing_correctness`.
- **Barrels graded against RES-B sizes** — turn 0.5/0.75, river 0.5/1.0 (not 0.33/0.75); a test asserts the graded `LegalAction` BET sizes match `BARREL_SIZES`.
- **Displayed == graded** per barrel node (same fractions + pot + same non-None gate + same distinctness fallback) — including a **short-stack parity test** (display offers one size exactly when grading collapses/bails to one, never two-vs-one divergence).
- **River still maps after a new-size turn barrel (refuter HIGH):** an integration test plays a turn barrel at 0.5 pot through `apply_hero_action` and asserts the river decision maps (not silently None); `_is_canonical_bet` accepts per-street `POSTFLOP_BET_FRACS`; `test_grade_map_turn_river.py` mocks updated to the new turn fractions.
- **No size verdict beside a bet-blunder (refuter LOW):** on an air hand where both BET merits clamp to 0, `sizing_correctness` is None (no "· size" sub-note next to a Mistake/Blunder action verdict).
- **Flop c-bet retrofit:** `grade_cbet` now populates `sizing_correctness` too; its `correctness`/`per_action` are byte-unchanged (R3 c-bet tests + any `grade_cbet` goldens stay green).
- **Additive / pin-safe:** `spot_signature()`/`_postflop_signature` byte-unchanged (CALL leg untouched); `TAXONOMY_VERSION==5`; `test_signature.py` pins green; `test_postflop.py` green (adjust only barrel tests that hard-coded a 0.33/0.75-derived numeric — directional assertions unchanged).
- **e2e:** a `sim_session`-level test plays a turn barrel choosing each size and asserts the persisted `sizing_correctness`; a single-size/check spot yields None.
- HU-only (multiway → no baseline); anti-tell intact (bot sizing untouched); no migration/schema/FE change (assert diff scope).
- `./scripts/verify.sh` + `ruff` + `cd frontend && npm run typecheck && npm run build` green; design-review the barrel two-size UI + sizing sub-note both themes.

## 6. Refuter-target risks
- **Canonical-bet-gate regression (refuter HIGH):** re-verify that changing turn/river bet fractions doesn't orphan the river mapper — `_is_canonical_bet` must accept the new per-street fractions; play a turn barrel at 0.5 pot and confirm the river still maps. Don't trust the mock helpers (hard-coded 0.33) — update them.
- **Displayed≠graded** — prove the barrel display helper and `_barrel_spot` derive from the SAME `POSTFLOP_BET_FRACS` fractions + same pot + same non-None grading gate; no third source (`HERO_NODE_SIZE`) leaking in; short-stack case offers one size on both sides.
- **Pin/golden safety** — the barrel-size change (0.33/0.75→RES-B) must not shift `spot_signature()` (CALL leg untouched) and must only shift barrel test assertions that were tied to the old numeric sizes; per_action/correctness for a given (hand, size) unchanged in shape.
- **c-bet retrofit non-regression** — adding `sizing_correctness` to `grade_cbet` must not alter its `correctness`/`per_action` (R3 tests byte-green).
- **Distinctness** — turn/river barrel small≠big after clamp on every pot/stack, or fallback to one size + None verdict.
- **Sizing-verdict semantics** — OPTIMAL = higher-frequency BET eval; confirm the frequency (merit) is read correctly and ties resolve to OPTIMAL; None on check/single-size.
- **Purity** — new `_bet_sizing_verdict` in `postflop.py` (domain) stays pure.
- **Multiway** — barrels stay HU-gated (no silent multiway grade).

## 7. File ownership
N4a owns (backend-only): `app/domain/postflop.py` (`_bet_sizing_verdict` + 3 grader bodies, additive), `app/domain/table/grade_map_postflop.py` (`_barrel_spot` param + **street-aware `_BET_FRACS`/`_is_canonical_bet`/`_check_bet`/`_check_bet_call`**), `app/domain/table/sizing.py` (`POSTFLOP_BET_FRACS`), `app/services/sim_session.py` (barrel display helpers with fallback + grading-gate), `backend/tests/test_postflop.py`, `backend/tests/test_grade_map_turn_river.py` (mock turn fractions updated), new `backend/tests/test_sim_postflop_sizing.py` (barrel sizing e2e + turn→river-maps integration + short-stack parity). **Does NOT touch** the 4 facing graders / new mappers (N4b), `evaluation.py`/`models.py`/`schemas`/migrations/FE (reuse N3), `personas*`/`srs.py` (anti-tell/frozen signature).

> ⚠️ Mostly sequential backend chain: `sizing.py` const → `_barrel_spot` (graded) + `sim_session` (displayed) in parallel-ish → grader verdict → tests. Single-owner hotspot `sim_session.py`. Small enough for a single agent.

## 8. Tickets (outline — see tickets/n4a-barrel-sizing-grades.md)
- **T1** — `BARREL_SIZES` const + fix `_barrel_spot` to RES-B pairs (graded); barrel-size test.
- **T2** — `_bet_sizing_verdict` + populate `sizing_correctness` in the 3 aggressor bet graders (additive); pin/golden + c-bet-non-regression tests.
- **T3** — barrel two-size display helpers in `sim_session.py` (parity with graded); e2e sizing test.
- **T4** — verify + design-review (barrel two-size UI + sizing sub-note both themes; coach mode).
