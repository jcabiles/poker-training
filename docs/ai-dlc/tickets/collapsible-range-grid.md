# Tickets — Collapsible range grid

Spec: `docs/ai-dlc/specs/collapsible-range-grid.md`. Frontend-only. 4 tickets.

## Shared contract (pin these names so tickets don't collide)
- **localStorage key:** `rangeGrid.collapsed` — string `"true"` / `"false"`. Absent → expanded.
- **Collapse read helper:** parse strictly — `stored === "true"` → collapsed; else expanded. Wrap
  read + write in try/catch; on throw, degrade to expanded.
- **Body element:** the existing 13×13 + legend wrapper gets `id="range-grid-body"` and stays
  **mounted**; hidden via the `hidden` attribute when collapsed (not unmounted).
- **Header control:** a `<button class="gridtoggle">` with `aria-expanded={!collapsed}` and
  `aria-controls="range-grid-body"`, containing the label ("Range") + a chevron affordance
  (▾ expanded / ▸ collapsed).
- **State init:** `useState(() => readCollapsed())` — lazy initializer, never a post-mount effect.

## T1 — Guard the global keydown handler (refuter HIGH) · owns `frontend/src/App.tsx`
Add a guard at the top of the window `keydown` handler (`~App.tsx:94-111`) so the Space/`n`
next-hand shortcut is skipped when an interactive control has focus.
- **Do:** bail early if `document.activeElement`/`e.target` tag ∈ {BUTTON, INPUT, SELECT, TEXTAREA}
  or `isContentEditable`. Touch nothing else in `App.tsx` (not the `showGrid` gate, not the mount).
- **Accept:** with focus on any `<button>` (e.g. the existing Theme button), pressing Space does
  NOT advance the hand; with focus on the page body after a hand loads, Space/`n` still advances.
- **Done-condition:** `cd frontend && npm run typecheck` clean; manual keyboard check both ways.
- **Dep:** none. Prereq for T2's keyboard acceptance to pass.

## T2 — Accordion header + collapse state + persistence (refuter MED-1/MED-2) · owns `frontend/src/components/RangeGrid.tsx`
Add the header button + collapse state per the shared contract; hide-don't-unmount the body.
- **Do:** lazy `useState` init from `localStorage`; write on toggle (guarded); render header
  `<button>` with `aria-expanded`/`aria-controls`; wrap body in `#range-grid-body`, apply `hidden`
  when collapsed. No `any`; strict boolean parse. No API/type changes.
- **Accept:** grid renders expanded on first load; clicking header hides body + legend, header
  stays; state survives hand-advance and page reload; `localStorage['rangeGrid.collapsed']` tracks
  it; throwing localStorage → still renders expanded, no crash.
- **Done-condition:** `npm run typecheck && npm run build` clean; Verify-by steps 2–4 pass.
- **Dep:** T1 (for the Space-toggle acceptance in the post-decision state).

## T3 — Header/toggle styles (refuter LOW-3) · owns `frontend/src/styles/app.css`
Style `.gridtoggle` as a real, discoverable control; tokens only.
- **Do:** padding / min tap target, `cursor:pointer`, hover affordance, chevron spacing; keep
  visual weight consistent with `.gridwrap`/`.gridtitle`; rely on global `:focus-visible`. No raw
  hex — `tokens.css` vars only.
- **Accept:** header looks clickable (hover + pointer), comfortably clickable target, AA contrast
  in both light and dark themes; `grep -nE '#[0-9a-fA-F]{3,6}' frontend/src/styles/app.css` shows
  no NEW hex added by this ticket.
- **Done-condition:** `npm run build` clean; visual check both themes.
- **Dep:** T2 (needs the `.gridtoggle`/chevron markup to exist).

## T4 — Verify (maker ≠ checker) · read-only, no owned files
A different agent than the T1–T3 builder verifies the whole feature end-to-end.
- **Do:** run `npm run typecheck && npm run build`; Playwright walkthrough of Verify-by steps 2–5,
  INCLUDING Space-toggle both before a decision and after (`result` truthy); confirm postflop shows
  no panel; grep for stray `any` and new hex.
- **Accept:** all Verify-by steps green; no regression to the next-hand shortcut; report a
  pass/fail with evidence.
- **Done-condition:** written verify report; `scripts/verify.sh` still `BACKEND VERIFY OK` (should
  be untouched — frontend-only change).
- **Dep:** T1, T2, T3.

## Build shape
T1→T2→T3 are one coherent build (shared naming, coupled behavior) → **one builder agent**,
sequential in that order. Then **T4 = a separate checker agent** (maker ≠ checker). Two agents
total, not parallel — the files are disjoint but the naming contract couples them, so parallel
workers would just re-coordinate. All frontend; backend/`scripts/verify.sh` untouched.
