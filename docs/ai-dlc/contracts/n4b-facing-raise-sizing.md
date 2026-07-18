# N4b contract map — facing-raise sizing grades (read-only scan, 2026-07-18, post-N4a)

HEAD: main @ 7b82a28. Anchors verified live. N4 split: N4a (barrels, shipped #48) + **N4b (facing-raises, this map)**.

## 1. The 4 facing graders are size-blind (`backend/app/domain/postflop.py`)
- `grade_vs_cbet` 680-779 (RAISE eval build 695-698, match **:743**) · `grade_vs_check_raise` 863-971 (build 883-886, match **:932** — comment :931 self-documents "RAISE matches by ActionType alone") · `grade_vs_turn_bet` 1192-1295 (build 1210-1213, match **:1259**) · `grade_vs_river_bet` 1523-1631 (build 1546-1549, match **:1595**).
- All four: single RAISE `ActionEval` from a single `next(la.min_bb …)` over legal_actions, and chosen-action resolution via `next((e for e in evals if e.action == decision.action), None)` — **`decision.size_bb` read nowhere**. Emitting two RAISE legs without generalizing first ⇒ ordering-dependent silent grab of whichever RAISE leg is first (Risk 1).
- `_match` (583-592): BET-side nearest-size resolver used by the 3 bet graders (:515, :1151, :1482) — generalizes cleanly to 2-RAISE disambiguation; not called by facing graders today.
- `_bet_sizing_verdict` (557-580): hardcoded `ActionType.BET` gate at :571 — needs a sibling/parameterized `_raise_sizing_verdict`; shape (higher-merit = optimal) transfers.
- `sizing_correctness` is unconditionally unset on all 4 facing-grader results (constructions :769, :961, ~:1285, :1621) — 100% new grading logic, not a dormant field.

## 2. Facing mappers (`grade_map_postflop.py`) + the flop gap
- `map_vs_turn_bet` 396-426, `map_vs_river_bet` 462-497 — both via shared `_faced_bet_spot` **321-364**: RAISE `LegalAction` at :358 with `raise_size = round(3 * bet, 1)` (**flat 3×**, :336); CALL leg `min_bb = bet` (:357, zero-prior-investment shortcut).
- **No flop facing mappers exist** (`map_flop_vs_cbet`/`map_flop_vs_check_raise`: zero hits repo-wide). Dispatcher `grade_map.py:44-45` routes flop only to `map_flop_cbet` → **hero facing a flop bet/check-raise in live Simulate is unconditionally "no baseline yet"**. `grade_vs_cbet`/`grade_vs_check_raise` are live+tested but reachable only via Practice (`scenarios.py` builders → `drill.py`) — flop facing in Simulate = turning on a dead path, genuinely new coverage (Risk 2).

## 3. Three competing raise-size formulas
- (a) `table/sizing.py`: `POSTFLOP_BET_FRACS` (36-40) is BET-only; `HERO_NODE_SIZE["raise"]=1.0` (:28) is the single displayed facing-raise size via `postflop_node_key` (54-81; CALL-in-kinds → "raise" at 65-67) + `pot_fraction_to_bb` (84-96, RAISE branch `current_bet_to + frac*(pot+to_call)`).
- (b) Flat-3x literals ×3: `grade_map_postflop.py:336` (Simulate turn/river), `scenarios.py:488` (`build_vs_cbet_spot`, `3*cbet`), `scenarios.py:576` (`build_check_raise_spot`, `3*raise_to`; NB incremental `call_amt = raise_to - cbet` at :575 — different call convention than `_faced_bet_spot`).
- (c) RES-B (`docs/ai-dlc/research/RES-B-bet-sizing.md`): :148 check-raise fork **2.5× / 3.5× the c-bet**; :149 facing-bet raise fork **2.5× / 3× the bet** (also :82-83 pot-fraction rationale). Today's flat 3× matches neither pair exactly — two-size offer is a behavior change, not a display split.

## 4. Signature risk — SAFE (verified)
`_postflop_signature` (`srs.py:107-162`) never reads RAISE `min_bb`/`max_bb` and doesn't enumerate/count legal_actions; only size-derived input is `faced_bet_bucket` (71-104) which reads **CALL leg min_bb only** (:90-93). `test_signature.py` pins (203-208) exercise no facing-RAISE node. **Two-RAISE emission is structurally signature-safe.**

## 5. N3/N4a plumbing — reusable, verified
`EvaluationResult.sizing_correctness` (`evaluation.py:69`) · `SimDecision` col (`models.py:111`, migration 0011, action-agnostic) · `GradeView` (`schemas/simulate.py:52`) · flow-through `sim_session.py:266-267` ungated on action type · FE `types.ts:252`, `SimTable.tsx:298`, `SimRecap.tsx:85-87` (label "size:" — generic). **No migration, no schema, no FE work.**
Display two-size patterns to mirror: `_hero_cbet_legal_actions` (`sim_session.py:339-353`), `_barrel_two_sizes` (375-394), dispatch in `_hero_legal_actions` (485-524; RAISE branch 506-512 is preflop-only; facing nodes fall to generic single-size 513-522 today). No `_is_*_raise_node` exists yet.

## Top risks
1. **Size-blind match = blocker**: generalize the 4 graders (two RAISE evals + `_match`-style resolver) BEFORE any two-RAISE mapper emission, else ordering-dependent silent bug.
2. **Flop facing mappers = new coverage surface**, not polish — needs own gate design (HU, canonical-bet); no existing flop facing mapper pattern to copy.
3. **3 flat-3x literals across 2 features** (Simulate mapper + 2 Practice builders) with different call conventions — centralizing must respect both or scope Practice out.
4. **Verdict semantics**: RES-B is texture-dependent (smaller dry / larger wet); current `_bet_sizing_verdict` is frequency-only. Decide: frequency-consistent (N4a-style) vs texture-aware (new logic).
5. **Display==graded parity**: new raise helpers must derive from the SAME fraction/multiplier source as the mapper (the N3/N4a bug class); `HERO_NODE_SIZE` path must be gated off only when the mapper maps (non-None gate + collapse-to-one fallback).

## Invariants cross-checked
Domain purity clean · signature frozen-safe (§4) · freq+EV shape unchanged · `TAXONOMY_VERSION==5` untouched (VS_* leak categories already exist, `grading.py:89-100`) · anti-tell: bot raise sizing (`personas_postflop.py:220-334`) separate path, untouched · HU gates inherited via callers · no migration needed · strict-superset: single-raise flows must stay byte-identical unless two sizes offered.
