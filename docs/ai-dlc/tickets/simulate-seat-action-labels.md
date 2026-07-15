# Tickets — Simulate: per-seat last-action labels + taller felt

Spec: `docs/ai-dlc/specs/simulate-seat-action-labels.md`. Slice of `roadmap/simulate-table.md`
(Track E). Small epic. Implement single-agent, ticket-by-ticket (files overlap the sim
hotspots — not parallel-safe within this slice).

DAG: **T1 (backend field + derivation + test)** → **T2 (FE wire: types + label render)** →
**T3 (CSS: label style + felt height)** → **T4 (verify: refuter + design-review + sweep)**.
T2 depends on T1's wire field; T3 depends on T2's markup; T4 gates the slice.

---

## T1 — Backend: derive `last_action` per seat
**Files (owned):** `backend/app/schemas/simulate.py`, `backend/app/services/sim_session.py`,
`backend/tests/` (new/extended test).
**Do:**
- Add `last_action: str | None` to `SeatView` (schema).
- In `get_session_view`, per seat compute `last_action`:
  - folded seat (`eng.status is FOLDED`) → `"fold"` (persistent).
  - else → the last `HistoryAction` in `state.action_history` with `position == eng.position`
    **and** `street == state.street` **and** `action` is not POST → its lowercase verb;
    else `None`.
- No migration (SeatView is per-request only), no domain change.
**Acceptance:** unit test asserts: (a) a seat that raised this street → `"raise"`; (b) after
street advance with no new action → `None` (per-street clear); (c) folded-on-earlier-street
seat → `"fold"`; (d) a seat whose only current-street entry is a blind POST → `None`.
**Done-condition:** `./scripts/verify.sh` → "BACKEND VERIFY OK"; `cd backend && ruff check .`
clean.

## T2 — FE: wire type + render the label
**Files (owned):** `frontend/src/api/types.ts`,
`frontend/src/components/simulate/SimTable.tsx`.
**Do:**
- Add `last_action: string | null` to `SeatView` in `types.ts` (match comment style).
- In SimTable, render a `.sim-last-action` element on both villain and hero pods, above the
  cards, Title-cased verb, **only when `revealed`** (existing lockstep gate — villain uses
  `revealed = seat.is_hero || isRevealed(seat.position)`; hero always revealed). Folded
  villains show "Fold". No amount. **Render nothing when `last_action` is `null`** (do not
  fabricate a stale verb — see spec caveat on cross-street batches). **Hero pod:** place the
  label as a sibling of `chips`/`hero-ring`/`herometa` at the `.heroseat` level, NOT inside
  `.hero-ring` (no `display:flex` there → `order` would no-op).
**Acceptance:** typecheck passes; label appears above cards; hidden until the seat is
`revealed` (no leak ahead of the event log).
**Done-condition:** `cd frontend && npm run typecheck && npm run build` green.

## T3 — CSS: label styling + taller felt
**Files (owned):** `frontend/src/styles/app.css` (+ possibly `SimTable.slotStyle` y-radius
in `SimTable.tsx` if the sweep needs it — coordinate with T2's owner = same agent).
**Do:**
- `.sim-last-action`: `order: -2` (above `.sim-chips` order:-1 → above the cards);
  felt-toned via existing tokens; AA ≥4.5:1 on **both** themes incl. Night felt + the
  `.tseat-folded` dim state; `white-space: nowrap`.
- Grow `.simulate .tablering` max-height `*5 → *6.5` and the `@media (max-height:920px)`
  override `*4 → *5`.
- Tokens only (no raw hex/px).
**Acceptance:** label sits above cards/puck; felt visibly taller; no token-lint / raw-value
violations; build green.
**Done-condition:** `cd frontend && npm run build` green.

## T4 — Verify: refuter + design-review + clipping sweep
**Files (owned):** none (review only).
**Do:**
- Fresh `refuter` on the diff (backend + FE).
- `design-reviewer` on `#/simulate` across both themes: AA contrast of the new label,
  lockstep intact, no regression.
- Playwright bounding-box sweep at 1440×900 / 1280×800 / 1024×768: assert **no** hero-pod
  or board clipping against `.stage overflow:hidden` and **no** pod overlap after the height
  bump. If anything clips, reduce the max-height / adjust top-half y-radius and re-sweep.
**Acceptance:** both reviewers acceptable; sweep clean at all three sizes.
**Done-condition:** `./scripts/verify.sh` + `cd frontend && npm run typecheck && npm run
build` all green; reviewer verdicts folded.
