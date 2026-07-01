# Delta spec — Collapsible range grid

> Small frontend-only feature. Not on the postflop roadmap. Built via the AI-DLC loop
> (scout → spec → refuter → tickets → build → verify). Refuter verdict folded in below.
>
> **Contract scan (verified by refuter against real code):** the range grid is `RangeGrid.tsx`,
> mounted in `App.tsx:170-174` inside an `<aside>`, gated only on
> `showGrid = Object.keys(grid).length > 0` (`App.tsx:118`). Backend sends `grid={}` on every
> non-preflop spot (`backend/app/api/v1/drill.py:199-201`), so the panel is inherently preflop-only.
> A **Theme** toggle button already exists (`App.tsx:126-128`, unpersisted) — so this is the app's
> first *persisted, accordion* toggle, not its first toggle. **Critical adjacent contract:**
> `App.tsx:94-111` registers a **window-level `keydown` handler** for the drill view; when `result`
> is truthy it intercepts Space and `n`/`N`, calls `preventDefault()`, and advances to the next hand.
> This directly collides with a focusable accordion button (see constraint C1).

## Goal (one line)
Let the user collapse/expand the 13×13 range grid via an in-panel accordion header, defaulting
to expanded and remembering the choice across hands and page reloads.

## Behavior (agreed with user)
- **Toggle shape:** in-panel **accordion header**. The grid panel gets a clickable header
  (label + chevron/▸▾ affordance). Clicking it collapses the grid *body* (the 13×13 cells +
  legend) while the header stays visible so the user can re-open it in place.
- **Default:** expanded.
- **Persistence:** the collapsed/expanded choice persists across drills AND page reloads via
  `localStorage`. First-ever load (no stored value) = expanded.
- **Data-gating unchanged:** the whole panel still only renders when `showGrid` is true
  (`grid` non-empty). Collapse state is layered on top of — independent of — that gate. When there's
  no grid data, nothing renders (header included), exactly as today.
- **Hide, don't unmount (refuter MED-1/MED-2):** when collapsed, the body (13×13 + legend) stays
  **mounted** and is hidden via the `hidden` attribute / a CSS class — NOT conditionally unmounted.
  Reason: keeps the `aria-controls` target alive in the DOM, and avoids remounting 169 grid cells
  on every toggle. (The whole `<aside>` still unmounts/remounts on the postflop↔preflop transition
  via the untouched `showGrid` gate — that's fine; see C2.)

## Files / interfaces to touch
- `frontend/src/components/RangeGrid.tsx` — add the accordion header (`<button>`) + collapse state
  + `localStorage` read/write; render the body always-mounted but hidden when collapsed. Owns the
  collapse state (self-contained; leaves `App.tsx`'s data-gate untouched).
- `frontend/src/App.tsx` — **only** the window `keydown` handler (`~94-111`): guard it so the
  next-hand shortcut is skipped when focus is on an interactive control (constraint C1). Do **not**
  touch the `showGrid` gate or the `<aside>` mount.
- `frontend/src/styles/app.css` — header/toggle button styles (reuse token vars; extend
  `.gridwrap`/`.gridtitle`). Give the header a real tap target + `cursor:pointer` + hover affordance
  (constraint C5). No raw hex — design tokens only.
- **No** change to `App.tsx`'s `showGrid` gate, `api/types.ts`, backend, or the API contract.

## Out of scope
- No external/controls-row toggle button (accordion header only).
- No backend, API, `openapi.json`, or TypeScript-type changes (`grid: Record<string,string>` stays).
- No change to *when* the grid appears (the `showGrid` data-gate is untouched).
- No animation polish beyond a basic show/hide (a CSS transition is optional, not required).
- No new dependency, no state-management library, no shared "collapsible" abstraction — this is a
  single local `useState` + `localStorage`, not a reusable framework.
- No new eslint config (see C6 — the "no any" rule is enforced by review, not tooling, this PR).

## Constraints (house rules + refuter findings)
- **C1 — keydown collision (refuter HIGH, blocking).** The window `keydown` handler at
  `App.tsx:94-111` must NOT hijack Space/`n` when the user is operating an interactive control.
  Guard it: at the top of the handler, bail if `document.activeElement` (or `e.target`) is a
  `BUTTON`/`INPUT`/`SELECT`/`TEXTAREA` (or `isContentEditable`). This fixes the accordion Space
  toggle AND protects the existing shortcut from any future focusable control. (Belt-and-suspenders
  `e.stopPropagation()` in the button's own handler is allowed but not sufficient alone.)
- **C2 — no expanded→collapsed flash (refuter MED-2).** Read `localStorage` in a `useState` **lazy
  initializer** (`useState(() => readCollapsed())`), NOT in a post-mount `useEffect`. The `<aside>`
  remounts `RangeGrid` on every postflop→preflop transition, so an effect-based read would paint
  "expanded" for one frame before flipping — a visible flash that breaks the persistence claim.
- **C3 — accessibility.** The toggle is a real `<button>` carrying `aria-expanded` (reflecting
  state) and `aria-controls` pointing at the body's stable `id`; because the body stays mounted
  (hide-don't-unmount), that id always resolves. Keyboard-operable (native `<button>` = Enter/Space
  for free, once C1 lands). Global `:focus-visible` outline applies. Contrast AA in both themes.
- **C4 — localStorage safety.** Guard reads/writes in try/catch (or feature-check) so a disabled /
  throwing `localStorage` degrades to the default (expanded), never crashes. One stable key:
  `rangeGrid.collapsed`. Parse to a strict `boolean` (e.g. compare `=== "true"`), no `any`.
- **C5 — tap target / affordance (refuter LOW-3).** `.gridtitle` today is 13px muted text with no
  padding — the header button needs padding / a min target size, `cursor:pointer`, and a hover
  affordance so it reads as interactive. Tokens-only; no raw hex.
- **C6 — "no any" is review-enforced (refuter LOW-1).** `tsc --noEmit` + `vite build` do NOT forbid
  explicit `any` (no eslint `no-explicit-any` in `frontend/`). Verify-by step 1 catches type errors
  and regressions but not stray `any`; the reviewer checks that by eye.

## Verify-by (end-to-end)
1. `cd frontend && npm run typecheck && npm run build` — clean.
2. Manual/Playwright: load a preflop drill → grid panel visible + expanded. Click the header →
   13×13 body + legend hide, header remains. Advance a hand → still collapsed. Reload the page →
   still collapsed. Click header → expands; reload → still expanded.
3. Reach a spot with no grid data (postflop) → no panel at all (header included), unchanged from
   today.
4. **Keyboard, both states (refuter HIGH):** Tab to the header, press Space — grid toggles (does
   NOT advance the hand). Test this **before** any decision AND **after** submitting a decision
   (`result` truthy, feedback on screen) — the post-decision case is the one C1 fixes. `Enter`
   toggles too; `:focus-visible` outline shows.
5. Regression: the existing Space/`n` "next hand" shortcut still works when focus is NOT on a
   control (e.g. body has focus after loading a hand).

## Pre-build note (not a code task)
Local `main` is stale (sandbox can't fetch GitHub; the merged postflop PR isn't in local `main`).
The freshest local frontend code is on `postflop-features` (`App.tsx` there has all drill modes +
the keydown handler above). Build should branch from up-to-date code — either `postflop-features`
locally, or `main` after the user pulls in their own terminal. Confirm the base branch at Gate 2.
