# Tickets — R1 "Reveal Hands" (2026-07-14)

> Spec: `docs/ai-dlc/specs/reveal-hands-r1.md` · Contracts:
> `docs/ai-dlc/contracts/reveal-hands-r1.md`. Refuter verdict: PASS (findings folded in).
> No migration, no domain change. Owned files flagged single-owner. Serial spine:
> T1 → T2 → T3 (backend) then T4 → T5 (FE); T6 tests + T7 design-review close it.

## Dependency DAG
```
T1 (schemas) ─┬─> T2 (face-down gate) ─┐
              └─> T3 (reveal endpoint) ─┼─> T4 (FE client+types) ─> T5 (FE buttons+felt) ─> T7 (design-review)
                                        └─> T6 (backend tests, parallel w/ FE after T3)
```
T2 and T3 both depend on T1 but are otherwise disjoint (T2 edits `_view()`, T3 adds a new
service fn + route) — can run in parallel by one owner sequentially or two if split carefully,
but both touch `sim_session.py` so treat `sim_session.py` as **single-owner** → do T2 then T3
in one pass. FE (T4→T5) starts once T3's response shape is committed.

---

## T1 — Reveal wire schemas (no leak surface)
**Do:** add `RevealedSeatView { seat_index: int, hole_cards: tuple[str,str] }` and
`RevealView { available: bool, scope: str, seats: list[RevealedSeatView] }` to
`backend/app/schemas/simulate.py` (mirror `ShowdownSeatView`). Do **not** add `hole_cards`
to `SeatView` or any always-on view.
**Owns:** `backend/app/schemas/simulate.py`.
**Acceptance:** models importable; `SeatView` unchanged (no hole-card field added).
**Done-condition:** `cd backend && ruff check . && python -c "from app.schemas.simulate import RevealView, RevealedSeatView"`.

## T2 — Face-down gate in `_view()`
**Do:** in `_view()` (`backend/app/services/sim_session.py`), when the hero's final status is
`PlayerStatus.FOLDED` at `hand_over`, emit an **empty** `showdown` list on the wire (suppress
the villain-only showdown). Hero not folded (incl. all-in/ALLIN) → `showdown` unchanged.
`settle()` is **not** modified.
**Owns:** `backend/app/services/sim_session.py` (`_view` only — shared with T3, single-owner file).
**Acceptance:** hero-folded + villain-showdown hand ⇒ `_view().showdown == []`; genuine
hero-in showdown ⇒ `showdown` byte-identical to today.
**Done-condition:** targeted pytest (added in T6) green; `./scripts/verify.sh` green.
**Depends:** T1. **Hazard:** trace no other consumer breaks — refuter confirmed only
`SimShowdown`/`SimTable` read `showdown`; nothing else (no ledger/grading reader).

## T3 — Reveal service fn + endpoint + capability flag
**Do:** (a) module-level constant `REVEAL_ENABLED = True` (backend module the service imports);
(b) `reveal(db, session_id, owner_id, scope)` in `sim_session.py`: `SessionNotFound` propagates
(→404 seam); resolve current hand via `_current_hand`; if `flag OFF` **or** `hand.status !=
"complete"` **or** hero not `FOLDED` → `RevealView(available=False, scope=scope, seats=[])`;
else deserialize `state_json` via `HandState.model_validate_json`, pick seats per scope
(`last-in` = non-hero `status in (IN, ALLIN)`; `all` = every non-hero seat), return
`RevealView(available=True, ...)`; (c) `GET /simulate/{session_id}/reveal/{scope}` in
`api/v1/simulate.py`, `response_model=RevealView`, `_OWNER_ID` threaded, `SessionNotFound` →
`HTTPException(404, "session not found")`, unknown scope → 200 `available=false` (or path enum,
never 404).
**Owns:** `backend/app/services/sim_session.py` (`reveal` fn + flag), `backend/app/api/v1/simulate.py`.
**Acceptance:** endpoint returns correct seat sets; hero excluded from BOTH sets; never returns
`state_json`/hero cards; 404 only for missing session; flag OFF ⇒ `available=false`.
**Done-condition:** T6 endpoint tests green; `ruff check .` clean.
**Depends:** T1, T2.

