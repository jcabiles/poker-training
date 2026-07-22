# "Risk Premium" vs. Cash-Game Range/Position Disadvantage — Research Note

Scope: NLHE cash, ~100bb. Question: what does "risk premium" correctly mean in poker, and is it the right term for pricing a defense against a raise/3-bet when out of position (OOP) and range-disadvantaged in a cash game?

## 1. The precise meaning of "risk premium"

**[SOURCED]** GTO Wizard's own glossary defines risk premium strictly as a **tournament/ICM concept**:

> "Risk Premium measures the extra risk you take stacking off in an MTT. It's a measure of survival pressure and a valuable tool for understanding ICM spots."
> Formula: **RP = Required Equity (ICM) − Required Equity (cEV)**, evaluated when stacks are fully committed.
— [GTO Wizard Glossary: Risk Premium](https://pages.gtowizard.com/glossary/risk-premium/)

**[SOURCED]** Mechanism: because tournament chips have non-linear value (ICM — the Independent Chip Model, which converts chip stacks into $EV based on payout structure), losing your stack costs you more $EV than winning an equivalent stack gains you. This is a **survival-value effect**, not a card-equity effect.

> "Risk premium describes the extra equity you need to call an all-in in poker tournaments because payout structures make losing chips more costly than gaining them... Each player has a unique risk premium against every other player in a tournament."
— [poker.org: Dara O'Kearney, Understanding Risk Premium](https://www.poker.org/poker-strategy/dara-okearney-understanding-risk-premium-size-matters-aPFY60b5iBDG/), [GTO Wizard Glossary](https://pages.gtowizard.com/glossary/risk-premium/)

**[SOURCED]** Worked example from PokerCoaching.com: "If you need 50% equity to call an all-in in a ChipEV scenario, and your Risk Premium is 12% on the bubble, then you would need 62% equity." Medium stacks tend to carry the highest risk premium (most to lose relative to their stack); risk premium is highest on the money bubble / near pay jumps.
— [PokerCoaching.com: Risk Premium in Tournaments](https://pokercoaching.com/blog/risk-premium-in-poker-tournaments/)

**[SOURCED] — explicit cash-game exclusion.** PokerCoaching.com states this directly, contrasting the two formats:

> "In cash games, chips equal money. If you double your stack, you double your money." Tournaments differ because "the value of chips changes constantly depending on stack sizes and payouts," which is what makes risk premium a live consideration — and, by clear implication, **inapplicable where chip value is linear (cash games)**.
— [PokerCoaching.com: Risk Premium in Tournaments](https://pokercoaching.com/blog/risk-premium-in-poker-tournaments/)

**Bottom line [SOLVED/derivable from sources above]:** "Risk premium" is a **specific, quantifiable ICM artifact** — the gap between the equity needed to call profitably under chip-EV (chipEV, i.e. treating chips as linearly worth money) math and the equity needed to call profitably under $EV-via-ICM math. It exists *only* because tournament payout structures make chip stacks nonlinearly valuable (survival/pay-jump pressure). **In a cash game, where 1 chip is always worth $1 regardless of stack size or who's at the table, this nonlinearity does not exist, so risk premium as defined by GTO Wizard/O'Kearney/PokerCoaching is zero/not applicable.**

## 2. How cash-game 100bb defense vs. a raise/3-bet is actually priced

**[SOURCED]** The GTO Wizard cash-game-specific article on defending 3-bet pots OOP **never uses the term "risk premium."** Instead it frames the extra difficulty of continuing OOP entirely through **equity realization**:

> "[OOP] realizing our equity becomes an ordeal because we always have to act first... we will always be at an informational and equity realization disadvantage across all streets... our opponent will always have more information about our range because we must act first."
— [GTO Wizard: Crush 3-Bet Pots OOP in Cash Games](https://blog.gtowizard.com/crush-3-bet-pots-oop-in-cash-games/)

That article also gives one concrete solver-derived number: the OOP preflop 3-bettor's average post-flop checking frequency is **33.9%** vs. **19.7%** for an IP 3-bettor — evidence of how much more passively OOP ranges must play to protect against equity-realization loss, though this is a checking-frequency stat, not a "how much extra equity to defend" number.

**[SOURCED]** GTO Wizard's dedicated **Equity Realization** article gives the formal framing that should replace "risk premium" in cash-game defend/fold pricing:

> Formula: **Equity × EQR × Pot = EV**, where EQR (equity realization, a percentage) captures how much of a hand's raw equity converts into actual expected value once future betting rounds are played out. **"All hands have lower EQR when playing out of position."**

Worked example given: in a J♥T♦9♥ board, an in-position raiser's weakest hand realizes **almost 100%** of its raw equity, while the same holding **out of position realizes less than 2%.** Facing a 33%-pot bet (which lays roughly 4:1 / ~20% pot-odds-required-equity by naive math), hands like 97o with ~44% raw equity still fold **more than 20% of the time** in solver output, precisely because OOP equity realization is expected to be so poor.
— [GTO Wizard: Equity Realization](https://blog.gtowizard.com/equity-realization/)

**[SOURCED]** GTO Wizard's "Mathematical Misconceptions in Poker" article names this exact error pattern directly — treating naive pot-odds equity as sufficient, and treating MDF (Minimum Defense Frequency — the minimum % of a range that must continue against a bet to keep a bluff-with-zero-equity indifferent, MDF = 1/(pot-odds-offered+1)) as a rule rather than a shield:

> "Equity does not equate to Expected Value! ... standard equity calculations assume the pot gets checked down, disregarding equity realization, position, implied odds, range advantage, and other postflop factors." "Many beginner players use these metrics [MDF] to justify poor calls or bluffs." Solvers "defend closer to MDF when in position than out of position because checking back weak hands has more positional value."
— [GTO Wizard: Mathematical Misconceptions in Poker](https://blog.gtowizard.com/mathematical-misconceptions-in-poker/)

**[SOURCED]** Upswing Poker corroborates the same framing (equity realization, not risk premium) independently:

> "Your hands will realize more equity when you are in position and less equity when you are out of position, since when in position you get to act last on every street and thus can make more informed decisions." Hands that are "strong, connected, and/or suited" over-realize equity (can profitably continue below 50% raw equity); "disconnected and/or offsuit hands tend to realize the least equity."
— [Upswing Poker: What is Equity Realization & How Does it Impact Strategy](https://upswingpoker.com/equity-realization-explained/), [Upswing Poker: Beyond Raw Equity](https://upswingpoker.com/raw-equity-vs-realized-equity/)

**[SOLVED/derivable]** Putting this together, the correct cash-game framing for "how much do I need to defend/call vs. a raise or 3-bet when OOP and range-disadvantaged" is:

1. Start from **pot odds** (the raw equity threshold to break even at showdown-only EV).
2. Adjust down for **equity realization (EQR)**: since realized EV = raw equity × EQR × pot, and OOP EQR is systematically below 100% (often far below for medium-strength hands), the *effective* continuing threshold is tighter than naive pot odds suggest.
3. **MDF** is a useful sanity check/shield against being over-exploited by bluffs, not itself the answer — and solvers deliberately defend *below* MDF when OOP because of the equity-realization/positional-value tradeoff of checking back weak hands.
4. None of steps 1–3 are "risk premium" in the technical sense used above — there is no chipEV-vs-$EV gap driving this in cash games. It's pot odds tempered by equity realization (a range/position-driven postflop-playability discount), plus MDF as a floor-check.

## 3. Published numbers on how much extra tightness/equity is needed OOP vs. a polarized 3-bet

**[CONTESTED/uncertain — no single universal number exists].** None of the sources reviewed (GTO Wizard glossary, GTO Wizard's OOP 3-bet-pot cash article, GTO Wizard's Equity Realization article, GTO Wizard's Mathematical Misconceptions article, Upswing's Equity Realization and Raw-vs-Realized-Equity articles) publish a single, general "defend X% tighter than pot odds when OOP facing a 3-bet" figure. The numbers that do exist are **spot-specific solver outputs**, not general rules:

- OOP 3-bettor's post-flop checking frequency: **33.9%**, vs. **19.7%** IP — [GTO Wizard: Crush 3-Bet Pots OOP in Cash Games](https://blog.gtowizard.com/crush-3-bet-pots-oop-in-cash-games/) [SOURCED, but this is a checking-frequency example, not a defend-frequency/equity-threshold rule]
- Example board (J♥T♦9♥): weakest IP hand realizes ~100% equity, weakest OOP hand (same holding) realizes **<2%** — [GTO Wizard: Equity Realization](https://blog.gtowizard.com/equity-realization/) [SOURCED, illustrative single example, not a general coefficient]
- Facing a 33%-pot bet, a 44%-raw-equity hand (97o) still folds **>20%** of the time in solver output despite having well above the ~20% pot-odds-required equity — [GTO Wizard: Equity Realization](https://blog.gtowizard.com/equity-realization/) [SOURCED, again a single illustrative spot]
- In a specific BB-3bet-vs-UTG-call example, GTO Wizard reports the OOP 3-bettor actually holds *more* raw equity (54.4% vs 45.6%) but still has to navigate realization difficulty — [GTO Wizard search summary of range-disadvantage article] [SOURCED via search snippet; recommend re-verifying full article text if this number is load-bearing]

**Why no single number exists [SOLVED/derivable]:** equity realization is a function of hand class (blockers, connectivity, suitedness), bet sizing, board texture, and stack depth — solvers output a full continuing range/strategy per spot rather than a scalar "tighten by N%" constant. Any single "flat OOP tax" percentage would be a simplification not supported by the primary solver-literature sources reviewed. Treat any specific "you need X% more equity OOP" figure from secondary sources (forum posts, coaching-site summaries) with caution unless it cites the exact solver spot it came from.

## Summary / crisp corrected definition

- **Risk premium** = a *tournament-only*, ICM-driven quantity: the gap between the equity needed to profitably call an all-in under chip-EV math vs. under $EV-via-ICM math, caused by the nonlinear dollar value of tournament chips (survival/pay-jump pressure). **[SOLVED/derivable + SOURCED]**
- It **does not apply to cash games** — cash chips have linear ($-for-$) value, so there is no chipEV/$EV gap to create a premium. **[SOURCED]**
- The cash-game phenomenon the user is likely reaching for — needing to continue tighter than naive pot odds when OOP and range-disadvantaged against a raise/3-bet — is correctly named **equity realization (EQR)** discount on top of pot odds, with **MDF** as a secondary floor/shield check. This is a *distinct mechanism* (postflop playability/information disadvantage) from ICM risk premium (survival-value nonlinearity), and the two should not be conflated or use the same term. **[SOURCED across 4 independent sources: GTO Wizard glossary, GTO Wizard cash 3-bet article, GTO Wizard equity-realization article, Upswing]**
- No source surveyed misuses "risk premium" to describe the cash-game OOP/range-disadvantage effect — the terminology is consistently kept separate across every source found. There is **no genuine industry disagreement/loose-usage to report** on this point; the risk is user-side conflation, not source-side inconsistency. **[CONTESTED/uncertain: absence of evidence of misuse is not proof no one ever misuses the term informally in forums — this is what the survey found, not an exhaustive claim.]**
- No general numeric "extra equity/tightness needed OOP vs. a polarized 3-bet" constant was found in the literature reviewed; only spot-specific solver examples exist. **[CONTESTED/uncertain — flagged explicitly, do not fabricate a number for the calibration spec.]**

## Sources

- [GTO Wizard Glossary: Risk Premium](https://pages.gtowizard.com/glossary/risk-premium/)
- [GTO Wizard: Crush 3-Bet Pots OOP in Cash Games](https://blog.gtowizard.com/crush-3-bet-pots-oop-in-cash-games/)
- [GTO Wizard: Equity Realization](https://blog.gtowizard.com/equity-realization/)
- [GTO Wizard: Mathematical Misconceptions in Poker](https://blog.gtowizard.com/mathematical-misconceptions-in-poker/)
- [GTO Wizard: Navigating Range Disadvantage as the 3-Bettor](https://blog.gtowizard.com/navigating-range-disadvantage-as-the-3-bettor/)
- [PokerCoaching.com: Risk Premium in Poker Tournaments — The ICM Concept Players Miss](https://pokercoaching.com/blog/risk-premium-in-poker-tournaments/)
- [poker.org: Dara O'Kearney — Understanding Risk Premium (size matters)](https://www.poker.org/poker-strategy/dara-okearney-understanding-risk-premium-size-matters-aPFY60b5iBDG/)
- [Upswing Poker: What is Equity Realization & How Does it Impact Strategy](https://upswingpoker.com/equity-realization-explained/)
- [Upswing Poker: Beyond Raw Equity — Unlocking the True Value of Your Poker Hands](https://upswingpoker.com/raw-equity-vs-realized-equity/)

Not independently re-verified in this pass (found via search summary only, not full-text fetch): the BB-3bet-vs-UTG 54.4%/45.6% equity example attributed to "Navigating Range Disadvantage as the 3-Bettor" — re-fetch directly before citing as a standalone number.
