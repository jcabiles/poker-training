# R3 — Hero bet-sizing: two size options (flop c-bet only)

**Status:** spec — Gate-2 scoped to flop-c-bet-only (2026-07-16) · **Consumes:** `docs/ai-dlc/research/RES-B-bet-sizing.md` §6.3 · **Wave:** W1 (‖ R4 ‖ R5) · **After:** R2 (extends its `LegalAction.size_bb` seam) · **Appetite:** ~1 small epic. · **Deferred to R3b:** vs-3bet/vs-4bet + turn/river/check-raise size grading (needs `grade()` size-matching).

## 1. Goal / outcome-link
Hero can't choose a bet size — a real $2/$3 skill the trainer omits. R3 surfaces **two** context-specific size options per supported node and grades the choice (freq+EV, approximate). Sizing decisions become gradeable.

## 2. Locked scope — FLOP C-BET ONLY (Gate-2, 2026-07-16)
**Narrowed from 3 nodes to 1** after the W1 refuter (FAIL) proved the preflop grader `grading.py::grade()` matches by `ActionType` only — a standard 4-bet and a shove grade **byte-identically** (both `RAISE`; `sizes` dict collides, `next(e.action==...)` ignores size). vs-3bet/vs-4bet therefore need size-matching built into the Practice-shared grader → **deferred to R3b** (after R3 + R5). See `roadmap/simulate-table.md` R3b.
- **This slice = the flop c-bet size choice only:** two BET options **0.33 / 0.75 pot as a fixed pair**. The existing `grade_cbet` (`postflop.py`) already scores by size — **no grader change**. FE `legalDecisions` already renders two BETs (keys B / V) — **no RAISE-branch work** (that's R3b).
- **Size-verdict folds into existing `Correctness` + `ev_loss_bb`** — NO new column, NO migration.
- **Wet/mono-board fix (refuter HIGH):** the two sizes must be a **fixed 0.33/0.75 pair**, NOT `HERO_NODE_SIZE[node]` + 0.75 — because `HERO_NODE_SIZE["cbet_wet"]==0.75` would collapse small==big into two identical bets. Mirror `map_flop_cbet`'s unconditional `round(0.33*pot,1)` / `round(0.75*pot,1)`.
- **Displayed == graded (refuter LOW):** `_hero_legal_actions` must round to the SAME precision `map_flop_cbet` uses (1 dp) so the shown size matches the graded size.

## 3. Contract map (from R3 scan, file:line anchors)
- **R2 seam:** `HERO_NODE_SIZE` (`backend/app/domain/table/sizing.py:22-29`) = ONE fraction per node; its docstring (`sizing.py:19-21`) literally names it "the size R3 will later offer as one of two options." `postflop_node_key` (`sizing.py:43-70`), `pot_fraction_to_bb` (`sizing.py:73-85`).
- **Hero legal actions today emit ONE size** — `sim_session.py:321-338` `_hero_legal_actions` → `la.model_copy(update={"size_bb": size})`, one per BET/RAISE. Base engine `legal_actions` (`engine.py:179-206`) returns one BET / one RAISE per node.
- **`LegalAction.size_bb`** (`spot.py:117-123`) — optional, **NOT hashed by `spot_signature()`** (confirmed `srs.py:48-68` reads no bet size). Adding a 2nd LegalAction to `legal_actions` is signature-safe by construction.
- **Flop c-bet size grading ALREADY EXISTS** — `postflop.py::grade_cbet`: `_bet_sizes` (`postflop.py:438-442`) reads `spot.legal_actions` for BET entries (small=`bets[0]`, big=`bets[-1]`); `_match` (`postflop.py:555-564`) picks the chosen `ActionEval` by nearest `size_bb`; verdict `postflop.py:519` requires action+size match for OPTIMAL, else EV-loss-tiered. **It only fires when the graded `Spot` carries 2 BET entries** — today that happens only inside `map_flop_cbet` (`grade_map_postflop.py:119-123`, the 0.33/0.75 pair), NOT in the live `SessionView.legal_actions`.
- **Preflop grading has NO size verdict** — `grading.py::grade` scores `ActionType` only via chart-mix; `sizes` (`grading.py:168`) is display-only. **vs-3bet / vs-4bet size grading = NEW machinery R3 must build.**
- **FE two-size is half-ready:** `frontend/src/lib/decisions.ts:22-51` `legalDecisions` handles two **BET** sizes (keys B / V) — the flop c-bet case works once the backend sends two BETs. But **RAISE is not handled** by the two-size branch → two RAISE `LegalAction`s would collide on duplicate key `R`. `SimActionBar.tsx:24` already calls `legalDecisions`. `types.ts` `LegalAction` already mirrors `size_bb`.

## 4. Changes (flop c-bet only)
### 4a. Emit two BET options for the flop c-bet
- `sim_session.py` `_hero_legal_actions` / `_hero_postflop_size_bb`: when the node is the flop c-bet (`postflop_node_key`==`cbet_*` and hero is the aggressor), emit **two** `LegalAction(BET)` — `small=round(0.33*pot,1)`, `big=round(0.75*pot,1)` (a **fixed pair**, texture-independent — NOT `HERO_NODE_SIZE[node]`, which collapses on wet/mono boards). Round to 1 dp so displayed==graded.
- The existing `grade_cbet` (`postflop.py`, `_bet_sizes`/`_match`) grades the choice with **zero grader change** — it already picks the chosen `ActionEval` by nearest `size_bb` and tiers OPTIMAL/ACCEPTABLE/MISTAKE/BLUNDER by EV-loss.
- Guarantee the LIVE `SessionView.legal_actions` (what FE shows) and the graded Spot from `map_flop_cbet` carry the **same** two sizes (parity — refuter risk).

### 4b. Frontend — none beyond what exists
- `legalDecisions` (`decisions.ts:22-51`) already renders two BET actions as "Bet small" (B) / "Bet big" (V). No change needed. **No RAISE-branch work in R3** (that's R3b, where two-RAISE nodes appear).
- No `types.ts` change (`size_bb` already present).

> **Deferred to R3b:** vs-3bet/vs-4bet two-RAISE options, the `grading.py::grade()` size-matching upgrade + alternate-size EV heuristic, and the `decisions.ts` RAISE-aware two-size branch. See roadmap R3b.

## 5. Pass/fail
- Hero c-betting the flop sees **two** BET options in `SimActionBar` (Bet small 0.33 / Bet big 0.75).
- Choosing a size yields a freq+EV verdict (approximate) persisted via existing `correctness`/`ev_loss_bb` — **no new column** (assert schema + migration head unchanged).
- **Wet/mono board still shows two DISTINCT sizes** (regression test for the `HERO_NODE_SIZE`==0.75 collapse the refuter caught).
- **Displayed size == graded size** (parity test: the `SessionView.legal_actions` sizes equal the `map_flop_cbet` Spot's sizes, same 1-dp rounding).
- Non-c-bet nodes still emit a single size + grade as today (unchanged).
- **Anti-sizing-tell intact:** bot sizing (`personas_postflop.py`) untouched.
- `verify.sh` + `cd frontend && npm run typecheck && npm run build` green; design-review the two-size c-bet UI both themes.

## 6. Refuter-target risks
- Does emitting two BET LegalActions in the LIVE `SessionView` (4a) change what `map_flop_cbet` builds for grading, or double-count? Confirm displayed and graded sizes agree.
- Wet/mono-board pairing: prove small≠big on every texture (the fixed 0.33/0.75 pair, not `HERO_NODE_SIZE`).
- Confirm `spot_signature()` / `_postflop_signature` untouched by adding a 2nd LegalAction (scan says safe — verify the postflop signature path too).

## 7. File ownership (W1 disjointness)
R3 owns: `sim_session.py` (`_hero_legal_actions`, `_hero_postflop_size_bb`), new tests. **Does NOT touch** `content/preflop/*` or `grade_map_preflop.py` (R4); `postflop.py` graders or `grade_map_postflop.py` (R5); **`grading.py`** (that's R3b). Uses `grade_cbet` + `legalDecisions` **as-is** (no edit). No `types.ts`/`decisions.ts` change. Clean disjoint.
> ⚠️ `sim_session.py` is also touched by R5 (`postflop_chart` service). Disjoint functions (`_hero_legal_actions` vs a new read-only `postflop_chart`) — lead integrates at fan-in; if both land big hunks, serialize.
> ⚠️ Relies on `grade_cbet` existing behavior only. If a build wants to *modify* `postflop.py`, STOP — R5's file.

## 8. Tickets (outline)
- **T1** — Emit two fixed-pair BET LegalActions (0.33/0.75, 1-dp) for the flop c-bet node in `_hero_legal_actions`; existing `grade_cbet` grades the choice.
- **T2** — Tests: wet/mono two-distinct-sizes regression; displayed==graded parity; verdict tiers on the size choice; signature-unchanged; anti-tell; design-review.
