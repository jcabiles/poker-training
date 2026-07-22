# Push/Fold and Shove-EV — Poker Math Calibration Research

Scope: short-stack all-in decisions (NLHE). Prepared as input to a poker-math calibration spec. App context: 100bb cash game, so tournament/ICM material is flagged as beyond current scope.

---

## 1. The shove-EV / all-in EV formula

**[SOLVED/derivable]** The standard two-branch EV formula for an all-in shove (or any bet with fold equity) is:

```
EV(shove) = F × Pot + (1 − F) × [Equity_called × FinalPot − Risk]
```

Where:
- **F** = probability villain folds (fold equity/frequency)
- **Pot** = the pot *before* your shove (what you win outright if villain folds)
- **Equity_called** = your all-in equity (% to win at showdown) when called
- **FinalPot** = total pot after both the effective-stack shove is called (Pot + your shove + villain's call, i.e., pot + 2× the shove amount when stacks are equal, or pot + your bet + villain's call in general)
- **Risk** = the amount you risk by shoving that you weren't already committing (typically the shove size itself, or the incremental amount beyond a previous bet/blind already in the pot)

This is algebraically identical to the more granular form seen in fold-equity literature:

```
EV = F × P + (1 − F) × [E × (P + B) − (1 − E) × B]
```

with P = pot before the bet, B = bet/shove size, E = equity when called. Expanding the called branch: `E × (P+B) − (1−E) × B` = (your equity share of the final pot) − (expected loss of your own bet when it doesn't win) — this is the same "equity_called × final_pot − risk" structure, just with the risk term implicit in how the E×(P+B) and (1−E)×B pieces net out. **[SOURCED estimate]** This formulation (F, P, B/risk, E as the four inputs) is corroborated across multiple independent poker-math explainers, not one canonical academic source — see Sources below (thepokerbank.com, Wikipedia "Fold equity" article, and general EV/fold-equity explainers). All converge on the same four-variable structure; none diverge on the underlying algebra.

**[SOLVED/derivable] Break-even fold frequency** (the minimum fold% needed for a zero-equity bluff shove to be profitable):

```
F_breakeven = Risk / (Pot + Risk)
```

i.e., if your shove risks B into a pot P, you need villain to fold at least B/(P+B) of the time to show an *immediate* profit even with 0% equity when called. Any additional showdown equity when called only adds further profit on top of this floor. This is a standard, uncontroversial derivation (set the "called" branch to its worst case, E=0, and solve for F such that EV ≥ 0).

**Worked numeric example [SOURCED estimate]**, from thepokerbank.com: hero shoves with hand equity 42.4% when called, opponent folds an estimated 50% of the time (so opponent's equity when called is 57.6%). Fold equity contribution = 0.5 × 57.6% = 28.8%. Total effective equity = 42.4% + 28.8% = 71.2%, converting a hand that's a slight underdog at showdown into a clearly profitable shove once fold equity is added. Note this "fold equity as an equity add-on" framing (Fold Equity = F × opponent's_equity) is a simplified percentage-space shortcut, not the dollar-EV formula above — useful for intuition but the Pot/Risk-denominated formula above is what should be implemented for actual $EV calculations.

---

## 2. Nash push/fold theory: stack-depth threshold and range widening

**[SOURCED estimate] Threshold for push/fold becoming the correct framework:** Commonly cited as **~15bb and below**, with a stricter/purer form below ~10bb:
- HoldemResources.net (HRC/HUNE calculator) frames push/fold as viable up to 20bb but notes "playing push-or-fold for >20bb is almost certainly a bad idea," with practical application concentrated around 10bb or less.
- Upswing Poker: "Push/fold should be utilized when your stack becomes short — around 15 big blinds (bb) or fewer."
- deepfold.co push/fold guide: "Below 15BB, your options simplify to shove or fold. Between 10–15BB you may still min-raise some hands (especially with antes), but below 10BB, it's pure push/fold for most positions."
- Multiple sources converge: **15-20bb is the outer boundary where push/fold starts becoming relevant; below ~10bb it dominates as close to the only profitable preflop framework**, especially heads-up/short-handed.

**[SOLVED/derivable]** Nash equilibrium push/fold ranges are computed by treating each preflop spot as a shove-or-fold / call-or-fold game and solving for the mutual best response (unexploitable strategy) — i.e., a strategy pair where the shover's range and the caller's range are simultaneously optimal against each other, so neither side can improve EV by deviating unilaterally. This is standard two-player zero-sum game-theory equilibrium computation, not a heuristic; the "Nash" label is used loosely by the poker community for this class of solved push/fold games (technically closer to a Nash equilibrium of a simplified push/fold-only game tree, since real poker allows more actions than "push or fold").

### Range widening as stacks shorten — representative widths

**[SOURCED estimate]**, from deepfold.co's push/fold guide (cross-referenced conceptually against HRC/Upswing methodology, though exact hand-by-hand combos should be verified against a live HRC/ICMIZER run before being hard-coded into the app):

**At 10bb effective:**
| Position | Approx. shove range | Example hands |
|---|---|---|
| UTG | ~12% | 66+, ATs+, AJo+ |
| BTN | ~40% | 22+, A2s+, A5o+, K5s+, K8o+, Q8s+, QTo+, J9s+, T9s |
| SB (vs BB, effectively heads-up) | ~50% | 22+, A2s+, A2o+, K2s+, K5o+, Q5s+, Q8o+, J7s+, T8s+ |

**At 15bb effective:**
| Position | Approx. shove range | Example hands |
|---|---|---|
| UTG | ~7% | 88+, AQ+ |
| BTN | ~22% | 22+, A2s+, A8o+, KTs+, QJs |
| SB | ~32% | 22+, A2s+, A2o+, K7s+, KTo+ |

**[SOURCED estimate]**, cross-check from Upswing Poker's 2026 analysis (which layers in min-raise as a third option alongside push/fold, so these numbers are the *combined* raise+shove range, not pure push/fold — flagged explicitly):
- At 10bb: UTG ≈ 16.1% combined (7.6% min-raise + 8.5% all-in); BTN ≈ 38.4% combined (9.1% min-raise + 29.3% all-in); SB ≈ 75.2% combined (4% min-raise + 54.3% all-in + 16.9% call-vs-shove-behind... note SB numbers here include facing action, so not directly comparable to a pure open-shove %).
- At 15bb: UTG ≈ 14.8%, BTN ≈ 38.9% (combined raise+shove).

**[SOURCED estimate]** Heads-up specific (HRC's HUNE — Heads-Up Nash Equilibrium calculator): covers effective stacks from 1bb to 200bb in 0.05bb increments, though the simplified public chart caps display at 20bb. Below roughly 10bb heads-up, push/fold is characterized by several sources as essentially the *only* profitable preflop strategy for the SB (small blind acts first heads-up and is the natural shover).

**Directional takeaway [SOLVED/derivable from game theory]:** as effective stack shrinks, (a) fold equity becomes a larger fraction of total pot relative to stack size, and (b) villain's optimal calling range must widen to defend against a wider shoving range (otherwise the shover can profitably shove any two cards) — this mutual widening is the equilibrium mechanism, not an empirical curiosity. The exact percentages above are equilibrium *outputs*, not something to re-derive from first principles for the app; they must come from a solver run (HRC/ICMIZER) or a validated chart if the app ever hard-codes push/fold ranges.

---

## 3. Canonical push/fold chart sources and how they're derived

**[SOURCED estimate]** All three tools solve the same underlying problem — a simplified push-or-fold (and call-or-fold) game tree — for a Nash/unexploitable equilibrium, differing mainly in scope (cash/chip-EV vs. ICM-aware) and UX:

- **SnapShove** (snapshove.com) — "an interactive push or fold chart that employs Nash equilibriums... ranges were calculated in over 1,000,000 unique game simulations... based on a perfect ChipEV Nash Equilibrium solution." Explicitly **chip-EV only, not ICM-aware** — a documented limitation: it doesn't account for tournament payout structure, so it's best treated as a chip-EV (cash-equivalent) reference even though it's marketed for tournament use. Built by Max Silver and team.
- **HoldemResources Calculator (HRC)** / **HoldemResources.net HUNE tool** — solves heads-up push-or-fold Nash equilibrium (SB can only shove-or-fold; BB can only call-or-fold facing a shove) across effective stacks 1bb–200bb in 0.05bb increments. Notes many hands require *mixed strategies* (not pure push/fold) across specific stack-depth windows — i.e., equilibrium play sometimes means shoving hand X only some % of the time at a given stack depth, with "gaps" where the correct frequency changes non-monotonically. HRC (the broader calculator product) is also used for full ICM/FGS (Future Game Simulation) push/fold analysis in MTTs.
- **ICMIZER** (icmizer.com) — "the engine at the heart of ICMIZER solves for the Nash equilibrium of an all-in spot. You enter the stacks, blinds, antes, and payouts, and it returns the unexploitable push, call, and fold ranges for every seat." Layers a **Future Game Simulation (FGS)** model on top of basic ICM — basic ICM treats the tournament as ending immediately at the current hand, FGS looks ahead across upcoming blind/ante levels for a more realistic long-run push/fold recommendation.

**[SOLVED/derivable]** Common derivation logic across all three: given effective stacks, blinds/antes, and (for ICM tools) payout structure, the solver iterates shove/call ranges for each seat until neither side can improve their EV (chip-EV or $EV via ICM) by unilaterally deviating — the fixed point is the Nash/unexploitable range pair. This is a well-defined, deterministic computation (not a heuristic or approximation), though runtime tools differ in whether they solve chip-EV (SnapShove, HRC base mode) or ICM-adjusted $EV (ICMIZER, HRC with ICM/FGS enabled).

---

## 4. Cash push/fold (cEV) vs. tournament push/fold (ICM) — beyond current scope

**Flag: this section is included for completeness only. The app is 100bb cash, so short-stack push/fold (a <20bb phenomenon) and ICM (a tournament-only concept — cash games have no elimination/payout-jump structure) are both out of scope for the current spec.**

**[SOURCED estimate]**
- **Cash push/fold** is rare in practice because cash-game stacks are normally re-buyable/toppable to 100bb; when it does occur (e.g., a player is temporarily short after losing a big pot), the correct framework is **pure chip-EV (cEV)** — every chip risked and won has constant real-money value, so there is no ICM distortion. SnapShove's underlying chip-EV Nash solve is actually the *more directly applicable* tool for a cash-game short-stack shove than an ICM tool would be, per the sources above.
- **Tournament push/fold** requires **ICM adjustment**: because tournament chips are not linearly convertible to real money (survival and pay-jump proximity carry extra value beyond raw chip count), the correct shove/call range is *tighter* than the equivalent cEV range, especially near the money bubble or a pay jump. **[SOURCED estimate]** Example cited: a chip-EV model might shove ATo as a clear +cEV play from UTG at 4bb, while an ICM-aware model (25% remaining field) shoves a narrower range (28.2% vs. 30.3% of hands in one cited comparison) because busting forfeits a near-locked min-cash. Deepfold.co's guide states ICM-tightened ranges can run "10–25% tighter than Nash [cEV] on the bubble."
- **Practical implication for this app**: since the app models 100bb cash, neither the <20bb push/fold regime nor ICM adjustment is currently relevant. If a future slice adds short-stack cash simulation (e.g., a player down to 15bb after a big pot in a cash session), the correct reference framework is **cEV push/fold** (SnapShove/HRC chip-EV mode), *not* ICM — ICM should only enter if/when a tournament mode is ever built, which is explicitly a non-goal per the current roadmap (`docs/ai-dlc/roadmap/professional-teacher-rework.md` lists "no solver tables" and the app scope as cash-focused).

---

## Sources

- [Fold Equity | thepokerbank.com](https://www.thepokerbank.com/strategy/mathematics/equity/fold/) — fold equity formula, worked example
- [Fold equity — Wikipedia](https://en.wikipedia.org/wiki/Fold_equity) — fold equity definition and formula framing
- [HeadsUp Push/Fold Nash Equilibrium — HoldemResources.net](https://www.holdemresources.net/hune) — HUNE calculator methodology, 1–200bb range, mixed-strategy notes
- [10 Push Fold Charts for Poker Tournaments — Upswing Poker](https://upswingpoker.com/push-fold-tournament-strategy-charts/) — 15bb threshold quote, 10bb/15bb combined raise+shove range percentages by position
- [Push/Fold Complete Guide: Nash Charts, ICM Adjustments, MTT Late-Stage Play — deepfold.co](https://deepfold.co/en/blog/push-fold-complete-guide) — 10bb/15bb range tables by position, cEV vs ICM distinction, 10–25% ICM tightening claim
- [SnapShove — Home](https://www.snapshove.com/) — chip-EV Nash equilibrium methodology, 1,000,000+ simulations claim
- [SnapShove — ICM Calculator](https://www.snapshove.com/app/icm-calculator/) — SnapShove's separate ICM tool offering
- [ICMIZER 3 — Poker ICM Calculator & Nash Calculator](https://www.icmizer.com/icmizerapp/) — ICMIZER product page
- [ICMIZER: ICM/FGS Nash Calculator Features & Capabilities](https://www.icmizer.com/icmizer/icmizer-features/) — Nash equilibrium solve description, FGS (Future Game Simulation) model
- [Short-Stacked Play in MTTs — GTO Wizard blog](https://blog.gtowizard.com/short-stacked-play-in-mtts/) — general short-stack context (background reading, not directly quoted above)

## Unsourced / flagged for follow-up

- The exact hand-combo push/fold ranges in the 10bb/15bb tables (Section 2) are traced to a single secondary source (deepfold.co) rather than a direct HRC/ICMIZER/SnapShove chart pull. They are internally consistent and directionally corroborated by Upswing's independent numbers, but **should be re-verified against a live HRC or ICMIZER solver run before being encoded as ground-truth data** in any calibration test, since exact combos are sensitive to ante structure and exact stack depth (solvers report at 0.05bb–1bb granularity, and "10bb" / "15bb" round numbers in secondary sources may already be interpolated/simplified).
- Could not access pokerstrategy.com's Nash ranges page directly (HTTP 403) — relied on secondary aggregation instead. Modern Poker Theory (Acevedo) was not directly fetchable via web search/fetch in this pass; no claims in this doc are attributed to it despite being named as a candidate source.
