# Spec — Phase 1b: Facing Aggression (vs-3-bet + vs-4-bet) + stack-depth variety

> Delta spec for **Phase 1b** only. Builds on Phase 0/1a (no rebuild). Roadmap: `docs/ai-dlc/roadmap.md`. Strategy source: `docs/research/01-preflop-strategy.md`. STOP at the plan gate — no code until approved.

## Goal (one line)
Complete the preflop aggression tree — **you open and face a 3-bet (4-bet/call/fold)** and **you 3-bet and face a 4-bet (jam/call/fold)** — reusing the existing frequency-tolerant grading + SM-2 + leak + modes loop, and add **light stack-depth variety** (75/100/150bb).

## In scope
1. **Content packs** `content/preflop/vs_3bet.json`, `content/preflop/vs_4bet.json` (research tiers, value-heavy at these stakes):
   - `vs_3bet`: hero opened from `position`, a 3-bettor at `facing` 3-bets → **4-bet (value+bluff) / call / fold**, keyed by (hero position × 3-bettor position).
   - `vs_4bet`: hero 3-bet from `position`, original opener at `facing` 4-bets → **jam / call / fold** (mostly fold; jam/call AA/KK/AK), keyed by (hero position × 4-bettor position).
2. **Sampler** builds the deeper action histories + legal actions + pots (below) and randomizes effective stack across **{75, 100, 150}bb** (content stays depth-agnostic; the depth-bucketed `spot_signature` already separates SRS items by bucket).
3. **Leak mapping** (no grading-engine change): `vs_3bet` → `VS_3BET_IP`/`VS_3BET_OOP` (by IP/OOP rule below); `vs_4bet` → `FOURBET_RESPONSE`. (All already reserved in `leaks.py`.)
4. **Small UI add**: a one-line **betting-line summary** in `PokerTable` (e.g. "CO opens 2.5 · BTN 3-bets 9") so facing-aggression spots are legible. Everything else (multi-action bar, colored grid, modes, stats) already handles the new nodes.

## Reused without change
Grading **math** (`grading.py`: proxy-EV, correctness tiers, `is_mixed`), `EvaluationResult`, SM-2, stats, drill modes, and `range_grid` all work for the new nodes unchanged. A 4-bet and a jam are both `raise`. *(Note: `range_grid` for a fold-heavy vs_4bet node will be mostly grey with small raise/call islands — correct, just sparse.)*
The ONLY grading change is the leak mapping (below).

## Canonical node_context strings (casing footgun)
Author the new packs with exactly `"vs_3bet"` and `"vs_4bet"` (matching `NodeContext.VS_3BET`/`VS_4BET`). Note the existing vs_rfi pack uses `"vs_RFI"` — don't copy that casing.

## IP/OOP rule + the leak_category_for change (blocking fix)
`leak_category_for` currently takes `(ctx, position)` and cannot see the opponent. **Change its signature to `leak_category_for(ctx, position, facing=None)`**; `_leak_for(spot)` passes `spot.facing`, and the `leak_focus` call site in `drill.py` passes `entry.facing` (an `Entry` already carries `facing`). Audit both call sites.
IP/OOP uses **postflop** seat order (later = in position): `SB<BB<UTG<UTG1<UTG2<LJ<HJ<CO<BTN`. For `vs_3bet`, hero is **IP** vs the 3-bettor if hero's seat is later than `facing`'s, else **OOP** → `VS_3BET_IP`/`VS_3BET_OOP`. (Use postflop order, NOT preflop action order.) `vs_4bet` → `FOURBET_RESPONSE` (no IP/OOP split).