## T4 — FE types + client fn
**Do:** add `RevealedSeatView` + `RevealView` to `frontend/src/api/types.ts` (hand-maintained);
add `getReveal(sessionId, scope)` to `frontend/src/api/client.ts` (thin `json(fetch(...))`).
**Owns:** `frontend/src/api/types.ts`, `frontend/src/api/client.ts`.
**Acceptance:** types match T1's models; `getReveal` typed.
**Done-condition:** `cd frontend && npm run typecheck` green.
**Depends:** T3 (response shape committed).

## T5 — Reveal buttons + felt flip
**Do:** two buttons ("Reveal Last-In" / "Reveal All") in `SimShowdown.tsx` beside "Deal Next
Hand", hidden/disabled when `available=false`; reveal state (`revealedSeats`/`revealScope`) in
`SimulateView.tsx`, reset on hand transition (mirror `heroBadge`/`narratedHandRef`); build a
`revealedBySeat` map and pass to `SimTable.tsx`, which flips those seats face-up on the felt
(alongside existing `showdownBySeat`). CSS via existing sim tokens in `app.css`; AA + focus
both themes.
**Owns:** `frontend/src/components/simulate/SimShowdown.tsx`,
`frontend/src/components/simulate/SimTable.tsx`, `frontend/src/components/SimulateView.tsx`,
`frontend/src/styles/app.css` (sim-scoped reveal rules only).
**Acceptance:** Watch-ON hero fold → buttons appear post-playback; click flips the correct set
on the felt; a stale reveal never bleeds onto the next hand (state reset verified);
Watch-OFF fold shows no buttons (skips to next hand).
**Done-condition:** `cd frontend && npm run typecheck && npm run build` green.
**Depends:** T4. **Hazard:** test the hero-fold FE staging path FIRST (recurred 3× historically).

## T6 — Backend tests (privacy sweep + reveal correctness)
**Do:** per the spec's test-determinism note, **construct a finished `HandState` directly**
(hero `FOLDED`, ≥2 villains `IN`/`ALLIN`, board dealt) rather than random bot playout. Assert:
(a) hero-folded hand ⇒ NO non-hero `hole_cards` anywhere on the `_view()` wire (NEW privacy
sweep — not the vacuous `test_hero_fold_ends_hero_participation`); (b) genuine hero-in showdown
⇒ `showdown` unchanged (regression); (c) reveal `last-in` returns only `IN`/`ALLIN` non-hero
seats; `all` returns every non-hero seat; hero in neither; (d) reveal on non-complete hand /
flag OFF ⇒ `available=false`; missing session ⇒ 404.
**Owns:** `backend/tests/test_sim_session.py` (+ new test file if cleaner).
**Acceptance:** all new tests green; total suite still green.
**Done-condition:** `./scripts/verify.sh` green.
**Depends:** T3 (can run parallel with T4/T5).

## T7 — design-review gate (UI slice)
**Do:** run `design-reviewer` on the Simulate table across both themes + breakpoints: fold as
UTG with Watch ON → face-down playout; reveal buttons; felt-flip on each scope; genuine
showdown still auto-reveals; AA contrast + visible focus on the new buttons/cards.
**Owns:** (review only — no new files).
**Acceptance:** design-review verdict acceptable (issues folded before merge).
**Done-condition:** reviewer PASS (or ship-with-nits, nits fixed).
**Depends:** T5.

---

## Parallelization summary
- **Backend spine (single owner of `sim_session.py`):** T1 → T2 → T3, in order.
- **After T3:** T6 (tests) ‖ T4 → T5 (FE) can run in parallel (disjoint files).
- **T7** closes after T5. Maker ≠ checker: refuter on the diff + design-reviewer on UI (T7).
- Total: 7 tickets, no migration, no domain-core change.
