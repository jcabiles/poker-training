# N2 — Grading visibility toggle · ticket DAG

Spec: `docs/ai-dlc/specs/n2-grading-visibility-toggle.md` · Contracts: `docs/ai-dlc/contracts/n2-grading-visibility-toggle.md`
**All frontend. No backend, no schema, no migration, no `types.ts`/`client.ts`/`App.tsx` change.** Verify: `cd frontend && npm run typecheck && npm run build && npm test`; backend stays green (`./scripts/verify.sh`).

| # | Ticket | Owned files | Depends | Done-condition |
|---|--------|-------------|---------|----------------|
| **T1** | Toggle component + styles | `frontend/src/components/simulate/SimGradingToggle.tsx` (new), `frontend/src/styles/app.css` (additive) | — | Presentational toggle (mirror `SimWatchToggle`), token-only CSS, AA + visible focus both themes; typechecks |
| **T2** | Wire toggle + gate the two render sites | `frontend/src/components/SimulateView.tsx` | T1 | `COACH_KEY`/`readCoachMode`(default false)/`changeCoachMode` + state; mount toggle in `sim-topbar-controls`; gate `lastGrade` (`:671`) + `SimRecap` mount (`:744`); computation untouched; typecheck+build green |
| **T3** | Review gate | — (review only) | T1,T2 | design-review both themes (badge+recap hide/show, SimShowdown present both modes, side-panel/dashboard unaffected); hidden-mode hand still writes `sim_decision`; persistence across reload; all deterministic checks green |

## Acceptance criteria per ticket
- **T1** — `SimGradingToggle.tsx`: `{ coachMode: boolean, onChange: (next: boolean) => void }`, no internal state. Two-state **Coach ↔ Real play** (coachMode true = Coach/shown). `aria-pressed={coachMode}` + descriptive `aria-label`; visible label "Grading". CSS reuses `SimWatchToggle`/segmented-control classes if they generalize, else minimal token-only rules appended near the watch-toggle block; AA contrast + visible focus in light AND dark.
- **T2** — in `SimulateView.tsx`, mirror the watch idiom exactly: `const COACH_KEY = "simulate.coachMode"`, `readCoachMode(): boolean` (try/catch, **default false**), `changeCoachMode(next)` (setItem try/catch + setState), `const [coachMode, setCoachMode] = useState<boolean>(readCoachMode)` — **no ref** (render-time read). Mount `<SimGradingToggle coachMode={coachMode} onChange={changeCoachMode} />` in `sim-topbar-controls`. Gate: line 671 pass `coachMode ? heroBadge : null`; line 744 wrap the `SimRecap` in `coachMode && (…)`, leaving `SimShowdown` OUTSIDE the wrapper. Do NOT touch `heroBadge`/`mergedRecap`/`tiersByOrdinal`/`gradedHandNo`/`revealHandEnd` computation.
- **T3** — maker≠checker `design-reviewer` (real browser, both themes): toggle flips badge + recap together; `SimShowdown` (cards/next-hand/reveal) present in BOTH modes; side-panel "Your record" + Dashboard unaffected; reload restores the mode; a hidden-mode mapped hand still increments the graded count (recording intact). `typecheck`+`build`+`npm test`+`verify.sh` green.

## Sequencing (honest)
Order **T1 → T2 → T3**. T1 (new component + its CSS) and T2 (SimulateView wiring) are technically disjoint files, but T2 imports T1's component and the whole slice is ~2 small files — a **single implementer sequential** is cleaner than a fan-out (which would only contend on the two single-owner hotspots `SimulateView.tsx`/`app.css`). No vitest-style infra needed — the reducer-free logic is verified by the design-review + a persistence/recording check.
