# Delta spec — Simulate: watch villains play out after hero folds

**Slice of:** `docs/ai-dlc/roadmap/simulate-table.md` (Simulate initiative). This partially
**reverses S11's** "hero-fold ⇒ instant skip to next hand" optimization, behind a user toggle.

## Goal
When the hero folds, let the user **watch the remaining villains play the hand out to
showdown** (villain-vs-villain), instead of instantly skipping to the next deal. A **"Watch"
toggle** (default ON) governs it; OFF restores today's instant skip.

## Why this is small
The backend **already computes** the full post-fold villain playout: `advance_to_hero`
(`backend/app/domain/table/play.py:173`) loops until `hand_over` whenever the hero is not
to-act, so `apply_hero_action` already returns every remaining `ActionEvent` + the `showdown`
settlement + the `recap` (returned whenever `state.hand_over`). Today the **frontend discards
it**: the "hero-fold shortcut" in `SimulateView.tsx:403-418` throws the fold response away and
immediately calls `postNextHand`. This change stops discarding it (when Watch is ON) and lets
the existing playback engine narrate it. **No backend, domain, schema, or migration change.**

## Behavior
- **Watch ON (default):** hero fold routes through the *normal* action path — the fold response
  is adopted, the existing `stagedIndex`/`revealAt` playback narrates the villain actions at the
  current Speed, folded villains muck (privacy unchanged — only `showdown_seats` reveal cards),
  the `SimShowdown` settlement slip appears, the **end-of-hand recap shows** (fold decision grade
  + tier), and the user deals the next hand via the existing "Deal next hand" control — identical
  flow to a hand played to showdown.
- **Watch OFF:** today's behavior verbatim — instant skip, street-report bump, auto-deal next
  hand, no recap.
- The toggle is read at **fold-decision time**; toggling it does **not** interrupt an in-flight
  playout (defined behavior, not a bug).
- **Accepted new visual state (refuter low-1):** with Watch ON the hero pod renders *folded*
  (dimmed) while the villain playout narrates, and the fold's grade badge (`SimVerdictBadge`)
  shows immediately on adopt (`SimulateView.tsx:120-124,259` — intentional badge-immediacy). This
  hero-folded + still-narrating-felt + visible-badge combination was impossible before (the
  shortcut discarded the fold view). It is accepted — do **not** special-case hiding the badge.
- **Fold-into-one-live-villain edge (refuter low-2):** if the fold ends the hand with no further
  villain action (`eventCount === 0`, e.g. action folds around to one live seat), `playing` is
  false on first render — recap/showdown appear with zero felt narration. Graceful degrade, not a
  bug; the "villains narrate to showdown" wording covers zero-length playouts.
- Speed `instant` + Watch ON ⇒ playout resolves instantly to showdown + recap + "Deal next hand"
  button (no auto-deal) — consistent with instant-speed played-to-showdown hands.

## Files / interfaces to touch
- `frontend/src/components/simulate/SimWatchToggle.tsx` — **new**. Single pill toggle labeled
  **"Watch"**, styled to match a Speed pill (`.sim-speed-face`), same size/shape as "Normal".
  Toggle-button semantics (`aria-pressed`), visible focus, AA contrast in both themes.
- `frontend/src/components/SimulateView.tsx` — new `watch` state (default `true`), persisted to
  `localStorage` mirroring the existing `speed` read/write; render `<SimWatchToggle>` **immediately
  left of** `<SimSpeedPicker>` inside `.sim-topbar-controls`; in `decide`, branch the `fold` case:
  `!watch` → existing skip shortcut; `watch` → normal path
  (`run((id) => postHeroAction(id, { action }))`).
- `frontend/src/styles/app.css` — pill styling for the toggle (reuse the Speed-pill token values;
  the checked/ON state must mirror `.sim-speed-input:checked + .sim-speed-face`). **Hotspot —
  single owner this pass.**

## Out of scope
- No backend / domain / `sim_session.py` / API / schema / migration change.
- No separate "skip this hand" button mid-playout (the toggle + Speed setting are the escape).
- No change to played-to-showdown hands, to the villain-range panel, or to grading logic.
- No interrupt of an already-animating folded playout when the toggle flips.

## Constraints (from profile)
- CSS values from **design tokens only** (no raw hex/px outside `tokens.css`).
- **WCAG AA** contrast + **visible focus** for the toggle in **both** themes (it is interactive).
- FE types stay hand-maintained in `frontend/src/api/types.ts` — but this change adds **no new API
  field**, so `types.ts` is untouched.
- Domain purity, `spot_signature()` freeze, StrategyProvider seam — all **untouched** (FE-only).

## Verify-by (end-to-end)
1. `cd frontend && npm run typecheck && npm run build` — green.
2. Boot (`./scripts/serve.sh start`), open Simulate. Toggle **defaults ON**; a "Watch" pill sits
   left of "Speed", same size/shape as "Normal".
3. Fold with Watch ON → villains narrate to showdown at the current Speed → settlement slip +
   end-of-hand recap show → "Deal next hand" advances. Folded villains never reveal cards except
   `showdown_seats`. Exercise **both** a multi-villain playout **and** a fold-into-one-live-villain
   hand (zero-narration degrade) — both must land on showdown + recap cleanly.
4. Toggle Watch **OFF**, fold → instant skip straight to the next hand (today's behavior), no recap.
5. Reload page → toggle state persisted. `./scripts/verify.sh` still green (no backend delta).
