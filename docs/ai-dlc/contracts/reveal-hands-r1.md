# Contract map — R1 "Reveal Hands" (2026-07-14)

> Read-only scout output (contract-mapper). Feeds `specs/reveal-hands-r1.md`.
> Feature: after hero folds, villains play out **face-down**; two buttons
> ("Reveal Last-In" / "Reveal All") fetch the finished hand's cards from a **new
> server endpoint**; genuine showdown still auto-reveals. No migration needed.

## 1. Hero-only wire privacy — structural, by shape
- Privacy is enforced by **shape**, not runtime checks. `SeatView`
  (`backend/app/schemas/simulate.py:17-27`) has **no** `hole_cards` field — R1 must
  NOT add one there. Module docstring states the rule (`schemas/simulate.py:3-7`).
- `ShowdownSeatView` (`schemas/simulate.py:30-33`) is the ONLY wire shape with
  `hole_cards: tuple[str,str]` — the sole precedent. Populated from
  `settle().showdown_seats` in `_view()` (`services/sim_session.py:298-308`).
- `SimHand.state_json` (`db/models.py:72-74`) holds the live `HandState`
  server-side ONLY (all 9 seats' hole cards + full_board; never wire-serialized).
  **R1's reveal endpoint is the first deliberate, scoped exception** — return
  per-seat `hole_cards` for the requested reveal set only, never `state_json` whole.
- **R1 must:** introduce cards via a NEW explicit response model (reuse/mirror
  `ShowdownSeatView`), never by adding a field to `SeatView`/`SimulateHandView`.

## 2. Showdown auto-reveal — the contract R1 must NOT break
- `settle()` (`domain/table/engine.py:349-363`) populates `showdown_seats` **only**
  when `len(non_folded) > 1` (a genuine multi-way rank comparison). A fold-out
  (1 remaining) yields `[]` already.
- **The R1 bug:** hero folds, ≥2 villains remain and reach a genuine showdown
  **among themselves** → `settle()` fills `showdown_seats` with their seats →
  `_view()` unconditionally puts them in `hand.showdown` → `SimShowdown.tsx:33-53`
  renders face-up. This is the current face-up leak (Watch-ON path only — see §3).
- **Precise trigger to gate on:** hero already folded this hand
  (`state.seats[HERO_SEAT].status is PlayerStatus.FOLDED` at `hand_over`) — there is
  no explicit "hero folded" flag. `PlayerStatus = IN | FOLDED | ALLIN`
  (`engine.py:57-60`).
- **R1 must:** preserve `settle()` / genuine-showdown behavior byte-for-byte; only
  gate the hero-folded case out of the wire `showdown` list. Do NOT touch `settle()`.

## 3. Hero-fold playout path — `play.py` + FE staging
- `advance_to_hero` (`domain/table/play.py:161-201`) advances bots until hero's turn
  or `hand_over`; returns `(state, events)`. `ActionEvent` is privacy-safe (NO hole
  cards, `play.py:49-62`) — untouched by R1. Called identically after every hero
  action (`sim_session.py:438`) — has no "hero folded" concept.
- **Watch toggle gap:** Watch-OFF fold (`SimulateView.tsx:425-457`, `decide()`)
  posts the fold then **immediately** deals the next hand WITHOUT `adopt()`-ing the
  fold view — the villain-showdown leak never reaches the browser at all. Watch-ON
  fold adopts + stages the villain action batch via `stagedIndex`
  (`SimulateView.tsx:206-259`) at the configured Speed → felt + log narrate it.
  **The face-down watch-and-guess loop only exists when Watch is ON.**
- **Face-up mechanism to flip:** `SimTable.tsx:211-224` — a non-hero seat renders
  face-up iff it's in `showdownBySeat` (i.e. `hand.showdown`); otherwise it already
  renders `<Card faceDown/>`. **The face-down fix is mostly BACKEND** (stop
  populating `showdown` for the hero-folded case); SimTable needs no change to keep
  cards down.
- Roadmap warning: fold-path FE state bugs recurred **3×** in waves 3-6 — test the
  hero-fold branch FIRST.

## 4. Finished-hand data source — no migration
- `SimHand.state_json` (`db/models.py:84`) = `state.model_dump_json()` written on
  every action (`sim_session.py:439,149`): complete durable snapshot, all 9 seats'
  `hole_cards` (all dealt at `start_hand`, `engine.py:87-101`) + `full_board`.
- Reveal endpoint reads it via `HandState.model_validate_json` (same pattern as
  `restore_session`/`villain_range`, `sim_session.py:381,399,652`), gating strictly
  on `hand.status == "complete"`.
- **Hand addressing:** reveal buttons live BESIDE "Deal Next Hand", i.e. fired
  BEFORE `deal_next_hand` advances `session.hand_no` (`sim_session.py:697`). So the
  session's current hand IS the just-completed one → `_current_hand`
  (`sim_session.py:162-167`) resolves it while `status=="complete"`. No `hand_no-1`
  needed. (After Deal Next Hand the row persists but is no longer the current hand —
  never deleted anywhere.)
- **Reveal sets:** "Last-In" = non-hero seats with final `status in (IN, ALLIN)`;
  "All" = all non-hero seats (every seat always has `hole_cards`).

## 5. Endpoint conventions (`api/v1/simulate.py`)
- Router `prefix="/simulate"` (`simulate.py:32`). Read-only session-derived views use
  `/{session_id}/<slug>` (e.g. `preflop-chart` :82, `villain-range/{seat}` :94) —
  reveal follows this, e.g. `/{session_id}/reveal/{scope}` (scope = `last-in|all`).
- **404 seam:** `SessionNotFound` → `HTTPException(404,"session not found")` ONLY.
  Every other unavailability (hand not complete, nothing to reveal, capability off)
  → **200 body with `available=false`**, never 4xx. FE `isSessionNotFound()`
  (`SimulateView.tsx:41-43`) greps `-> 404$` to trigger session-recovery — a wrong
  404 would wrongly wipe the session.
- Declare `response_model=<View>` from `app.schemas.simulate`; service returns the
  Pydantic type field-by-field (never raw dict). Thread `_OWNER_ID=""` sentinel.

## 6. FE integration points
- "Deal Next Hand" lives in `SimShowdown.tsx:59-66`, gated by
  `hand.hand_over && revealHandEnd` (`SimulateView.tsx:671-681`;
  `revealHandEnd = !playing` :510 — buttons wait for playback to finish). New buttons
  go here.
- **Watch-OFF caveat:** `SimShowdown` never mounts for a Watch-OFF fold (view
  discarded) — reveal buttons won't appear there. Scope decision (see spec).
- Reveal state (`revealedCards`/`revealScope`) belongs in `SimulateView.tsx` (sole
  hand-scoped state owner); reset on `gradeKey`/hand transition like
  `narratedHandRef`/`heroBadge` (`:280-317`) so it can't bleed to the next hand.
- One new `api/client.ts` fn (thin `json(fetch(...))`, `:100-169`); add
  `RevealView`/`RevealedSeatView` to hand-maintained `types.ts` (mirror
  `ShowdownSeatView` `:222-226`).
- Render target = inside `SimShowdown` (per "beside Deal Next Hand"), not `SimTable`.

## 7. Capability seam (spec-mandated, new plumbing)
- Spec: reveal routes through a **server-side capability seam** (endpoint +
  togglable flag), NOT an always-on client toggle — a future hidden-persona mode must
  withhold it. **No existing flag mechanism** in `backend/app/` (`SimSession`
  `db/models.py:45-56` has no capability column; no settings flag registry).
- A module-level constant / settings flag gating the endpoint satisfies "togglable
  flag" with **no schema change**. A *per-session* flag would need a `SimSession`
  column + migration — only if the design wants per-session withholding now.

## Escalation
- **No hard blocker.** Cards fully recoverable from `state_json`; no migration.
- **Decision 1 — Watch-OFF scope:** reveal is only reachable in the Watch-ON path as
  built; Watch-OFF folds skip straight to the next hand.
- **Decision 2 — capability seam shape:** constant/settings flag (no migration) vs
  per-session DB column (migration).
