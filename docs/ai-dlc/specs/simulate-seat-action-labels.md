# Delta spec — Simulate: per-seat last-action labels + taller felt

Created 2026-07-14. Slice of `roadmap/simulate-table.md` (Track E — session/UI/polish).
Follows the S9b crowding fix and S11 pacing polish. NEXT-tier UI refinement (all NOW
slices S1–S11 shipped).

## Goal (one line)
Show each seat's last action as a verb label on the felt — directly above that seat's
cards and above its bet-size puck — and grow the Simulate felt vertically so the added
text isn't crowded.

## Requirements (Gate 1, confirmed 2026-07-14)
1. **Scope = per street.** The label shows the seat's last action *on the current
   street*; it clears when the street advances (same rhythm as the `.sim-chips`
   bet-size puck). A **folded** seat keeps reading "Fold" persistently (it stays
   dimmed) regardless of which street it folded on.
2. **Content = verb only.** `Fold / Check / Call / Bet / Raise` — Title Case. No
   amount in the label; the amount already lives in the `.sim-chips` puck below it
   (no duplication → less width → de-crowds).
3. **Height = generous.** Grow the sim ring ~+1.5 card-heights, re-verified against
   `.stage overflow:hidden` clipping by a Playwright bounding-box sweep (back off if
   anything clips).

## Data source decision (not a user choice — correctness)
Use a **backend-derived field**, not FE-from-`events`. `hand.events` only carries bot
actions *since the last hero decision* (misses the hero, misses pre-batch actions, and
is wiped on reload). The domain `HandState.action_history` (`list[HistoryAction]{street,
position, action, amount_bb}`) records **every** action and is **not** reset per street,
so per-seat last-action is fully derivable in the view builder. This survives reload
(action_history lives in the persisted `state_json`), covers all 9 seats + the hero, and
needs **no migration and no domain change** — `SeatView` is assembled per request, never
stored.

## Files / interfaces to touch
- `backend/app/schemas/simulate.py` — add `last_action: str | None` to `SeatView`.
- `backend/app/services/sim_session.py` (`get_session_view`) — derive `last_action` per
  seat from `state.action_history`:
  - **derivation:** last `HistoryAction` whose `position == eng.position` **and**
    `street == state.street` **and** `action != POST`; its `action.value` (lowercased
    verb) is `last_action`. If none this street → `None`.
  - **folded override:** if `eng.status is FOLDED` → `last_action = "fold"` (persistent
    across streets — a fold is a hand-level state).
  - **POST excluded:** forced blinds are not a voluntary action; the blind amount already
    shows in the chips puck. A seat whose only current-street entry is POST → `None`.
- `frontend/src/api/types.ts` — add `last_action: string | null` to `SeatView`
  (hand-maintained; keep the comment style).
- `frontend/src/components/simulate/SimTable.tsx` — render the label on both villain and
  hero pods, above the cards, **gated on `revealed`** (the existing lockstep gate — the
  felt must never show an action before the event log narrates it). Title-case the verb.
- `frontend/src/styles/app.css` —
  - new `.sim-last-action` class: `order: -2` (renders above `.sim-chips`'s `order:-1`,
    which is above the cards); felt-toned, AA ≥4.5:1 on **both** themes incl. the lighter
    Night felt and the `.tseat-folded` dim state; nowrap.
  - grow `.simulate .tablering { max-height: calc(var(--card-h) * 5) → * 6.5 }` and the
    `@media (max-height: 920px)` override `* 4 → * 5`.
  - if the sweep shows vertical spread is still tight, bump the **top-half** y-radius in
    `SimTable.slotStyle` (currently `sin<0 ? 41 : 38`) — never the bottom (38 keeps the
    hero pod clear of `.stage overflow:hidden`).

## Known caveats (refuter pass, 2026-07-14 — accepted, not blockers)
- **Cross-street batch lockstep coarseness.** `advance_to_hero` (`domain/table/play.py`)
  batches bot actions across street boundaries into one `events` array, and `revealAt`
  records each seat's *last* index in the whole batch. For a seat whose only batched action
  was on a now-closed street, its reveal threshold fires while `last_action` is already
  `None` (correctly cleared per-street server-side) → the pod reveals with no verb at the
  moment the log narrates that action. This is a **pre-existing** quirk (the `.sim-chips`
  puck already behaves this way — a seat with 0 current-street chips shows no puck); the
  label only makes the absence more noticeable. **Accepted as-is** — do not add per-action
  street-boundary staging to "fix" it (out of scope; would re-open S11 pacing). Render
  nothing when `last_action` is `None`; never fabricate a stale verb.
- **Hero-pod placement pitfall.** The `order:-2` trick works only for a direct flex child
  of a flex-column. The villain pod (`.tseat`) is flat flex-column ✓. The hero pod nests
  cards inside `.hero-ring` (no `display:flex`), so the label MUST be a sibling of
  `chips` / `hero-ring` / `herometa` at the `.heroseat` level — not inside `.hero-ring`.

## Out of scope
- No amount in the label (verb only); no whole-hand action history (per-street only).
- No new domain logic, no engine change, no `action_history` change, **no migration**.
- No change to `PokerTable.tsx` / Practice / Quiz felt (sim-scoped selectors only).
- No `events[]` / event-log change; no new API endpoint.
- No mobile/≤600px work (roadmap-deferred; desktop + tablet only).
- No new design tokens unless a felt-safe existing token can't hit AA.

## Constraints (from profile invariants)
- CSS values from design tokens only (no raw hex/px outside `tokens.css`).
- WCAG AA contrast + visible focus, **both** themes (label is text on felt → verify the
  Night felt, which has repeatedly measured under-AA at low mixes — see `.sim-persona`).
- `types.ts` hand-maintained to match the wire (schema.d.ts unwired).
- Domain purity untouched (no domain files in this slice).
- `spot_signature()` untouched; no SRS/grading path touched.
- Lockstep (S11): label respects the same staged `revealed` gate as chips/fold state.

## Verify-by (end-to-end)
- `./scripts/verify.sh` → "BACKEND VERIFY OK" (pytest incl. a new `last_action`
  derivation test: current-street verb, per-street clear, folded override, POST excluded)
  + boot probe.
- `cd backend && ruff check .` clean.
- `cd frontend && npm run typecheck && npm run build` green.
- Manual/Playwright on `#/simulate`: deal a hand → each acted seat shows a Title-Case verb
  above its cards; label updates as seats act and **clears on street change**; folded
  seats read "Fold"; hero pod shows the hero's own last action. Bounding-box sweep at
  1440×900 / 1280×800 / 1024×768 → **no** hero-pod or board clipping and **no** pod
  overlap after the height bump. `design-reviewer` verdict acceptable (AA both themes,
  lockstep intact).
