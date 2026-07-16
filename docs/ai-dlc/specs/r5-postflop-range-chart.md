# R5 — Postflop range chart: openable call/fold/raise for the current spot

**Status:** spec (Gate-2 pending) · **Consumes:** `docs/ai-dlc/research/RES-C-postflop-ranges.md` · **Wave:** W1 (‖ R3 ‖ R4) · **Appetite:** ~1 large epic.

## 1. Goal / outcome-link
No point-of-need postflop range view — hero can't see "what should call/fold/raise here." R5 adds an openable panel (preflop-chart interaction pattern) showing the action mix for hero's **current** postflop spot, and widens postflop grading coverage to match. Deepest transfer gap.

## 2. Locked interview decisions (2026-07-16)
- **Chart renders the grader's own `per_action`** (chart==grader by construction). **No re-pointing S6/S7 graders. No new `content/postflop` data.** Keep the merit pipeline authoritative (RES-C §13).
- **Widen `map_decision_point` to turn/river** so a supported spot both opens the chart AND gets a live graded verdict persisted to `sim_decision` (chart + live grading move together). The turn/river GRADERS already exist (S6/S7) — only the **Spot mapper** is missing.
- **HU-first:** multiway spots stay unmappable → chart shows "no baseline yet" (consistent with `map_flop_cbet` refusing multiway today).

## 3. Contract map (from R5 scan, file:line anchors)
- **`per_action` is chart-ready** — `evaluation.py:36-40,61-78`: `ActionEval{action, size_bb, frequency(0-1), ev_bb}`. Every postflop grader builds exactly 3 (`postflop.py` cbet:445, vs_cbet:652, vs_check_raise:835, turn_barrel:1052, vs_turn_bet:1162, river_barrel:1376, vs_river_bet:1491). **Call `provider.optimal(spot)` (decision=None) → chart mix, zero grading side effects** (graders early-return before `chosen_eval`/`correctness`).
- **Taxonomy frozen** — `_hand_category` (`postflop.py:220-274`): `strong|weak_made|draw|air`. `weak_made`=plain top pair (do NOT promote — Phase-2e-0 bug). River busted-draw→air (`_river_cat_effective`, `postflop.py:1292-1295`); a river "draw" row would be a lie the grader never emits.
- **Frequencies are DERIVED** — `_merits*` → `_apply_multiway` (positive-merit-only, `postflop.py:395-426`) → `_frequencies` (drop-neg+normalize, `postflop.py:429-435`). **The chart must render `per_action`, never re-derive** — re-deriving risks rounding/negative-clip/order drift (RES-C §13 top risk).
- **`range_advantage` node-context-dispatched + street-decaying** — `postflop.py:115-205` (flop 1.0→turn 0.5→river 0.0); call sites warn against passing hero's own position twice (`:843,:1386,:1500`). Chart reads `adv` off the graded result, never re-derives.
- **Dispatcher gate** — `grade_map.py:28-40` `map_decision_point`: PREFLOP→`map_preflop`, FLOP→`map_flop_cbet`, else `return None` ("turn/river out of v1 scope", line 40). **This one line is the entire turn/river no-grade gate.** Live callers: chart + `sim_session.py:492` `apply_hero_action` (writes `DrillAttempt`/`SimDecision`). Widening ⇒ live turn/river decisions now grade+persist.
- **`map_flop_cbet` canonical-shape parity** — `grade_map_postflop.py:35-128`: HU only, hero=single raiser at canonical open, BB lone caller checks flop, ranges from real content entries, depth supports both bet buckets; **None on any doubt.** The turn/river mappers must copy this "None on doubt" posture.
- **Provider singleton** — `_grading_provider()` (`sim_session.py:110-117`), `TieredFeedbackProvider(CompositeProvider(...))` (`factory.py:28-45`); `CompositeProvider._by_street` (`composite.py:46-51`) routes FLOP/TURN/RIVER; `supports()` gates on street + node_context intersection (`providers/{postflop,turn,river}.py:21-29`). **Chart endpoint MUST reuse this singleton**, never construct its own.
- **Preflop-chart pattern to mirror** — `GET /simulate/{id}/preflop-chart` (`api/v1/simulate.py:90-99`) → `sim_session.preflop_chart:636-665` → `PreflopChartView{available,node_label,grid,exploit_note}` (`schemas/simulate.py:116-126`). **`grid` is a 169-combo shape — incompatible with an action-mix panel → R5 needs a DISTINCT response schema.** FE `SimRangeChart.tsx`: collapse/`localStorage`/fetch-on-expand/stale-guard idiom **reusable**; the 13×13 render is **not** — need a new action-mix render. Mount `SimulateView.tsx:708-714` gates preflop-only; R5 needs a widened postflop gate + an `identityKey` discriminating postflop decision points within a hand.
- **Signatures inert** — sim persists via `_sim_signature` (`sim_session.py:536-543`, `sim:ctx:pos`), NEVER `spot_signature()`/`_postflop_signature`. Widening live grading writes `SimDecision`+`DrillAttempt(source=simulate)` through the sim namespace ⇒ the frozen `_postflop_signature` conditional-append (`srs.py:107-163`) stays untouched, `TAXONOMY_VERSION` stays 5. **R5 must NOT route sim spots into `record_attempt`/SRS.**

