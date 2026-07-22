# Sol Findings

## Verdict

The core algebra is mostly correct: pot odds, MDF/alpha, pure-bluff break-even, polar river bluff share, combinatorics, rule-of-2-and-4, and the multiway fold-root arithmetic all recompute cleanly. The documents are weakest where they turn clean toy-game formulas into calibration targets. The largest risk is that the bot/grader could treat MDF, polar bluff ratios, and illustrative solver/population numbers as broadly prescriptive when their assumptions are narrow. I found no arithmetic-breaking error in the main tables, but several labeling and applicability issues that could still mis-calibrate a training engine.

## CRITICAL Errors

### 1. `01 §3.2`, `02 §1` — MDF is over-labeled as a defense “floor”

**Claim:**  
“MDF is the floor” and “continue with ≥ MDF vs a balanced bettor.”

**Why shaky/wrong:**  
MDF is a toy-game indifference threshold for preventing a bettor from profitably bluffing any two cards with a single bet size, assuming no future-street realization effects, no raises changing EV, no rake, and a betting range capable of sustaining the relevant bluffs/value. In real NLHE nodes, especially flop/turn, OOP, multi-street, rake-influenced, or range-disadvantaged spots, solver defense can be below or above naive MDF.

The docs do include caveats, but still repeatedly phrase MDF as a minimum continue requirement. That is dangerous for hero grading: grading a fold as wrong simply because it falls below MDF can be wrong when the bettor is under-bluffing, range advantage is severe, realization is poor, or the node is not a river bluff-catcher game.

**Correct statement:**  
MDF is a baseline anti-auto-profit benchmark for a one-street bet. Use it as a sanity check for price sensitivity, not as a universal minimum defense target. For actual bot/grader decisions, compare range equity, realization, raising options, future-street EV, rake, and opponent strategy.

**Source(s):**  
GTO Wizard glossary and strategy articles on MDF/defense frequency: https://blog.gtowizard.com/  
SplitSuit MDF explainer: https://www.splitsuit.com/poker-mdf-minimum-defense-frequency  
Janda, *Applications of No-Limit Hold’em*; Tipton, *Expert Heads Up No-Limit Hold’em*

**Confidence:** High

### 2. `01 §3.1`, `01 §3.9`, `03 abstract/§3` — “multiway has no unique equilibrium” is overstated

**Claim:**  
“Multiway pots have no unique game-theoretic solution,” “no unique equilibrium,” and “there is provably no unique optimal strategy.”

**Why shaky/wrong:**  
The statement is directionally useful but technically too broad. Finite multi-player games do have Nash equilibria. They may have multiple equilibria, equilibrium strategies may not be interchangeable, and Nash equilibrium loses the two-player zero-sum minimax guarantee. But saying there is “no unique game-theoretic solution” or “provably no unique optimal strategy” as a blanket rule overstates what Pluribus/Brown-Sandholm prove and may mislead readers into thinking multiway GTO is undefined rather than less clean and less practically canonical.

**Correct statement:**  
Multi-player poker has Nash equilibria, but unlike two-player zero-sum poker, equilibria need not be unique, equilibrium play does not provide the same minimax unexploitable guarantee, and practical multiway poker does not have a single canonical solver answer for app calibration.

**Source(s):**  
Brown & Sandholm, Pluribus, *Science* 2019: https://www.science.org/doi/10.1126/science.aay2400  
General Nash existence: https://en.wikipedia.org/wiki/Nash_equilibrium

**Confidence:** High

### 3. `02 §9`, `03 §3` — multiway n-th-root defense is correct only for symmetric independent fold targets, not real defense obligations

**Claim:**  
“Each opponent’s fold ceiling scales as the n-th root of α, meaning each opponent individually defends less than heads-up.”

**Arithmetic check:**  
For half-pot bluff: α = B/(P+B) = 0.5/1.5 = 0.3333.  
Two opponents: each fold rate if symmetric independent = sqrt(0.3333) = 0.57735.  
Each continue rate = 42.26%.  
Combined folds = 0.57735² = 0.3333. Arithmetic is correct.

**Why shaky/wrong:**  
The arithmetic answers: “If each opponent folds independently at the same rate, what per-player fold frequency gives the bettor the same immediate pure-bluff break-even?” It does not establish that each player’s GTO defense requirement is 42%, because multiway ranges are not symmetric, actions are sequential, players can raise, card removal matters, equities differ, and callers behind change the EV of continuing.

