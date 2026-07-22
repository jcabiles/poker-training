---
title: Poker Math — Comprehensive Reference (GTO, Ranges, Sizing, Exploits)
tags: [poker, gto, poker-math, reference, poker-coach]
created: 2026-07-21
context: authored to serve as the ground-truth reference for validating the poker-coach bot engine
scope: No-Limit Texas Hold'em (NLHE), cash-game focus (~100bb, e.g. live $2/$3), 9-max & 6-max
status: draft — pending adversarial review (Claude Opus + Codex Sol refuters)
---

# Poker Math — Comprehensive Reference

> [!abstract] What this document is (plain terms)
> This is a from-the-ground-up map of **all the math and reasoning a poker player (or a poker bot) needs** to pick hands to play, size bets, and decide fold/call/raise — before the flop, after the flop, and against different kinds of opponents. Every section starts with a plain-language explanation (a callout like this one) and *then* gives the technical detail and the actual numbers. It is written for No-Limit Hold'em cash games at roughly 100 big blinds deep. The purpose is to be a **trusted yard-stick**: something we can hold the poker-coach bots up against and say "the bot is right / the bot is wrong" with a citation.

> [!info] Companion documents
> This file is the **conceptual explainer** (derivable + GTO-solvable math + principles). Two companions hold the rest:
> - **Poker Math — Calibration & Numbers (Spec)** — the sourced/derivable numeric tables (equity realization, rake, c-bet-by-texture, 3-bet combinatorics, sizing) for calibrating and validating the bots.
> - **Poker Math — Persona & Multiway Modeling (Estimates)** — the parts with *no single solved answer* (player-type stat bands, exploit magnitudes, multiway play), every figure explicitly labeled an estimate.

---

## How we know this math is right (confidence basis)

> [!note] In plain terms
> Almost nothing here is my personal opinion. Two kinds of claims live in this document, and they earn trust in two different ways. The **formulas** (pot odds, minimum defense frequency, expected value) are just algebra and probability — anyone can re-derive them on paper and check them. The **strategy claims** (which hands to raise from which seat, how to attack a calling station) are the long-standing consensus of the field's most respected books and solver outputs, and I cite them so a reviewer can go verify. Where a number is an approximation or a rule of thumb rather than an exact solved value, I say so.

**Two classes of claim, two standards of proof:**

1. **Derivable math** — combinatorics, pot odds, EV, MDF, bluff-to-value ratios, break-even frequencies. These are provable from first principles. Every formula in this document is stated with its derivation or a worked example so it can be independently checked. They are not "poker opinions"; they are arithmetic.

2. **Strategic frameworks and empirical ranges** — position ranges, c-bet theory, exploit adjustments, player-type stat profiles. These are the documented consensus of authoritative sources (below). Specific range percentages and stat bands are **representative/canonical**, not solver-exact (solver outputs vary by exact node, sizing tree, and rake); this is flagged wherever it matters.

**Primary sources this document is built to agree with:**

- **Books:** David Sklansky, *The Theory of Poker*; Ed Miller/Sunny Mehta/Matt Flynn, *Professional No-Limit Hold'em: Vol I* (SPR & commitment); Matthew Janda, *Applications of No-Limit Hold'em* and *No-Limit Hold'em for Advanced Players* (balance, bet-to-value, range construction); Will Tipton, *Expert Heads Up NLHE* (game-tree/indifference); Michael Acevedo, *Modern Poker Theory* (solver-era GTO); Andrew Brokos, *Play Optimal Poker* (equilibrium intuition); Ed Miller, *The Course* (exploitative live play).
- **Solver/education:** GTO Wizard blog, Upswing Poker, Red Chip Poker, PokerStrategy, SplitSuit; solver engines (PioSOLVER, GTO+, Jesolver) as the equilibrium ground truth.
- **Theory of the algorithm:** counterfactual regret minimization (CFR) literature — Zinkevich et al. 2007; Bowling et al. (heads-up limit essentially solved, 2015); Brown & Sandholm (Libratus 2017, Pluribus 2019 for 6-max).

> [!warning] Known limitation
> Solver-exact strategies are node-specific and depend on the allowed bet-size tree and rake. This document gives the **canonical shapes and representative numbers** that hold across sources, not a solver's per-runout output. Multiway pots (3+ players) have **no unique game-theoretic solution**; all multiway guidance is principled heuristic, not "solved."

---

## Table of contents

1. **Foundations** — combinatorics, probability, equity, equity realization
2. **The economic engine** — pot odds, expected value, fold equity, implied odds, break-even frequencies
3. **The game-theory layer (GTO)** — Nash equilibrium, MDF/alpha, bluff-to-value, indifference, bet sizing, range construction, range/nut advantage, blockers, solvers/CFR
4. **Preflop** — position, RFI, facing raises (3-bet/4-bet/5-bet), blind defense, sizing, stack depth, multiway
5. **Postflop** — board texture, hand-strength taxonomy, c-bet/turn/river theory, facing bets, SPR & commitment, multiway, realization
6. **Opponent modeling & exploitation** — player types, population stats, exploit adjustments, range estimation, Bayesian narrowing
7. **From theory to a bot** — strategy representation, heuristic vs solver, calibration & validation
8. **Glossary & formula sheet**

---

# Part 1 — Foundations

> [!note] In plain terms
> Before any strategy, you need the raw ingredients: how many ways a hand can be dealt, how likely a card is to come, and what "equity" (your share of the pot if all money went in now) actually means. Everything later — every fold, call, and raise — is built on these four ideas.

## 1.1 Card combinatorics (combos)

> [!note] In plain terms
> A "combo" is one specific two-card holding, like the ace of spades + king of hearts. Two hands that look the same on a chart ("AK") are actually many distinct combos, and counting them precisely is how you estimate "how likely is it the opponent actually has the nuts right now." When a card you can see (in your hand or on the board) is one they'd need, it removes some of their combos — that's a **blocker**.

- A 52-card deck yields **C(52,2) = 1,326** distinct starting hands (combos).
- Per hand class:
  - **Pocket pair** (e.g. AA): C(4,2) = **6** combos.
  - **Suited** (e.g. AKs): **4** combos (one per suit).
  - **Offsuit** (e.g. AKo): **12** combos (4×4 − 4 suited).
  - **Any two unpaired ranks** (AK total): **16** combos (4 suited + 12 offsuit).
