# Spec — Phase 2c: Postflop SRS Review

> Delta spec for **Phase 2c** only. Builds on 2a/2b. Closes the core product loop for postflop: the flop **c-bet** and **vs-c-bet** spots already drill + persist `DrillAttempt` + create `SRSItemRow`s, but `_next_review` can't reconstruct them, so they never re-surface. This slice makes them re-surface via SM-2 — like preflop. STOP at the plan gate — no code until approved.

## Goal
Postflop spots (CBET, VS_CBET) **re-surface in `mode=review`** via SM-2, keyed on their texture/SPR/faced-bet archetype. First DB migration since 1c. No new strategy content — pure learning-loop infra over the 2a/2b graders.

## Why it's needed (current gap)
- `record_attempt` already creates an `SRSItemRow` for every graded spot incl. postflop — but only stores `node_context/position/facing/limper_count/villain_type`. The postflop **archetype** (texture class, SPR bucket, faced-bet bucket) is NOT stored.
- `_next_review` reconstructs a spot by looking up the **preflop** content index; for a postflop row that lookup returns `None`, so it falls through to random. Postflop leaks never come back.

## Key decision (refuter blocker 1 — the heart of the feature)
**The due row must graduate even when the reconstructed board is only an approximate (tier-b/c) match.** Reconstruction is rejection-sampled, so the served spot's texture/SPR/faced-bet buckets often differ from the due row's — which means `spot_signature(reconstructed)` ≠ `row.signature`. Without a fix, re-grading creates a NEW row and the original due row never advances → infinite due backlog (the whole feature silently fails).
**Fix:** carry the original signature on the served spot and honor it on re-grade.
- Add `Spot.srs_signature: str | None = None` — **metadata, EXCLUDED from `spot_signature()`** (the signature is computed from canonical fields only; this field is never read by it). It round-trips through the frontend automatically (the client echoes the whole spot back to `/drill/grade`).
- `_rebuild_postflop` sets `spot.srs_signature = row.signature` on the served spot.
- `record_attempt` keys on `spot.srs_signature or spot_signature(spot)`; the grade route uses the **same** key for its `DrillAttempt` row (no analytics/SRS signature drift).
This makes tier-b/c approximate boards correctness-safe: the player practices a same-node spot and SM-2 credits the exact archetype row regardless. (Approximate-board fidelity is a known, accepted limitation — noted, not silent.)

## In scope
1. **Migration 0004** (`alembic/versions/0004_srs_postflop.py`, `down_revision="0003"`): add 4 **nullable** columns to `srs_item` — `street`, `texture_class`, `spr_bucket`, `faced_bet_bucket`. Nullable so existing preflop rows are untouched (NULL). `upgrade()` may use plain `op.add_column`; `downgrade()` uses `op.batch_alter_table` (SQLite, per the 0003 pattern). 0004 becomes head.
2. **`SRSItemRow`** (`db/models.py`): add the 4 fields (`str | None = None`).
3. **`Spot`** (`domain/spot.py`): add `srs_signature: str | None = None` — metadata only; `spot_signature()` does not read it (preflop + postflop hashes byte-identical to 2b).
4. **`record_attempt`** (`services/review.py`):
   - Key: `sig = spot.srs_signature or spot_signature(spot)`.
   - Always set `street` on a new row. For a **postflop** spot set `texture_class`/`spr_bucket`/`faced_bet_bucket` (reuse `domain/srs.py` + `domain/texture.py` helpers). **Guard `classify`**: only when `len(spot.board) >= 3` (else leave `texture_class=None`) — `classify` raises on <3 cards.
   - **Backfill**: when the row already exists but its bucket columns are NULL and the spot is postflop, populate them (covers legacy 2a/2b rows + the first post-migration attempt). Does not touch SM-2 math.
   - Preflop rows: `street="preflop"`, buckets `None`.
