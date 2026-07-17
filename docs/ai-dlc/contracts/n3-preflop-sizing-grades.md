# N3 contract map — preflop sizing grades (read-only scan, 2026-07-17, post #43/#44)

Slice touches the **Practice-shared** preflop grader (now in the **domain core**) + a **migration**. Anchors verified against current tree.

## The grader (moved!)
- `grade()` now lives at **`backend/app/domain/grading.py:162-248`** (moved into domain during #43; covered by `backend/tests/test_domain_purity.py:14`). Any helper N3 adds here must keep passing the no-web/DB-imports purity test.
- **Collision:** `sizes = {la.action: la.min_bb for la in spot.legal_actions}` (`grading.py:168`) — ActionType-keyed; two RAISE entries → second overwrites first.
- **Eval build:** `for a in legal` (`grading.py:178`), `legal = [la.action …]` (`:165`) — one `ActionEval` per distinct action-type. **Must rewrite to iterate `spot.legal_actions` directly** so each RAISE emits its own eval with its own `size_bb`.
- **Match (action-only):** `ce = next((e for e in evals if e.action == decision.action), None)` (`grading.py:209`) — ignores size. N3 adds a nearest-`size_bb` `_match()`.
- **Precedent to mirror:** `backend/app/domain/postflop.py::_match()` (`:555-564`) — CHECK/fold by action; BET by `min(bet_evals, key=lambda e: abs((e.size_bb or 0)-target))`; `target is None → bet_evals[0]`. Facing graders with ONE raise deliberately keep plain `next(...)` (`postflop.py:715,904`) — the precedent for "one size ⇒ match by action" (= the strict-superset degrade for 4-bet+).

## Strict superset / blast radius
- **Only caller:** `HeuristicProvider._grade` (`backend/app/domain/providers/heuristic.py:42`, self-call `:60`). Single provider singleton via `factory.py:37,44`, shared by Practice (`api/v1/drill.py`) AND Simulate (`sim_session.py:113-120`). → any `grade()` change reaches Practice.
- Practice constructs only ONE `LegalAction(RAISE)` per grade() call (two-size emission is Simulate-only in `sim_session.py`). So Practice's `spot.legal_actions` stays single-RAISE ⇒ if `_match()` degrades to `next(...)` for ≤1 raise, Practice is byte-unchanged.
- **17 tests** in `backend/tests/test_grading.py` (incl. `test_aa_jam_vs_4bet_is_optimal`/`test_72o_jam_vs_4bet_is_blunder` at `:163-178` — single-RAISE VS_4BET jam, must stay green).

## Two-size emission (R3 template to mirror)
- `_is_flop_cbet_node()` (`sim_session.py:324-330`) + `_hero_cbet_legal_actions()` (`:333-346`, fixed 0.33/0.75-pot pair, clamped, `.model_copy(update={min_bb:…, size_bb:None})`) + `.extend()` in `_hero_legal_actions()` (`:349-373`, the BET branch `:359-361`).
- **Node detection (free):** `map_decision_point(state, HERO_SEAT)` already called in `_hero_preflop_size_bb` (`sim_session.py:294`); inspect `spot.node_context[0]`. Preflop mapper (`grade_map_preflop.py:62-100`): `len(raises)==0`→RFI, `==1`→VS_RFI/BLIND_DEFENSE (hero raise = 3-bet), `==2`→VS_3BET (hero raise = **4-bet, the cap**), `==3`→VS_4BET, `>=4`→already `None`. **Two sizes ONLY at RFI + VS_RFI + BLIND_DEFENSE; VS_3BET and beyond stay single-size shove/call/fold.**

## The two sizes (must synthesize — no authored data)
- `Entry.sizing_bb` (`content/models.py:49`) is a SINGLE `float|None` per entry (verified: `content/preflop/rfi.json` single `sizing_bb` values). No two-size preflop table wired anywhere. `_OPEN_SIZE` (`scenarios.py:62`) + `HERO_NODE_SIZE` (`table/sizing.py:22-29`, postflop) are single-valued. **N3 synthesizes the 2nd size** (recommended = authored `sizing_bb`; alternative = a bigger derived size), like R3 synthesized the pot-fraction pair. Must guarantee small≠big after clamp+1dp (R3 wet-board-collapse lesson).

## Schema / migration
- `SimDecision` (`backend/app/db/models.py:88-114`): id, owner_id, session_id, sim_hand_id, street, ordinal, chosen_action, **correctness (nullable)**, ev_loss_bb, leak_category (nullable), coverage, created_at.
- Write: `_sim_decision_row()` (`sim_session.py:231-266`), one `db.add` per decision (`:534`).
- **Migration head = `0010`** (`backend/alembic/versions/0010_sim_decision_and_source.py`). N3 adds `0011` (`down_revision="0010"`), additive nullable `sizing_correctness` column (pattern = `0010`'s nullable adds).
- **Dashboard read (`street_report()` `sim_session.py:584-619`):** per-row count on `.correctness`; `total_decisions = graded + no_baseline` (`:618`). **A new column it never reads = zero impact; denominator byte-unchanged** (this is why "two columns, one row" was chosen over "two rows").
- `GradeView` (`schemas/simulate.py:44-54`): street, ordinal, chosen_action, correctness, ev_loss_bb, coverage, verdict, reasoning. Mirror `frontend/src/api/types.ts:246-255`. `_grade_view()` (`sim_session.py:203-221`). Add additive `sizing_correctness`.
- `EvaluationResult` (domain, `evaluation.py`) is what `grade()` returns — add additive `sizing_correctness` there too so the verdict rides out of the pure grader.

## FE two-raise branch
- `BASE_KEY` (`decisions.ts:11-17`) → `raise:"R"`; generic branch (`:36-49`) gives every raise key `"R"`. Two raises collide → 2nd keyboard-unreachable (`SimActionBar.tsx:45` first-match). React render safe (`key={i}` index).
- R3 two-BET precedent: `decisions.ts:~20-31` (filter bets, `bets.length>1`, keys `"B"`/`"V"`, "Bet small/big" labels). Mirror for RAISE with a NEW key (existing set `F/C/R/K/B/V` — `SimActionBar.tsx:29` — add one, e.g. `"E"`).

## Anti-sizing-tell / signature / purity
- Bot sizing `table/sizing.py::preflop_raise_to()` (`:99-123`) + `PersonaSizing` untouched — N3 only touches HERO legal actions + grader. Confirmed separate.
- `spot_signature()` (`srs.py:48-68`) never reads `size_bb`; `LegalAction.size_bb` "not hashed" (`spot.py:121-123`). Frozen-safe.
- `TAXONOMY_VERSION` unchanged.
