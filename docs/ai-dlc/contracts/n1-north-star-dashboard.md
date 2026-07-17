# N1 contract map — north-star dashboard (read-only scan, 2026-07-16)

Area: the Simulate per-street report → the two north-star rates → where a dashboard mounts. Verdict: **N1 is frontend-only. No backend, no migration, no `types.ts`/`client.ts` change.**

## Data already exists
- **Backend aggregation done** — `street_report` (`backend/app/services/sim_session.py:584-619`) returns per street `{graded, optimal, acceptable, mistake, blunder, ev_loss_bb, no_baseline}`, all four streets zero-filled, owner-scoped (`:592`), excludes `correctness is None` from `graded` (`:609-611`).
- **Endpoint** `GET /simulate/report/streets` (`backend/app/api/v1/simulate.py:88-90`; owner `_OWNER_ID=""` `:45`). `sim_decision` is a dedicated Simulate-only table → no `source` filter needed (unlike `DrillAttempt`, `stats.py:38-42`).
- **Schemas** `StreetReportRow` / `StreetReportView` (`backend/app/schemas/simulate.py:57-77`): `rows[]` + `total_decisions` (= graded + no_baseline all streets).
- **FE types** match already (`frontend/src/api/types.ts:260-274`). **FE client** `getStreetReport()` (`frontend/src/api/client.ts:142-144`).

## The two rates
- `Correctness` enum `backend/app/domain/evaluation.py:17-21`: `optimal | acceptable | mistake | blunder`. Good grouping precedent `_GOOD={"optimal","acceptable"}` at `backend/app/services/stats.py:13`.
- Primary math already client-side: `accuracyPct(row)=(optimal+acceptable)/graded`, `null` when `graded===0` (`SimStreetReport.tsx:18-21`). Optimal rate = `optimal/graded` (new). Aggregate = client-side sum over the four rows (new).
- "No baseline yet" = `correctness IS NULL` (mirrored by `coverage` in {`not_found`,`unmappable`}); already excluded from `graded`. Convention: show `—`, never `0%`/`NaN`, when `graded===0` (`SimStreetReport.tsx:19,102,106,131`); surface `no_baseline` as its own count.

## No migration
`sim_decision` (migration `0010_sim_decision_and_source.py`) already has `street` (nn), `correctness` (nullable), `ev_loss_bb` (nn), `coverage` (nn) — matches model `backend/app/db/models.py:88-115`. Zero schema change.

## Mount / IA
- Flat hash router: `View` union + `VIEW_IDS` (`frontend/src/lib/hashRoute.ts:9,11`); nav `VIEWS` (`App.tsx:27-33`); render dispatch (`App.tsx:389-393`). Fallback unknown-view → `home`.
- `SimStreetReport` mounts twice in `SimulateView` (live aside `:755-759`; empty-shell aside `:769-772`), both `refreshKey`-driven. No nested router inside Simulate.
- No chart lib (`frontend/package.json`) — bespoke token-CSS only. Nearest precedent `.sim-tally`/`.sim-tier-*` (`SimStreetReport.tsx:108-121`; CSS `app.css:3254-3270`, `3506-3532`). Tokens `tokens.css` (`--space-*:97-103`, `--radius-*:106-111`). Report CSS from `app.css:3403`.
- Shared FE util `simGrade.ts` (`streetLabel`, `fmtEvLoss`) imported by `SimStreetReport.tsx:5` — right home for the shared aggregate helper.

## Risks flagged
- Don't count `no_baseline` into `graded`. Don't render `0%`/`NaN` at zero. Don't touch `spot_signature()` / `backend/app/domain/`. Reuse `getStreetReport()` verbatim — a new backend aggregation would be rejected scope (trend/per-session = Next).
