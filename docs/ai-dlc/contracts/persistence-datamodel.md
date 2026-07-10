# Contract — persistence / data-model layer (single-user → multi-user seam)

> Read-only scan for the "professional-teacher-rework" roadmap. Scope: `backend/app/db/{models,session,migrate}.py`,
> `backend/alembic/`, `backend/app/domain/srs.py`, `backend/app/services/{review,stats}.py`,
> `backend/app/api/v1/{drill,stats}.py`, `backend/app/schemas/{drill,stats}.py`.

## Current schema (tables + migration head)

- **Alembic head: `0005`** (`backend/alembic/versions/0005_drill_attempt_hand_class.py`), linear `0001→…→0005`, no branches.
  Migrations auto-run on every boot (`app/main.py:19` → `app/db/migrate.py:22-24`, `alembic upgrade head`) against a single
  hardcoded SQLite file. **(NB: roadmap.md still says head 0004 — stale.)**
- **`drill_attempt`** (`app/db/models.py:22-35`) — one graded decision. `id` PK autoincrement; `spot_signature` (indexed,
  join-by-value, not a real FK); `leak_category:int|None` (IntEnum value, no DB constraint); `chosen_action`, `correctness`,
  `ev_loss_bb`, `provider` (free-text discriminator — already used as `"heuristic"`/`"quiz"`, e.g. `drill.py:339`);
  `created_at`; `hand_class:str|None` (added 0005, nullable, **not backfilled**). **No user/owner column.**
- **`srs_item`** (`app/db/models.py:38-60`) — one SM-2 row per spot **archetype**. `signature:str` is the **PK** =
  `spot_signature()` (`app/domain/srs.py:48-68` preflop / `:107-128` postflop), a **content-derived** hash → today implicitly
  **global per archetype, not per player**. SM-2 state: `ease_factor(2.5)`, `interval_days`, `repetitions`, `due_date`,
  `last_grade`, `updated_at`. Index `ix_srs_item_due_date` on `due_date` (0002) — the exact index "today's plan" reads.
- **No profile/settings/user table exists anywhere** — the whole schema is 2 tables. grep-confirmed: no
  `user`/`player_id`/`owner`/`tenant`/`auth`.

## Single-user coupling points (ranked by blast radius)

1. **`srs_item.signature` is the sole PK and is content-derived, not per-user** (`models.py:43`, `srs.py:48`). Looked up via
   bare `session.get(SRSItemRow, sig)` in `record_attempt()` (`services/review.py:45`). A 2nd user today would **silently
   share/overwrite** SM-2 progress on every shared archetype — a correctness bug, not an error. This is the ONE place a bare
   "add nullable column" is insufficient: `session.get(Model, pk)` assumes the single-column PK.
2. **Six unscoped `select()` sites** — `due_items()` (`review.py:78-84`) + `summary()`/`leak_stats()`/`hand_error_weights()`
   (`stats.py:38-39,72-73,107-109`), consumed by `/drill/next?mode=review|leak_focus|challenge` (`drill.py:150-184`) and
   `/stats/{leaks,summary}` (`stats.py:11-18`). All assume "whole DB == this one user." Additive nullable seam → each needs a
   `.where(owner_id == … or .is_(None))` when it lands (this is the real blast radius, not the schema change).
3. **Single SQLite file + module-level global `engine`** (`session.py:9-15`, hardcoded `backend/data/poker_coach.db`,
   `check_same_thread=False`). Fine for one local user; the ceiling on multi-user without per-tenant DB routing. No change
   needed for a nullable-column seam.
4. **Process-global singletons** in `drill.py:55-59` (`_provider`, `_INDEX`, `_RNG` shared mutable) — concurrency/identity
   smell, harmless single-user.
5. **FE-local unscoped state** — `STUDY_TEST_KEY` in `App.tsx:52,60` is per-browser localStorage, not server-side.

## Minimal seam recommendation (shape only — not building it)

- One nullable `owner_id:str|None` column on **both** `drill_attempt` and `srs_item` via a new migration `0006`, following the
  existing `add_column(..., nullable=True)` pattern (`0003_srs_villain_type.py:16`, `0005:16`). No backfill; `NULL` = "the
  local user." Alembic already uses SQLite-safe `batch_alter_table` (`alembic/env.py:22,38`).
- **The hard part is the PK, not the column.** Decide now, while there's zero data to migrate: widen `srs_item` PK to composite
  `(owner_id, signature)` **now** (cheap insurance) vs leave `signature` PK and defer (later = full-table-rebuild PK surgery,
  even under batch mode). ⚠️ Do NOT fold `owner_id` into the `signature` hash — `srs.py:1-11` warns changing `spot_signature()`
  orphans all persisted SRS history. Composite PK avoids that; hashing owner in does not.

## Placement-diagnostic + today's-plan storage fit

- **"Today's plan" needs no new storage** — `due_items()` (`review.py:78-84`) already reads `srs_item` by `due_date` on an
  existing index, and `/drill/next?mode=review` consumes it end-to-end (incl. postflop reconstruction `drill.py:91-147`).
  Pure read-only surfacing → new endpoint/view only.
- **Placement diagnostic has no home.** Natural fit given the schema: its output IS an initial `srs_item` state → **seed
  `srs_item` rows directly** (starting `ease_factor`/`interval_days`/`due_date` from diagnostic performance) via the existing
  `record_attempt()` create-or-update path (`review.py:34-75`). No new table needed. If raw diagnostic *answers* must persist,
  a `drill_attempt` row with `provider="placement"` is low-friction. Both writes inherit the owner-scoping need from point #1.

## Risks

- **Silent-collision, not error** — the `srs_item.signature` bare-PK issue merges two users' SM-2 histories without throwing
  (`review.py:45`). Biggest "don't discover the hard way" item.
- `leak_category` is an **unenforced int taxonomy** (`domain/leaks.py:18-47`), validated app-side only; never reuse a retired
  number (hand-maintained invariant, not a DB constraint).
- `hand_class` nullable+unbackfilled; `hand_error_weights()` silently skips `None` rows (`stats.py:113`) — new nullable seam
  columns join this same sparse-and-silently-skipped pattern (consistent, name it so reviewers don't read sparse data as a bug).
- Tests build a fresh temp SQLite via `run_migrations(url)` (`tests/test_db.py:8-12`, `test_review.py:12-16`) → a nullable
  migration is auto-exercised & low-risk, but any `srs_item` PK-shape change requires touching these fixtures.
