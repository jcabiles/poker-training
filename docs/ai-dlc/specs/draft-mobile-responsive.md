# DRAFT spec — Mobile responsiveness (app shell + Simulate felt)

> **STATUS: DRAFT — Gate-1 interview NOT held. Do not build.** Prepared 2026-07-12.
> Roadmap: NEXT item "Simulate mobile responsiveness" (deferred by the desktop-primary
> decision; measured evidence from the S9 design review + 2026-07-12 wave-4.5 review).

## Goal (one line, provisional)
Make phone widths usable: fix the APP-WIDE masthead overflow (affects every route), and
give the 9-max Simulate felt a sub-600px strategy instead of collapsed overlapping pods.

## Known facts (measured)
- `.masthead-right` / EV-ledger widget doesn't wrap (`flex-wrap: nowrap`, right edge at
  ~574px) ⇒ horizontal body scroll ≤ ~400px on EVERY route — pre-existing, NOT Simulate
  code. An app-shell fix needs its own design review across Practice/Quiz too.
- At 375px the 9-max felt collapses: 30 overlapping seat pairs measured; hero cards over
  the pot; persona meta chopped. The wave-4.5 wide-shell change neither causes nor
  worsens this (max-width caps at the viewport either way).
- Stats strip cramps at mobile widths (app-shell).
- Two candidate felt strategies (roadmap): felt `min-width` + horizontal-scroll wrapper
  (cheap, keeps geometry) vs a sub-600px compact/vertical seat layout (real redesign).

## Open Gate-1 questions (user must answer)
1. **Is portrait phone a real usage context for a localhost desktop trainer?** (The
   roadmap's own gating question — a "no" shrinks this to the masthead fix only.)
2. If yes: scroll-wrapper felt (cheap) or compact vertical layout (proper)?
3. Tablet portrait (~768px) already ships clean — is landscape phone (~667px) in scope?
4. Does the masthead fix ship alone first (it's the every-route bug)?

## Constraints (inherited, non-negotiable)
Tokens-only CSS · AA + visible focus both themes · shared felt base classes cross-owned
with Practice/Quiz (sim-scoped overrides only) · app-shell changes need design review on
ALL routes · no horizontal body scroll at any supported width.

## Verify-by (provisional)
scrollWidth == viewport at 375/414/667px on every route; felt strategy per Gate-1 answer
verified at 375px with zero overlapping pods; Practice/Quiz visually unchanged at desktop
widths; design-reviewer pass both themes.