- The 13×13 hand grid: **169 distinct hand classes** (13 pairs + 78 suited + 78 offsuit), covering all 1,326 combos.
- **Card removal / blockers:** holding one ace cuts an opponent's AA from 6→3 combos and AK from 16→12. Board cards remove combos too. This is why "I hold the ace of clubs" matters when the flush completes — you block some of their nut flushes. Combo counting is the arithmetic behind every range estimate.

## 1.2 Probability & outs

> [!note] In plain terms
> An "out" is a card that turns your losing hand into a winning one. Counting outs and converting them to a percentage tells you how often you'll improve — which you then compare against the price you're being asked to pay. The "rule of 2 and 4" is the fast mental shortcut for that percentage.

- **Outs → equity (rule of 2 and 4):** outs × 2 ≈ % to hit on the **next** card; outs × 4 ≈ % to hit across **flop→river** (two cards). The ×2 rule slightly **under**states one-card equity (9 outs → 18% vs 19.1% true, because the real denominator is 47 unseen cards, not 50); the ×4 rule is close for **≤8 outs** and increasingly **over**states beyond that (15 outs → 60% vs ~54% true). [corrected per review 2026-07-21]
- **Exact:** with a flop seen, 47 cards are unknown. Flush draw = 9 outs → next card 9/47 = **19.1%**; by the river 1 − (38/47)(37/46) = **35.0%** (rule-of-4 says 36%).
- **Common draws:** flush draw 9 outs; open-ended straight draw (OESD) 8 outs; gutshot 4 outs; combo draw (FD+OESD) up to 15 outs; overcards 6 outs (often discounted).
- Probabilities compound across streets; a draw's value depends on how many cards are still to come (two on the flop, one on the turn).

## 1.3 Equity

> [!note] In plain terms
> Equity is your fair share of the pot right now — the percentage of the time you'd win if the hand were dealt out to the end with no more betting. If you're 60% to win a $100 pot, your equity is $60. It's the single most important number strategy is built on, but note it is measured against a **specific opponent hand or an opponent's whole range**, not in a vacuum.

- **Hand vs hand:** e.g. AKo vs QQ ≈ 43% / 57% preflop (a "race"/"coin-flip" family).
- **Hand vs range:** your hand's average win-% against every combo the opponent could hold, weighted by combo count. This is the decision-relevant number, because opponents hold ranges, not single hands.
- **Range vs range:** each side's aggregate equity — the basis for whole-strategy decisions (who bets, who checks).
- **Equity distribution:** a range's equity is not one number but a *shape* — some hands crush, some are trash. Two ranges with equal average equity can play very differently (a "polarized" range of nuts+air vs a "condensed" range of medium hands). This shape drives bet-sizing choice (Part 3).
- **Computation:** exact by enumeration (evaluate every runout) or estimated by Monte-Carlo sampling. Solvers use exact equities at terminal nodes.

## 1.4 Equity realization (R)

> [!note] In plain terms
> You rarely collect your full equity, because the hand isn't dealt out for free — there's more betting, and you might get pushed off your hand before the river. "Realization" is the haircut (or bonus) on your raw equity from things like being out of position or not having the betting lead. It's why a hand with 50% raw equity can be a losing call: you won't get to *realize* all 50%.

- **Realization factor R** scales raw equity to *realized* equity: realized ≈ raw × R.
- **R < 1** (under-realize) when out of position (OOP), lacking initiative, or facing a range that can barrel you off marginal holdings.
- **R > 1** (over-realize) when in position (IP), holding the betting initiative, or holding hands that make easy top-pair/strong-draw continues.
- Rough anchors: suited connectors and small pairs over-realize via implied odds; offsuit gappers and dominated aces under-realize. The IP-vs-OOP realized-equity gap is **highly spot-dependent** — often single digits to ~15 points in shallow/high-playability spots, but **20–40+ points** when the OOP range is capped or low-playability (one illustrative single flop: ~79% OOP vs ~118% IP realization). Treat it as a range, never a fixed constant. [revised per research 2026-07-21]
- **Why it matters:** blind-defense and flatting decisions (Part 4) use realized, not raw, equity against the pot odds. This is a first-class variable, not a footnote.

---

# Part 2 — The economic engine (pot odds, EV, fold equity)

> [!note] In plain terms
> This is where money enters. Every decision in poker is ultimately "does this action make or lose chips on average?" The tools here convert equity and bet sizes into a profit-or-loss answer. If you internalize only one part of this document, make it this one — it is the engine under literally every fold, call, and raise.

## 2.1 Pot odds & break-even equity

> [!note] In plain terms
> Pot odds are the price of continuing: you compare what you must put in to what you'd win. If you must call $50 to win a $150 pot, you're getting 3-to-1, so you only need to win about 25% of the time to break even. Compare your equity to that break-even number — if your equity is higher, calling makes money.

- Facing a bet **B** into a pot of **P** (pot *before* the bet):
  - You call **B** to win **P + B**.
  - **Break-even equity = B / (P + 2B)** (your risk / final pot).
- Worked: pot P = 100, bet B = 50 (half-pot). Break-even = 50 / 200 = **25%** equity needed to call.
- Common break-evens to call: vs **⅓-pot → 20%**, vs **½-pot → 25%**, vs **¾-pot → ~30%**, vs **pot → 33%**, vs **2× overbet → 40%**.
- **Rule:** call if (realized) equity ≥ break-even equity. Note the *realized* qualifier (§1.4) — raw equity above the price is not automatically a call OOP.

## 2.2 Expected value (EV) — the master equation

> [!note] In plain terms
> Expected value is the long-run average profit of a choice: add up each possible outcome times how often it happens. Winning players don't try to win each hand; they take the action with the highest EV every time and let the math pay off over thousands of hands. Every other formula in this document is a special case of EV.

- **EV(action) = Σ (probability of outcome × chips won/lost in that outcome).**
- **EV(call) = equity × (final pot) − amount to call.** (Equivalently, call is +EV when equity > break-even from §2.1.)
- **EV(fold) = 0** (you surrender only chips already committed, which are sunk).
- **EV(bet/raise)** combines fold equity and showdown equity (§2.3).
- Decisions are made by **argmax EV** across legal actions — but note a *balanced* (GTO) strategy deliberately **mixes** actions that are close in EV to remain unexploitable (Part 3). Pure EV-max is the *exploitative* stance.

## 2.3 Fold equity & the EV of a bet

