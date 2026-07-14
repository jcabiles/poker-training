# Tickets — Simulate villain range reveal

> Spec: `specs/simulate-villain-range.md`. Runs AFTER the preflop-chart slice merges
> (shared FE files). Refuter pass on the spec REQUIRED before V1. Sequential — one owner
> per ticket, V1→V2→V3.

## V1 — Domain: range estimator (heavy-worker)
NEW pure `domain/table/range_estimate.py`: preflop-exact posterior over persona pack
combos (action-frequency weighting) + postflop approximate conditioning via the merit
ladder per candidate combo. Dead-card exclusion (hero + board only). Purity-allowlisted.
- Accept: pack-posterior fixture (open wide / 4-bet narrow subset); NO-PEEK test (same
  public line, different actual cards ⇒ identical weights); postflop narrowing test;
  perf measured (<~150ms/estimate or coarsened).
- Done: new tests + purity + verify.sh green.
- Owns: `domain/table/range_estimate.py`, purity allowlist line, new test file.

## V2 — Backend wire (implementer, needs V1)
Service helper (public action history from persisted events — never hole cards) +
`GET /simulate/{id}/villain-range/{seat}` + `VillainRangeView` schema.
- Accept: hero/folded seats → available=false; endpoint fixture matches V1 output;
  no state_json card fields ever serialized.
- Done: endpoint tests + verify.sh green.
- Owns: `services/sim_session.py`, `api/v1/simulate.py`, `schemas/simulate.py`,
  endpoint tests.

## V3 — Frontend panel (ux-ui, needs V2)
`SimVillainRange.tsx` weighted heat chart ("estimated" tag postflop), reveal button on
live villain pods (`SimTable.tsx`), panel state + staged-index lockstep + refetch-on-
narrated-action (`SimulateView.tsx`), `types.ts` mirror, `.sim-vrange-*` CSS.
- Accept: open/narrow/close-on-fold flows; lockstep (chart never leads the log); AA +
  focus both themes; typecheck/build green.
- Done: `design-reviewer` acceptable.
- Owns: `SimVillainRange.tsx`, `SimTable.tsx`, `SimulateView.tsx`,
  `frontend/src/api/types.ts`, `app.css` (`.sim-vrange-*`).
