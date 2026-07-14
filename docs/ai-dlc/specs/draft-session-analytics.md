# DRAFT spec — Session analytics view (per-street decision quality)

> **STATUS: DRAFT — Gate-1 interview NOT held. Do not build.** Prepared 2026-07-12 while
> the user was away; open questions below are the Gate-1 agenda.
> Roadmap: NEXT item "Session analytics view" (promoted from Later at user request —
> "show me analytics on whether I made good/bad/acceptable decisions at each street").

## Goal (one line, provisional)
Grow the S10 minimal per-street report into a real analytics surface: trends over time,
per-session and per-position breakdowns, leak-category drill-down — all fed by
`sim_decision` rows (street, tier, ev_loss_bb, leak_category, session FK already exist).

## Known facts (from current code/contracts)
- Data source is complete: S10's `sim_decision` has street/ordinal/correctness/ev_loss_bb/
  leak_category/coverage + session and hand FKs; no schema change strictly required.
- A session dimension needs `sim_session.created_at` (exists) for time bucketing.
- Practice already has a stats surface (`services/stats.py`, Home dashboards) — sim
  analytics must stay VISUALLY and QUERY-level separate (source-filter invariant).
- Rates must exclude no-baseline rows; coverage shown honestly (S10 aggregate rule).

## Open Gate-1 questions (user must answer)
1. Where does it live — a new top-level tab, a section inside Simulate, or Home?
2. Time axis: per-session series, per-day, or rolling-N-hands?
3. Charts: tokens-only CSS bars are free; a charting library needs ask-first (invariant).
4. Which cuts matter first: street × tier (the stated vision), position, leak category,
   persona faced?
5. Does the S10 minimal report already answer enough? (Roadmap says review after ~2 weeks
   of real use — this spec may shrink.)

## Constraints (inherited, non-negotiable)
Tokens-only CSS · AA both themes · FE types hand-maintained · EVs labeled ≈ · no new
backend writes (read-only aggregates) · Practice stats reads untouched.

## Verify-by (provisional)
Aggregates match hand-computed fixtures; no-baseline exclusion tested; design-reviewer
pass; verify.sh + typecheck/build green.