**Correct statement:**  
The n-th-root formula is an immediate fold-equity toy model for symmetric independent defenders. It is valid as a warning that fold equity collapses multiway, but not as a per-player MDF target.

**Source(s):**  
Brown & Sandholm, Pluribus: https://www.science.org/doi/10.1126/science.aay2400  
GTO Wizard multiway Nash discussion: https://blog.gtowizard.com/

**Confidence:** High

## MODERATE Issues

### 4. `02 §3`, `02 §7` — shove/bet EV notation is inconsistent

**Claim:**  
`Shove/bet EV = F·P + (1−F)·[E·(P+B) − (1−E)·B]`

**Check:**  
This expression simplifies to `F·P + (1−F)·[E(P+2B) − B]`, which is correct if `P` is the pot before hero bets and `B` is hero’s risk matched by villain.

**Issue:**  
The notation differs from `01`, which uses `equity_when_called × (P + 2B) − B`. `02`’s `E·(P+B) − (1−E)·B` is correct but easier to misread as final pot missing villain’s call.

**Correct statement:**  
Prefer one notation everywhere:  
`EV(bet) = F·P + (1−F)·[E·(P+2B) − B]`.

**Confidence:** High

### 5. `01 §2.4`, `01 §3.2` — alpha is equated too casually with “villain’s maximum profitable fold frequency”

**Claim:**  
Alpha is “villain’s maximum profitable fold frequency” and the bettor’s break-even bluff frequency.

**Issue:**  
Alpha is the defender’s maximum fold frequency that prevents an immediate zero-equity bluff from auto-profiting. It is not “villain’s maximum profitable fold frequency” in all contexts. With equity when called, blockers, future streets, or range EV, bets can profit at lower fold rates; with poor equity or bad future realization, they may need more.

**Correct statement:**  
Alpha is the immediate break-even fold frequency for a zero-equity one-street bluff of size B into pot P.

**Confidence:** High

### 6. `01 §5.7`, `02 §5`, `03 §3` — “~70% → ~35% c-bet halving” is too weakly sourced for calibration

**Claim:**  
HU c-bet roughly halves from ~70% to ~35% in 3-way pots.

**Issue:**  
The docs label this as a rule of thumb and secondary aggregator, which is good. But it appears in multiple places and could become a target. It should not be used as a bot validation number. C-bet frequency depends heavily on positions, ranges, board, stack depth, bet-size tree, rake, and whether the aggressor is IP/OOP.

**Correct statement:**  
Use “multiway c-bet frequency decreases substantially” as the calibration principle. If a numeric target is needed, derive it from app-specific representative spots or keep a wide texture/position band.

**Source(s):**  
GTO Wizard c-bet/multiway materials: https://blog.gtowizard.com/  
Upswing Poker c-betting articles: https://upswingpoker.com/

**Confidence:** Medium-high

### 7. `01 §4.2` — “6-max equivalent seats run tighter” is unclear and potentially wrong

**Claim:**  
“In 6-max the equivalent seats run tighter — map by seats-behind, not by name.”

**Issue:**  
If mapping by seats behind, a 6-max HJ is effectively LJ/UTG in a 6-max table and is often comparable to 9-max LJ, not necessarily “tighter” than the equivalent seat. The phrase can confuse seat-name mapping versus functional-position mapping.

**Correct statement:**  
Compare positions by players left to act, not labels. A 6-max first-in seat is not equivalent to 9-max UTG; it is closer to a middle-position opening spot.

**Confidence:** Medium

### 8. `02 §6` — derived live rake cost `35–60 bb/100` is plausible but very assumption-sensitive

**Claim:**  
`bb/100 ≈ (30–40 raked hands/100 × $3.5–4.5 avg rake) / $3 = 35–60 bb/100`.

**Arithmetic check:**  
Low: 30 × 3.5 / 3 = 35 bb/100.  
High: 40 × 4.5 / 3 = 60 bb/100. Correct.

**Issue:**  
This measures table rake paid, not necessarily hero’s personal rake burden in bb/100 unless allocated evenly by participation or pots won. For player winrate modeling, rake paid is not uniformly distributed across all seated players; it is extracted from pots won and disproportionately affects loose players and small pots.

**Correct statement:**  
This is a table-level or seat-allocated order-of-magnitude estimate, not a direct individual rake bb/100 without specifying allocation method.