## 4. Changes
### 4a. Turn/river Spot mappers (the hard lift — the real cost center of R5)
- New `map_turn_barrel` / `map_vs_turn_bet` / `map_river_barrel` / `map_vs_river_bet` in **`grade_map_postflop.py`** — canonical HU shapes. **Mirror the existing `scenarios.py:630-955` builders** (`build_turn_barrel_spot`/`build_vs_turn_bet_spot`/`build_river_barrel_spot`/`build_vs_river_bet_spot`) which already define the canonical shapes + reuse the same RFI/BLIND_DEFENSE content entries as flop. Build a `Spot` with real board/cards/stacks/pot, tag `node_context` so `TurnHeuristicProvider`/`RiverHeuristicProvider` `supports()` fires. **None on any doubt.** HU only (multiway→None).
- ⚠️ **Appetite honesty (refuter MED):** each mapper gates **2–3 sequential streets of exact-match bet sizing** (preflop raise-to-canonical, flop c-bet ==0.33/0.75-pot-AND-called, turn barrel ==0.33/0.75-pot-AND-called for river) — a materially deeper state machine than `map_flop_cbet`'s single-street gate. This is NOT "copy the pattern." Each mapper ships with an explicit multi-street gate **test matrix** (every off-size / not-called / multiway branch → None). If the four mappers prove larger than the slice can hold, split them into their own ticket pass — do not silently under-test the gates.
- Optionally widen flop beyond c-bet (vs_cbet / vs_check_raise) if cheap; else defer.

