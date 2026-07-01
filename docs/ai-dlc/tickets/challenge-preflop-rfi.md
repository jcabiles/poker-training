# Tickets — Challenge mode (preflop RFI, difficulty-biased sampling)

Spec: `docs/ai-dlc/specs/challenge-preflop-rfi.md`. 6 build tickets + 1 verify. New migration 0005.

## Shared contract (pin these)
- Mode string: `challenge`. Leak filter for RFI = `leak_category IN {100,101,102,103,104}`.
- New column: `DrillAttempt.hand_class: str | None`, written on EVERY grade via
  `hole_cards_to_class` (`app/domain/content/notation.py:91-99`).
- Difficulty constants (named, commented): `wF=0.6, wE=0.4, ε=0.02, Mmin=0.5, Mmax=2.0, MIN_N=5`.
- Personal metric: **mean `ev_loss_bb`** per hand class; <MIN_N attempts ⇒ neutral 1.0.
- Sampler signature: `sample_challenge_spot(rng, personal_weights: dict[str,float] | None = None,
  eff_bb=...)` — pure domain, no DB import.

## T0 — Deterministic hand_rank (prereq, refuter HIGH-2) · owns `backend/app/domain/hand_rank.py` (+ test)
Make the rank table stable across `PYTHONHASHSEED` (24 `_strength()` ties currently resolve by set
iteration order).
- **Do:** sort with a stable tie-break, e.g. `sorted(all_hands(), key=lambda h: (_strength(h), h))`.
- **Accept:** `HAND_RANK["KQo"]`/`["88"]` identical under `PYTHONHASHSEED=1` and `=42`; all existing
  tests still green.
- **Done:** `cd backend && PYTHONHASHSEED=1 python -m pytest -q` and `=42` agree; new determinism test passes.
- **Dep:** none. **Prereq for T2** (edge score uses rank order).

## T1 — hand_class column + migration 0005 + persist · owns `backend/app/db/models.py`, new `backend/alembic/versions/0005_*.py`, persist path in `backend/app/api/v1/drill.py`
- **Do:** add nullable `hand_class` to `DrillAttempt`; Alembic 0005 (down_revision 0004) adds the
  column, downgrade drops it; at the persist path (~drill.py:214-223) set `hand_class =
  hole_cards_to_class(spot.hero.hole_cards)` on every grade (all modes).
- **Accept:** `alembic upgrade head` + `downgrade` clean; grading any spot writes a `hand_class`.
- **Done:** `./scripts/verify.sh` → `BACKEND VERIFY OK`.
- **Dep:** none. **Prereq for T3.** (Keep the drill.py edit to the persist line only — T4 owns the
  mode dispatch later.)

## T2 — Domain difficulty scorer + sampler (pure) · owns `backend/app/domain/challenge.py` (new) + `backend/tests/test_domain_purity.py` (list) + domain tests
- **Do:** implement F (flip across the 6 RFI seats via `range_grid` + the `_key` index), E
  (rank-ORDER distance to nearest differing-action hand at the seat — NOT `_range_floor`; refuter
  HIGH-1), `D_obj=wF·F+wE·E`, `W=(ε+D_obj)·M(H)`, joint `(P,H)` sampling then deal a random combo
  (`combos_for_range`) and `build_spot`. Accept injected `personal_weights` (default all-neutral).
  Add `app.domain.challenge` to `test_domain_purity.py`'s module list.
- **Accept:** purity test green with the new module listed; distribution test (seeded, cold start)
  ranks boundary hands ≫ premiums/trash; edge test (2c) — E low for 74o/82o/93o at BTN; flip test
  (2b); determinism test (2d).
- **Done:** `cd backend && python -m pytest -q` green including the new tests.
- **Dep:** T0.

## T3 — `hand_error_weights` service · owns `backend/app/services/stats.py` (+ test)
- **Do:** `hand_error_weights(session) -> dict[str,float]`: group `DrillAttempt` by `hand_class`
  filtered to `leak_category IN {100..104}`; ≥MIN_N attempts → mean `ev_loss_bb` mapped to
  `[Mmin,Mmax]`, normalized to mean ≈1.0; guard zero/one-row/all-equal (no div-by-zero; return `{}`
  or neutral). Omit classes below MIN_N.
- **Accept:** unit test — seeded attempts with heavy errors on KJo raise KJo's weight; thin/empty
  history returns neutral/empty without error.
- **Done:** `python -m pytest -q` green.
- **Dep:** T1 (needs the column).

## T4 — API wiring · owns `backend/app/api/v1/drill.py`
- **Do:** `_next_challenge(session)` — fetch `hand_error_weights(session)`, call
  `sample_challenge_spot(_RNG, personal_weights=...)`; add `elif mode == "challenge"` to
  `next_drill`; update the module docstring mode list.
- **Accept:** `GET /api/v1/drill/next?mode=challenge` returns a preflop RFI spot with a `grid`;
  grading it works and persists `hand_class`.
- **Done:** API test for the new mode green; `./scripts/verify.sh` OK.
- **Dep:** T2 + T3.

## T5 — Frontend mode · owns `frontend/src/api/types.ts`, `frontend/src/App.tsx`
- **Do:** `Mode` union += `"challenge"`; `MODES` += `{ id: "challenge", label: "Challenge" }`.
- **Accept:** `npm run typecheck && npm run build` clean; "Challenge" selectable, drives
  `?mode=challenge`.
- **Dep:** none (independent).

## T6 — Verify (maker ≠ checker) · read-only, no owned files
A different agent than the builders verifies end-to-end against the spec's Verify-by (steps 1–6 incl.
2b/2c/2d): `./scripts/verify.sh`, `alembic upgrade head`, purity test, distribution/edge/flip/
determinism/personal-blend tests, the `?mode=challenge` API probe, and frontend build. Report
pass/fail with evidence. **Dep:** T0–T5.

## Build shape (waves, ≤3 agents concurrent, one file = one owner)
- **Wave 1 (parallel, disjoint):** T0 · T1 · T5.
- **Wave 2 (parallel, disjoint):** T2 (needs T0) · T3 (needs T1).
- **Wave 3:** T4 (needs T2+T3) — sole owner of drill.py's dispatch.
- **Wave 4:** T6 checker (maker ≠ checker).
