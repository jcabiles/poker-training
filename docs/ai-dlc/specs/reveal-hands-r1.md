# Delta spec — R1 "Reveal Hands: face-down playout + two reveal buttons" (2026-07-14)

> Roadmap slice: `docs/ai-dlc/roadmap/simulate-table.md` Epic-2 **R1** (mark `[x]` when
> pass/fail passes). Contract map: `docs/ai-dlc/contracts/reveal-hands-r1.md`.
> Inherits north-star (deepen the transfer layer) + all global no-gos.

## Goal (one line)
After the hero folds, still-live villains play out **face-down**; two buttons
("Reveal Last-In" / "Reveal All") fetch the finished hand's cards from a **new
server-side reveal endpoint** (gated by a togglable capability flag); a genuine
hero-in showdown still auto-reveals unchanged.

## Locked decisions (2026-07-14 interview)
- **Watch-ON only.** Reveal buttons mount in `SimShowdown` (the Watch-ON hand-end
  panel). Watch-OFF folds skip the villain playout and deal the next hand — no reveal
  there, by design. No new Watch-OFF affordance.
- **Capability flag = a module/settings constant** gating the reveal endpoint
  (default ON). **No schema change, no migration.** A future per-session hidden-persona
  flag is out of scope.
- **"Reveal Last-In"** = non-hero seats whose final status is `IN` or `ALLIN` at
  `hand_over`. **"Reveal All"** = every non-hero seat dealt into the hand (all 9 always
  have hole cards). Hero is never in either set (hero folded).
- **Reveal flips the felt** (refuter low-3, resolved 2026-07-14): revealed cards turn
  face-up at each seat on the felt (`SimTable`), matching genuine-showdown behavior — not a
  separate list in the panel.

## The precise behavior change
1. **Face-down gate (backend, `_view()` in `services/sim_session.py`):** when the hero's
   final status this hand is `PlayerStatus.FOLDED` at `hand_over`, the wire `hand.showdown`
   list is **empty** — even if `settle()` produced `showdown_seats` for a villain-vs-villain
   showdown. This suppresses the current face-up leak. When the hero did **not** fold
   (reached showdown / won), `showdown` is populated exactly as today (auto-reveal
   unchanged). Gate strictly on `FOLDED` (an all-in hero is a genuine showdown participant).
   `settle()` itself is **not** modified.
2. **Playout still animates (already works):** the post-fold villain `ActionEvent` batch
   continues to stage/narrate via `stagedIndex` at the configured Speed. Face-down seats
   already render `<Card faceDown/>` in `SimTable` when absent from `showdownBySeat` — no
   SimTable change needed to keep them down.
3. **New reveal endpoint** returns the requested set's hole cards for the just-completed
   hand, sourced from `SimHand.state_json`.
4. **Two buttons** in `SimShowdown` beside "Deal Next Hand"; clicking fetches the reveal set
   and **flips those seats face-up ON THE FELT** (`SimTable`), matching genuine-showdown
   behavior — the revealed cards appear where hero watched the action, not only in the panel.
   Reveal state lives in `SimulateView`, passed to `SimTable`, reset on hand transition.

## Files / interfaces to touch
**Backend**
- `backend/app/schemas/simulate.py` — new `RevealView` (e.g. `{ available: bool, scope: str,
  seats: list[RevealedSeatView] }`) + `RevealedSeatView { seat_index: int, hole_cards:
  tuple[str,str] }` (mirror `ShowdownSeatView`). Do **not** add `hole_cards` to `SeatView`.
- `backend/app/services/sim_session.py` —
  (a) face-down gate in `_view()` (empty `showdown` when hero `FOLDED` at `hand_over`);
  (b) new `reveal(db, session_id, owner_id, scope)` service fn: load session (raise
  `SessionNotFound` → 404 seam); resolve the current hand via `_current_hand`; if
  `hand.status != "complete"` **or** capability flag OFF **or** hero not folded →
  `RevealView(available=False, ...)`; else deserialize `state_json` via
  `HandState.model_validate_json`, select seats per scope (excluding hero), return
  `RevealView(available=True, seats=[...])`. Reuse the `_view()` card-reading pattern.
