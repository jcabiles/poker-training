# N2 — Grading visibility toggle: coach mode ↔ real-play mode

**Status:** spec (Gate-2 pending) · **Roadmap slice:** Epic 3 · N2 · **Outcome-link:** the same table serves rehearsal *and* coaching. · **Appetite:** ~1 small epic (FE-only). · **Codex dual-review:** no (runtime EPERMs in this sandbox — Claude `refuter` only).

## 1. Goal / outcome-link
The live verdict badges + end-of-hand recap make it impossible to rehearse a hand "for real." N2 adds a **persistent global toggle** that hides/shows the in-hand grading, so the same Simulate table serves both rehearsal (hidden) and coaching (shown). **Grading is still computed + recorded when hidden** — the N1 dashboard and side-panel record keep filling. **Frontend-only.**

## 2. Locked interview decisions (2026-07-17)
- **Blast radius = in-hand verdicts only.** Hidden mode hides the **live hero verdict badge** + the **end-of-hand recap grading** (`SimRecap`). The side-panel "Your record" (`SimStreetReport`), the N1 Dashboard, and Practice stay visible — they're aggregate history, not in-the-moment coaching.
- **Default = real-play (grading HIDDEN).** ⚠️ This **flips today's always-on behavior** — on first visit / cleared storage, grading starts hidden; the user opts into coach mode. (User's explicit choice; intentional behavior change, not a regression.)
- **One global switch** (roadmap no-go) — no per-decision/per-street granularity.
- **No change to what's recorded** — gate the RENDER only; `sim_decision`/`DrillAttempt` writes unchanged.
- **Client-only preference** — localStorage, mirroring `SimWatchToggle`. No new endpoint (roadmap no-go satisfied — a client pref suffices).
- **`SimShowdown` stays** (cards, chip deltas, reveal buttons, **next-hand**) — it carries no grading; only `SimRecap` is withheld.

## 3. Contract map (from N2 scan — full map in `contracts/n2-grading-visibility-toggle.md`)
- **Live badge:** `SimVerdictBadge` at `SimTable.tsx:208` (`{lastGrade && …}`), fed by `lastGrade` prop from `SimulateView.tsx:671` ← `heroBadge` state (`:299-301`).
- **Recap:** `SimRecap` mounted `SimulateView.tsx:744`, inside the `hand.hand_over && revealHandEnd` gate (`:733`); reads `mergedRecap` (`:518-522`). Grading-only.
- **Next-hand is in `SimShowdown`** (`SimulateView.tsx:735-743`, `onNextHand={nextHand}`) — NOT in `SimRecap`. Withholding `SimRecap` strands nothing.
- **Verdict unconditionally on the wire** (`sim_session.py:566-568`); **recording upstream + independent** (`sim_session.py:531-551`, commit `:565`) → zero backend change, "records when hidden" already true.
- **Precedent = `SimWatchToggle`:** state/persistence inside `SimulateView` — `WATCH_KEY="simulate.watch"`, `readWatch()`/`changeWatch()` (`SimulateView.tsx:45,81-87,131-141`), mounted `sim-topbar-controls` (`:644`). Presentational component `SimWatchToggle.tsx` (props in / `onChange` out). N2 mirrors this; **no `App.tsx` touch**, **no click-time ref** (display read at render time).
- **Out of scope, must not be affected:** `SimDashboard`, `SimStreetReport` (side panel), Practice `DecisionBar`/`FeedbackPanel`.

## 4. Changes (all frontend — zero backend, zero migration)
### 4a. Toggle state + persistence (`SimulateView.tsx`)
- Add `COACH_KEY = "simulate.coachMode"`, `readCoachMode(): boolean` (default **false** = hidden), `changeCoachMode(next)` — mirror `WATCH_KEY`/`readWatch`/`changeWatch` exactly (try/catch, private-mode-safe). Add `const [coachMode, setCoachMode] = useState<boolean>(readCoachMode)`. **No ref** (render-time read).
### 4b. Toggle control (`SimGradingToggle.tsx`, new)
- Presentational, mirroring `SimWatchToggle.tsx` shape: `{ coachMode, onChange }` props, no internal state. **Pinned copy:** a two-state toggle framed **Coach ↔ Real play** — `coachMode === true` = **Coach** (grading shown), `false` = **Real play** (hidden). Visible label "Grading"; the button shows the active mode; `aria-pressed={coachMode}` + an `aria-label` like "Grading feedback: coach mode" / "…: real-play mode"; visible focus. Mount in `sim-topbar-controls` (`SimulateView.tsx:644` area) alongside `SimWatchToggle`/`SimSpeedPicker`.
### 4c. Gate the two render sites (`SimulateView.tsx`)
- Line 671: pass `coachMode ? heroBadge : null` as `lastGrade` → the existing `{lastGrade && <SimVerdictBadge/>}` guard hides the badge. (No `SimTable.tsx` edit.)
- Line 744: wrap the `SimRecap` mount in `coachMode && (…)` so it's withheld when hidden. **`SimShowdown` stays outside the gate.** (No `SimRecap.tsx` edit.)
- **Do NOT** alter the `heroBadge`/`mergedRecap` computation or the `revealHandEnd`/`gradedHandNo` machinery — gate the render only.
### 4d. Styles (`app.css`, additive)
- Toggle CSS — reuse the existing `SimWatchToggle` / segmented-control classes if they generalize; else add minimal token-only rules. AA contrast + visible focus both themes.