5. **Postflop review reconstruction** (`api/v1/drill.py`):
   - `_rebuild_postflop(row) -> Spot | None`: pick the builder by node — `build_cbet_spot` (hero=opener=`row.position`, pairing `(row.position, BB)`) or `build_vs_cbet_spot` (hero=BB, pairing `(row.facing, BB)`, `cbet_frac = 0.33 if row.faced_bet_bucket=="small" else 0.75`). Generate a bounded batch (~150) of candidates and pick by **tiered match**: (a) exact `(texture_class, spr_bucket, faced_bet_bucket)`; else (b) `texture_class` only; else (c) the first candidate (same node + position). **Set `spot.srs_signature = row.signature`** on the result. Returns `None` only if the node/positions can't form a builder pairing (e.g. `vs_cbet` row with NULL `facing`).
   - `_next_review`: for a due row whose `node_context` is `cbet`/`vs_cbet`, call `_rebuild_postflop`; serve it if non-None, else continue. Preflop path unchanged. Falls back to `_next_random()` when nothing is due/reconstructable. Robust to NULL-bucket rows (tier-c, no crash).
   - **`due_items`**: add `ORDER BY due_date ASC` so the most-overdue items surface first (no starvation of a fixed DB order).
6. **Grade route** (`api/v1/drill.py`): compute `sig = req.spot.srs_signature or spot_signature(req.spot)` once; use it for both the `DrillAttempt` row and (via the spot's `srs_signature`) `record_attempt`.

## Contract changes
- DB: `srs_item` gains `street`, `texture_class`, `spr_bucket`, `faced_bet_bucket` (all nullable) via migration 0004.
- `Spot` gains `srs_signature: str | None = None` (metadata; **excluded from `spot_signature()`**). Round-trips through the frontend; harmless if absent. (Add the optional field to the frontend `Spot` TS type so it isn't a typing surprise — no behavior change.)
- **No change to `spot_signature`** (the faced-bet bucket landed in 2b) or to any grader.
- No API shape change (`/drill/next?mode=review` already exists; it now serves postflop spots too).

## Out of scope (deferred)
- Turn / river / check-raise-as-aggressor · **equity-backed** range advantage · multiway · solver · mastery-gating · squeeze · a dedicated postflop review UI (review postflop spots render in the existing Practice view, board + fold/call/raise or check/bet bar).

## Constraints
Live/simplified · SM-2 math stays pure in `domain/srs.py` · review service stays in the service layer · domain stays web/DB-free · **migration is additive + nullable** (preflop rows untouched; preflop review unchanged) · reconstruction reuses the 2a/2b builders (no new spot-construction logic) · the rejection-sampling cap is bounded and **tier-c fallback is explicit** (same node, not silent-random) · any new deps → `RUN-THESE-COMMANDS.md` (target: none).

## Verify-by
1. `pytest` green incl:
   - **migration**: `0004` is head; `srs_item` has the 4 new columns; an existing DB upgrades cleanly; preflop rows have NULL buckets.
   - **record_attempt persistence**: grading a CBET spot writes a row with `street="flop"`, a non-null `texture_class`/`spr_bucket`, `faced_bet_bucket="none"`; a VS_CBET spot writes `faced_bet_bucket` in `{small,big}`; a preflop spot writes `street="preflop"` and NULL buckets.
   - **reconstruction**: `_rebuild_postflop` for a CBET row returns a flop CBET spot with hero at `row.position`; for a VS_CBET row returns a vs-cbet spot (hero=BB) whose `faced_bet_bucket` matches the row; tiered fallback returns a same-node spot when no exact texture match; returns sanely (no crash) on a NULL-bucket row.
   - **review round-trip**: grade a postflop spot → force its row due → `mode=review` returns a **postflop** spot of the same node (street=flop), and it grades + persists. Preflop review still returns preflop spots and is unaffected.
   - **DUE ROW GRADUATES (the blocker-1 test)**: a served review spot carries `srs_signature == row.signature`; re-grading it (even when the reconstructed board's own `spot_signature` differs) updates the **same** SRS row — `repetitions`/`interval_days` advance and the count of `SRSItemRow`s does NOT grow. (Explicitly construct a reconstructed spot whose canonical signature ≠ the override, and assert the override row is the one that advances.)
   - **legacy backfill**: a postflop row with NULL buckets gets them populated on the next attempt; `record_attempt` never crashes on a `<3`-card board.
   - **signature unchanged**: preflop + postflop `spot_signature` byte-identical to 2b (this slice adds DB columns + a metadata field, not signature inputs); a spot with `srs_signature` set hashes the same as without it.
2. Backend boots (lifespan runs migrations incl. 0004); `mode=review` serves postflop spots after they're due; all 2a/2b/preflop modes + quizzes unaffected.
3. Frontend unchanged (review postflop spots render in the Practice view). `vite build` + `tsc --noEmit` still clean.
4. `scripts/verify.sh` green incl. a postflop-review probe.
