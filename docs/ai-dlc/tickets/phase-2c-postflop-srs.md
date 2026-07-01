# Tickets — Phase 2c: Postflop SRS Review

Spec: `docs/ai-dlc/specs/phase-2c-postflop-srs.md`. 5 tickets — infra over the 2a/2b graders (no new strategy). One-file-one-owner. Build only after the gate is approved. The refuter's critical blocker (due rows never graduating) is fixed via a `Spot.srs_signature` override threaded review→grade→record_attempt.

> **STATUS: ALL 5 TICKETS BUILT & VERIFIED (T1–T5).** 148 backend tests green (incl. the due-row-graduation test); `scripts/verify.sh` → `BACKEND VERIFY OK`; frontend `vite build` + `tsc --noEmit` clean. Migration 0004 is head. (Also fixed a pre-existing UTC-vs-local streak bug surfaced in passing.) Live Playwright check pending (needs the user's dev servers up).

## DAG / waves
```
T1 ─┬─ T2 ─ T3 ─┐
    └─ T4 ───────┴─ T5
```
- W1: **T1** (migration + models + `Spot.srs_signature`)
- W2: **T2** (record_attempt, needs T1), **T4** (frontend type, needs T1) — parallel
- W3: **T3** (review reconstruction + grade-route override, needs T2)
- W4: **T5** (verify + docs)

---

### T1 — Migration + models + Spot field
Migration `0004_srs_postflop.py` (`down_revision="0003"`, head): add nullable `street`/`texture_class`/`spr_bucket`/`faced_bet_bucket` to `srs_item` (`op.add_column` up; `batch_alter_table` drop down). `SRSItemRow` gains the 4 fields. `Spot` gains `srs_signature: str | None = None` (metadata, NOT read by `spot_signature`).
- **Owns:** `alembic/versions/0004_srs_postflop.py`, `app/db/models.py`, `app/domain/spot.py`, `tests/test_signature.py` (invariance), `tests/test_migrations.py` (or extend existing).
- **Done when:** `alembic upgrade head` → 0004; columns exist; preflop rows NULL-bucketed; `spot_signature` byte-identical with/without `srs_signature` set (preflop + postflop).

### T2 — record_attempt persistence + backfill
`record_attempt`: key on `spot.srs_signature or spot_signature(spot)`; set `street` always; set postflop buckets when `len(board)>=3` (guarded `classify`); **backfill** NULL buckets on existing postflop rows; SM-2 math unchanged. `due_items`: add `ORDER BY due_date ASC`.
- **Owns:** `app/services/review.py`, `tests/test_review.py` (or `tests/test_srs.py`).
- **Depends:** T1.
- **Done when:** postflop grade writes `street="flop"` + non-null buckets (cbet→`faced_bet_bucket="none"`, vs_cbet→`small`/`big`); preflop writes `street="preflop"`+NULL; legacy NULL row backfills on next attempt; never crashes on `<3`-card board; `srs_signature` override routes to the named row.

### T3 — Review reconstruction + grade override
`api/v1/drill.py`: `_rebuild_postflop(row)` (builder by node + constrained pairing + `cbet_frac` from bucket; ~150 candidates; tiered exact→texture→first match; sets `spot.srs_signature=row.signature`; `None` if unbuildable). `_next_review` postflop branch (serve rebuilt spot, else continue). Grade route computes `sig = req.spot.srs_signature or spot_signature(req.spot)` for both `DrillAttempt` + `record_attempt`.
- **Owns:** `app/api/v1/drill.py`, `tests/test_api.py`.
- **Depends:** T2.
- **Done when:** **DUE ROW GRADUATES** — grade a postflop spot → force due → `mode=review` serves a same-node flop spot carrying the override → re-grade advances THE SAME `SRSItemRow` (row count does not grow) even when the reconstructed board's canonical signature differs; preflop review unchanged; no crash on NULL-bucket / unbuildable rows.

### T4 — Frontend type
Add `srs_signature?: string | null` to the `Spot` TS interface so the review spot round-trips cleanly.
- **Owns:** `frontend/src/api/types.ts`.
- **Depends:** T1.
- **Done when:** `tsc --noEmit` + `vite build` clean; review postflop spot grades live (board echoes `srs_signature` back).

### T5 — Verify + docs
`scripts/verify.sh` postflop-review probe (grade postflop → due → review serves flop → re-grade advances same row). Roadmap/README/ticket status.
- **Owns:** `scripts/verify.sh`, `README.md`, roadmap/ticket status.
- **Depends:** T1–T4.
- **Done when:** `verify.sh` green; live Playwright: a postflop spot, made due, re-surfaces in Review mode.

---

## Notes
- Riskiest: **T3** (the graduation correctness — the override must thread review→grade→record_attempt so the due row advances regardless of reconstructed-board fidelity) and **T1** (migration applies on an existing DB + signature invariance). Both get focused tests.
- Approximate-board reconstruction (tier-b/c) is an accepted, documented limitation — correctness is preserved by the signature override; only the exact board shown may differ from the archetype. Equity-backed grading + turn/river stay deferred (2d+).