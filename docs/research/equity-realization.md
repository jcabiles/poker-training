# Equity Realization Factor (R) — Research Notes

Scope: NLHE cash, ~100bb, live $2/$3 context. Purpose: calibrate a poker-math spec's use of realized equity ≈ raw equity × R.

Tagging key: **[SOLVED/derivable]** = follows directly from a solver output or an algebraic identity; **[SOURCED estimate]** = a specific number published by a credible source, not independently re-derived here; **[HEURISTIC/uncertain]** = qualitative/directional claim repeated across sources but without a precise, citable figure.

---

## 1. The concept and the formula

**Definition.** Equity Realization (EQR, or R) is the ratio between what a hand actually earns (its share of the pot in EV terms) and its raw/static equity (win probability if the hand were checked to showdown with no further betting). [SOLVED/derivable]

**Canonical formulas** (two equivalent phrasings appear across sources):

- GTO Wizard glossary: `EQR = pot-share / equity`, where pot-share is the hand's expected share of the pot (from EV) and equity is raw all-in/showdown equity. Example given: a hand winning 70% of the pot with 40% raw equity has EQR = 0.7/0.4 = **175%**. [SOURCED estimate — GTO Wizard Glossary, "Equity Realization (EQR)", https://gtowizard.com/glossary/equity-realization-eqr/]
- GTO Wizard blog (equivalent form): `Equity × EQR × pot = EV`. [SOURCED estimate — GTO Wizard, "Equity Realization", https://blog.gtowizard.com/equity-realization/]
- Upswing Poker: `Equity Realized = Realization % × Raw Equity`, e.g. 0.75 × 40% = 30%. [SOURCED estimate — Upswing Poker, "How Equity Realization Impacts Every Hand You'll Ever Play", https://upswingpoker.com/equity-realization-explained/]
- Red Chip Poker (empirical/backward-solved form used in their walkthrough): `R = EV_realistic / EV_estimated`. Worked example: 3♠3♥ on T♠7♦2♥, 49% raw equity, EV_estimated (naive) = $2.94, EV_realistic (from a GTO solver) = $1.36 → **R = 0.62 (62%)**. [SOURCED estimate — Red Chip Poker, "Equity Realization", https://redchippoker.com/equity-realization/]

All four are algebraically the same idea: **realized EV = raw equity × pot × R**, i.e. the spec's `realized equity ≈ raw equity × R` is the standard framing used industry-wide. This is well-established, not a simplification unique to the spec. [SOLVED/derivable]

**What drives R** (consistent across GTO Wizard, Upswing, Red Chip, PokerNerve):

1. **Position (IP vs OOP).** Acting last each street gives more information, more control over pot size, and denies the OOP player that same leverage. This is the single most-cited driver. [HEURISTIC/uncertain — directionally universal, magnitude varies by spot, see §3]
2. **Initiative / range advantage.** The player who bet last (or has the "range advantage," i.e., more strong hands in their range) can apply pressure and fold out worse equity, causing their range to over-realize while the defending range under-realizes. [HEURISTIC/uncertain]
3. **Hand type / playability.**
   - Suited > offsuit, connected > gapped, for the same nominal hand strength, because they retain more redraws and disguise. GTO Wizard's specific flop-frequency numbers: 76s flops "something" 62.4% of the time vs 76o at 55.9% (a 6.5-point gap); 87s at 62.4% vs 85s at 57.1%. [SOURCED estimate — Upswing Poker, equity-realization-explained]
   - **Draws vs. made hands:** counterintuitively, draws often *over-realize* and marginal made hands *under-realize*. GTO Wizard's worked example on a K♥8♦5♦ flop, 100bb effective: 7♥6♥ (open-ended straight draw, ~40% raw equity vs the betting range) earns **5.81bb EV**, while K♠T♣ (top pair weak kicker, ~75% raw equity) earns only **5.36bb EV** — the draw, despite having roughly half the raw equity, realizes more value because both players can bet/bluff more confidently with a draw's binary future (make it or don't) than a marginal made hand's murky multi-street decision tree. [SOURCED estimate — GTO Wizard, "I'd Rather Be Drawing", https://blog.gtowizard.com/id-rather-be-drawing/]
   - Weakest draws are the exception: GTO Wizard notes 3♥2♥ (bottom-of-range flush draw) still over-realizes but only to ~87% in one cited scenario — better draws over-realize by more, because getting "bet off" the draw before showdown, and running into a bigger flush when it completes, both cut into the reward. [SOURCED estimate — GTO Wizard, "Equity Realization" / cross-referenced via secondary summary, https://blog.gtowizard.com/equity-realization/]
   - **Domination / medium-strength hands under-realize the most.** Both GTO Wizard and Red Chip agree: hands with a "fair chance" of winning at showdown but not strong enough to bet for value are squeezed from both sides — they lose value whether they're called (often behind) or forced to fold to pressure. Very strong hands over-realize via value betting and denial; very weak hands paradoxically also over-realize via bluffing; it's the murky middle that suffers. [HEURISTIC/uncertain — qualitative consensus, no single numeric anchor across all sources]
4. **Stack depth (SPR).** Deeper effective stacks amplify the IP/OOP and playability gaps (more streets = more opportunities for the informational/positional edge to compound); shallow stacks compress R toward raw equity for everyone since there's less room to maneuver post-flop. Janda (per secondary summary) states this directly: with deeper stacks IP realizes more than 100% and OOP realizes less than 100%; as stacks shorten, the gap narrows. [SOURCED estimate — Matthew Janda, *Applications of No-Limit Hold'em* (Janda), summarized via secondary sources — could not access exact page/chapter text; treat the direction as reliable, the book itself as the primary citation to track down for exact wording]
5. **Range composition and skill.** A polarized/strong range generates more fold equity across the board; player skill in exploiting or being exploited postflop shifts realization further from the solver GTO baseline in either direction. [HEURISTIC/uncertain]

---

## 2. Published R values / tables

There is **no single canonical public table** of "R by hand class × position" the way there is for, say, preflop opening ranges. EQR is solver-output-dependent (board, ranges, stack depth, bet sizing all shift it), so most public numbers are **worked examples from one specific spot**, not generalized lookup tables. Below are the concrete numbers that are actually published, organized by type.

### 2a. Single-spot worked examples (most rigorous — these are direct solver outputs)

| Spot | Hand / Player | Raw equity | Realized (EQR or EV) | R | Source |
|---|---|---|---|---|---|
| 9♠3♠2♦ flop, BB vs IP raiser (PIO Solver) | BB (OOP), whole range | 46.5% | EV 36.8% of pot | **R ≈ 79.1%** (OOP) | [SOURCED estimate — pokercoaching.com, "Become A Poker Equity Expert", Matt Affleck, https://pokercoaching.com/blog/become-a-poker-equity-expert/] |
| same spot | IP player, whole range | (complement) | — | **R ≈ 118.1%** (IP) | same source |
| T♠7♦2♥ flop, $0.50/$1 6-max | 3♥3♠ (OOP, one specific hand not a range) | 49% | EV realistic $1.36 vs naive $2.94 | **R = 62%** | [SOURCED estimate — Red Chip Poker, "Equity Realization", https://redchippoker.com/equity-realization/] |
| A♦2♦ isolated hand, OOP vs IP (illustrative, not board-specified) | A2s OOP | — | "less than 2%" | **R ≈ near 0%** (extreme case) | [SOURCED estimate — GTO Wizard, "Equity Realization", https://blog.gtowizard.com/equity-realization/] |
| Same hand, IP | A2s IP | — | "almost 100%" | **R ≈ 100%** | same source |
| 98s, OOP, low nut potential (illustrative) | 98s OOP | — | "less than 25%" | **R ≈ 25% or below** | same source |
| K♥8♦5♦ flop, 100bb effective | 7♥6♥ (OESD) | ~40% | 5.81bb EV | R > 100% (over-realizes) | [SOURCED estimate — GTO Wizard, "I'd Rather Be Drawing"] |
| Same flop | K♠T♣ (top pair weak kicker) | ~75% | 5.36bb EV | R < 100% (under-realizes) | same source |
| K♠Q♥3♦ flop, 40bb effective, BB vs BTN | A7o | 40% | folded (R effectively too low to continue) | R low enough to force a fold despite raw equity > pot-odds requirement | [SOURCED estimate — GTO Wizard, "What are Pot Odds in Poker?", https://blog.gtowizard.com/what-are-pot-odds-in-poker/] |
| Same spot | 42s | 18% | called (R high enough despite lower raw equity) | R high via implied odds/playability | same source |

**Read on the A2s and 98s figures:** these are presented by GTO Wizard as illustrative extremes ("a hand can realize almost none of its equity, or almost all of it") rather than typical averages — treat them as bounds on the *range* of R, not central tendencies. [HEURISTIC/uncertain — labeled illustrative by the source itself]

### 2b. Preflop / BB-defense realization (heavily cited, but traced to a single recurring worked example)

The most commonly repeated "preflop R" figure across coaching sites (PokerCoaching/Matt Affleck lineage, mirrored on multiple aggregator sites):

> **K9o vs a UTG open, 100bb effective:** raw equity ≈ 35%. Realization ≈ **60%** on average → realized equity ≈ **21%**. Since the pot-odds requirement to continue vs. a 2.2bb UTG open is ≈25%, K9o is a fold *despite* 35% raw equity clearing the naive pot-odds bar — realized equity (21%) falls short of the 25% threshold. [SOURCED estimate — traced to PokerCoaching.com lineage / repeated in vip-grinders.com "Big Blind Defense" guide; I could not independently verify the exact solver run behind the "60%" figure, so treat the 60% as this source's assertion, not a re-derived solver output]
>
> The same source notes that at **20bb effective**, the same K9o becomes a profitable call — shallower stacks compress the IP/OOP realization gap (fewer streets for the IP player to leverage information/position), consistent with the Janda directional claim in §1.4. [SOURCED estimate — same lineage]

A second, independently-sourced datapoint in the same genre: solver-optimal BB defense frequencies against a 2.5x open (100bb, 6-max, low-moderate rake) run **~5–15 percentage points tighter than raw MDF (minimum defense frequency) math would suggest** — e.g., MDF math says defend ~65%, solver-optimal is closer to 50–58%, depending on stakes/rake. [SOURCED estimate — secondary summary of solver-based coaching content; exact primary study not independently located — flag as needing direct-source verification if this figure is load-bearing in the spec]

**What's missing:** I could not find a publicly available, single, comprehensive table of "R by 169 starting hands × position" the way GTO Wizard/Acevedo would have internally from solver runs. Michael Acevedo's *Modern Poker Theory* is reported (via book description/review secondary sources) to contain **"equity realization heatmaps" broken down by position (EP vs BN) and stack depth** — this is the closest thing to the systematic table the spec wants, but I could not access the actual page images/numbers (Scribd/dokumen.pub mirrors were unavailable — landing pages/maintenance only). **Action item: source a physical/PDF copy of Modern Poker Theory (Acevedo) and pull the heatmap numbers directly rather than relying on a secondary description.** [HEURISTIC/uncertain — existence of the table is sourced, its contents are not]

### 2c. Postflop tendencies (qualitative, well-supported directionally; no single numeric table)

- Strong hands and very weak (bluffing) hands over-realize; medium-strength hands under-realize the most. [HEURISTIC/uncertain — repeated identically across GTO Wizard and Red Chip, but always qualitative]
- Suited/connected hands out-realize offsuit/disconnected hands of similar raw equity, with the one quantified example being the flop-connection-rate gap (76s 62.4% vs 76o 55.9%; 87s 62.4% vs 85s 57.1%) — note this is *flop contact rate*, a proxy/driver for R, not R itself. [SOURCED estimate — see §1.3]
- Draws (especially strong ones — big flush draws, OESDs with overcard backup) tend to over-realize versus made hands of comparable or even greater raw equity, per the K85dd worked example above. [SOURCED estimate]

---

## 3. The IP-vs-OOP realized-equity edge magnitude — verifying the doc's "~5–10%"

**Verdict: the spec's "~5–10%" figure appears too narrow/possibly mis-scoped, and no source gives a single clean aggregate number for "the IP/OOP edge" — it is highly spot-dependent.** Here is the evidence:

- The one clean solver-derived single-flop example found (9♠3♠2♦, BB vs IP raiser) shows OOP realizing **~79%** and IP realizing **~118%** — a **~39 percentage-point gap** on that specific board, far larger than 5–10%. [SOURCED estimate — pokercoaching.com]
- GTO Wizard's illustrative bounds (A2s: ~2% OOP vs ~100% IP; 98s OOP: <25%) show the gap can be **enormous** (tens to ~100 points) in extreme/low-playability cases, though GTO Wizard explicitly frames these as illustrative extremes, not averages. [SOURCED estimate — GTO Wizard]
- Janda's directional claim (via secondary summary) is that deeper stacks push IP above 100% and OOP below 100%, with the **gap shrinking as stacks get shorter** — implying there is no single fixed number; it is a function of SPR. [SOURCED estimate — secondary summary of Janda]
- I could not find any source publishing a single "average IP vs OOP realization edge across all spots" statistic (e.g., "IP realizes X% more than OOP on average across all flops/ranges"). Every credible source frames R as context-dependent (board texture, ranges, stacks, bet sizing) and explicitly warns against treating it as a fixed constant. [HEURISTIC/uncertain]

**Recommendation for the spec:** Replace a single point estimate like "~5–10%" with a **range-and-caveat framing**, e.g.: *"IP typically realizes more equity than OOP; the gap is highly spot-dependent — small (roughly single-digit to ~15 points) in shallow/high-SPR-constrained or very connected/high-playability spots, and can widen to 20–40+ points on boards/ranges where the OOP player's range is capped or low-playability (e.g., disconnected offsuit holdings OOP facing continued aggression)."* If the spec needs one defensible anchor number for "typical" mid-SPR 100bb single-raised-pot spots, the **79% OOP / 118% IP (~39-point gap)** worked example is the most rigorous single citable number found, but it is one flop, not an aggregate — it should be labeled as an illustrative single-spot data point, not a general constant. [SOURCED estimate + explicit recommendation]

---

## 4. How R feeds a call/defend decision

**Mechanism (well-established, consistent across GTO Wizard, Upswing, Red Chip, PokerNerve, and the pot-odds literature):**

1. Standard pot odds gives a **required equity threshold**: `Equity Needed = Call Amount / (Pot + Call Amount)`. [SOLVED/derivable]
2. This threshold implicitly **assumes the pot is checked to showdown with no further action** — i.e., it assumes R = 100%. [SOLVED/derivable]
3. Because R is usually < 100% OOP (and can be > 100% IP), the correct decision rule is to compare **realized equity, not raw equity, to the pot-odds threshold**: continue only if `raw equity × R ≥ required equity`. [SOLVED/derivable — this is the direct algebraic consequence of the R definition in §1]
4. Worked demonstration (K♠Q♥3♦, 40bb, BB vs BTN, GTO Wizard): naive pot odds says "call with ≥20% equity." A7o has 40% raw equity — comfortably clears naive pot odds — yet the GTO solver **folds** it, because A7o's realized equity is depressed by its inability to continue profitably on many turns/rivers (poor playability, dominated top-pair type situations, no redraws). Conversely 42s, with only 18% raw equity, **calls**, because its combo-draw/implied-odds profile lets it realize more of (or exceed) its raw equity on favorable run-outs. [SOURCED estimate — GTO Wizard, "What are Pot Odds in Poker?"]
5. Practical folding heuristic repeated across sources: **"pot odds are the math baseline; adjust for position, playability, and implied odds before deciding."** [HEURISTIC/uncertain — repeated framing, not a formula]

**For the spec**, the clean, defensible formalization is:

```
Continue (call/defend) iff:  raw_equity × R  ≥  pot_odds_required_equity
```

with R itself estimated from the drivers in §1 (position, initiative, hand playability/connectivity, draw-vs-made status, SPR) rather than treated as a constant — every source is explicit that R is not a fixed number and using a single global R (e.g., "OOP always ×0.7") is a simplification that will misprice both the extremes (near-0% and >100% R cases in §2a) and the direction of the SPR effect (R gap narrows as stacks shorten, per Janda). [HEURISTIC/uncertain — this is my synthesis/recommendation, flagged as such, not a source's literal words]

---

## Sources

- GTO Wizard Glossary — "Equity Realization (EQR)": https://gtowizard.com/glossary/equity-realization-eqr/
- GTO Wizard Blog — "Equity Realization": https://blog.gtowizard.com/equity-realization/
- GTO Wizard Blog — "I'd Rather Be Drawing": https://blog.gtowizard.com/id-rather-be-drawing/
- GTO Wizard Blog — "What are Pot Odds in Poker?": https://blog.gtowizard.com/what-are-pot-odds-in-poker/
- GTO Wizard Blog — "Mathematical Misconceptions in Poker": https://blog.gtowizard.com/mathematical-misconceptions-in-poker/
- GTO Wizard Blog — "Interpreting Equity Distributions": https://blog.gtowizard.com/interpreting-equity-distributions/
- GTO Wizard Blog — "Overcalling From the BB": https://blog.gtowizard.com/overcalling-from-the-bb/
- GTO Wizard Blog — "What is Equity in Poker?": https://blog.gtowizard.com/what-is-equity-in-poker/
- Upswing Poker — "How Equity Realization Impacts Every Hand You'll Ever Play": https://upswingpoker.com/equity-realization-explained/
- Red Chip Poker — "Equity Realization": https://redchippoker.com/equity-realization/
- Red Chip Poker — "Pot Odds, Equity and Equity Realization" (podcast): https://redchippoker.com/pot-odds-equity-realization-poker-podcast/
- PokerNerve — "Equity Realization - Playing From The Big Blind": https://pokernerve.com/equity-realization/
- PokerCoaching.com (Matt Affleck) — "Become A Poker Equity Expert": https://pokercoaching.com/blog/become-a-poker-equity-expert/
- Poker Academy — "How to understand equity realization (EQR)?": https://poker.academy/blog/post/how-to-understand-equity-realisation-eqr
- vip-grinders.com — "Big Blind Defense: Range & Strategy Guide" (K9o example lineage; page returned 403 on direct fetch, cited via search-index summary — verify directly before treating as load-bearing): https://www.vip-grinders.com/poker-strategy/big-blind-defense/
- Matthew Janda — *Applications of No-Limit Hold'em* (book; direction of the SPR/position claim sourced via secondary summaries, not directly paginated — recommend pulling the primary text before final calibration)
- Michael Acevedo — *Modern Poker Theory* (book; reported to contain equity-realization heatmaps by position/stack depth — existence confirmed via book descriptions/reviews, exact figures NOT independently verified; direct copy needed)

## Figures I could NOT source (flag for the spec)

1. **No single aggregate "IP realizes X% more than OOP on average" statistic exists in the public literature searched.** The spec's "~5–10%" should be replaced with the range-and-caveat framing in §3, anchored on the one rigorous worked example found (~79% OOP vs ~118% IP, ~39-point gap on one flop) rather than a false-precision single number.
2. **No public 169-hand × position R lookup table.** Acevedo's *Modern Poker Theory* reportedly has the closest thing (EP vs BN heatmaps by stack depth) but I could not access the actual figures — needs a direct copy of the book.
3. **The "60% average realization" behind the widely-repeated K9o/UTG-open example** could not be traced to a primary solver run — it's asserted by a coaching-content lineage (PokerCoaching/Matt Affleck, mirrored by vip-grinders) without a shown derivation. Usable as a directional/illustrative figure, not as a precise calibration constant.
4. **The "solvers defend 5–15 points tighter than MDF" BB-defense figure** likewise traces to secondary coaching summaries, not a primary study with a named solver run/board set — flag if this is meant to be load-bearing.