- `backend/app/api/v1/simulate.py` — `GET /simulate/{session_id}/reveal/{scope}`
  (`scope` ∈ `last-in|all`), `response_model=RevealView`, `_OWNER_ID` threaded,
  `SessionNotFound` → `HTTPException(404, "session not found")`. Unknown scope → 200
  `available=false` (or 422 via a path enum — implementer's call, must NOT 404).
- Capability flag: one module-level constant (e.g. `REVEAL_ENABLED = True`) in a backend
  module the service imports (e.g. top of `sim_session.py` or a small settings module).

**Frontend**
- `frontend/src/api/types.ts` — add `RevealedSeatView` + `RevealView` (hand-maintained).
- `frontend/src/api/client.ts` — one fn `getReveal(sessionId, scope)` (thin `json(fetch)`).
- `frontend/src/components/simulate/SimShowdown.tsx` — two buttons beside "Deal Next Hand"
  ("Reveal Last-In" / "Reveal All"). Hide/disable when the endpoint reports `available=false`.
- `frontend/src/components/simulate/SimTable.tsx` — accept a `revealedBySeat` map (alongside
  the existing `showdownBySeat`) and flip those seats' cards face-up on the felt.
- `frontend/src/components/SimulateView.tsx` — reveal state (`revealedSeats`/`revealScope`),
  reset on hand transition (mirror `heroBadge`/`narratedHandRef` reset). Wire `getReveal`;
  build `revealedBySeat` and pass it to `SimTable`.
- CSS for the buttons/revealed row via existing sim-scoped tokens in
  `frontend/src/styles/app.css` (tokens only; AA + focus both themes).

## Out of scope
- No auto-reveal on fold; no reveal in the Watch-OFF path; no per-session capability
  column/migration; no persona/read tagging on revealed seats (hidden-persona mode is
  NEXT); **no change to genuine-showdown behavior** (`settle()` untouched); no new pacing;
  no reveal of the hero's own cards (already shown); no reload-durable reveal state.

## Constraints (invariants — must hold)
- Domain core `backend/app/domain/` gets **no** change (reveal is service+API+FE only) —
  domain-purity test stays green.
- Hero-only wire privacy: villain hole cards reach the client **only** via the reveal
  endpoint's explicit `RevealView` or a genuine showdown — never on `SeatView`, never as
  `state_json`. Mirror S9's zero-leak sweep in tests.
- `spot_signature()` untouched; no schema change / no Alembic migration.
- FE types hand-maintained in `types.ts`; CSS from tokens only; WCAG AA + visible focus both
  themes (design-review gate).
- 404 reserved for `SessionNotFound`; all other unavailability → 200 `available=false`.
- EVs/labels: N/A (no grading added here).

## Test-determinism note (refuter med-1 — read before writing tests)
Bots act via `_fresh_rng()` (`random.Random(secrets.randbits(256))`) — **not** seeded from
the persisted `rng_seed` (`sim_session.py:11-16` docstring). Playing through bots to
reproduce "hero folds → ≥2 villains reach a genuine showdown among themselves" is flaky
(the analogous `test_play_hand_to_showdown` needs a 30-hand retry loop and still can't force
a *villain-only* post-fold showdown). **Construct a finished `HandState` directly** (hero
`FOLDED`, ≥2 villains `IN`/`ALLIN`, board dealt) and exercise `_view()` / the reveal service
against it, rather than relying on random bot playout, for the face-down + reveal unit tests.

## Verify-by (end-to-end — what `/verify-change` checks)
1. **Backend** `./scripts/verify.sh` green (pytest + boot probe) with new tests:
   - hero folds → villains reach a genuine showdown among themselves → `_view().showdown`
     is empty (face-down); no villain hole cards on the wire. **This is a NEW privacy-sweep
     test** — the existing `test_hero_fold_ends_hero_participation` only asserts the hero seat
     is absent from `showdown` (vacuously true whether `showdown` is `[]` or non-empty), so it
     is NOT the regression guard for this leak; write a fresh assertion that NO non-hero
     `hole_cards` appear anywhere on the `_view()` wire for a hero-folded hand.
   - hero folds → fold-out (single winner) → reveal endpoint `scope=last-in` returns the lone
     winner; `scope=all` returns every non-hero seat.
   - hero folds → villain showdown → `scope=last-in` returns the showdown participants only.
   - hero **not** folded → genuine showdown still auto-reveals (`_view().showdown` unchanged,
     golden-stable).
   - reveal on a non-complete hand / unknown session → `available=false` / 404 respectively.
   - capability flag OFF → reveal returns `available=false`.
2. **Lint** `cd backend && ruff check .` clean.
3. **Frontend** `cd frontend && npm run typecheck && npm run build` green.
4. **Manual / design-review** (both themes): fold as UTG with Watch ON → villains play out
   face-down; "Reveal Last-In" shows only end-of-hand live villains; "Reveal All" shows every
   dealt villain; a genuine hero-in showdown still auto-reveals; hero-fold FE staging stays
   lockstep (test that path first — recurred 3× historically); AA contrast + visible focus.

## Appetite
~1 small epic (no migration; backend gate + endpoint + FE buttons; playout/pacing reused).
