# Spec — Phase 1a: Real Preflop Trainer (opens + defense + vs-limpers)

> Delta spec for **Phase 1a** only. Builds on Phase 0 (no rebuild). Roadmap: `docs/ai-dlc/roadmap.md`. Strategy source: `docs/research/01-preflop-strategy.md`. Phase 1 is sliced **1a → 1b → 1c**. STOP at the plan gate — no code until approved.
> Revised after refuter pass (concrete grading model, schema/signature/taxonomy fixes, scope trim).

## Goal (one line)
Make the preflop skeleton a genuinely useful trainer for the most common live spots — **RFI, facing-an-open (call/3-bet/fold), blind defense, vs-limpers** — through the full loop: **frequency-tolerant grading from real content packs + SM-2 spaced repetition + auto leak tracking + a lean dashboard.**

## In scope
1. **Real content packs** (`content/preflop/*.json`), from the research tiers, replacing the Phase 0 stub: `rfi` (all positions + sizes), `vs_rfi` (call/3-bet/fold by hero × opener position), `blind_defense` (SB/BB vs steal by opener position), `vs_limpers` (over-limp/isolate/fold by limper count 1–3 + position). Mixed frequencies only where research supports (e.g., A5s–A2s 3-bet bluffs).
2. **Frequency-tolerant multi-action grading** — new `grading.py`, used by `HeuristicProvider`, with the **concrete model below**.
3. **Scenario sampler** for all 1a node types with canonical `action_history` (below). **100bb only in 1a** — stack-depth content/variety deferred to 1b (avoids SRS-granularity noise; see Decisions).
4. **SM-2 spaced repetition** — `srs_item` table + scheduler; correctness→quality (optimal=5, acceptable=4, mistake=2, blunder=0); `review` mode serves due archetypes.
5. **Leak tracking + stats API** — aggregate `DrillAttempt` by `leak_category`; `GET /stats/leaks` (ranked) + `GET /stats/summary`.
6. **Drill modes** — `/drill/next?mode=random|review|leak_focus`.
7. **Lean frontend** — multi-action decision bar (fold/call/raise), mixed-spot indicator, mode selector, compact stats strip (accuracy, top-3 leaks, due count, streak), 3-state grid coloring (raise/call/fold + hero highlight). *Rich dashboard + EV heatmap deferred to 1b.*

## Grading model (concrete — replaces vague "boundary distance")
**Strength metric:** a static `HAND_RANK[169]` table — each starting hand's heads-up all-in-equity percentile in `[0,1]` (AA=1.0, 72o≈0.0). Baked as a constant (documented ordering); deterministic.

For a spot: look up the entry by node-aware key (below). Build `chart_mix = {action: freq}` for non-fold actions whose `combos` contain the hand; empty ⇒ pure fold `{fold:1.0}`. `top` = max-freq action.

Per legal action `a`, **proxy_ev** (a graded proxy, NOT solver bb-EV; solver replaces in Phase 3):
- `a` is `top`: `ev = 0.0`
- `a` in `chart_mix`, not top: `ev = -0.3 * (chart_mix[top] - chart_mix[a])`  (mixed alts ≈ near-0 loss)
- `a` off-chart and `a == fold` while a play exists: `ev = -(0.8 + 2.5 * HAND_RANK[hand])`  (folding strong hands hurts more)
- `a` off-chart and aggressive (call/raise on a fold hand): `ev = -(0.8 + 3.0 * (1 - HAND_RANK[hand]))`  (weaker hands punished more)

`best_action` = max proxy_ev (tie → priority raise>call>fold). `ev_loss_bb = best_ev - chosen_ev` (≥0).
**Correctness:** chosen == top ⇒ OPTIMAL; chosen in chart_mix with freq>0.15 ⇒ ACCEPTABLE; else by ev_loss: ≤0.5 ACCEPTABLE, ≤2.0 MISTAKE, else BLUNDER. **`is_mixed`** = ≥2 actions with freq>0.15.
**Named-hand test anchors (must pass):** AA fold UTG ⇒ BLUNDER; 72o raise UTG ⇒ BLUNDER; AKs raise CO ⇒ OPTIMAL; A5s call in an A5s-3bet-mix spot ⇒ ACCEPTABLE; a chart call when 3-bet is top ⇒ ACCEPTABLE (mixed).

