# Contract — frontend IA + design tokens

> Read-only scan for the "professional-teacher-rework" roadmap. Key files: `frontend/src/App.tsx`,
> `components/RangeGrid.tsx`, `styles/tokens.css`, `styles/app.css`, `api/types.ts`, `api/client.ts`,
> `backend/app/domain/grading.py`, `backend/app/api/v1/drill.py`.

## Current app shell + views

- `View = "drill" | "texture" | "equity"` — plain `useState<View>` (`App.tsx:22-28,67`). **No router library**
  (`package.json` deps = only react/react-dom); view switching is pure conditional rendering (`App.tsx:190-230`).
- **No URL sync / deep-linking / resume** — reload resets to `view="drill"`, `mode="random"`, calls `loadNext("random")`
  on mount (`App.tsx:67-102`). Last-used mode/view never restored.
- `App.tsx` is a **single component owning ALL state** (view/spot/grid/result/mode/studyTestMode/summary/leaks) — no
  context/provider, no separate shell. Topbar (`167-174`), `StatsStrip` (`176`, drill-HUD-shaped), and the `VIEWS` tab row
  (`178-188`) render unconditionally above the view switch.
- Global keyboard shortcuts gated on `view === "drill"` (`App.tsx:128-153`) — invisible contract: any new view must share or
  add its own guard. Theme toggle flips `documentElement.dataset.theme` but is **not persisted** (`App.tsx:155-158`) —
  inconsistent with the two localStorage-backed prefs (`studyTestMode`, `rangeGrid.collapsed`).

## Mode system state (post cheap-wins) — confirmed

Wave 1 regrouping is LIVE and is the only mode UI. `PREFLOP_MODES` (random/review/leak_focus/exploit/challenge) +
`POSTFLOP_MODES` (postflop/vs_cbet/vs_check_raise) render as two labeled `ModeGroup`s (`App.tsx:31-44,192-205`;
`ModeGroup.tsx` `role="group"`+`aria-labelledby`). `Mode` union = exactly these 8 (`types.ts:87-95`). Flat buttons gone.
`StudyTestToggle` (CW-6) is orthogonal, state in `App.tsx`, persisted to `localStorage["studyTestMode"]`; `showGrid`
(`App.tsx:160-163`) = Study shows immediately, Test hides until `result` set. **CW-4/6/7 confirmed shipped.**

## Design-token maturity

- **Solid:** semantic colors `--bg/surface/text/muted/border/primary/good/bad/warn` × light + `[data-theme=dark]`
  (`tokens.css:2-49`), felt/card/suit tokens, action set `--act-raise/call/fold/mixed/on` (`:69-75`). `:focus-visible` =
  3px `--primary` outline (`:62-66`) — good reusable foundation for new nav/hub.
- **Missing (all single flat values, no ramps):** `--radius:10px`, `--space:8px` (multiples via `calc()` — de-facto scale,
  no named steps), one `--shadow` per theme with **no elevation model** (felt→panel→card→overlay; `.panel` doesn't even use
  it). **No type scale at all** — font sizes are raw px scattered across `app.css` (20/15/13/12/11/9px). Zero `--text-*` vars.
- Minor purity gaps: untokenized `rgba(0,0,0,X)` overlays at `app.css:54,433`.

## Grid-cell rendering reality — dominant-color, and it's a BACKEND contract

- `NextDrillResponse.grid: Record<string,string>` (`types.ts:63`) = handclass → `"raise"|"call"|"fold"|"mixed"`, from
  `range_grid()` (`backend/app/domain/grading.py:241-257`). That fn **computes the full per-action mix internally** (`_chart_mix`,
  `full` dict, `:248-250`) then **collapses to one label** (`"mixed"` if ≥2 cross `MIX_THRESHOLD`, else top action, `:251-256`).
  Wired at `drill.py:209`.
- FE renders one class per cell (`RangeGrid.tsx:95`, flat `.cell.action-*` `app.css:413-416`); the `.cell` node has no inner
  segment structure.
- **→ "proportional freq-mix cells" is two-sided:** widen `range_grid()` + API response to return per-action frequencies
  (not a collapsed label) AND restructure `RangeGrid.tsx` markup+CSS (segmented/stacked bar). Not a color/token swap.

## Where new hub/path/plan views slot in

- Adding a 4th `View` is mechanically cheap (extend union + `VIEWS` + a branch). But there's no shell component and the
  existing `VIEWS` tab row already IS the top-level nav — a real home hub **competes with it** for that role (a decision, not
  an insert). `StatsStrip` is session-HUD-shaped, not a dashboard.
- **No router → no deep-linkable/resumable path node or "today's plan" step.** A linkable/resumable learning path needs new
  routing infra (even minimal hash-based). Everything resets to Practice/random on reload.
- No curriculum/content-pack concept reaches the FE today — nearest analog is the flat `Mode` enum. A curriculum/plan view is
  new data plumbing end-to-end.
- Conventions a new view should follow: the `view===` keyboard guard, the localStorage try/catch persistence pattern
  (`App.tsx:50-64`, `RangeGrid.tsx:16-30`).

## Risks

1. **Invariant violated in practice:** `types.ts:1-2` claims types mirror `openapi.json` via `npm run gen:api` →
   `src/api/schema.d.ts`, but **that file doesn't exist** — everything imports the hand-maintained `types.ts`. Drift risk is
   live. Any slice touching API shapes (e.g. freq-mix grid) must regenerate/reconcile, not hand-edit `types.ts` again.
2. **Freq-mix grid needs a backend change** — slicing it "frontend-only" hits a wall at `grading.py:241-257`.
3. **No elevation/type-scale tokens** — hub hierarchy is greenfield on top of `tokens.css`.
4. **No router** — resumable path / today's-plan needs new routing.
5. **Structural `App.tsx` assumptions** (unconditional topbar/StatsStrip/VIEWS row + drill-gated shortcuts) must be
   explicitly accounted for by a hub view.
6. **Theme not persisted** — normalize if the hub adds more prefs.