> [!note] In plain terms
> When you bet, you can win two ways: everyone folds (you take the pot now), or you get called and still have the best hand often enough. "Fold equity" is the value of the first way. It's why betting a weak hand (a bluff) can profit — you don't need the best hand if they fold enough.

- **EV(bet) = f × P + (1 − f) × [equity_when_called × (P + 2B) − B]**, where **f** = fold frequency, **P** = pot, **B** = bet.
- The first term (**f × P**) is **fold equity**; the second is the showdown value when called.
- A **pure bluff** (0% equity when called) profits whenever **f × P > (1 − f) × B**, i.e. when fold frequency exceeds the break-even below.

## 2.4 Break-even bluff frequency (risk/reward)

> [!note] In plain terms
> A bluff is a bet that only wins if they fold. The break-even is simple: compare what you risk to what's in the pot. Bet half-pot as a pure bluff and they only need to fold one time in three for you to profit. This is the mirror image of pot odds, seen from the bettor's side.

- A pure bluff of **B** into pot **P** needs fold frequency **f > B / (P + B)** to profit.
- Worked: half-pot bluff (B = 0.5P) → needs folds > 0.5P / 1.5P = **33%**.
- By size: **⅓-pot → 25%**, **½-pot → 33%**, **pot → 50%**, **2× → 67%** fold frequency to break even as a pure bluff.
- This quantity — the villain's *maximum* profitable fold frequency — is exactly **alpha** in the GTO layer (§3.2). Exploitative and GTO views meet here.

## 2.5 Implied & reverse-implied odds

> [!note] In plain terms
> Sometimes a call is wrong on today's price but right because of money you expect to win *later* when you hit — that's implied odds (great for draws to strong, disguised hands). The reverse also happens: you make your hand but lose a bigger pot to an even better one — that's reverse-implied odds (the curse of second-best hands). These adjust the raw pot-odds verdict.

- **Implied odds:** effective price improves because of expected future winnings when you hit. Favors nutted, disguised draws (sets, nut flush draws, straight draws to the nuts) — lets you profitably call below the raw pot-odds threshold.
- **Reverse-implied odds:** expected future *losses* when you make a second-best hand (e.g. top pair weak kicker, non-nut flush). Worsens the effective price; demands *more* than the raw threshold.
- **Depth-dependent:** both grow with effective stack depth (more money behind = bigger future swings), tying directly to stack-depth strategy (§4.6) and SPR (§5.6).

---

# Part 3 — The game-theory layer (GTO)

> [!note] In plain terms
> "GTO" (game-theory optimal) means playing a strategy so well-balanced that no opponent can exploit you, no matter what they do. You give up trying to read them; instead you make yourself un-readable and un-beatable. Real players deviate from GTO to exploit weak opponents (Part 6), but GTO is the baseline "correct" play and the reference every deviation is measured against. This section is the theoretical heart of modern poker.

## 3.1 Nash equilibrium & what "solved" means

> [!note] In plain terms
> A Nash equilibrium is a set of strategies where neither player can improve by changing their own play alone — a stalemate of optimal responses. When people say a spot is "solved," they mean a computer found this equilibrium. For heads-up (two-player) poker it's a genuine, well-defined answer; for three-or-more players it is not (there can be many equilibria and no single "right" one).

- A **Nash equilibrium** is a strategy profile where each player's strategy is a best response to the others' — no unilateral deviation gains.
- In **two-player zero-sum** games (heads-up poker), the equilibrium is the **unexploitable** strategy: playing it guarantees you can't lose in the long run to *any* opponent (you break even vs another equilibrium, win vs mistakes).
- **Multiway (3+): no unique equilibrium** and equilibrium play is not guaranteed unexploitable — a critical caveat for full-ring/6-max postflop and for any bot modeling multiway pots.
- GTO is **maximally defensive**, not maximally profitable. Against exploitable opponents, deviating (Part 6) earns more — but risks being counter-exploited by a thinking player.

## 3.2 Minimum Defense Frequency (MDF) & alpha

> [!note] In plain terms
> If you fold too often, an opponent can bet any two cards and profit purely from your folding. MDF is the minimum share of your range you must keep (call or raise) to stop that. Its twin, "alpha," is the flip side: the maximum share you're allowed to fold. Bigger bets let you fold more (higher alpha), because the opponent is risking more to steal.