## Contract changes (additive — keep the no-rebuild guarantee)
- **`Entry`** gains `limper_count: int | None = None`. Node-aware lookup: `rfi`→(ctx,pos); `vs_rfi`/`blind_defense`→(ctx,pos,facing=opener); `vs_limpers`→(ctx,pos,limper_count). Respec `HeuristicProvider._lookup` accordingly.
- **`EvaluationResult`** gains `is_mixed: bool = False`. (Additive; existing consumers unaffected.)
- **`spot_signature`** extended to include `facing` (opener position or "-") and `limper_count` (or 0). **Supersedes the Phase 0 signature** — safe now because no SRS/attempt history depends on it yet; update the golden stability test to the new canonical subset. Without this, BB-vs-UTG and BB-vs-BTN collide and SRS/leaks are useless.
- **Leak taxonomy** (100–199): `RFI_EP..RFI_SB` (100–104), `BLIND_DEFENSE` (110, renamed from BB_DEFENSE; covers SB+BB facing a steal), `VS_RFI` (112), `VS_LIMPERS` (150), `SIZING` (160). `VS_3BET_*`/`FOURBET`/`SQUEEZE` stay reserved for 1b. **Resolution rule:** hero in SB/BB facing an open ⇒ `BLIND_DEFENSE`; hero in a non-blind position facing an open ⇒ `VS_RFI`. Call-vs-3bet-vs-fold nuance is carried in **`rationale_tags`** (`over_call`/`under_3bet`/`over_fold`/`over_3bet`), shown as a breakdown — not separate categories (avoids ambiguous assignment).

## Sampler action_history contract (per node type) — with golden fixtures
- `rfi`: history = blinds posted (SB,BB); pot 1.5bb; legal fold/raise(open size).
- `vs_rfi`: history = blinds + opener `raise` to size S from `facing` position; pot = 1.5 + S; legal fold/call(S)/raise(3-bet size). hero in a non-blind seat after opener.
- `blind_defense`: as vs_rfi but hero in SB/BB; SB completes excluded (raise-or-fold modeled).
- `vs_limpers`: history = blinds + N `call` (limp) posts; pot = 1.5 + N; legal fold/call(1bb)/raise(iso size = 4 + N bb). 
A golden fixture test pins the exact Spot shape for one `vs_rfi` and one `vs_limpers` spot.

## Stats definitions
- **Session streak** = consecutive local-calendar days with ≥1 graded attempt (uses `DrillAttempt.created_at`; no new field).
- **Accuracy** = % of attempts graded OPTIMAL or ACCEPTABLE, per category and overall. **Trend** = last-20-attempt accuracy vs prior-20.

## Files to touch
`content/preflop/*.json` (new) · `content/schema/contentpack.schema.json` (add limper_count) · `backend/app/domain/{grading.py(new),scenarios.py,leaks.py,srs.py,evaluation.py}` · `backend/app/domain/content/models.py` · `backend/app/domain/providers/heuristic.py` · `backend/app/db/models.py` + new migration · `backend/app/services/{stats.py,review.py}` (new) · `backend/app/api/v1/{drill.py,stats.py}` · `frontend/src/` (decision bar, mode selector, stats strip, grid coloring, mixed indicator, api/types).

## Out of scope (deferred)
- **1b:** vs-4bet, vs-3bet-after-opening, squeeze, mastery-gating, stack-depth content/variety, rich dashboard + EV heatmap.
- **1c:** exploit/archetype (villain-type) drills.
- ALL postflop · solver tables · live session logger.

## Constraints
Preflop/live/simplified · grading behind `StrategyProvider`, results stay freq+EV+coverage(+is_mixed) · domain stays pure · CSS tokens + AA contrast for the new grid action colors (both themes) · SRS table via Alembic migration, auto-run on boot · any new deps go in `RUN-THESE-COMMANDS.md`, not chat.

## Verify-by
1. `pytest` green incl: **range-correctness sanity** (AA in every RFI range; trash absent from EP; ranges widen by position; 3-bet ranges value-heavy), the **named-hand grading anchors** above, SM-2 progression, stats aggregation + streak, sampler validity + golden fixtures per node type, signature stability (new subset), domain purity.
2. `alembic upgrade head` from clean creates `srs_item`; auto-migrate on boot.
3. Backend boots; `/drill/next?mode=...` returns valid spots for each mode; `/drill/grade` grades multi-action nodes with freq+EV+coverage+is_mixed; `/stats/leaks`+`/stats/summary` aggregate; OpenAPI lists all.
4. Frontend builds; live (Playwright): a vs_rfi spot grades correctly, decision bar offers fold/call/raise, grid shows colored action mix, mixed-spot indicator appears on a mixed hand, stats strip populates, `review`/`leak_focus` modes load.
5. CSS contrast/token check passes for new grid colors.
