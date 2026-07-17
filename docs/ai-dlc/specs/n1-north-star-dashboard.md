# N1 — North-star dashboard: Good Decision Rate + Optimal Play Rate, by street

**Status:** spec (Gate-2 pending) · **Roadmap slice:** Epic 3 · N1 (supersedes R6) · **Outcome-link:** the north-star metric block in `docs/ai-dlc/roadmap/simulate-table.md`. · **Appetite:** ~1 small epic (FE-only). · **Codex dual-review:** yes.

## 1. Goal / outcome-link
The two north-star rates only appear today as a cramped numbers table in the Simulate side panel. N1 gives them a real home: a dedicated **Dashboard** view with the two rates as prominent KPI cards on top and a by-street breakdown below. Makes "how good are my decisions, and where do I leak" answerable at a glance. **Ships entirely from existing `sim_decision` data** — no backend, no migration.

- **Good Decision Rate = (optimal + acceptable) / graded** — PRIMARY.
- **Optimal Play Rate = optimal / graded** — secondary.
- "No baseline yet" decisions are EXCLUDED from the `graded` denominator (existing convention — inherited, not re-invented).

## 2. Locked interview decisions (2026-07-16)
- **New top-level "Dashboard" nav view** (added to the nav next to Simulate/Practice). **Not** the default landing view — `home` stays default.
- **v1 = aggregate KPI cards + by-street breakdown.** No over-time trend (natural Next slice; would need a new date-bucketed aggregation). **This revises the roadmap's N1 line**, which mentioned a "trend/mix chart" — the *mix* (by-street breakout) ships; the *over-time trend* is deferred per this interview (roadmap N1 line annotated to match).
- **Simulate decisions only** (`sim_decision` table). Practice reps NOT counted — deferred to N7's cumulative-metrics interview.
- **By-street rows show BOTH rates + graded count** (+ no-baseline note), not just the primary.
- **Simulate side panel is slimmed to a compact all-time headline** — just the two overall rates (all-time), no per-street table. The full per-street breakdown moves to the Dashboard. **Stays frontend-only** (compact headline = client-side sum of the same `getStreetReport()` rows; NOT current-session-scoped, which would need new backend).
- **Honest empty/zero state** — show `—`/"no data", never `0%` or `NaN`, when `graded === 0`. Surface graded count + no-baseline so sparse coverage reads honestly.
- **Frontend unit tests via vitest** (decision 2026-07-16): the FE has NO test runner today (backend has 593 tests; FE has none). N1 adds **vitest + a minimal config** — the repo's first FE test infra — and unit-tests the `aggregateRates` reducer. Backend keeps its existing suite (`verify.sh`).

## 3. Contract map (from N1 scan, file:line anchors)
- **Backend already computes everything — zero backend change.** `street_report` (`backend/app/services/sim_session.py:584-619`) returns, per street, `{graded, optimal, acceptable, mistake, blunder, ev_loss_bb, no_baseline}`, always all four streets zero-filled, owner-scoped (`:592`), excluding `correctness is None` from graded (`:609-611`). Endpoint `GET /simulate/report/streets` (`backend/app/api/v1/simulate.py:88-90`, owner `_OWNER_ID=""` at `:45`).
- **Schema already exposes the fields** — `StreetReportRow` / `StreetReportView` (`backend/app/schemas/simulate.py:57-77`): `rows[]` + `total_decisions` (= graded + no_baseline across all streets).
- **FE types already match** — `StreetReportRow` / `StreetReportView` (`frontend/src/api/types.ts:260-274`). **No `types.ts` change.**
- **Client fetch already exists** — `getStreetReport()` (`frontend/src/api/client.ts:142-144`). **No `client.ts` change.**
- **The primary-rate FORMULA already exists** (currently a PRIVATE, non-exported function `accuracyPct(row)` = `(optimal+acceptable)/graded`, `null` when `graded===0`, scoped inside `SimStreetReport.tsx:18-21` — not in `simGrade.ts`, not imported anywhere). N1 **moves/generalizes it into `simGrade.ts` as `goodPct`** (behavior-identical), adds `optimalPct` = `optimal/graded`, and an all-streets aggregate reducer.
- **Correctness enum** — `Correctness(StrEnum)` `backend/app/domain/evaluation.py:17-21`: `optimal | acceptable | mistake | blunder`. The `_GOOD = {"optimal","acceptable"}` grouping precedent lives at `backend/app/services/stats.py:13`.
- **No-migration confirmed** — `sim_decision` (migration `0010_sim_decision_and_source.py`) already carries `street`, `correctness (nullable)`, `ev_loss_bb`, `coverage`. Model `backend/app/db/models.py:88-115`.
- **Routing** — `View` union + `VIEW_IDS` (`frontend/src/lib/hashRoute.ts:9,11`); nav `VIEWS` array (`App.tsx:27-33`); render dispatch (`App.tsx:389-393`, `view === "simulate" ? <SimulateView /> : <QuizPanel />`).
- **Side-panel mount points** — `SimStreetReport` mounts twice inside `SimulateView`: live-session aside (`SimulateView.tsx:755-759`) and pre-session empty-shell aside (`SimulateView.tsx:769-772`). Both take `refreshKey`. Slimming the component updates both mounts at once.
- **No chart library** (`frontend/package.json` — only react/react-dom). All Simulate visuals are bespoke token-CSS. Nearest precedent: the `.sim-tally` / `.sim-tier-good|neutral|warn|bad` colored count markers (`SimStreetReport.tsx:108-121`, CSS `app.css:3254-3270`, `3506-3532`). A proportional by-street **bar** is new (small) token-CSS.
- **Tokens** — `frontend/src/styles/tokens.css` (`--space-*` `:97-103`, `--radius-*` `:106-111`, color tokens elsewhere). Report CSS block starts at `app.css:3403` (`.sim-report`).
- **Shared FE util** — `streetLabel` / `fmtEvLoss` in `frontend/src/components/simulate/simGrade.ts` (imported by `SimStreetReport.tsx:5`). The new aggregate helper belongs here so both the Dashboard and the slimmed panel share one implementation.