- **MDF = P / (P + B)** — minimum fraction of your range you must continue with vs a bet **B** into pot **P**.
- **Alpha = 1 − MDF = B / (P + B)** — the fraction you may fold; also the bettor's break-even bluff frequency (ties back to §2.4).
- By size: **⅓-pot → MDF 75% / α 25%**, **½-pot → 67% / 33%**, **⅔-pot → 60% / 40%**, **pot → 50% / 50%**, **2× overbet → ~33% / 67%**.
- **Crucial nuance:** MDF is a **defense-against-exploitation** benchmark for *unbounded* betting ranges. When a bettor is **capped** (can't have many nutted hands) or **polarized** with the right value:bluff ratio, pure pot-odds/range analysis overrides raw MDF. MDF is the *floor*, not the whole answer. A bot that ignores price *and* MDF entirely (folding the same regardless of size) is unambiguously wrong.

## 3.3 Bluff-to-value ratios (polarized river)

> [!note] In plain terms
> When you make a big polarized bet on the river (nuts or nothing), how many of those bets should be bluffs? Just enough that a hand that only beats a bluff is indifferent to calling — so you can't be exploited by them always calling or always folding. The bigger you bet, the more bluffs you're allowed, because you're laying the caller a worse price.

- For a polar river bet of fraction **f** of the pot, the balanced **bluff fraction of the betting range = f / (1 + 2f)**; **value:bluff = (1 + f) : f**.
- By size: **⅓-pot → 20% bluffs (4:1 value)**, **½-pot → 25% (3:1)**, **⅔-pot → ~28.6% (2.5:1)**, **pot → 33% (2:1)**, **2× overbet → 40% (1.5:1)**.
- **Direction that matters most:** bluff frequency **rises with bet size**. A strategy that bluffs at a *fixed* rate regardless of the size it chooses is theoretically broken — the value:bluff ratio becomes decoupled from the price laid.
- **Earlier streets differ:** flop/turn "bluffs" usually carry equity (draws), so raw river ratios don't transfer directly — semi-bluffs are priced with their equity and the value of barreling later streets (§5.3–5.4). The river polar case is the clean canonical benchmark.

## 3.4 The indifference principle & mixed strategies

> [!note] In plain terms
> Optimal play often means doing the same thing only *some* of the time with a given hand — e.g. calling with this bluff-catcher 60% and folding 40%. The reason: you set your frequencies so the opponent gains nothing by switching their own choice (they're "indifferent"). Those in-between percentages are the fingerprint of GTO play, and they're why a good bot must roll dice, not always pick one action.

- At equilibrium, a player is made **indifferent** between two actions with a given hand; the *opponent's* frequencies are what enforce this.
- This produces **mixed strategies**: a hand class may bet 70% / check 30%, or call 55% / fold 45%. The mix is not randomness for its own sake — it's the frequency that removes the opponent's edge.
- **Implication for modeling:** a correct strategy is a **frequency vector per decision node**, sampled probabilistically — never a deterministic "always take the single highest-value action" (that leaks information and is exploitable).

## 3.5 Bet-sizing theory

> [!note] In plain terms
> How much to bet isn't one number — it's a tool matched to your goal. Small bets deny equity cheaply and work with your whole range on boards you own; big bets and overbets go with a "nuts or air" range to charge draws and pressure medium hands. Using multiple sizes, each with a correctly-built range, is what solvers do — and it's why one fixed size for everything is a leak.

- **Small bets (⅓–½ pot):** used with **wide, merged, uncapped** ranges on boards that favor you (range/nut advantage, §3.7). Cheap denial, high frequency.
- **Big bets / overbets (¾–2×+):** used with **polarized** ranges (strong value + bluffs) to maximize fold equity and charge draws; require nut advantage.
- **Geometric sizing:** to get stacks in by the river, bet the same *fraction* each street such that the pot grows geometrically — maximizes value from a strong range over multiple streets.
- **Merged vs polar:** merged = value + thinner value/protection at a smaller size; polar = nuts + air at a larger size. Sizing and range construction are **inseparable** — the size implies the range and vice versa.
- **Anti-tell requirement:** across the hands you bet a given size, the range must be balanced (value + bluffs), so the *size itself* doesn't reveal hand strength. (This is one property the poker-coach engine already gets right.)

## 3.6 Range construction

> [!note] In plain terms
> You never play one hand in isolation — you play your whole range of possible hands the same way, so the opponent can't tell which one you have. "Constructing a range" means deciding, for every hand you could hold here, how often it bets/checks/calls/folds. The three classic shapes — polarized, linear, condensed — are the vocabulary for this.

- **Polarized:** strong value + bluffs, little in between (bet big). Typical of raises, river jams, 3-bets OOP.
- **Linear / merged:** the top X% of hands by strength, no air (raise for value/protection, smaller). Typical of IP 3-bets and value regions.
- **Condensed / capped:** medium-strength hands, few nuts (calls, flats) — vulnerable to being bet off by a polar range.
- A well-formed range assigns each combo a **frequency** for each action such that the aggregate is balanced (§3.4) and the sizes are consistent (§3.5).

## 3.7 Range advantage & nut advantage

> [!note] In plain terms
> On a given board, ask two questions: whose range is stronger overall (range advantage), and who holds more of the absolute best hands (nut advantage)? The player with those advantages gets to bet aggressively; the one without should check and play cautiously. This is why the pre-flop raiser bombs an ace-high board but slows down on low connected ones.

- **Range advantage:** higher aggregate equity across your whole range on this texture → license to bet at high frequency.
- **Nut advantage:** you hold **more of the top combos** (sets, straights, nut flushes) → license to use **large** sizes and overbets (you have the hands to back them).
- Example: preflop raiser has range **and** nut advantage on **A-high dry** boards → small, high-frequency c-bet. On **low connected** boards (e.g. 765ss) the caller's range catches up → raiser checks more, uses polar sizing when betting.
- These two advantages determine **whether to bet, how often, and how big** — they are the bridge from preflop ranges to postflop action.

## 3.8 Blockers & card removal in strategy

> [!note] In plain terms
> The cards in your own hand secretly change what the opponent can hold. If you hold an ace, they're less likely to have aces or ace-king — so an ace is a great card to *bluff* with (they have fewer strong hands to call you) and, held by them-blocking hands, changes who should bet. Elite play uses blockers to pick which hands bluff and which fold.

- **Blocking value / unblocking folds:** the best bluffs **block the opponent's calling/value combos** and **unblock their folding combos** (e.g. bluff the river with a hand that holds a card to the nut straight/flush, reducing their nut combos).
- **Value bets** prefer to **unblock** the opponent's calling range (you want them to have hands that pay).
- Combinatorially, blockers shift the value:bluff math of §3.3 at the individual-combo level — which specific hands fill the bluff quota is a blocker decision.

## 3.9 Solvers & CFR (how equilibria are computed)

> [!note] In plain terms
> Solvers are programs that find the balanced strategy by playing millions of hands against themselves and slowly fixing their own mistakes. The core algorithm, "counterfactual regret minimization," keeps a tally of "how much I regret not doing X" and shifts toward the less-regretted actions until it settles at equilibrium. This is where the authoritative numbers in this document ultimately come from.

- **Counterfactual Regret Minimization (CFR):** iterative self-play that minimizes per-node regret; the **average** strategy over iterations converges to a Nash equilibrium in two-player zero-sum games (Zinkevich et al., 2007).
- **Milestones:** heads-up **limit** Hold'em essentially solved (Bowling et al., 2015, *Science*); **Libratus** beat pros at heads-up no-limit (Brown & Sandholm, 2017); **Pluribus** beat pros at 6-max (2019) using depth-limited search + blueprint strategies — but 6-max has **no unique equilibrium**, so Pluribus is "superhuman," not "solved."
- **Practical solvers** (PioSOLVER, GTO+, Jesolver) solve single spots given a starting range, board, stacks, and a bet-size tree; outputs are the per-combo frequency vectors this document's strategy sections summarize.
- **Abstraction:** to stay tractable, solvers bucket similar hands/bets; finer trees = more accurate but slower. This is why "GTO numbers" carry small variation between tools and sizings.

---

# Part 4 — Preflop

> [!note] In plain terms
> Preflop is where you decide which hands to play and how, based on where you're sitting and what's happened before you. It's the most-studied, most-standardized part of poker: the correct opening hands per seat are essentially settled, and getting them right is the highest-leverage, lowest-variance skill. Everything postflop inherits the ranges you build here.

## 4.1 Position

> [!note] In plain terms
> Acting last is a structural advantage: you see what everyone does before you decide, and you can control the pot size. The later your seat, the more hands you can profitably play. This single fact shapes every preflop range — tight up front, loose on the button.

- 9-max seat order: **UTG, UTG+1, UTG+2, LJ, HJ, CO, BTN, SB, BB** (6-max drops the three earliest). "Position" = how late you act postflop.
- Acting **in position (IP)** gives more information and better pot control → **higher equity realization** (§1.4) → you can play more hands profitably.
- Consequence: opening ranges **widen monotonically** from UTG (tightest) to BTN (widest); the blinds are special (they act last preflop but first postflop).

## 4.2 Raise-first-in (RFI) ranges by position

> [!note] In plain terms
> "RFI" is the range of hands you open-raise with when everyone before you folded. It gets wider the closer you are to the button. These ranges are close to solved and widely published; a bot's opening ranges should match them per seat.

- Representative RFI frequencies (**9-max seat frame**, 100bb, ~2.5bb open, modern solver-adjacent): **UTG ~15–18%**, **LJ ~19–22%**, **HJ ~23–26%**, **CO ~27–32%**, **BTN ~40–48%**, **SB ~ raise-or-fold, wide (~35–45% raise)**. In **6-max** the equivalent seats run tighter — map by *seats-behind*, not by name (6-max HJ = first-in ≈ 19–20%).
- Shape: early seats favor high-card strength and pairs; late seats add suited connectors, suited gappers, and weaker suited aces/broadways (they realize equity better IP).
- **Sizing:** ~2–2.5bb online, **~3bb+ live** (deeper effective fields, more callers) — the poker-coach $2/$3 context uses larger opens by design.

## 4.3 Facing a raise: 3-bet, 4-bet, 5-bet

> [!note] In plain terms
> When someone raises before you, your re-raise is a "3-bet"; if they re-raise you back it's a "4-bet"; the final all-in shove is usually the "5-bet." Each of these has its own correct range built from strong hands (value) plus a measured number of bluffs, and the bluffs are chosen using blockers. This ladder is where a lot of a bot's realism lives.

- **3-bet ranges** (facing an open):
  - **IP (e.g. BTN vs CO):** more **linear/merged** — value hands + strong suited playables; you realize equity well IP.
  - **OOP (e.g. SB/BB vs BTN):** more **polarized** — premium value + **blocker bluffs** (e.g. Axs, which blocks AA/AK), because flatting OOP under-realizes.
  - Typical 3-bet frequency ~**5–11%** depending on positions; sizing **~3× the open IP, ~4× OOP**.
- **4-bet ranges** (facing a 3-bet): value-heavy (**QQ+, AK**-ish core) plus **Axs blocker 4-bet bluffs**; sizing **conventionally ~2.2–2.5× the 3-bet** (a live/coaching convention, *not* a solver-pinned number).
- **5-bet / shove** (facing a 4-bet): at 100bb, **value-heavy and shove-dominant** (commonly cited ~**QQ+/AK**, but forum-level, not solver-sourced); the rest fold. Shorter stacks widen this.
- **Flatting / cold-calling:** continuing without raising — stronger IP (you can realize), thinner OOP; the flat range is **condensed/capped** and must be protected by *also* having some 3-bets.
- **Squeeze:** facing an open **plus** one or more callers, a 3-bet ("squeeze") uses the dead money and needs a larger size; ranges tighten toward value + high-blocker bluffs.

## 4.4 Blind defense

> [!note] In plain terms
> The big blind already has money in the pot and acts last preflop, so it gets a discount to continue and defends very wide against a steal — but it's out of position postflop, so it under-realizes and can't just call with anything. The small blind is trickier (in the middle) and usually plays a 3-bet-or-fold style. This is a spot beginners misplay in both directions.

- **BB vs steal:** excellent pot odds (already posted 1bb, closing the action) → **wide** defense, but discounted by **equity realization** (OOP postflop, R < 1). Defense mixes flat + 3-bet; the raw pot-odds "you only need X%" is tempered by R.
- **SB vs steal:** OOP to the BB even if the raiser folds → many strategies play **3-bet-or-fold** (avoid a capped OOP flatting range), sometimes with a small flatting range at deeper stacks.
- The blinds are net losers by structure; the goal is to **lose the least** (defend correctly), not to profit.

## 4.5 Preflop sizing

> [!note] In plain terms
> Bet sizes preflop follow simple, learnable conventions, and they change the pot geometry for the whole hand. Open around 2–3 big blinds, 3-bet about 3–4× the open, 4-bet a bit over 2× the 3-bet. Live games use bigger sizes than online. Getting sizes right sets up sane stack-to-pot ratios postflop.

- **Open:** 2–2.5bb online, 3bb+ live; **add ~1bb per limper** when isolating.
- **3-bet:** ~3× the open **IP**, ~3.5–4× **OOP** (more, to charge the OOP disadvantage and deny realization).
- **4-bet:** conventionally ~2.2–2.5× the 3-bet (convention, not solver-pinned). **5-bet:** all-in at 100bb.
- Sizes are **stakes/format-calibrated, not per-hand-strength varied** — the same size covers the whole range at that node (anti-tell, §3.5).

## 4.6 Stack depth & effective stacks

> [!note] In plain terms
> The number that matters is the smaller of the two stacks (the "effective stack") — that's the most you can win or lose. Deeper stacks reward speculative, implied-odds hands (small pairs, suited connectors that make big disguised hands); shorter stacks reward raw high-card strength and simplify toward all-in decisions. Depth quietly reshapes every range.

- **Effective stack** = min of the players' stacks; it caps the pot and sets postflop **SPR** (§5.6).
- **Deeper (150bb+):** implied odds grow → set-mining and suited connectors gain; big pairs lose relative value (harder to stack off safely).
- **Shorter (≤40bb):** high-card equity and pairs dominate; play compresses toward push/fold and 3-bet-shove dynamics.
- The poker-coach app fixes **100bb** — the canonical, most-studied depth — so depth is a constant there (a legitimate scope simplification).

## 4.7 Multiway preflop adjustments

> [!note] In plain terms
> When several players are in, hands that make the pure nuts (sets, straights, flushes) go up in value and hands that just make a pair go down — someone is more likely to have something. So multiway you tighten, favor suited/connected hands with nut potential, and bluff less. This matters a lot in loose live games where pots are routinely multiway.

- More players → **value tightens** (a bare top pair is worth less; nutted/coordinated hands worth more) and **bluffing drops** (fold equity collapses as you must get through everyone).
- Suited, connected, nut-making hands **over-perform** multiway; offsuit high-card hands **under-perform**.
- Isolation raises (over limpers) exist to *reduce* the field and reclaim initiative.

---

# Part 5 — Postflop

> [!note] In plain terms
> Postflop is where ranges collide with a board and the money gets big. The core skill is reading how the community cards interact with each player's likely hands, then choosing to bet (for value or as a bluff), check, call, or fold. It's less standardized than preflop and where the biggest edges — and the poker-coach bots' biggest gaps — live.

## 5.1 Board texture

> [!note] In plain terms
> "Texture" is the personality of the flop: is it dry and safe (one high card, nothing coordinates) or wet and dangerous (cards that make straights and flushes likely)? Texture decides who has the advantage and therefore who should be betting and how big. Reading texture is the first postflop step.

- Axes: **dry vs wet** (how many draws/strong hands it makes), **connected** (straighty), **suitedness** (rainbow / two-tone / monotone), **paired**, **high vs low**, **static vs dynamic** (how likely the best hand changes by the river).
- **Dry, high boards** (A72r) favor the preflop **raiser** (range + nut advantage) → small, frequent c-bets. **Wet, low, connected boards** (T98ss) favor the **caller** → raiser checks more, polarizes when betting.
- Texture is read from board cards only (no hole-card info) — the correct routing signal for a strategy engine.

## 5.2 Hand-strength taxonomy

> [!note] In plain terms
> Postflop you sort your hand into a bucket: a made hand (pair, two pair, set, straight...), a draw (cards that could complete a strong hand), or air (nothing yet). But the bucket alone isn't enough — what matters is your equity *against the opponent's range on this specific board*, not the absolute rank. A "great" hand on one board is a bluff-catcher on another.

- **Made-hand ladder:** high card < weak/second pair < top pair (by kicker) < overpair < two pair < set/trips < straight < flush < full house+.
- **Draws:** gutshot (4 outs), OESD (8), flush draw (9), combo draws (12–15); classified by outs and nuttiness.
- **Critical correction:** absolute strength is a **proxy**, not the truth. The decision-relevant quantity is **equity vs the opponent's range** (§1.3) and **nuttiness** (a non-nut flush ≠ the nut flush). A ladder that treats all "monster" hands identically, or that ignores texture, is a documented simplification that loses information.

## 5.3 C-betting (flop continuation)

> [!note] In plain terms
> The preflop raiser usually keeps the lead by betting the flop — a "c-bet." On boards you own, you bet small with almost everything to deny equity cheaply; on boards that help the caller, you bet less often and bigger with a polarized range. Frequency and size both flex with texture, not with your specific hand.

- The preflop aggressor bets the flop at high frequency on **favorable** textures (range/nut advantage) using **small** sizing (⅓ pot), and at **lower** frequency, **larger/polarized** on unfavorable textures.
- IP vs OOP differs: IP can c-bet more often (position lets you realize); OOP checks more and uses a **check-raise** defense.
- Bluff c-bets prefer **backdoor equity + overcards** (hands that can barrel later) over pure air.

## 5.4 Turn & river play

> [!note] In plain terms
> The turn is where you decide whether to keep firing (barrel) — good barrel cards are ones that improve your range or scare theirs. The river is the moment of truth: you bet your best hands for value, pick bluffs using blockers, and defend against their bets using pot odds and MDF. Bets get bigger and mistakes get most expensive here.

- **Turn barreling:** continue betting on cards that **improve your range** or **hurt the caller's** (scare cards, cards completing your draws); check back / give up on bricks that favor the caller. Semi-bluffs are priced by their equity + fold equity (§2.3).
- **River value betting:** bet the hands that get called by worse; **thin value** requires the opponent to call with enough worse hands. No draws remain, so ranges are at their most defined.
- **River bluffing:** pure bluffs now (no equity) — selected by **blockers** (§3.8) and sized to hit the target bluff:value ratio (§3.3).
- **River bluff-catching:** call/fold using pot odds and **MDF** vs the bettor's size and range; the decision is "how many bluffs does their range contain vs the price?" — explicitly **price-dependent**.

## 5.5 Facing bets: continue, fold, raise

> [!note] In plain terms
> When you face a bet, three numbers decide your move: the price (pot odds), how much of your range you must keep (MDF), and your equity against what they'd bet. Strong hands and good draws can raise; medium hands call at the right price; weak hands fold — and how often you fold *must* shift with the size of their bet. A player whose folding ignores bet size is exploitable.

- **Continue vs fold:** call when (realized) equity ≥ pot-odds break-even (§2.1); defend at least MDF (§3.2) vs a balanced bettor.
- **Raise:** with strong value (for value) and select semi-bluffs/blockers (fold equity + equity); raising caps your calling range, so it must be balanced.
- **The size-response requirement:** because break-even equity and MDF both move with bet size, correct defense frequency is a **function of the price**. Folding at a fixed rate regardless of bet size is a first-order error (this is exactly one of the poker-coach engine's flagged gaps).

## 5.6 Stack-to-pot ratio (SPR) & commitment

> [!note] In plain terms
> SPR is the size of the stacks compared to the pot at the start of a street — it tells you how committed you are. Low SPR means the pot is already big relative to what's left, so you get the money in with fairly ordinary strong hands; high SPR means you need a much better hand to stack off. But — and this is the common trap — low SPR does **not** mean "never fold"; it means the *equity you need* to continue drops, not that it vanishes.

- **SPR = effective stack / pot**, measured at the start of the street.
- **Low SPR (≤ ~3):** you're committed with **top-pair-good-kicker / overpairs+**; get it in. **High SPR (>10):** you need **sets/strong two-pair+** to stack off.
- **Correct framing (Miller/Flynn/Mehta):** SPR sets the **equity threshold** required to commit — low SPR *lowers* that threshold (price-driven). It does **not** create an automatic "pot-committed, never fold" state; that's the "pot-committed fallacy." A rule that zeroes all folding below an SPR threshold, regardless of range/board/opponents, overstates commitment.

## 5.7 Multiway postflop

> [!note] In plain terms
> With three or more players seeing a flop, someone connects far more often, so you bluff much less and value bet more selectively. The clean two-player math (MDF, bluff ratios) no longer strictly applies because defense is shared across several opponents. Loose live games are full of these spots, so a realistic bot must handle them, not pretend they're heads-up.

- Bluffing frequency **drops sharply** vs each added opponent (fold equity must survive *everyone*); c-bet frequency roughly **halves** from heads-up to 3-way (approximate solver aggregate, ~70%→35% — a rule of thumb, not a solved constant; see the Modeling note).
- Value betting **tightens** (more players → more likely someone has a real hand) and thins less.
- MDF is **distributed** across defenders — no single player must meet the heads-up MDF; collective defense matters. There is **no unique solved answer** multiway (§3.1), so this is principled heuristic.

## 5.8 Postflop equity realization

> [!note] In plain terms
> The same realization idea from preflop keeps operating: position and having the betting lead let you cash in more of your equity after the flop too. A draw in position is worth more than the identical draw out of position, because you'll get to see more cards and bluff more credibly. It quietly tilts close calls.

- IP + initiative → **R > 1** (barrel, control pot, realize draws); OOP + no initiative → **R < 1** (get barreled off).
- This is why identical raw-equity spots resolve differently by position, and why "just compare equity to pot odds" is incomplete without R.

---

# Part 6 — Opponent modeling & exploitation

> [!note] In plain terms
> GTO assumes a perfect opponent. Real opponents are flawed in patterned ways, and the biggest money in poker comes from spotting the pattern and deviating to punish it. This section is about naming the common player types, measuring them with stats, and adjusting — and it's the layer most relevant to modeling *personality-driven bots*, because a persona IS a set of deviations from GTO.

## 6.1 Player-type taxonomy

> [!note] In plain terms
> Players cluster into a handful of recognizable types based on two dials: how many hands they play (loose vs tight) and how aggressively they bet (aggressive vs passive). A "TAG" is tight-aggressive, a "calling station" is loose-passive, a "maniac" is hyper-aggressive, and so on. Naming the type tells you their likely leak before you've seen a single showdown.

- Two axes: **loose↔tight** (how many hands played) and **aggressive↔passive** (bet/raise vs call/check).
- **Nit** (very tight-passive): plays few hands, rarely bluffs, over-folds — but their big bets are the nuts.
- **TAG** (tight-aggressive): the winning baseline — selective hands, aggressive with them.
- **LAG** (loose-aggressive): many hands, high pressure; hard to play against, higher variance.
- **Calling station** (loose-passive): calls far too much, rarely raises, hates folding.
- **Passive fish** (loose-passive): plays many hands, limps/calls, low aggression.
- **Maniac** (hyper-loose-aggressive): raises/re-raises constantly, over-bluffs, spews.

## 6.2 Population stats (how types are measured)

> [!note] In plain terms
> Tracking software summarizes a player in a few numbers: how often they voluntarily put money in (VPIP), how often they raise preflop (PFR), how aggressive they are after the flop (AF), and how often they go to showdown (WTSD). These stats are how you objectively assign someone a type — and how you'd measure whether a bot is behaving like the type it claims to be.

- **VPIP** — % of hands they voluntarily put money in preflop (looseness).
- **PFR** — % they raise preflop (preflop aggression). The **VPIP−PFR gap** signals passivity (big gap = lots of calling/limping).
- **3-bet %** — preflop re-raise frequency.
- **AF** (aggression factor) = (bets + raises) / calls — a ratio. **AFq** (aggression frequency) = (bets + raises) / (bets + raises + calls + folds) × 100 — the % of postflop actions that are aggressive (per Upswing; distinct from the AF ratio, and the two are often conflated).
- **WTSD** — went-to-showdown %; **W$SD** — won money at showdown %.
- **Fold-to-c-bet**, **c-bet %** — flop tendencies.
- **Representative 6-max profiles** (VPIP/PFR/AF, approximate): **nit ~12/10/low**, **TAG ~20/17/2–3**, **LAG ~28/23/high**, **calling station ~40+/low PFR/AF<1**, **maniac ~50+/very high/very high**, **passive fish ~40/low/low**. Full-ring runs a few points tighter. These are population estimates, not solved values.

## 6.3 Exploitative adjustments

> [!note] In plain terms
> Once you know the type, you tilt your play to attack their specific mistake. Against someone who never folds, stop bluffing and bet your good hands bigger. Against someone who folds too much, bluff relentlessly. Against a wild aggressor, stop bluffing and just call down with decent hands and let them hang themselves. Each leak has a direct counter.

- **vs calling station / passive fish:** **stop bluffing**, **value bet thinner and bigger** (they pay off), isolate them, never try to fold them out.
- **vs nit:** **steal/bluff more** (they over-fold), but **respect their aggression** (fold marginal hands to their raises — their bets are real).
- **vs maniac:** **stop bluffing**, **call down lighter / bluff-catch wider**, **trap** with strong hands and let them barrel into you; tighten your own bluffs to near zero.
- **vs LAG:** **3-bet/4-bet back** and don't over-fold; deny their fold equity by continuing more.
- **General principle:** exploit = deviate toward **argmax EV** given the opponent's *actual* (non-equilibrium) frequencies. The cost is you become exploitable yourself — fine vs a non-adapting opponent, dangerous vs a thinker.

## 6.4 Modeling an opponent as a range + strategy

> [!note] In plain terms
> To reason precisely, you turn "he's a station" into numbers: a set of hands he'd play and how often he takes each action with them. That lets you compute the right response mathematically instead of by feel. It's also exactly what a persona-driven bot *is* — a range plus a set of action frequencies.

- An opponent model = a **starting range** (which combos) + a **strategy** (action frequencies per hand per node), often inferred from their stats.
- Given that model, your best response is the **EV-maximizing** action against their frequencies (§2.2) — this is the formal version of "exploitation."
- A **persona bot** is literally this object: a range + frequency vectors deliberately skewed to embody a type's leaks.

## 6.5 Range estimation & Bayesian narrowing

> [!note] In plain terms
> As the hand unfolds, each action the opponent takes is a clue that narrows the set of hands they can still have. If a tight player 4-bets, you cross off everything except monsters. The formal tool is Bayes' rule: start with their likely hands, then reweight by how likely each hand is to have taken the action you just saw. Do this street by street and their range sharpens into focus.

- **Bayes:** P(hand | action) ∝ P(action | hand) × P(hand). Start with the preflop **prior** range; multiply each combo by the **likelihood** their strategy takes the observed action with it; **renormalize**.
- Apply **street by street**, folding in **card removal** (board + your cards) at each step; the range narrows as more actions accrue.
- Accuracy depends on the assumed strategy (P(action|hand)) — against a known type, use that type's frequencies; this is where opponent modeling and range reading merge.
- (The poker-coach app already does a card-free version of this to display an estimated villain range.)

---

# Part 7 — From theory to a bot

> [!note] In plain terms
> This section bridges the math to code: how you actually represent a strategy inside a program, the trade-off between "look it up in a solver table" and "approximate it with rules," and — crucially — how you prove the bot behaves correctly after you build it. This is the part that turns the rest of the document into a testable engineering spec.

## 7.1 Representing a strategy

> [!note] In plain terms
> Inside the software, a strategy is a table that says, for each situation and each possible hand, the probability of each action. The bot then rolls dice against those probabilities. Storing frequencies (not single decisions) is what lets the bot mix — the fingerprint of good play from §3.4.

- A strategy is a **map: (information set) → (probability distribution over legal actions)**, where an information set = everything the actor knows (their cards, position, action history, board).
- Actions are **sampled** from the distribution (categorical draw), with a seeded RNG for reproducibility — never argmax (§3.4).
- Sizing is drawn from a **size distribution** per node, ideally **decoupled from hand strength** so the size doesn't leak information (§3.5).

## 7.2 Heuristic vs solver-based engines

> [!note] In plain terms
> There are two ways to give a bot its strategy: bake in a solver's exact answers (accurate but huge, rigid, and only as good as the pre-computed spots), or use rules-of-thumb that approximate the theory (flexible, cheap, explainable, but not exact). A beginner trainer often deliberately chooses the heuristic route and labels its numbers "approximate" — which is a legitimate trade-off *as long as the heuristics respect the first-order math* (pot odds, MDF, size-scaled bluffing).

- **Solver-based:** store/query equilibrium strategies — most accurate, but large, node-specific, and brittle outside precomputed spots; no "personality."
- **Heuristic:** hand-authored rules approximating theory — interpretable, fast, tunable into personas, but only as correct as the rules encode. **The danger:** heuristics that omit a first-order law (e.g. defense that ignores price, bluffing that ignores size) are not "simplified GTO," they are **wrong** — the simplification excuse doesn't cover a missing fundamental.
- **Hybrid:** heuristic frequencies whose *targets* are pinned to solver/theory numbers (MDF, bluff:value by size) — "simplified but defensible."

## 7.3 Calibration & validation (proving it's right)

> [!note] In plain terms
> After building the bot, you must show it actually behaves correctly — not just that the code runs. The gold standard is to simulate many hands and check the bot's measured stats and decision frequencies against the theory numbers in this document (does it fold ~50% to a pot-size bet? does it bluff more when it bets bigger?). Tests that only lock in the current behavior prove consistency, not correctness — you need tests anchored to theory.

- **Behavioral calibration:** simulate N hands and measure VPIP/PFR/3-bet/AF/WTSD/fold-to-c-bet against **theory- or population-anchored bands** (§6.2). Passing = the bot embodies its type.
- **Decision-frequency checks (the correctness bar):** assert against the derivable numbers — e.g. defense frequency ≈ MDF for the faced size (§3.2); bluff share rises with bet size toward §3.3; commitment follows SPR equity thresholds not a fold-cliff (§5.6).
- **Engine-anchored vs theory-anchored tests:** a test that pins *current output* catches regressions but **cannot detect an inaccurate model** — it will happily lock in a wrong number. Correctness requires at least some **theory-anchored** acceptance checks with a cited target.
- **Statistical rigor:** use adequate sample sizes and tolerance bands (e.g. 3σ binomial) so calibration isn't fooled by variance.

---

# Part 8 — Glossary & formula sheet

> [!note] In plain terms
> A quick-reference for the terms and the handful of formulas that do the heavy lifting. If you remember nothing else, remember pot odds, EV, and MDF — the rest hangs off those three.

## Formula sheet

- **Combos:** pair 6 · suited 4 · offsuit 12 · unpaired total 16. Deck = C(52,2) = 1326.
- **Outs→equity:** ≈ outs×2 (one card), outs×4 (two cards).
- **Pot-odds break-even to call B into pot P:** **B / (P + 2B)**.
- **EV(call)** = equity × final pot − call. **EV(fold)** = 0.
- **EV(bet)** = f·P + (1−f)·[equity_called·(P+2B) − B].
- **Break-even bluff (pure):** fold freq > **B / (P + B)**  = **alpha**.
- **MDF** = **P / (P + B)**; **alpha** = **B / (P + B)**.
- **Polar river bluff fraction** = **f / (1 + 2f)**; **value:bluff** = **(1+f):f** (f = bet/pot).
- **SPR** = effective stack / pot; low SPR lowers the commitment equity threshold (not a fold-cliff).
- **Realized equity** ≈ raw equity × R (R>1 IP/initiative, R<1 OOP/no initiative).

## Glossary

- **Equity:** share of the pot you'd win on average now.
- **Range:** the set of hands (with frequencies) a player can have here.
- **Polarized / linear / condensed:** nuts-or-air / top-X%-no-air / medium-heavy range shapes.
- **MDF / alpha:** min you must defend / max you may fold vs a bet.
- **SPR:** stack-to-pot ratio; commitment gauge.
- **VPIP/PFR/AF/WTSD:** looseness / preflop aggression / postflop aggression / showdown frequency.
- **Blocker:** a card you hold that removes combos from the opponent's range.
- **Realization (R):** fraction of raw equity you actually collect.
- **CFR:** counterfactual regret minimization, the solver algorithm.
- **IP / OOP:** in position / out of position.

---

## Appendix — scope notes & known simplifications

> [!note] In plain terms
> Honesty about the edges: what this document deliberately leaves out or approximates, so no one mistakes a simplification for a solved fact.

- **Cash, ~100bb:** tournament **ICM** (chip-value ≠ money-value near payouts) is out of scope; it changes calling/shoving ranges materially near the bubble.
- **No rake modeling:** real rake tightens marginal opens/calls slightly.
- **Multiway = heuristic:** 3+ players have no unique equilibrium; all multiway numbers are principled rules of thumb.
- **Representative ranges:** RFI %s, stat profiles, and bluff ratios are canonical/approximate, not solver-exact for a specific sizing tree.
- **Live vs online:** live $2/$3 uses bigger sizes, more limping, more multiway — reflected where noted.

