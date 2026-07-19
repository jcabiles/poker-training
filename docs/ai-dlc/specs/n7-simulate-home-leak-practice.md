# N7 — Simulate as home + Practice organized around leaks (spec)

_Epic 3 · supersedes the R6/N7-IA intent. Interview locked 2026-07-18 (metric scope);
direction set by the Epic-3 roadmap ("Simulate becomes the app home AFTER grading + dashboard
land; Practice reframes around the dashboard's low-rate spots")._

## Goal

Three faithful, reversible moves that make Simulate the centre of the app and point Practice at the
hero's real leaks:

**A. Simulate as home.** Simulate becomes the default/landing view and the first nav item; the
existing curriculum hub stays reachable, relabeled **"Learn"**.

**B. Metric stays Simulate-only (lock).** The cumulative Good-Decision / Optimal-Play totals count
**only** `sim_decision` rows — already true by construction (separate table from `drill_attempt`).
N7 pins it with a regression test; **no behavior change**.

**C. Practice organized around leaks.** A new read-model ranks the hero's worst **Simulate spot
families** (`node_context` × `position`) by Good-Decision-Rate; the dashboard surfaces them and each
drillable family links straight into the matching **Practice** drill mode. Non-drillable families
(turn/river barrels — no Practice mode exists) are shown honestly, not faked.

## Design

### A — Simulate as home (FE only)

- `frontend/src/lib/hashRoute.ts` — change the unrecognized-view fallback from `"home"` to
  `"simulate"` (update the N6/N7 comment). `View`/`VIEW_IDS` unchanged (Home still exists).
- `frontend/src/App.tsx` — reorder `VIEWS` so `simulate` is first; relabel `home` → **"Learn"**.
  **Audit every `view === "home"` / `view !== "home"` conditional** (the plan-fetch guard at
  ~205 and any others) — they key on the still-valid `home` id, so they keep working; the audit
  just confirms nothing assumed home-is-default. First-load with no hash lands on Simulate.
- No route is removed; deep links (`#/home`, `#/dashboard`, …) still resolve. Reversible by
  flipping the fallback back.

### B — Metric-only-Simulate lock (backend test)

- `street_report` (and the new leak read-model) read `select(SimDecision)...` exclusively — no
  `DrillAttempt` join/union. Add a regression test that asserts a Practice `drill_attempt` row
  (incl. a `source='simulate'`-tagged one) never changes the dashboard/leak numbers, and that the
  read-models reference only `SimDecision`. Documents the decision; catches a future accidental
  cross-read.

### C — Leak-by-spot read-model + Practice entry points

**Backend — `app/services/sim_session.py`:**
- `leak_by_spot(db, owner_id, min_sample=_LEAK_MIN_SAMPLE) -> LeakReportView` — over
  **graded** `SimDecision` rows (correctness not None; unmappable/no-baseline excluded — they are
  coverage gaps, not leaks). Group by `(node_context, position)`; per group compute `graded`,
  `good` (optimal+acceptable), `good_rate = good/graded`, `ev_loss_bb` (sum). Keep groups with
  `graded >= min_sample`; **rank worst-first** by `good_rate` asc, then `ev_loss_bb` desc; cap at
  `_LEAK_TOP_N`. `street` carried for display. A group whose `node_context` maps to a Practice mode
  gets `drill_mode`; else `drill_mode=None`.
- `_NODE_TO_DRILL_MODE` — `rfi/vs_rfi/vs_3bet/blind_defense/vs_limpers` → same-name family modes;
  `cbet → "postflop"`, `vs_cbet → "vs_cbet"`, `vs_check_raise → "vs_check_raise"`;
  turn/river barrel + vs-turn/river-bet → **None** (no Practice drill exists — honest gap).
- `_LEAK_MIN_SAMPLE = 5`, `_LEAK_TOP_N = 6` (module constants).

**Backend — schema + endpoint:**
- `LeakSpotRow` (node_context, position, street, graded, good, good_rate, ev_loss_bb,
  drill_mode: str | None, node_label: str) and `LeakReportView` (rows, min_sample) in
  `app/schemas/simulate.py`.
- `GET /simulate/report/leaks` → `leak_by_spot(db, _OWNER_ID)`. Session-independent (all-time),
  like `/report/streets`. No 404 concern (no session).

**Frontend:**
- `api/types.ts` + `api/client.ts` — `LeakSpotRow`/`LeakReportView` + `getLeakReport()`.
- A **"Your leaks"** panel on the **Dashboard** (`SimDashboard`): worst spot families, each row =
  the spot label + street + Good-rate + ≈EV-lost. A drillable row is a button/link to
  `#/drill/<mode>` ("Drill this"); a non-drillable row shows a muted **"Simulate only"** tag.
  Empty state ("not enough graded decisions yet") below `min_sample`. Tokens-only CSS, AA + focus.
- This is the "Practice organized around leaks" seam: the dashboard ranks leaks and routes into
  Practice — Practice's own drill code is **not** rewired (lower risk; the entry points carry the
  intent). Recorded as the v1 interpretation.

## Pass / fail

1. First load with no hash lands on **Simulate**; nav lists Simulate first; "Learn" (old Home) is
   still reachable and renders; every existing route still resolves (deep-link test / no regression
   in the home-guarded plan fetch).
2. `leak_by_spot` returns worst-first families over **graded** rows only (unmappable excluded),
   respects `min_sample`, caps at `_LEAK_TOP_N`, and sets `drill_mode` per the node map (None for
   turn/river). Unit test with seeded `SimDecision` rows asserts ordering + the drill-mode mapping +
   the min-sample cutoff.
3. `GET /simulate/report/leaks` returns the ranked rows; a Practice `drill_attempt` row (incl.
   `source='simulate'`) leaves both the street report and the leak report **unchanged** (metric-only
   lock test).
4. Dashboard renders the leak panel: drillable rows link to `#/drill/<mode>`; non-drillable rows
   show "Simulate only"; empty state below threshold; AA + focus both themes; typecheck + build.
5. `verify.sh` green; **no migration** (read-model only — reuses N5's stored dims); no
   `spot_signature()` / grader / pin / `TAXONOMY_VERSION` change; `types.ts` hand-synced.

## No-gos

- No new `sim_decision` columns / no migration (read-model only over N5's dims).
- Practice reps still **do not** count toward the Good-Decision / Optimal-Play totals (Simulate-only
  — the lock is the whole point of B).
- No solver ranges; leaks are ranked from real `sim_decision` outcomes only.
- No trend/progress graphs (still a NEXT bet); the leak panel is a ranked snapshot.
- No persona-conditioned leak split (that's L1, deferred).
- No removal of any route/view; Home/Learn stays.
- Don't rewire Practice's internal drill selection this slice — dashboard entry points only.