## Sampler action-history contract (per new node) — with golden fixtures
Sizes (total-to amounts in the history): open = position open-size (existing `_OPEN_SIZE`); 3-bet ≈ 3× open; 4-bet ≈ 2.3× the 3-bet; jam = effective stack. `pot_bb` = sum of all chips in (blinds + every raise's total-to).

**Call-amount convention (blocking fix, applies to ALL nodes incl. retro 1a):** a `LegalAction(call).min_bb` = the **incremental** chips hero must add = (amount to match) − (hero's chips already in). E.g. BB calling a 2.5 open = **1.5** (BB already posted 1.0), not 2.5; hero calling a 4-bet of 17.25 after 3-betting to 7.5 = **9.75**. Fix the existing 1a sampler call amounts (vs_rfi/blind_defense/vs_limpers) to this convention too. *(Grading correctness doesn't depend on the call magnitude — this fixes the displayed call size.)*

**Other sampler rules:** `facing` appears exactly **once** in `players` even when it acts twice (vs_4bet). For vs_4bet the raise is a **jam** → set its `min_bb`/`max_bb` = `eff_bb` (do NOT use `entry.sizing_bb`). Guard: reject/skip any entry where `position == facing` (a hero can't face themselves) — add a content sanity test.

- `vs_3bet`: history = blinds · hero(open) raise · `facing`(3-bettor) raise(3-bet). legal = fold / call(incremental to 3-bet) / raise(4-bet = `entry.sizing_bb`). hero `to_act`.
- `vs_4bet`: history = blinds · `facing`(opener) raise(open) · hero raise(3-bet) · `facing`(4-bettor) raise(4-bet). legal = fold / call(incremental to 4-bet) / raise(jam = `eff_bb`). hero `to_act`. `facing` listed once in `players`.
A golden fixture pins one `vs_3bet` and one `vs_4bet` Spot shape with **exact** numeric pot + call amounts.

## Files to touch
`content/preflop/{vs_3bet,vs_4bet}.json` (new) · `backend/app/domain/grading.py` (leak mapping + IP/OOP helper) · `backend/app/domain/scenarios.py` (new node histories + depth variety) · tests (`test_ranges.py`, `test_grading.py`, `test_scenarios.py`) · `frontend/src/components/PokerTable.tsx` (betting line) · `frontend/src/api/types.ts` if needed.

## Out of scope (deferred)
- **Squeeze / multiway preflop**, **mastery-gating** (its own slice), **depth-specific content** (light variety only here).
- **Backlog:** soften off-chart grading severity (marginal calls currently over-graded as BLUNDER) — tracked, not in 1b.
- ALL postflop · solver tables · live session logger.

## Constraints
Preflop/live/simplified · grading stays behind `StrategyProvider`; results stay freq+EV+coverage+is_mixed · domain pure · content as versioned data · no new migration (no new tables) · CSS tokens (betting-line uses existing tokens) · any new deps → `RUN-THESE-COMMANDS.md`.

## Verify-by
1. `pytest` green incl: range sanity for vs_3bet/vs_4bet (4-bet ranges value-heavy: AA/KK/AK present; vs_4bet continue range tight — AA/KK present, low offsuit absent) **and no entry has `position == facing`**; named-hand anchors for the new nodes (AA jam-vs-4bet = OPTIMAL; 72o 4-bet = BLUNDER); **IP/OOP leak mapping** (CO-opens-vs-BTN-3bet → VS_3BET_OOP; BTN-opens-vs-BB-3bet → VS_3BET_IP); **incremental call amounts** (BB calling a 2.5 open = 1.5; vs_4bet call = exact golden value); sampler golden fixtures for vs_3bet/vs_4bet with exact pot+call; depth variety produces ≥2 stack buckets; domain purity.
2. Backend boots; `/drill/next?mode=random` can return vs_3bet/vs_4bet spots with valid histories; `/drill/grade` grades them (freq+EV+coverage+is_mixed); existing routes unaffected.
3. Frontend builds; live (Playwright): a vs_3bet spot shows the betting line, offers fold/call/raise(4-bet), grades correctly, grid colors the 4-bet/call/fold range.
4. CSS contrast/token check passes.
