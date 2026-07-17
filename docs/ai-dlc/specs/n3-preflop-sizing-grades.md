# N3 — Preflop sizing grades: open + 3-bet (4-bet+ = shove/call/fold)

**Status:** spec (Gate-2 pending) · **Roadmap slice:** Epic 3 · N3 (supersedes R3b preflop half) · **Consumes:** RES-B · **Outcome-link:** the sizing-verdict half of the north-star, preflop. · **Appetite:** ~1 epic (backend + migration + FE). · **Codex dual-review:** no (sandbox EPERM — Claude `refuter` only).

## 1. Goal / outcome-link
Hero can't choose or be graded on preflop sizing — the app picks the size. N3 offers **two** size options on opens (RFI) and 3-bets, grades the choice as a **separate sizing verdict**, and fixes a real bug: today a standard 4-bet and an all-in shove grade byte-identically (the grader matches by action type, ignoring size). At 4-bet+ hero gets only shove/call/fold (the cap).

## 2. Locked interview decisions (2026-07-17)
- **Verdict data model = two columns, one row.** Keep `SimDecision.correctness` as the ACTION verdict; add a nullable **`sizing_correctness`** column beside it (migration `0011`). N1 dashboard denominator stays byte-identical (`street_report` reads only `correctness`).
- **Sizing heuristic = recommended → optimal, alternative → acceptable.** The app's authored size (chart entry `sizing_bb`) grades **optimal**; a bigger synthesized size grades **acceptable**. Both curated to be reasonable ⇒ the sizing verdict is optimal-or-acceptable, **never a blunder** for the two offered sizes. No invented EV precision.
- **Two sizes ONLY at RFI + VS_RFI + BLIND_DEFENSE** (open + 3-bet). VS_3BET (hero's raise = 4-bet) and beyond stay **single-size shove/call/fold** — no sizing grade (the cap). ≥5-bet pots already unmappable.
- **Synthesis rule** (no authored two-size data): recommended = authored `sizing_bb`; alternative = a bigger derived size — **open: `+1.0bb`**, **3-bet: `round(sizing_bb × 1.25, 1)`** — both **clamped into `[min_bb, max_bb]`, 1-dp**. Tunable in impl; the invariant is legal + displayed==graded.
- **Distinctness fallback (refuter MED):** the clamp ceiling is `max_bb = eff_bb` (hero's stack), so at **short effective stacks** the recommended and alternative can both clamp to `eff_bb` and collapse to equal (R3's collapse mode, but stack-relative). When they can't be made distinct (`alt ≤ recommended` after clamp+round, or `alt > eff_bb`), **fall back to a SINGLE RAISE** (the recommended size) — no two-size offer and `sizing_correctness = NULL` for that spot. Honest "can't support two distinct sizes here" rather than a fake pair. The one helper enforces this for both the graded and displayed paths.
- **Null cases:** `sizing_correctness` is `NULL` when hero doesn't raise (fold/call), at 4-bet+/unmapped nodes, or when the node isn't a two-size node. Action verdict and sizing verdict are **independent** — a raise whose action is off-chart still gets its size classified (they're separate signals).
- **Strict superset:** when ≤1 RAISE is legal, `grade()` output is byte-identical to today (Practice untouched; the 17 `test_grading.py` tests stay green).

## 3. Contract map (full map in `contracts/n3-preflop-sizing-grades.md`)
- **`grade()` moved to the domain core** `backend/app/domain/grading.py:162-248` (purity-tested, `test_domain_purity.py:14`). Collision `sizes={la.action:…}` (`:168`); eval-build `for a in legal` dedups by action-type (`:165,178`) — **must iterate `spot.legal_actions` directly** so each RAISE emits its own eval+size; action-only match `:209`. Mirror `postflop.py::_match()` (`:555-564`, nearest `size_bb`).
- **Only caller** `heuristic.py:42,60`; single provider singleton (`factory.py:37,44`) shared Practice+Simulate; Practice sends one RAISE → superset-safe.
- **Two-size template (R3):** `_is_flop_cbet_node`/`_hero_cbet_legal_actions`/`.extend()` (`sim_session.py:324-373`). Node via `map_decision_point`→`node_context[0]` (mapper `grade_map_preflop.py:62-100`).
- **Schema:** `SimDecision` `db/models.py:88-114`; write `_sim_decision_row` `sim_session.py:231-266`; migration head **`0010`** → add `0011`. Dashboard `street_report` `sim_session.py:584-619` reads only `.correctness` → new column invisible. `GradeView` `schemas/simulate.py:44-54` + mirror `types.ts:246-255`; `_grade_view` `sim_session.py:203-221`. `EvaluationResult` (domain `evaluation.py`) is grade()'s return — carries the verdict out.
- **FE:** `BASE_KEY.raise="R"` (`decisions.ts:11-17`), generic branch `:36-49`; two-BET precedent `~:20-31` (keys B/V). Shortcut set `F/C/R/K/B/V` (`SimActionBar.tsx:29`) — add ONE new key.
- **Frozen-safe:** `spot_signature()` never hashes `size_bb`; anti-sizing-tell (`table/sizing.py`, personas) untouched.

## 4. Changes

> **⚠️ Core fix (refuter HIGH):** the two sizes must reach the **graded `Spot`**, not just the FE display. Simulate grades via a SEPARATE spot from `map_decision_point → map_preflop → _preflop_spot → build_spot`, which emits ONE RAISE. **Verified: `map_decision_point`/`map_preflop` are called ONLY from `sim_session.py`** (grading `:527`, hero-size `:294`, chart `:690/:748`); **Practice (`drill.py`) never uses them** — it builds via `scenarios.build_spot` directly and grades the FE-submitted spot. So N3 injects the two graded sizes **in `apply_hero_action` (sim_session), right after `map_decision_point` and before grading** — NOT in `map_preflop`/`build_spot` (which would distort the preflop chart at `:690/:748` and is shared with Practice's builder). This keeps the two-size behavior Simulate-grading-only; Practice's `build_spot` path and the chart stay single-RAISE ⇒ strict superset holds.

### 4a. Shared size-synthesis helper (`sim_session.py`)
- One helper `_preflop_two_sizes(recommended, min_bb, max_bb, node) -> list[float]`: recommended = the node's authored size (the original single RAISE's size / `entry.sizing_bb`); alternative = synthesized bigger (**open `+1.0bb`**, **3-bet `round(rec×1.25,1)`**); both clamped to `[min_bb, max_bb]`, 1-dp. **Distinctness fallback:** if the two collapse (short eff-stack squeezes both to the same clamp ceiling, or alt ≤ recommended after rounding), **return ONE size** (recommended) — no two-size offer, no sizing grade for that spot. Used by BOTH the graded-spot rewrite (4b) and the display path (4c), so displayed == graded by construction.

### 4b. Inject two sizes into the GRADED spot (`sim_session.py::apply_hero_action`) — the fix
- After `spot = map_decision_point(state, HERO_SEAT)` (`:527`) and before `evaluate(spot, decision)` (`:530`): when `spot.street is PREFLOP` and `spot.node_context[0] in {RFI, VS_RFI, BLIND_DEFENSE}`, replace the single RAISE `LegalAction` with **two** RAISE `LegalAction`s (sizes from `_preflop_two_sizes`) via `model_copy`. VS_3BET+ and the fallback-single case leave the one RAISE untouched. Now `grade()` sees two RAISE options and can classify the size. **Only this call site is rewritten** — the chart (`:690/:748`) and hero-size (`:294`) `map_decision_point` calls stay single-RAISE.

### 4c. Display path (`sim_session.py::_hero_legal_actions`)
- New `_hero_open_or_3bet_legal_actions(la, state)` (mirror `_hero_cbet_legal_actions`) uses the SAME `_preflop_two_sizes` helper; `.extend()` two `LegalAction(RAISE)` for RFI/VS_RFI/BLIND_DEFENSE, gated identically. Fallback → one. Displayed sizes == graded sizes by construction (same helper).

### 4d. Grader — per-raise evals + `_match()` + sizing verdict (`domain/grading.py`, `domain/evaluation.py`)
- Rewrite the eval-build so **each `spot.legal_actions` RAISE yields its own `ActionEval` with its own `size_bb`** (kill the ActionType-keyed `sizes` collision at `:168`). Add a preflop `_match(evals, decision)` mirroring `postflop._match`: fold/call/check by action; RAISE by nearest `size_bb` (`min(..., key=abs(size-target))`, `target None → first raise eval`). **≤1 RAISE ⇒ byte-identical to today's `next(...)`** (Practice + 4-bet+).
- **Sizing verdict (self-contained in `grade()`):** when hero's action is RAISE and the spot carries **≥2 RAISE evals**, `sizing_correctness` = **OPTIMAL** if hero matched the **smallest** raise size (= recommended, by the synthesis rule), else **ACCEPTABLE** (the bigger alt). Else `None` (single-raise / non-raise / fold / call). No extra plumbing — read off `spot.legal_actions`. Add additive `sizing_correctness: Correctness | None` to `EvaluationResult` (`evaluation.py`), default `None`.
- Stays pure (no web/DB) — purity test must remain green.

### 4e. Persistence (`db/models.py`, `alembic/versions/0011_*.py`, `sim_session.py`)
- `SimDecision`: add `sizing_correctness: str | None = Field(default=None)`.
- Migration `0011` (`down_revision="0010"`): `op.add_column("sim_decision", sa.Column("sizing_correctness", sa.String(), nullable=True))`; `down` drops it. Existing rows read back unchanged.
- `_sim_decision_row`: write `sizing_correctness` from the `EvaluationResult`.

### 4f. API surface (`schemas/simulate.py`, `types.ts`, `sim_session.py`)
- `GradeView`: additive `sizing_correctness: str | None`. `_grade_view` populates it. FE `types.ts` `GradeView` mirror (hand-edit).

### 4g. FE two-raise UX (`decisions.ts`, `SimActionBar.tsx`)
- `legalDecisions`: RAISE-aware two-size branch mirroring the two-BET one — filter `action==="raise"`, if `>1` assign distinct keys (`"R"` small / a NEW key e.g. `"E"` big+primary) and labels ("Raise small ${bb}bb" / "Raise big ${bb}bb"). Both keyboard-reachable.
- `SimActionBar.tsx`: document the new shortcut in the `F/C/R/K/B/V` comment; render unchanged (pure consumer).

### 4h. Display the sizing verdict (`SimRecap.tsx`, `SimTable.tsx` `SimVerdictBadge`)
- When `sizing_correctness != null` (coach mode only — N2 already gates visibility), show it as a **secondary sub-note** alongside the action verdict (e.g. recap row appends "· size: OK/Best"; badge optional). Additive, tone-consistent with `tierOf`. Does not alter the action verdict display.

## 5. Pass/fail
- Hero opening (RFI) or 3-betting (VS_RFI/BLIND_DEFENSE) sees **two** graded size options; choosing recommended → **OPTIMAL** sizing verdict, the bigger alt → **ACCEPTABLE**; persisted to `sim_decision.sizing_correctness`.
- **Engages end-to-end, not just in unit tests (refuter HIGH):** on a real Simulate open/3-bet hand, the GRADED spot from `apply_hero_action` carries two RAISE legal actions and `sizing_correctness` actually populates — assert via a `sim_session`-level test that plays an RFI hand and reads back the persisted `sizing_correctness` (not only a hand-built `grade()` unit test).
- **Chart + Practice stay single-RAISE:** the preflop chart (`map_decision_point` at `:690/:748`) and Practice (`build_spot`) still build ONE RAISE — assert the chart's action mix + Practice grading are unchanged (the two-size rewrite is scoped to `apply_hero_action` only).
- **Standard-4bet vs shove no longer grade identically** — a new direction test: two RAISE sizes at a VS_3BET/VS_4BET-style single-node produce distinguishable evals via `_match` (the collision fix), even though N3 offers no *choice* there.
- At **4-bet+** only shove/call/fold is offered (no second size), and the sizing verdict is `NULL`.
- **Practice single-raise flows byte-unchanged** — the existing `test_grading.py` suite (17) stays green; `_match()` is a strict superset (identical output when ≤1 RAISE legal, incl. CALL/BET/FOLD/CHECK); add the standard-vs-shove direction test + a two-RAISE `_match` test + a VS_4BET-stays-single-size test.
- **Migration `0011` up/down clean**; existing `sim_decision` rows read back unchanged; head advances 0010→0011.
- **N1 dashboard denominator byte-unchanged** — `street_report` `total_decisions`/`graded` counts numerically identical before/after (assert on the same DB).
- **Two offered sizes always distinct + within `[min_bb,max_bb]`**, OR the spot falls back to a single RAISE with `sizing_correctness=NULL` (short-stack collapse case) — never two equal sizes (regression vs the R3 collapse); **displayed size == graded size** (1-dp parity, same helper both paths).
- **Both raise options keyboard-reachable** (distinct keys); recap shows the sizing verdict in coach mode; hidden in real-play (N2).
- **Anti-sizing-tell intact** (bot sizing untouched); `spot_signature()` + `TAXONOMY_VERSION` unchanged; **domain purity test green**.
- `./scripts/verify.sh` + `cd frontend && npm run typecheck && npm run build` green; design-review both themes.

## 6. Refuter-target risks
- **Does the fix actually reach the graded spot? (refuter HIGH — resolved, re-verify at build):** the two sizes are injected in `apply_hero_action` after `map_decision_point`, so the graded spot carries two RAISEs. Confirm the injection fires on real hands AND that the chart (`:690/:748`) / hero-size (`:294`) `map_decision_point` calls are NOT rewritten (single-RAISE), and Practice's `build_spot`/`drill.py` path is untouched.
- **Collision fix completeness:** proving `_match()` alone isn't enough — if the eval-build still collapses two RAISEs into one `ActionEval`, there's nothing to disambiguate. Verify BOTH the eval-build (one eval per legal RAISE with distinct size) AND the match are fixed.
- **Strict superset:** any behavior change when ≤1 RAISE is legal = a Practice regression. Prove byte-identical output for the single-raise path (run `test_grading.py` + a diff on a fixed spot).
- **Cap boundary:** the two-size branch must gate strictly on RFI/VS_RFI/BLIND_DEFENSE; VS_3BET (hero 4-bet) must NOT gain a second size. Verify the node_context gate.
- **Distinct sizes:** small≠big after clamp+round on every node (the R3 wet-board lesson) — including when `min_bb`/`max_bb` squeeze the pair.
- **Denominator safety:** confirm `street_report` counts are numerically identical (the whole reason "two columns" beat "two rows").
- **Purity:** the new `_match`/sizing logic in `domain/grading.py` must not import web/DB — purity test.
- **Migration reversibility:** down-migration drops the column cleanly; forward re-applies; no data loss on existing rows.
- **FE key collision:** the new raise key must not clash with `F/C/R/K/B/V`; both raises reachable by keyboard + mouse.

## 7. File ownership
N3 owns: **backend** `app/domain/grading.py`, `app/domain/evaluation.py` (additive field), `app/services/sim_session.py` (**hotspot**: the `_preflop_two_sizes` helper + the **graded-spot rewrite in `apply_hero_action`** + the display path `_hero_legal_actions` + `_sim_decision_row` write + `_grade_view`), `app/db/models.py`, `app/alembic/versions/0011_*.py` (new), `app/schemas/simulate.py`, `backend/tests/test_grading.py` + a new `sim_session`-level end-to-end sizing test; **frontend** `src/api/types.ts` (**hotspot**, hand-edit), `src/lib/decisions.ts`, `src/components/simulate/SimActionBar.tsx`, `src/components/simulate/SimRecap.tsx`, `src/components/simulate/SimTable.tsx` (badge sub-note). **Deliberately does NOT touch** `grade_map_preflop.py`/`scenarios.py`/`build_spot` — injecting the two sizes in `apply_hero_action` (not the shared mapper/builder) is what keeps the change Simulate-grading-only, leaving Practice's `build_spot` path and the preflop chart single-RAISE. Also untouched: `table/sizing.py`/personas (anti-tell), `srs.py` (frozen signature), N1's `SimDashboard`/`street_report` denominator.

> ⚠️ Backend chain is largely sequential: `evaluation.py` + `models.py` (schema) → migration `0011` → `grading.py` (grader) → `sim_session.py` (emit+write+view) → `schemas`. FE (`types.ts` → `decisions.ts` → display) after the API field exists. Limited parallelism.

## 8. Tickets (outline — see tickets/n3-preflop-sizing-grades.md)
- **T1** — Schema: `EvaluationResult.sizing_correctness` (domain) + `SimDecision.sizing_correctness` + migration `0011` (up/down + read-back test).
- **T2** — Grader: fix eval-build (per-RAISE evals) + `_match()` + sizing verdict in `grade()`; strict-superset + direction + two-RAISE-match tests; purity green.
- **T3** — Emission: two-size RFI/3-bet in `_hero_legal_actions`; cap gate; distinct+parity; write `sizing_correctness` in `_sim_decision_row`; `_grade_view` + `GradeView` field.
- **T4** — FE: `types.ts` mirror; `decisions.ts` RAISE two-size branch + new key; `SimActionBar` shortcut doc; recap/badge sizing sub-note.
- **T5** — Verify/design-review: `verify.sh` + `typecheck`/`build` green; dashboard denominator-unchanged assert; design-review the two-raise UI + sizing verdict both themes.
