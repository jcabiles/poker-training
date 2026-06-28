# Tickets — Phase 1a: Real Preflop Trainer

Spec: `docs/ai-dlc/specs/phase-1a-preflop-trainer.md`. 11 tickets (larger because you chose "Fuller 1a (+vs-limpers)"; rich dashboard + EV heatmap were trimmed to 1b). Small, one-file-one-owner.

> **STATUS: BUILT (2026-06-28).** T1–T11 done. 70 backend tests green; `scripts/verify.sh` boots + probes all routes; frontend typechecks + `vite build` clean. Live Playwright UI check pending a running dev server.

## DAG / waves
```
T1 ─┬─ T2 ─┐
    ├─ T3 ─┼─ T5 ─┐
    │   └── T4    │
    ├─ T6 ────────┼─ T9 ─ T10 ─ T11
    ├─ T7 ────────┤
    └─ T8 ────────┘
```
- W1: **T1**
- W2: **T2, T3, T6, T7, T8** (parallel — disjoint files)
- W3: **T4** (after T3), **T5** (after T2+T3)
- W4: **T9** (after T5+T6+T7+T8)
- W5: **T10**
- W6: **T11**
Single-agent build: T1→T11 in order.

---

### T1 — Contract additions (foundation)
Add `Entry.limper_count`, `EvaluationResult.is_mixed`; rework leak taxonomy (`BLIND_DEFENSE`=110, `VS_RFI`=112, keep namespaces); extend `spot_signature` to include `facing` + `limper_count` and update its golden stability test.
- **Owns:** `domain/leaks.py`, `domain/evaluation.py`, `domain/srs.py`, `domain/content/models.py`, `content/schema/contentpack.schema.json`, `tests/test_signature.py`, `tests/test_schemas.py`.
- **Depends:** —
- **Done when:** `pytest` green; new signature distinguishes BB-vs-UTG from BB-vs-BTN; schema accepts `limper_count`.

### T2 — Grading engine
`HAND_RANK[169]` equity-percentile table + `grading.py` implementing the frequency-tolerant model (proxy EV, correctness tiers, `is_mixed`). Include the named-hand anchor tests.
- **Owns:** `domain/grading.py`, `domain/hand_rank.py`, `tests/test_grading.py`.
- **Depends:** T1.
- **Done when:** all named-hand anchors pass (AA-fold-UTG=BLUNDER, AKs-raise-CO=OPTIMAL, mixed-call=ACCEPTABLE, etc.).

### T3 — Author content packs
Author `rfi`, `vs_rfi`, `blind_defense`, `vs_limpers` packs from `docs/research/01-preflop-strategy.md` into `content/preflop/*.json`; wire startup loading to replace the stub.
- **Owns:** `content/preflop/*.json`, content-loading glue in `domain/providers/factory.py`.
- **Depends:** T1.
- **Done when:** packs validate against schema and load; cover all positions + node types in scope.

### T4 — Range-correctness sanity (maker ≠ checker for T3)
Independent tests asserting the authored ranges are sane.
- **Owns:** `tests/test_ranges.py`.
- **Depends:** T3.
- **Done when:** AA in every RFI range; trash absent from EP; ranges widen by position; 3-bet ranges value-heavy; vs_limpers iso ranges tighter than RFI.

### T5 — Provider uses grading + node-aware lookup
Rewrite `HeuristicProvider` to grade all 1a nodes from loaded packs via `grading.py` and the node-aware `_lookup` (facing / limper_count).
- **Owns:** `domain/providers/heuristic.py`, `tests/test_provider.py`.
- **Depends:** T2, T3.
- **Done when:** grades RFI/vs_rfi/blind_defense/vs_limpers spots with freq+EV+coverage+is_mixed + correct leak_category + rationale_tags.

### T6 — Multi-node scenario sampler
Extend `sample_*` to build valid spots per node type with the canonical `action_history`, facing/limper_count, legal actions + sizes (100bb only).
- **Owns:** `domain/scenarios.py`, `tests/test_scenarios.py`.
- **Depends:** T1.
- **Done when:** golden fixtures for one `vs_rfi` + one `vs_limpers` spot pass; every node type samples valid spots.

### T7 — SM-2 spaced repetition
`srs_item` model + migration; SM-2 update fn (correctness→quality); `review` queue service (due archetypes).
- **Owns:** `db/models.py` (srs_item), new Alembic migration, `services/review.py`, SM-2 fn in `domain/srs.py`.
- **Depends:** T1.
- **Done when:** `alembic upgrade head` creates `srs_item`; a missed item's interval/ease update correctly; due query works.

### T8 — Leak stats + endpoints
Aggregate `DrillAttempt` by category; `GET /stats/leaks` (ranked) + `GET /stats/summary` (accuracy, due count, streak, trend).
- **Owns:** `services/stats.py`, `api/v1/stats.py`, `tests/test_stats.py`.
- **Depends:** T1.
- **Done when:** endpoints return ranked leaks + summary incl. streak = consecutive days.

### T9 — Drill modes + persistence wiring
`/drill/next?mode=random|review|leak_focus`; `/drill/grade` persists attempt + updates SRS + emits leak category.
- **Owns:** `api/v1/drill.py`, `tests/test_api.py`.
- **Depends:** T5, T6, T7, T8.
- **Done when:** all three modes return valid spots; grading persists an attempt and updates the SRS item.

### T10 — Lean frontend
Multi-action decision bar (fold/call/raise), mode selector, mixed-spot indicator, compact stats strip, 3-state grid coloring (+ tokens, AA contrast both themes), api/types update.
- **Owns:** `frontend/src/**`.
- **Depends:** T9.
- **Done when:** `vite build` + typecheck clean; live smoke (Playwright) shows multi-action grading, colored grid, stats strip, modes.

### T11 — Verify sweep + docs
Wire all new checks into `scripts/verify.sh`; update README/roadmap status; record any new run/install commands in `RUN-THESE-COMMANDS.md`.
- **Owns:** `scripts/verify.sh`, `README.md`, roadmap status, `tests/conftest.py` if needed.
- **Depends:** T1–T10.
- **Done when:** full Verify-by checklist runs green via one command.

---

## Notes
- No new backend deps expected (stdlib + existing). If the frontend needs a chart lib for the stats strip, keep it dependency-free (CSS bars) to avoid an npm round-trip — or it goes in `RUN-THESE-COMMANDS.md`.
- Content authoring (T3) is the judgment-heavy ticket; T4 is its independent checker (maker ≠ checker).