## 4. Changes (all frontend — zero backend, zero migration)
### 4a. Shared aggregate helper (`simGrade.ts`, additive)
- Add `goodPct(row)` = `(optimal+acceptable)/graded` (mirror of existing `accuracyPct`), `optimalPct(row)` = `optimal/graded`, both `null` when `graded===0`.
- Add `aggregateRates(rows: StreetReportRow[])` → `{ graded, optimal, acceptable, no_baseline, goodPct: number|null, optimalPct: number|null }` summing across all rows (aggregate KPI = client-side reduction; `null` rates when total `graded===0`).

### 4b. New Dashboard view (`SimDashboard.tsx`, new file)
- Fetches `getStreetReport()` (same lifecycle idiom as `SimStreetReport` — mount fetch, best-effort failure hide, skeleton while `null`).
- **Top:** two aggregate KPI cards — **Good Decision Rate** (large, primary) and **Optimal Play Rate** (smaller, secondary), from `aggregateRates(rows)`. Show total graded (and no-baseline count) as honest context. `—`/"no data" when `total_decisions === 0` or aggregate `graded === 0`.
- **Below:** by-street breakdown — for each of Preflop/Flop/Turn/River, a row/card showing **both** `goodPct` and `optimalPct`, the `graded` count, and a `no_baseline` note; primary rate rendered as a proportional token-CSS **bar**. `—` per street when `graded===0`. `≈EV-loss` per street is OPTIONAL (data present; include muted only if cheap, else defer).
- Reuses `streetLabel` from `simGrade.ts`. Approximate labeling: the rates are exact verdict ratios (no ≈ needed); any ≈EV-loss shown keeps the existing `≈` treatment.

### 4c. Slim the side panel (`SimStreetReport.tsx`)
- Replace the per-street `<table>` with a **compact all-time headline**: the two overall rates (`aggregateRates(rows)`) + total graded, no per-street rows. Keep the `refreshKey` fetch lifecycle, the skeleton, the `total_decisions === 0` empty state, and the best-effort-hide-on-failure behavior. Both existing mount points (`SimulateView.tsx:755-759`, `:769-772`) inherit the compact form — **no `SimulateView.tsx` edit needed**.

### 4d. Routing (`hashRoute.ts` + `App.tsx`)
- `hashRoute.ts:9,11` — add `"dashboard"` to the `View` union and `VIEW_IDS`.
- `App.tsx:27-33` — add `{ id: "dashboard", label: "Dashboard" }` to `VIEWS`.
- `App.tsx:389-393` — add a `view === "dashboard" ? <SimDashboard /> : …` render branch.

### 4e. Styles (`app.css`, additive)
- New token-only rules for the Dashboard KPI cards + by-street bars, and the slimmed compact-headline panel. AA contrast + visible focus in both themes. Append near the existing `.sim-report` block (`app.css:3403`).