### 4a′. Permanent coverage ceiling — state it honestly (refuter LOW)
Only **4 turn/river node contexts exist** (TURN_BARREL, VS_TURN_BET, RIVER_BARREL, VS_RIVER_BET), all requiring the *"opener c-bet the flop and got called"* continuation line. Every other live turn/river shape — hero checked the flop, flop-check-raise pots carried forward, 3-bet/4-bet pots, donk/lead, delayed c-bet, probe — **has no grader and stays "no baseline yet" forever**, regardless of mapper quality. R5 does not fabricate coverage for these; the chart honestly shows "no baseline yet." (Matches RES-C §12's non-spot list.)

### 4b. Dispatcher
- `grade_map.py` `map_decision_point`: route `Street.TURN`/`Street.RIVER` to the new mappers (was `return None`). Dispatcher is lead-owned; **R5 owns this postflop branch edit.**

### 4c. Chart endpoint (new, read-only)
- `GET /simulate/{id}/postflop-chart` (`api/v1/simulate.py`) → new `sim_session.postflop_chart(db, id, owner)` service. Availability gate mirrors `preflop_chart` (session/hand/street/hero-turn/`map_decision_point`→None). On success: `provider.optimal(spot).per_action` from the **shared singleton**, plus hero `_hand_category` label + `node_label`, **approximate-EV labeled**.
- New schema `PostflopChartView{available, node_label, hand_category, actions: [{action, size_bb, frequency, ev_bb}], approx: true}` (`schemas/simulate.py`). Distinct from `PreflopChartView`.
- FE `types.ts`: add `PostflopChartView` (additive; hand-maintained mirror).

### 4d. Frontend panel
- New `SimPostflopChart.tsx` — reuse `SimRangeChart`'s panel chrome (collapse, `localStorage`, fetch-on-expand, stale-guard) with a **new action-mix render** (bars per action, freq + ≈EV, category caption). Mount in `SimulateView` with a postflop gate + `identityKey` = `${session}#${hand}#${street}#${pot_bb}` (discriminates multiple postflop hero turns).

## 5. Pass/fail
- On a supported flop/turn/river spot the chart opens and shows a call/fold/raise (or check/bet-small/bet-big) action mix with **approximate labeling**; an unmapped/multiway spot shows "no baseline yet" (never fabricated).
- **Consistency test (the whole point):** the chart's action mix == the grader's `per_action` for the same spot, by construction (same `provider.optimal` call). A live turn/river hero decision now gets a graded `sim_decision` verdict matching what the chart showed.
- **S6/S7/S8 grader tests + hash pins byte-identical** — R5 touches the MAPPER + chart, never the graders or `srs` signatures (assert pins `6832…/0cdf…/9c1a…` unchanged; `TAXONOMY_VERSION`==5).
- Chart endpoint writes nothing (read-only; assert zero `sim_decision`/`DrillAttempt` rows created by a chart fetch).
- No new `content/postflop` data; graders un-re-pointed.
- `verify.sh` + `cd frontend && npm run typecheck && npm run build` green; design-review both themes.

## 6. Refuter-target risks
- **Does widening `map_decision_point` silently persist off-shape turn/river spots?** The new mappers must be as strict as `map_flop_cbet` (None on doubt) or `apply_hero_action` writes a fabricated-texture `sim_decision`. This is the S5/S6 truncation hazard resurfacing — verify each mapper's canonical gates.
- **Chart==grader claim:** prove the chart calls the exact same `provider.optimal(spot)` the grader uses (same singleton, same spot construction) — no parallel re-derivation of frequencies or `range_advantage`.
- **Pin integrity:** confirm no grader / `srs` / `_postflop_signature` edit crept in; sim path stays on `_sim_signature`, never `record_attempt`/SRS.
- Multiway: assert turn/river mappers return None for 3+ live players (no HU-graded multiway).
- FE `identityKey`: does a second postflop hero turn in the same hand/street/pot refetch correctly (stale-guard)?

## 7. File ownership (W1 disjointness)
R5 owns: `grade_map_postflop.py` (new mappers), `grade_map.py` (turn/river dispatch branch — lead-coordinated), new `postflop_chart` service in `sim_session.py` (**read-only, additive — coordinate the `sim_session.py` touch with R3**), `api/v1/simulate.py` (new endpoint), `schemas/simulate.py` (new view), FE `SimPostflopChart.tsx` + `SimulateView` mount, `types.ts` (additive `PostflopChartView`). **Reads `postflop.py` graders as-is (no edit).**
> ⚠️ **`sim_session.py` is touched by BOTH R3 (hero legal actions) and R5 (postflop_chart service).** Disjoint FUNCTIONS, same file → real collision risk. Mitigation: R5's `postflop_chart` is a new self-contained read-only function appended at the service boundary; lead integrates at fan-in. If both land big edits, serialize R5's `sim_session.py` hunk after R3's.

## 8. Tickets (outline)
- **T1** — Turn mappers (`map_turn_barrel`, `map_vs_turn_bet`) in `grade_map_postflop.py`, mirroring `scenarios.build_turn_*_spot`; canonical HU, None-on-doubt; **explicit multi-street gate test matrix** (off-size flop c-bet, uncalled flop, wrong turn size, multiway → all None).
- **T2** — River mappers (`map_river_barrel`, `map_vs_river_bet`), same posture + matrix; busted-draw→air honored via the existing grader (no grader edit).
- **T3** — Dispatcher: route TURN/RIVER in `map_decision_point`; assert live grading persists a matching `sim_decision`; pins byte-identical.
- **T4** — `GET /postflop-chart` endpoint + `postflop_chart` service (shared singleton, read-only) + `PostflopChartView` schema; zero-write test.
- **T5** — FE `SimPostflopChart` (reused chrome + new action-mix render) + mount/identityKey; consistency test chart==grader; design-review.
