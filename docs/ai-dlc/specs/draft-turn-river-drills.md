# DRAFT spec — Turn/river teaching surface in Practice

> **STATUS: DRAFT — Gate-1 interview NOT held. Do not build.** Prepared 2026-07-12.
> Roadmap: NEXT item "Turn/river teaching surface in Practice" (teacher-roadmap mandate:
> a street ships WITH teaching).

## Goal (one line, provisional)
Give the turn/river graders (S6/S7, already live) their Practice-mode teaching surface:
drill modes that deal turn/river decision spots, plus point-of-need concept cards for the
barrel and bluff-catch families.

## Known facts (from current code/contracts)
- Graders exist for all four streets (TURN_BARREL, VS_TURN_BET, RIVER_BARREL,
  VS_RIVER_BET) with tiered feedback — Practice just never deals those spots as drills.
- Practice drill modes are content/scenario driven (`scenarios.py` builders + drill mode
  registry); flop drills are the pattern to extend.
- SRS already supports turn/river archetype dims (turn_class/river_class columns, S6/S7).
- Concept cards are the point-of-need pattern permitted by the no-lessons-library no-go.
- This is Practice-surface work — file-disjoint from all Simulate slices.

## Open Gate-1 questions (user must answer)
1. Drill mode structure: one combined "late streets" mode, or separate turn and river
   modes in the mode picker?
2. Spot generation: replay-style continuation (flop spot extends to turn) or standalone
   dealt turn/river spots?
3. Concept card scope: barrel + bluff-catch only, or also busted-draw discipline (the S7
   demotion rule is a natural card)?
4. Do turn/river drills enter the SRS due queue immediately or after a settling period?
5. Priority vs the Simulate-side items — this is the only NEXT item with zero
   dependencies; when should it actually run?

## Constraints (inherited, non-negotiable)
Grading via the one provider · freq+EV results · strategy in versioned content ·
`spot_signature()` frozen (turn/river signatures already exist — reuse) · concept cards
point-of-need only · tokens-only CSS, AA both themes.

## Verify-by (provisional)
Turn and river spots dealable in Practice with graded feedback + concept card on demand;
SRS rows use existing signature shapes; verify.sh + typecheck/build green;
design-reviewer pass.