## 5. Pass/fail
- A **Dashboard** entry appears in the nav; selecting it (or `#/dashboard`) renders the dashboard; it is NOT the default view (`home` still default; `#/dashboard` deep-links + reload-restores via existing hash routing).
- With graded decisions present, the Dashboard shows two KPI cards — Good Decision Rate `(optimal+acceptable)/graded` and Optimal Play Rate `optimal/graded` — matching a hand-computed aggregate over the `getStreetReport()` rows, plus a by-street breakdown where **each street shows both rates + graded count**.
- **Empty/zero honesty:** with no graded decisions, the Dashboard and the slimmed side panel show "no data"/`—`, never `0%`/`NaN`; a street with `graded===0` shows `—` (not `0%`). No-baseline counts are surfaced, not hidden.
- **Aggregate == sum of parts:** the aggregate Good/Optimal rate equals the client-side sum of `optimal`/`acceptable`/`graded` across the four street rows — enforced by a **vitest** unit test on `aggregateRates` (sum-of-parts, `null`-on-zero, only-no-baseline street). `npm test` (new script) green.
- **Side panel slimmed:** both `SimStreetReport` mounts now show the compact two-rate headline, not the per-street table; the fetch/refresh/empty lifecycle still works (bumping `refreshKey` after a hand refetches).
- **No backend touched:** `street_report` service, endpoint, schemas, `sim_decision` model, and Alembic head are byte-unchanged (assert migration head unchanged; grep shows no edit under `backend/`). No `types.ts` / `client.ts` change.
- **Invariants:** no `backend/app/domain/` change; `spot_signature()` untouched; all new CSS values from tokens; AA contrast + visible focus verified in both themes (design-review).
- `cd frontend && npm run typecheck && npm run build` green; `./scripts/verify.sh` green (unchanged backend); design-review both themes.

## 6. Refuter-target risks
- **Denominator drift:** does any new aggregate accidentally count `no_baseline` (or `mistake`/`blunder` streets with `graded===0`) into `graded`? Prove `aggregateRates` sums only `graded`/`optimal`/`acceptable` and divides by summed `graded`, `null` when zero — matching the frozen `accuracyPct` convention.
- **Div-by-zero / NaN:** every rate path (aggregate + per-street + slimmed headline) must render `—` when `graded===0`, never `0%`/`NaN` — assert on empty data and on a street with only no-baseline rows.
- **Silent backend creep:** confirm N1 adds NO endpoint, NO schema field, NO `types.ts`/`client.ts` change — it must reuse `getStreetReport()` verbatim. A new backend aggregation would be scope the slice rejected (that's the trend/per-session Next work).
- **Routing regressions:** adding `"dashboard"` to `View`/`VIEW_IDS` must not break the `parseHash` fallback (unknown view → `home`) or `formatHash`; existing views still route.
- **Two-mount parity:** slimming `SimStreetReport` changes BOTH mounts — verify the pre-session empty-shell mount and the live-session mount both still render + refetch correctly.
- **Shared-helper coupling:** `simGrade.ts` gains helpers imported by both `SimDashboard` and the slimmed `SimStreetReport` — confirm no import cycle and that `accuracyPct`'s existing callers are unaffected (or fold `accuracyPct` into the new `goodPct` without changing behavior).

## 7. File ownership
N1 owns (all FE): `frontend/src/components/simulate/simGrade.ts` (additive helpers), `frontend/src/components/simulate/simGrade.test.ts` (new vitest test), `frontend/src/components/simulate/SimDashboard.tsx` (new), `frontend/src/components/simulate/SimStreetReport.tsx` (slim), `frontend/src/lib/hashRoute.ts` (View + VIEW_IDS), `frontend/src/App.tsx` (VIEWS + render branch — **hotspot, single-owner**), `frontend/src/styles/app.css` (additive rules — **hotspot, single-owner**), `frontend/package.json` + `frontend/package-lock.json` (add vitest devDependency + `test` script — **single-owner**), a minimal vitest config (`frontend/vitest.config.ts`, or fold into `vite.config.ts`). **Touches NO backend file, NO `types.ts`, NO `client.ts`, NO migration.**

> ⚠️ `App.tsx` and `app.css` are hotspots — one owner each. `simGrade.ts` is a shared dependency of two tickets (helper + its consumers): the helper lands first, consumers import. Given the coupling (shared helper + single-owner CSS + single-owner App.tsx), this slice is **cleaner as a single-agent sequential build** than a parallel fan-out — parallelism here is marginal.

## 8. Tickets (outline — see tickets/n1-north-star-dashboard.md)
- **T0** — Stand up FE test infra: add `vitest` devDependency + `test` script + minimal config; a trivial passing test proves `npm test` runs. (Blocks T1's test.)
- **T1** — `simGrade.ts`: add `goodPct` / `optimalPct` / `aggregateRates`; vitest test aggregate == sum-of-parts + null-on-zero + only-no-baseline. (Depends on T0.)
- **T2** — `SimDashboard.tsx`: KPI cards + by-street both-rate breakdown; empty/`—` handling; reuse `getStreetReport()`.
- **T3** — Slim `SimStreetReport.tsx` to the compact two-rate headline; preserve fetch/refresh/empty lifecycle; both mounts verified.
- **T4** — Routing: `hashRoute.ts` (`View`+`VIEW_IDS`) + `App.tsx` (`VIEWS` + render branch); `#/dashboard` deep-link/reload + unknown-view fallback intact.
- **T5** — `app.css`: token-only KPI-card + by-street-bar + slimmed-panel styles; AA contrast + visible focus both themes.
- **T6** — Design-review (ux-ui-designer → design-reviewer) both themes; `typecheck && build` + `verify.sh` green.
