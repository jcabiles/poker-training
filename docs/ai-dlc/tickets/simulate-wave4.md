# Tickets — Simulate wave 4: S9 (hero plays / persistence) + S8 (multiway grading)

> Specs: `docs/ai-dlc/specs/simulate-s9.md` (full mid-hand restore; defer sim_decision;
> play.py productionizes the test harness EXACTLY) and `docs/ai-dlc/specs/simulate-s8.md`
> (binary HU/multiway; both sides; third conditional `mw` append; NO migration/model/
> rebuild/leak change — multiway spots never persist in v1).
> Branch: single shared `feat/simulate-wave4` **off main AFTER PR #30 merges** (it has —
> main @ 7718c0d). Per-ticket commits; disjoint ownership.
> DAG: **T1 ‖ T2 ‖ T3 ‖ T4 ‖ T5 parallel** (T2 authors endpoints to T1's frozen service
> signatures; T3 mirrors T2's frozen schema; T5 authors tests to T4's frozen builder kwarg
> + helper names — wave-2/3 cross-reference pattern; import errors from not-yet-committed
> peer work mid-wave are EXPECTED — report, do not patch). T6 = lead fan-in + close-out.

## Repo invariants injected into every brief (agents have fresh context)

- Domain core `app/domain/` has **no web/DB imports** (test-enforced). A NEW domain module
  must be added to `test_domain_purity.py`'s exact-string allowlist or it is silently
  unchecked. Services (`app/services/`) may touch the DB.
- Results are **freq+EV, never boolean**; grading stays behind the async `StrategyProvider`.
- `spot_signature()`: preflop branch **byte-locked**; postflop dims **conditionally
  appended** (OMITTED for streets/counts they don't describe — a constant append still
  changes the hash). Pinned literals in `test_signature.py` never change.
- Every schema change ships an **additive** Alembic migration (chain at 0008 → S9 adds
  0009; **S8 adds none**). `types.ts` is hand-maintained. CSS from design tokens only, AA
  contrast + visible focus **both themes**.
- Graders never read persona data. Villain hole cards / board never serialized (hero-only
  wire).
- **Scratch files go to `$TMPDIR`, never repo paths. Commit as soon as your done-check
  passes. Do NOT run `git stash`/`reset`/`checkout` on the shared branch. Do NOT touch
  files another ticket owns.**

## S9 — hero plays / session persistence / stacks / ledger

- [ ] **T1 — Play-loop + persistence + session service (heavy-worker).**
  `app/domain/table/play.py` (new): `LINEUP`/`assign_lineup`, `ActionEvent`, `bot_decision`,
  `advance_to_hero` — **mirror `tests/test_personas_postflop.py`'s `_preflop_facing`/
  `_preflop_decision`/`_postflop_decision`/`_live_opponents`/`_play_hand` PER-DECISION**
  (preflop size = `la.min_bb`; postflop threads `current_bet_to=state.current_bet_bb`),
  differing only by stopping at `hero_seat`. **Parity is per-decision only** (same
  `(state, seat, pack, rng)` ⇒ same `Decision`) — NOT per-hand: production skips the hero's
  RNG draw, so a full playout diverges from `_play_hand` by design; never assert full-hand
  parity. The service (not `play.py`) owns the **bot-action RNG lifecycle**: a fresh
  `random.Random(secrets.randbits(256))` per `advance_to_hero` call (deal uses `rng_seed`;
  bot actions are intentionally NOT replayable from `rng_seed` — see spec). Add `'app.domain.table.play'` to
  `test_domain_purity.py`. `app/db/models.py`: `SimSession`/`SimSeat`/`SimHand` per spec
  (rng_seed str; state_json text; composite PK on SimSeat; owner_id '' sentinel).
  `backend/alembic/versions/0009_sim_tables.py`: additive, `down_revision="0008"`, up+down.
  `app/services/sim_session.py`: the five frozen functions (create/restore/apply_hero_action/
  deal_next_hand/leave) + `SessionView` assembly with **privacy scrub** (build views
  field-by-field from the rehydrated `HandState`; only hero + `showdown_seats` carry hole
  cards) + carry-over stacks + auto-rebuy (`stack<1.0` → 100, `buyins += 100-stack`).
  `backend/tests/test_sim_session.py` (new): play a hand to showdown, fold, restore mid-hand
  (rehydrate → same `to_act_seat`/legal actions), bust→rebuy→ledger (net_bb 2dp-clean),
  chip conservation across a hand (deltas sum 0), **deal reproducibility** (same `rng_seed` ⇒
  byte-identical deal — NOT full-hand bot-action replay), and a **per-decision parity test**
  that `bot_decision(state, seat, pack, rng)` returns the same `Decision` the harness's
  `_preflop_decision`/`_postflop_decision` yields for identical inputs.
  **Owns:** `app/domain/table/play.py` (new) · `backend/tests/test_domain_purity.py` ·
  `app/db/models.py` · `backend/alembic/versions/0009_sim_tables.py` (new) ·
  `app/services/sim_session.py` (new) · `backend/tests/test_sim_session.py` (new).
  **No-gos:** no grading/verdicts/attempt-recording · no `sim_decision` · no SRS writes ·
  no `api/`/`schemas/` edits (T2's) · no FE edits (T3's) · no S8 file edits · never invent
  new bot sizing (calibration is frozen) · never serialize `full_board`/non-hero hole cards.