## 5. Pass/fail
- A toggle appears in the Simulate top bar; flipping it **hides/shows the live hero verdict badge AND the end-of-hand recap** (`SimRecap`) together.
- **`SimShowdown` (cards, chip deltas, reveal buttons, next-hand) is present in BOTH modes** — hiding grading never strands the user or removes cards/next-hand.
- **Preference persists across reload** (localStorage `simulate.coachMode`); **default is hidden** (real-play) on cleared storage.
- **With grading hidden, a played mapped hand still writes `sim_decision` rows** — assert the write path is unchanged (e.g. the side-panel/dashboard `graded` count still increments after a hidden-mode hand; backend diff empty).
- **Out-of-scope surfaces unaffected:** side-panel "Your record", N1 Dashboard, and Practice still show their numbers in hidden mode.
- **Toggling mid-hand** immediately hides/shows the badge on the next render without breaking hand state (render-gated).
- No backend / schema / migration / `types.ts` / `client.ts` / `App.tsx` change (assert diff scope).
- AA contrast + visible focus both themes; `verify.sh` + `cd frontend && npm run typecheck && npm run build` green; design-review both themes.

## 6. Refuter-target risks
- **Computation vs render:** prove `heroBadge`/`mergedRecap` are still computed when hidden (state machinery intact) — a regression here breaks the recap ordinal-merge or the mid-session reload-restore. N2 must gate only the pass/mount.
- **Recording when hidden:** prove the `sim_decision`/`DrillAttempt` write (`sim_session.py:531-551`) is untouched and still fires in hidden mode (the whole point — dashboard keeps filling).
- **Stranding:** confirm next-hand + reveal + cards live in `SimShowdown`, not `SimRecap`, so withholding the recap leaves a way forward (verified in scan).
- **Default flip:** default hidden changes existing behavior — intended (user choice); ensure it's a clean default, not a bug that also breaks coach mode.
- **Leak into out-of-scope surfaces:** confirm the toggle is NOT threaded into `SimStreetReport`/`SimDashboard`/Practice (blast radius = the two SimulateView render sites only).
- **Stale read:** unlike `SimWatchToggle` (ref for click-time), the grading toggle is render-time — confirm no stale-closure need; flipping re-renders correctly.

## 7. File ownership
N2 owns (all FE): `frontend/src/components/SimulateView.tsx` (**hotspot, single-owner** — toggle state + persistence + two render-gates + mount), `frontend/src/components/simulate/SimGradingToggle.tsx` (new), `frontend/src/styles/app.css` (additive — **hotspot, single-owner**), new FE tests. **Touches NO backend file, NO `types.ts`, NO `client.ts`, NO `App.tsx`, NO `SimTable.tsx`/`SimRecap.tsx`, NO migration.**

> ⚠️ `SimulateView.tsx` and `app.css` are single-owner hotspots. This slice is small and its edits are interdependent (toggle state → gates → styles all in the same two files) → **single-agent sequential build** (a fan-out would just contend on these two files).

## 8. Tickets (outline — see tickets/n2-grading-visibility-toggle.md)
- **T1** — `SimGradingToggle.tsx` (presentational, mirror `SimWatchToggle`) + `app.css` toggle styles (token-only, both themes).
- **T2** — `SimulateView.tsx`: `COACH_KEY`/`readCoachMode`/`changeCoachMode` + state; mount the toggle; gate `lastGrade` pass (`:671`) and `SimRecap` mount (`:744`); leave computation untouched.
- **T3** — Tests + verify: hidden-mode still writes `sim_decision` (unchanged write path); persistence across reload; SimShowdown present both modes; design-review both themes; `typecheck`+`build`+`verify.sh` green.
