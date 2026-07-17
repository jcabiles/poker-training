# N1 — North-star dashboard · ticket DAG

Spec: `docs/ai-dlc/specs/n1-north-star-dashboard.md` · Contracts: `docs/ai-dlc/contracts/n1-north-star-dashboard.md`
**All frontend. No backend, no migration, no `types.ts`/`client.ts` change.** Verify: `cd frontend && npm run typecheck && npm run build && npm test`; backend stays green (`./scripts/verify.sh`).

| # | Ticket | Owned files | Depends | Done-condition |
|---|--------|-------------|---------|----------------|
| **T0** | Stand up FE test infra | `frontend/package.json`, `frontend/package-lock.json`, `frontend/vitest.config.ts` | — | `npm test` runs a trivial passing test; `typecheck`+`build` still green |
| **T1** | `aggregateRates` + rate helpers | `frontend/src/components/simulate/simGrade.ts`, `…/simGrade.test.ts` | T0 | vitest: aggregate == sum-of-parts, `null` on `graded===0`, only-no-baseline street → `null`; `npm test` green |
| **T2** | `SimDashboard` view | `frontend/src/components/simulate/SimDashboard.tsx` (new) | T1, T5(class-name contract) | Renders 2 KPI cards + by-street both-rate breakdown from `getStreetReport()`; `—`/"no data" at zero; typechecks |
| **T3** | Slim `SimStreetReport` | `frontend/src/components/simulate/SimStreetReport.tsx` | T1, T5(class-name contract) | Compact two-rate headline (no per-street table); fetch/refresh/empty lifecycle intact; BOTH mounts render; typechecks |
| **T4** | Routing | `frontend/src/lib/hashRoute.ts`, `frontend/src/App.tsx` | T2 | `#/dashboard` renders `SimDashboard`; nav shows Dashboard; unknown-view→`home` fallback + `formatHash` intact; `typecheck`+`build` green |
| **T5** | Dashboard + slim-panel styles | `frontend/src/styles/app.css` | — (class-name contract fixed up front) | Token-only KPI-card + by-street-bar + slimmed-panel CSS; AA contrast + visible focus BOTH themes |
| **T6** | Design-review + green gate | — (review only) | T2,T3,T4,T5 | ux-ui-designer → design-reviewer both themes; `typecheck`+`build`+`npm test`+`verify.sh` all green |

## Acceptance criteria per ticket
- **T0** — vitest added as devDependency; `"test": "vitest run"` (and/or watch) script; minimal config resolving TS + jsdom if needed for later component tests (pure-function test needs no DOM). A one-line sample test passes. No app-code change.
- **T1** — `goodPct(row)` (= existing `accuracyPct` behavior, moved/generalized), `optimalPct(row)`, `aggregateRates(rows)` → `{graded, optimal, acceptable, no_baseline, goodPct, optimalPct}`; all rate fields `null` when summed `graded===0`. Test covers: normal mix, all-zero, only-no-baseline, single-street. If `accuracyPct` is folded into `goodPct`, `SimStreetReport`'s existing behavior is unchanged.
- **T2** — primary card = Good Decision Rate (large), secondary = Optimal Play Rate (small), from `aggregateRates`; total graded + no-baseline shown as honest context; by-street rows each show both rates + graded count + no-baseline note, primary as a proportional token bar; every zero path → `—`. Reuses `getStreetReport()` verbatim (no new client call). Same fetch/skeleton/best-effort-hide idiom as `SimStreetReport`.
- **T3** — replace the `<table>` with the compact headline; keep `refreshKey` effect, skeleton, `total_decisions===0` empty state, failure-hide. Verify the pre-session empty-shell mount (`SimulateView.tsx:769-772`) AND live mount (`:755-759`) both render — no `SimulateView.tsx` edit.
- **T4** — add `"dashboard"` to `View` + `VIEW_IDS` (`hashRoute.ts:9,11`); `{id:"dashboard",label:"Dashboard"}` to `VIEWS` (`App.tsx:27-33`); `view==="dashboard" ? <SimDashboard/> : …` branch (`App.tsx:389-393`). `parseHash("#/dashboard")` → dashboard; `parseHash("#/bogus")` → `home` still.
- **T5** — all values from `tokens.css` (`--space-*`, `--radius-*`, existing color/`--sim-tier-*` tokens); no raw hex/px literals; AA contrast + visible focus in light AND dark. Class-name contract agreed with T2/T3 before coding.
- **T6** — maker≠checker: `design-reviewer` (not the builder) grades both themes against the rubric; all deterministic checks green.

## Sequencing / parallelism (honest)
The clean order is **T0 → T1 → {T2 ‖ T3 ‖ T5} → T4 → T6**. But the coupling is real: T2/T3 both import T1's helper and both consume T5's class names; T4 imports T2's component; `app.css` and `App.tsx` are single-owner hotspots. For a slice this small and interdependent, a **single implementer working sequentially is cleaner than a parallel fan-out** — parallelism buys little and adds class-name-contract coordination overhead. Recommend single-agent sequential; reserve `/parallel-waves` for slices with genuinely disjoint, independent tickets (N3/N4 postflop work will fit that better).
