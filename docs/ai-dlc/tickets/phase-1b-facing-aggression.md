# Tickets — Phase 1b: Facing Aggression (vs-3-bet + vs-4-bet)

Spec: `docs/ai-dlc/specs/phase-1b-facing-aggression.md`. 5 tickets, small, one-file-one-owner.

> **STATUS: BUILT (2026-06-28).** T1–T5 done. 80 backend tests green; `scripts/verify.sh` boots + samples vs_3bet/vs_4bet + grades; frontend typechecks + builds. Live Playwright UI check pending a running dev server.

## DAG / waves
```
T1 ─┐
T2 ─┴─ T3 ─ T4 ─ T5
```
- W1: **T1, T2** (parallel — disjoint files)
- W2: **T3** (needs T2's content for coverage)
- W3: **T4**
- W4: **T5**
Single-agent: T1→T5 in order.

---

### T1 — Leak mapping (facing-aware) + new-node grading anchors
Change `leak_category_for(ctx, position, facing=None)`; compute IP/OOP for `vs_3bet` (postflop seat order) → `VS_3BET_IP`/`VS_3BET_OOP`; `vs_4bet` → `FOURBET_RESPONSE`. Update `_leak_for` (pass `spot.facing`) and the `leak_focus` call site in `drill.py` (pass `entry.facing`).
- **Owns:** `domain/grading.py`, the one `leak_category_for(...)` line in `api/v1/drill.py`, `tests/test_grading.py`.
- **Depends:** —
- **Done when:** anchors pass — AA jam-vs-4bet = OPTIMAL, 72o 4-bet = BLUNDER (synthetic entries); CO-vs-BTN-3bet → VS_3BET_OOP, BTN-vs-BB-3bet → VS_3BET_IP.

### T2 — Content packs (vs_3bet, vs_4bet) + range sanity
Author `content/preflop/vs_3bet.json` (4-bet value+bluff / call / fold) and `vs_4bet.json` (jam / call / fold, fold-heavy) using exact `node_context` strings `"vs_3bet"` / `"vs_4bet"`. Add range-sanity tests.
- **Owns:** `content/preflop/{vs_3bet,vs_4bet}.json`, `tests/test_ranges.py` (additions).
- **Depends:** —
- **Done when:** packs validate + load; 4-bet ranges contain AA/KK/AK; vs_4bet continue ranges tight (AA/KK present, low offsuit absent); **no entry has `position == facing`**.

### T3 — Sampler: new-node histories + incremental call fix + depth variety
Build `vs_3bet`/`vs_4bet` spots (histories per spec, `facing` once in `players`, jam = `eff_bb`). Fix `LegalAction(call).min_bb` to the **incremental** amount across ALL nodes. Randomize eff ∈ {75,100,150}. Golden fixtures with exact pot+call.
- **Owns:** `domain/scenarios.py`, `tests/test_scenarios.py`.
- **Depends:** T2.
- **Done when:** golden vs_3bet/vs_4bet fixtures pass with exact pot+call; BB-call-open = 1.5; every authored entry samples to full coverage; depth variety yields ≥2 stack buckets.

### T4 — Frontend betting-line
Add a one-line betting-line summary to `PokerTable` (e.g. "CO opens 2.5 · BTN 3-bets 9") from `action_history`; confirm multi-action bar + colored grid render for the new nodes.
- **Owns:** `frontend/src/components/PokerTable.tsx` (+ `api/types.ts` if needed).
- **Depends:** T3.
- **Done when:** `vite build` + typecheck clean; a vs_3bet spot shows the line + fold/call/raise(4-bet).

### T5 — Verify sweep + docs
Extend `scripts/verify.sh` to assert random mode can yield vs_3bet/vs_4bet and grades them; update README + roadmap + tickets status.
- **Owns:** `scripts/verify.sh`, `README.md`, roadmap/ticket status.
- **Depends:** T1–T4.
- **Done when:** full verify-by runs green via one command; live Playwright check of a vs_3bet spot passes.

---

## Notes
- No new migration (no new tables). No new backend deps.
- Incremental-call fix is shared in `scenarios.py` (T3) — existing 1a tests don't assert call magnitudes, so they won't break; T3 adds the assertions.
