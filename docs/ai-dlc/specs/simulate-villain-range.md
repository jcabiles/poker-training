# Spec — Simulate villain range reveal (live, per-action, all streets)

> NEXT-item slice, roadmap `docs/ai-dlc/roadmap/simulate-table.md`. Gate-1 scope locked
> BY THE USER 2026-07-12: all streets from day one; postflop explicitly an ≈-labeled
> ESTIMATE. Built autonomously under the 2026-07-12 "proceed with everything"
> instruction; solo-inception — refuter pass mandatory before build.
> Runs AFTER the preflop-chart slice (shares `SimulateView.tsx`/`types.ts`/`app.css`).

## Goal (one line)
A per-villain reveal button that shows the current estimated hand-range of any live
(non-folded) villain as a weighted 13×13 chart that narrows as they act — exact
conditioning preflop, ≈-labeled approximate conditioning postflop — without ever peeking
at their actual cards.

## The load-bearing invariant — NO CARD PEEKING
The range is computed ONLY from public information: the villain's persona pack + the
action sequence they took + the revealed board. The conditioning code must never read
the villain's actual hole cards from `state_json` (which the server holds). This is both
an information-integrity rule (the chart is an honest "what could they have") and the
privacy structure S9 established. Test-enforced: the computed range for a hand must be
IDENTICAL across re-deals where only the villain's actual cards differ (same persona,
same public line).

## Mechanics (verified against code; refuter-corrected 2026-07-12)
- **Reconstruction is a REPLAY, not a list scan (refuter high-1/high-2).** A villain's
  node at each historical decision depends on GLOBAL hand state: preflop `facing` is
  computed from the whole interleaved `action_history` (`play.py _preflop_facing`), and
  postflop `sample_postflop_decision` conditions on point-in-time `pot_bb`/`stack_bb`/
  `opponents`/`current_bet_to` — none persisted standalone. The estimator therefore
  replays the hand from `start_hand()` through `apply()` per historical action to
  regenerate each decision's context (a few apply() calls per estimate — cheap vs the
  ~430 hands/s full-hand ceiling), reconstructing facing exactly as `_preflop_facing`
  does. Tested against MULTIWAY lines, not just HU open/4-bet.
- **Preflop = exact.** With per-decision context reconstructed, the posterior is
  deterministic pack math: weight(combo) ×= P(observed action | combo class, node) from
  the pack's mix frequencies; classes the persona never plays that way drop to 0.
- **Postflop = approximate, ≈-labeled.** Per candidate combo: what WOULD this persona
  have done holding it at that reconstructed decision (rung + lever probabilities, incl.
  the SPR-commit branch — snapshot errors there zero fold mass, hence the replay
  requirement) → reweight by the observed action. Category-level approximation OK; UI
  labels every postflop chart "estimated".
- **Class ↔ combo granularity (refuter med-2):** pack mixes are 169-class-level; dead-
  card math is 1326-combo-level. Expand matching classes to suit combos, zero the
  blocked combos, re-aggregate to class weights for the 13×13 chart. Fixture: hero holds
  AhKs ⇒ villain's AKo class weight REDUCED (not zeroed), AKs drops only blocked combos.
- **Dead cards:** hero's cards + revealed board only; other villains' unseen cards are
  NOT excluded (hero can't know), prior showdowns don't carry into a new hand's deck.
- **NO-PEEK is structural (refuter high-3):** the V2 service layer strips the loaded
  `HandState` to a `PublicActionHistory` projection (street/position/action/amount only
  — no `SeatState`, no hole cards) BEFORE calling the domain estimator; the pure
  function's parameter TYPE cannot carry hole cards. (Replay internals reconstruct
  context from the projection + a fresh deal-free state, never from `state_json` seats.)
- **Folded villains have no button** (user decision) — using the STAGED fold state
  (same per-seat `revealed` computation SimTable already uses), never raw `seat.status`
  (refuter low-2); the panel closes when its villain folds (staged) AND on `hand_over`
  (showdown reveals real cards — an estimate beside the truth is noise; refuter low-3).
- **Pacing lockstep needs a truncation param (refuter med-1):** `stagedIndex` is client-
  only. The endpoint takes `?through_action=N`; the FE passes its narrated count per
  refetch, the estimator conditions on that prefix only. Server never volunteers the
  fully-resolved posterior during playback.
- **Availability semantics (refuter low-1):** 200 + `available=false` for hero/folded/
  hand-over seats (benign poll states); HTTP 404 stays reserved for `SessionNotFound`.

## Files / interfaces to touch
**Backend**
- NEW `backend/app/domain/table/range_estimate.py` (pure domain, purity-allowlisted):
  `estimate_range(persona_pack, public_actions, board, dead_cards) -> dict[combo, weight]`
  + preflop-exact and postflop-approx internals. NO import of hole-card state.
- `backend/app/services/sim_session.py` — read-only helper: session + seat → public
  action history (from persisted hand events) → estimate.
- `backend/app/api/v1/simulate.py` — `GET /simulate/{id}/villain-range/{seat}` →
  `{seat, persona_label, street, weights: {combo_class: float}, exact: bool}`;
  404-style `available=false` for hero/folded seats.
- `backend/app/schemas/simulate.py` — `VillainRangeView`.
**Frontend**
- `frontend/src/api/types.ts` — mirror.
- NEW `frontend/src/components/simulate/SimVillainRange.tsx` — weighted 13×13 heat chart
  (cell opacity ∝ weight — NOT RangeGrid's action segments; new sim-owned cell renderer,
  reusing only the outer panel idiom); "estimated" tag when `exact=false`; per-villain
  open/close.
- `frontend/src/components/simulate/SimTable.tsx` — small reveal affordance on live
  villain pods (button, ≥24px target, visible focus).
- `frontend/src/components/SimulateView.tsx` — panel state; staged-index gating; refetch
  on each narrated villain action while open.
- `frontend/src/styles/app.css` — `.sim-vrange-*` section (tokens-only).

## Out of scope
Hero range display (the preflop-chart slice) · equity-vs-range math · persisting
estimates · multiway exploit notes · any change to persona play itself · turn/river
grading interplay · hidden-persona mode (future gate for this button — noted, not built).

## Constraints (invariants)
Domain purity (no web/DB imports; no `state_json` access from domain) · NO-PEEK
invariant above (test-enforced) · ≈ labeling on postflop charts · tokens-only CSS, AA
both themes, focus visible · perf: estimate computed on request + on narrated action
while open, never per-frame; if a postflop estimate exceeds ~150ms server-side, coarsen
to category buckets (measure first).

## Verify-by (end-to-end)
- Preflop exactness: BTN open → wide chart; same persona 4-bet line → strict subset,
  matches hand-computed pack posterior (fixture).
- No-peek: two seeded deals, same persona + same public line, different actual villain
  cards ⇒ byte-identical weights (test).
- Postflop: chart narrows after a barrel; carries "estimated" tag; combos blocked by
  board/hero cards are zero-weight.
- Folded villain: no button; open panel closes on fold. Staged playback: chart lags the
  log, never leads (lockstep test with S11 pacing).
- `./scripts/verify.sh` + ruff + FE typecheck/build green; refuter pass BEFORE build;
  `design-reviewer` acceptable both themes.
