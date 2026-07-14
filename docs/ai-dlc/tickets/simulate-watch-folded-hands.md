# Tickets — Simulate: watch villains play out after hero folds

Spec: `docs/ai-dlc/specs/simulate-watch-folded-hands.md`. **Frontend-only.** Ship in one PR.
Sequential (all touch or depend on `SimulateView.tsx`); T1 and T3 can be drafted in parallel but
land together. `frontend/src/styles/app.css` is a hotspot → single owner (T1).

## T1 — Watch toggle component + pill styling
Create `frontend/src/components/simulate/SimWatchToggle.tsx`: a single pill toggle labeled
**"Watch"**, same size/shape as a Speed pill ("Normal"). Props `{ watch: boolean; onChange:(next:boolean)=>void }`.
Toggle-button semantics (`<button type="button" role="switch"`/`aria-pressed`), title/tooltip
"Play out folded hands". Add pill CSS to `frontend/src/styles/app.css` reusing the Speed-pill
tokens; ON state mirrors `.sim-speed-input:checked + .sim-speed-face`; visible `:focus-visible`.
- **Owns:** `SimWatchToggle.tsx` (new), `app.css` (hotspot, this pass).
- **Acceptance:** component renders a pill visually matching "Normal"; ON/OFF visually distinct;
  AA contrast + visible focus in both themes.
- **Done:** `cd frontend && npm run typecheck && npm run build` green; component imported by T2.

## T2 — Watch state + render toggle left of Speed
In `SimulateView.tsx`: add `watch` state (default `true`), read/write to `localStorage`
mirroring the existing `speed` pattern (`readSpeed`/`changeSpeed`). Render `<SimWatchToggle>`
**immediately left of** `<SimSpeedPicker>` in `.sim-topbar-controls` (line ~564).
- **Owns:** `SimulateView.tsx` (state + render only; fold branch is T3).
- **Acceptance:** toggle appears left of Speed, defaults ON, persists across reload.
- **Done:** typecheck + build green. Depends on T1.

## T3 — Branch the hero-fold path on the toggle
In `SimulateView.tsx` `decide` (~lines 397-425): when `action === "fold"`, branch on `watch`:
`!watch` → today's skip shortcut verbatim; `watch` → normal path
`run((id) => postHeroAction(id, { action }))` (adopt the fold response so villains narrate to
showdown + recap shows). Fold refuter findings in here (report bump, openRangeSeat close,
narrated-count base, timer cancel are handled by `adopt`/normal path — confirm none is lost).
- **Owns:** `SimulateView.tsx` (`decide` fold branch).
- **Acceptance:** Watch ON + fold → villain playout narrates to showdown + settlement + recap +
  "Deal next hand" works; Watch OFF + fold → instant skip to next hand (today's behavior), no recap.
- **Done:** typecheck + build green; manual verify per spec step 3-4. Depends on T2.

## T4 — Verify + design review
Run `cd frontend && npm run typecheck && npm run build` and `./scripts/verify.sh` (must stay green
— no backend delta). Manual verify-by steps 2-5 from the spec. Spawn `design-reviewer`
(maker ≠ checker) on the running app: pill parity with Speed, AA contrast + focus both themes,
folded-playout narration reads correctly, no card leak of folded villains.
- **Owns:** nothing (review only).
- **Acceptance:** all verify commands green; design-reviewer verdict ship (nits folded).
- **Depends on:** T3.
