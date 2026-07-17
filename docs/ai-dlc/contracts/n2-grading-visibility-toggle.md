# N2 contract map — grading visibility toggle (read-only scan, 2026-07-17)

Area: the two in-hand verdict surfaces in Simulate + the toggle/persistence precedent. Verdict: **N2 is frontend-only. No backend, no schema, no migration, no `types.ts`/`client.ts` change.**

## The two in-scope surfaces
- **Live hero badge** — `SimVerdictBadge` rendered at `frontend/src/components/simulate/SimTable.tsx:208` (`{lastGrade && <SimVerdictBadge grade={lastGrade} />}`); component inline at `SimTable.tsx:293-313`, reads `grade.correctness` via `tierOf()` + `grade.ev_loss_bb`. Fed by prop `lastGrade: GradeView | null` (`SimTable.tsx:73`), passed from `SimulateView.tsx:671`, sourced from `heroBadge` state (`SimulateView.tsx:299-301`, from `hand.last_grade`).
- **End-of-hand recap** — `SimRecap` (`frontend/src/components/simulate/SimRecap.tsx`), mounted `SimulateView.tsx:744` inside the `hand.hand_over && revealHandEnd` gate (`:733`). Reads `mergedRecap` (`SimulateView.tsx:518-522` — live `tiersByOrdinal` merged over persisted `hand.recap`). Purely grading (on-baseline %, ≈EV given up, per-decision tier + "why").

## Verdict already on the wire; recording is upstream
- `last_grade` + `recap` populated on EVERY `apply_hero_action` response, unconditionally (`backend/app/services/sim_session.py:566-568`). No request/session flag suppresses it; `Decision` body carries only `action`/`size_bb` (`client.ts:114-116`). → **display is 100% client-decidable.**
- `SimDecision` + `DrillAttempt` writes happen at `sim_session.py:531-551`, committed at `:565` — BEFORE the view/`last_grade` objects are built (`:566-568`). No display flag reaches this path. → **"still recorded when hidden" holds today with zero backend change.**

## Precedent to mirror: `SimWatchToggle`
- Simulate-scoped toggle whose state + persistence live INSIDE `SimulateView` (not `App.tsx`): key `WATCH_KEY = "simulate.watch"` (`SimulateView.tsx:45`), `readWatch()` (`:81-87`), `changeWatch()` (`:133-141`), state (`:131`), mounted in `sim-topbar-controls` (`SimulateView.tsx:644`) next to `SimSpeedPicker`. Presentational component `frontend/src/components/simulate/SimWatchToggle.tsx` (props in / `onChange` out, no internal state).
- Persistence idiom (4 examples: theme, studyTestMode, `simulate.speed`, `simulate.watch`): module-level `*_KEY`, `read*()`/`write*()` with try/catch + hardcoded default. N2 reuses this — new key `simulate.coachMode` (boolean).
- NOTE: `SimWatchToggle` mirrors its state to a ref for click-time reads in `decide()`. **N2 does NOT need the ref** — a display toggle is read at render time.

## Next-hand control is NOT in SimRecap
- `SimShowdown` (`SimulateView.tsx:735-743`) owns `onNextHand={nextHand}` + cards/chip-deltas/reveal buttons; it carries NO grading. `SimRecap` (`:744`) is grading-only. → withholding the whole `SimRecap` when hidden strands nothing.

## Out of scope (confirmed separate — must NOT be affected)
- **N1 Dashboard** (`SimDashboard`, top-level `view==="dashboard"`) — aggregate `getStreetReport()`, no `GradeView`. Stays visible.
- **Side-panel "Your record"** (`SimStreetReport`, `SimulateView.tsx:757`) — aggregate; per this slice's decision, stays visible in hidden mode. (It's physically inside `SimulateView` — do NOT thread the toggle into it.)
- **Practice** (`DecisionBar`/`FeedbackPanel`, `App.tsx` drill branch) — separate tree, `EvaluationResult` not `GradeView`, no shared render path. Untouched.

## Risks to respect
- Gate the RENDER, not the computation — keep computing `heroBadge`/`mergedRecap` (order-sensitive: `gradedHandNo` reset, `revealHandEnd` pacing, live-tier-merge). Only conditionally pass/mount.
- Domain purity + `spot_signature()` untouched by construction (no backend edit).