**Source(s):**  
Upswing rake impact: https://upswingpoker.com/rake-poker-strategy-adjustments/

**Confidence:** High

### 9. `01 §1.4`, `02 §2` — EQR examples are not calibration bands

**Claim:**  
OOP R ≈ 79%, IP R ≈ 118%, capped hand as low as ~2%, K9o raw 35% → realized 21%.

**Issue:**  
The docs mostly label these illustrative, but the section title “Equity realization bands” and app-calibration context may encourage hard-coding. EQR is highly hand/range/action/tree dependent. A single scalar `raw_equity × R` can be acceptable for a heuristic bot, but it is not ground-truth math.

**Correct statement:**  
Use EQR as a heuristic adjustment with wide, spot-dependent ranges. Validate only directionally unless the app defines a specific spot class.

**Source(s):**  
GTO Wizard EQR glossary: https://www.gtowizard.com/en/glossary/equity-realization-eqr/

**Confidence:** High

## MINOR / Nits

### 10. `01 §1.1` — “holding one ace cuts AK from 16→12” needs rank specificity

Correct if hero holds an ace and no king is blocked: AK combos become 3 aces × 4 kings = 12. If hero holds a king instead, also 12. If board/hand blocks both ranks, different.

**Confidence:** High

### 11. `01 §3.9` — practical solver “abstraction” wording is dated

PioSOLVER/GTO+ postflop solves generally use explicit bet-size trees and hand classes/card abstraction differently than large AI systems. “Solvers bucket similar hands/bets” is more true of large abstractions and older AI systems than ordinary postflop solver use.

**Confidence:** Medium

### 12. `01 §5.6` — SPR thresholds are useful but not universal

“Low SPR ≤3 commit TPGK/overpairs” and “high SPR >10 need sets/strong two-pair+” are standard SPR heuristics, but board texture, ranges, multiway status, and opponent type can override them. The docs caveat this well; keep it labeled heuristic.

**Confidence:** Medium-high

### 13. `03 §1` — player-type stat bands are defensible but not “published truth”

The VPIP/PFR bands are reasonable HUD/coaching approximations. AF labels like “high” and “very high” need numeric app targets if used for bot validation, but published sources vary enough that exact bands should remain fuzzy.

**Confidence:** Medium

## Could Not Refute

- `MDF = P/(P+B)` and `alpha = B/(P+B)` recompute correctly for the one-street bluff model.
- Pot-odds break-even to call `B/(P+2B)` is correct.
- Pure-bluff break-even fold frequency `B/(P+B)` is correct.
- Polar river bluff fraction `f/(1+2f)` and value:bluff `(1+f):f` are correct under the stated polar river assumptions.
- Validation table arithmetic in `02 §1` is correct: 1/3, 1/2, 2/3, 3/4, pot, and 2x values all check out.
- Combinatorics in `01 §1.1` and `02 §4` check out: 1326 total, pairs 6, suited 4, offsuit 12, KK+ 0.9%, QQ+/AK 2.6%, TT+/AQ+ 4.7%.
- Rule of 2-and-4 correction is correct: one-card ×2 slightly understates; two-card ×4 overstates increasingly beyond about 8 outs.
- Multiway fold-root arithmetic itself is correct; only its strategic interpretation needs tightening.
- Rake `35–60 bb/100` arithmetic is correct given the stated assumptions.

## Sources

- GTO Wizard glossary and strategy articles: https://www.gtowizard.com/en/glossary/ and https://blog.gtowizard.com/
- GTO Wizard EQR glossary: https://www.gtowizard.com/en/glossary/equity-realization-eqr/
- SplitSuit MDF: https://www.splitsuit.com/poker-mdf-minimum-defense-frequency
- Upswing Poker rake strategy: https://upswingpoker.com/rake-poker-strategy-adjustments/
- Upswing Poker strategy library: https://upswingpoker.com/
- Brown & Sandholm, Pluribus, *Science* 2019: https://www.science.org/doi/10.1126/science.aay2400
- Zinkevich et al., CFR paper: https://papers.nips.cc/paper_files/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- Bowling et al., heads-up limit Hold’em, *Science* 2015: https://www.science.org/doi/10.1126/science.1259433
- Matthew Janda, *Applications of No-Limit Hold’em*
- Will Tipton, *Expert Heads Up No-Limit Hold’em*
- Michael Acevedo, *Modern Poker Theory*