- [ ] **T2 — Simulate API + wire schemas (implementer).**
  `app/schemas/simulate.py`: `SeatView`/`ShowdownSeatView`/`EventView`/`SimulateHandView`
  (superset, replaces S1 shape)/`SessionView` per spec. `app/api/v1/simulate.py`: rewrite to
  the five endpoints (`POST /session`, `GET /session/{id}`, `POST /session/{id}/action`,
  `POST /session/{id}/hand`, `POST /session/{id}/leave`) delegating to T1's frozen
  `sim_session` service via `Depends(get_session)`; 404 shape preserved; illegal action →
  400. **Delete the S1 in-memory `SimSession` dataclass + `_SESSIONS` dict entirely** (fully
  superseded by T1's DB-backed `SimSession` table — name-collides otherwise).
  `backend/tests/test_simulate_api.py` (new): create→act→showdown happy path, restore
  endpoint returns the live decision point, **privacy assertion** (no non-hero/non-showdown
  hole cards in any payload; `state_json`/`full_board` never present), 404 on missing/ended,
  400 on illegal action, next-hand carry-over.
  **Owns:** `app/api/v1/simulate.py` · `app/schemas/simulate.py` ·
  `backend/tests/test_simulate_api.py` (new).
  **No-gos:** no service/domain/model edits (T1's — author to frozen signatures; import
  errors mid-wave are expected) · no FE edits · no grading.

- [ ] **T3 — Playable table UI (ux-ui-designer).**
  `frontend/src/components/SimulateView.tsx` + `components/simulate/*` (new): real table
  (board/pot/per-seat persona badge+stack+status+chips-in-front via `PokerTable`), hero
  action bar (reuse `lib/decisions.ts::legalDecisions` predetermined sizing — no free-form),
  instant bot resolution (static `events` list, no animation), ledger panel (`net_bb`),
  hand-over showdown + "Deal next hand", **reload restore** via `localStorage` session_id
  (`GET /session/{id}`; 404 → clear + fresh, preserve `isSessionNotFound`), "Leave table".
  `frontend/src/api/types.ts`: mirror every new field. `frontend/src/api/client.ts`:
  `getSession`/`postHeroAction`/`postNextHand`/`leaveSession`. `frontend/src/styles/
  tokens.css` (+ `app.css`): new token-backed values; AA contrast + focus both themes.
  Commit to a named aesthetic; the `design-reviewer` owns the verdict.
  **Owns:** `frontend/src/components/SimulateView.tsx` · `frontend/src/components/simulate/*`
  (new) · `frontend/src/api/types.ts` · `frontend/src/api/client.ts` ·
  `frontend/src/styles/tokens.css` · `frontend/src/app.css` · `frontend/src/App.tsx` (only
  if needed; single-owner this wave).
  **No-gos:** no backend edits · no free-form bet input · no `PokerTable.tsx` rewrite (adapt
  onto it) · no pacing/animation lib · tokens-only (no literal colors) · never render a
  non-hero seat's hole cards except at showdown.

## S8 — multiway grading extension

- [ ] **T4 — Multiway grader core + signature append (heavy-worker).**
  `app/domain/spot.py`: `players_in_pot(spot)` + `is_multiway(spot)` (no `Spot` field
  added). `app/domain/postflop.py`: `_apply_multiway(...)` + new `_MW_*` constants; every
  grader routes base merits through it when `is_multiway(spot)` (aggressor: dampen bluff
  merit / hold value; facing: tighten bluff-catch) — **HU output byte-identical**; reads no
  persona data. `app/domain/srs.py`: THIRD conditional append `if players_in_pot(spot) > 2:
  parts.append("mw")` (after river_class) + docstring update; **recompute the three pinned
  hashes to prove HU byte-identity — never edit a pin.** `app/domain/scenarios.py`:
  optional `players_in_pot: int = 2` kwarg on all 7 postflop builders + `_multiway_seats`
  helper (adds extra IN seats without touching the opener/caller).
  **Owns:** `app/domain/spot.py` · `app/domain/postflop.py` · `app/domain/srs.py` ·
  `app/domain/scenarios.py`.
  **No-gos:** no migration/`db/models.py`/`review.py`/`drill.py` (multiway never persists in
  v1) · no `leaks.py`/`grading.py`/`feedback.py` (no new category, `TAXONOMY_VERSION` stays
  5) · no provider/`supports()`/`NOT_FOUND` changes (multiway is graded, not NOT_FOUND) ·
  no persona-aware grading · no HU output change · no test-file edits (T5's).

- [ ] **T5 — Multiway direction + signature-invariance tests (implementer).**
  `backend/tests/test_multiway.py` (new): direction — multiway acceptable-**bluff** freq
  **strictly lower** + value freq **≥** HU, for cbet/vs_cbet/turn_barrel/vs_turn_bet/
  river_barrel/vs_river_bet (same seed, only `players_in_pot` differs, via T4's frozen
  builder kwarg); multiway c-bet graded (FOUND freq+EV, not NOT_FOUND, not HU-identical);
  no-persona-read inspection. `backend/tests/test_signature.py` (additions only): companion
  `*_unchanged_by_multiway_dimension` for flop/turn/river (HU hash == existing literal);
  multiway hash ≠ HU twin; 3-way == 4-way (binary bucket). `backend/tests/test_provider.py`
  (additions only): multiway spot routes to a graded verdict, not NOT_FOUND.
  **Owns:** `backend/tests/test_multiway.py` (new) · `backend/tests/test_signature.py` ·
  `backend/tests/test_provider.py`.
  **No-gos:** no source edits (T4's — author to frozen names) · existing `test_postflop.py`/
  `test_turn_graders.py`/`test_river_graders.py`/`test_feedback_tiers.py`/pinned signature
  tests pass UNMODIFIED · never update a pinned hash literal.

## Close-out

- [ ] **T6 — Lead fan-in.** Full `pytest -q` + ruff + `./scripts/verify.sh` + FE
  typecheck/build; migration 0009 up/down; **hand-diff the 3 new models in `db/models.py`
  field-by-field against `0009_sim_tables.py`** (migrations are hand-written — no autogenerate
  drift check; 3 tables/1 migration = higher blast radius); the three signature pins literal
  + unchanged; S3/S4 persona bands + S6/S7 grader tests byte-identical; play.py↔harness
  PER-DECISION parity (never full-hand); privacy assertion (no leaked hole cards);
  `design-reviewer` on the table (both themes);
  **refuter on the combined diff** (empirical: recompute hashes, exercise restore, probe
  privacy); targeted fix rounds via SendMessage; PR `feat/simulate-wave4`; mark S8 + S9
  `[x]` in the roadmap with done-notes; update the memory file.
