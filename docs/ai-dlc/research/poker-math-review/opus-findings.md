# Opus Adversarial Review — Poker Math Docs

**Reviewer:** Fresh-context Opus refuter. **Date:** 2026-07-21.
**Targets:** `01-comprehensive-reference.md`, `02-calibration-spec.md`, `03-persona-multiway.md`.
**Method:** Every formula recomputed independently in Python; every disputable number checked against GTO Wizard, PokerTracker, Upswing, Brown & Sandholm, and the academic multiway literature. Arithmetic was *not* trusted — it was redone from scratch.

---

## 1. Verdict

These docs are unusually clean. **I could not find a single arithmetic error in any formula or worked example** — MDF, alpha, break-even-to-call, break-even-bluff, the polar river bluff fraction, the multiway n-th-root defense, the 3-bet combinatorics, the rake pot-fractions, and both EV/shove-EV formulations all recompute exactly, and the two algebraically-different EV forms in doc 02 §3 and §7 are in fact identical. The authoritative numbers I spot-checked (K9o 35%→21% at R≈60%; EQR 175% worked example; the ~70%→~35% multiway c-bet halving; risk-premium = ReqEq(ICM)−ReqEq(cEV) tournament-only; player-type VPIP/PFR bands) all match their cited sources. The labeling discipline (`[SOLVED]`/`[SOURCED]`/`[DERIVED-ASSUMPTION]`, "illustrative not constant") is honest and mostly correct. There are **no CRITICAL errors that would mis-calibrate bots or grading.** What remains are a handful of MODERATE conceptual-precision issues (chiefly: MDF is presented as a defense benchmark that *includes raising*, but the P/(P+B) formula it cites is the flat-call form and understates required defense once raising is allowed; and the multiway n-th-root model silently assumes independent, symmetric opponents) and some MINOR nits. The confidence chain in the brief largely holds.

---

## 2. CRITICAL errors (would mis-calibrate bots/grading)

**None found.** I specifically tried to break the price/frequency tables that will drive the Epic-4 recalibration (the whole point of the fix). They are correct to the decimal:

| Bet (×pot) | MDF | alpha | BE-call | My recompute | Doc |
|---|---|---|---|---|---|
| ⅓ | 75% | 25% | 20% | 75.00 / 25.00 / 20.00 | ✔ |
| ½ | 66.7% | 33.3% | 25% | 66.67 / 33.33 / 25.00 | ✔ |
| ⅔ | 60% | 40% | 28.6% | 60.00 / 40.00 / 28.57 | ✔ |
| ¾ | 57% | 43% | 30% | 57.14 / 42.86 / 30.00 | ✔ |
| pot | 50% | 50% | 33% | 50.00 / 50.00 / 33.33 | ✔ |
| 2× | 33% | 67% | 40% | 33.33 / 66.67 / 40.00 | ✔ |

Polar river bluff fraction f/(1+2f) and value:bluff (1+f):f recompute exactly (⅓→20%/4:1, ½→25%/3:1, ⅔→28.57%/2.5:1, pot→33.3%/2:1, 2×→40%/1.5:1). The size-scaling *direction* the Epic-4 fix depends on ("bluff frequency and defense both move with bet size; a flat rate is broken") is stated correctly and is the right target for the fix. **The docs give the RIGHT targets for the two confirmed bot bugs.**

---

## 3. MODERATE issues (mislabels, false precision, misapplied concepts)

### M1 — MDF formula P/(P+B) is presented as a "defend (call **+ raise**) ≥ X%" benchmark, but that formula is the flat-call form; it understates required defense once raising is on the table. — **confidence: med**
- **Where:** `01` §3.2 and §5.5; `02` §1 ("MDF = P/(P+B) … continue (call+raise) with ≥57% of range").
- **Claim:** MDF = P/(P+B) is the minimum fraction to *continue (call or raise)*.
- **Why it's shaky:** The GTO Wizard MDF/alpha article explicitly warns that P/(P+B) "doesn't work with a raise, it only works for an initial bet" — when a defender raises, the attacker's risk/reward changes and the simple pot/(pot+bet) ceiling no longer describes the indifference point. P/(P+B) is the fraction that makes a *pure-bluff, called-and-loses-the-whole-pot* bettor indifferent; it is a **call-frequency** benchmark. Labeling it "call+raise ≥57%" conflates two things. This does not change the *fold* ceiling (alpha) a bot should respect, so the practical bot target is still fine — but the grader should not treat "raised, so I've met MDF" as arithmetically equivalent to "called MDF%."
- **Correct statement:** MDF/alpha as P/(P+B) is the benchmark **against an initial bet, treating defense as calling**; raising is a *separate* strengthening of your defense whose math is not captured by this formula. Keep the alpha column as the fold-ceiling target (that's what the price-blind-defense bug needs); don't imply the same number governs raise-inclusive defense.
- **Source:** GTO Wizard, *MDF & Alpha* — https://blog.gtowizard.com/mdf-alpha/

### M2 — MDF assumes an *uncapped, any-two* betting range; the docs caveat this but still print MDF as the primary "defend ≥" number in the validation table used for grading. — **confidence: med**
- **Where:** `02` §1 validation table; `01` §3.2.
- **Claim:** "a bot's fold frequency should track the α column against a balanced bettor."
- **Why it's shaky:** This is *correct with the "balanced bettor" qualifier* — and the docs do add the capped-range caveat. But MDF is a **maximally-exploitative-prevention floor**, not a description of equilibrium defense. GTO Wizard's own material notes real solver defending ranges "often sit well below raw MDF" because bluffs carry equity and check-raise threats reshape the node, especially pre-river. For a *river* bluff-catch node vs a polarized bettor the correct tool is pot-odds indifference, not MDF — and the docs say this (`01` §3.2, §5.4), so this is a labeling-prominence risk, not an error. **Risk to watch:** if the grader hard-asserts "fold ≈ alpha" on flop/turn nodes, it will grade a theoretically-correct bot as wrong.
- **Correct statement:** Use alpha as the *fold-ceiling* sanity check (catches the price-blind bug). Do **not** assert equilibrium defense ≈ MDF on flop/turn or vs capped/polar bettors; use pot-odds-vs-actual-value:bluff there, as the docs elsewhere state.
- **Source:** GTO Wizard, *MDF & Alpha* — https://blog.gtowizard.com/mdf-alpha/ ; *Mathematical Misconceptions in Poker* — https://blog.gtowizard.com/mathematical-misconceptions-in-poker/

### M3 — Multiway n-th-root defense silently assumes **independent and symmetric** opponents. — **confidence: med**
- **Where:** `02` §9; `03` §3.
- **Claim:** vs n opponents each may fold up to the n-th root of the HU fold ceiling; e.g. HU 33% → each of two folds ~58% (√0.33 ≈ 0.574), each defends ~42%.
- **Recompute:** √0.33 = 0.5745 ✔; 1−0.5745 = 0.4255 ≈ 42% ✔; HU half-pot MDF = 66.7% so "42% < the tighter HU figure" is internally consistent ✔. The arithmetic is right and the doc correctly takes the root of alpha (fold), not of MDF.
- **Why it's shaky:** The n-th-root identity only holds if (a) the two opponents' fold events are **independent** and (b) they fold at the **same** rate. Real multiway defenders are correlated (shared board, shared ranges) and asymmetric (positions differ), and — as the docs themselves stress — multiway has no unique equilibrium, so there is no reason each defends the *equal* root share. The doc labels the arithmetic `[SOLVED]` and the implementation `[HEURISTIC]`, which is the right split, but the "~58% each / ~42% each" number is only exact under an idealization that never occurs at the table. It should be flagged as "equal-split idealization," not a defense target to grade against.
- **Correct statement:** The n-th-root is the *symmetric-independent* special case; treat "42% each" as illustrative of the *direction* (each defends less than HU), never as a per-opponent grading constant.
- **Source:** multiway non-uniqueness — Brown & Sandholm, *Superhuman AI for multiplayer poker*, Science 2019 (https://noambrown.com/papers/19-Science-Superhuman.pdf); Abou Risk & Szafron, three-player Kuhn poker equilibria (EV-transfer family).

### M4 — Rule-of-2-and-4 correction is right in direction but the "×4 close for ≤8 outs" boundary is soft. — **confidence: low**
- **Where:** `01` §1.2.
- **Claim:** ×4 is close for ≤8 outs and increasingly overstates beyond; 15 outs → 60% vs ~54% true.
- **Recompute:** 9 outs one card: ×2=18% vs true 19.15% (×2 *understates*, doc correct). 9 outs by river: ×4=36% vs true 34.97% (×4 slightly *overstates* even at 9 outs). 15 outs by river: ×4=60% vs true 54.12% ✔.
- **Why it's a nit:** ×4 already overstates at **9** outs (36 vs 35), so "close for ≤8 outs" is defensible but the crossover isn't a clean 8. Immaterial to bot math; flagging only for the "explain to others" goal.
- **Correct statement:** ×4 begins to overstate around 8–9 outs and the gap widens fast past ~10; ×2 mildly understates throughout. Direction claims are correct.

### M5 — "risk premium is ICM-only" is correct, but the docs occasionally lean on "equity realization" to carry *all* the OOP-pricing weight. — **confidence: low**
- **Where:** `02` §8; `01` §1.4.
- **Claim:** the cash effect mislabeled "risk premium" is just equity realization.
- **Assessment:** The *correction is right* and matches GTO Wizard's glossary (RP = ReqEq(ICM) − ReqEq(cEV), tournament-only — https://pages.gtowizard.com/glossary/risk-premium/). Minor over-reach: OOP under-realization is the dominant cash effect, but "range disadvantage pricing" also includes raw range/nut-advantage asymmetries and rake, which EQR alone doesn't fully capture. The doc's "pot odds tempered by EQR, MDF as secondary floor" framing is fine; just don't imply EQR is the *sole* cash analog. Low materiality.

### M6 — "5–10% IP edge" was already corrected, but the replacement "20–40+ points when OOP is capped" and "as little as ~2% realization" are single-spot extremes presented near band language. — **confidence: low**
- **Where:** `01` §1.4; `02` §2.
- **Assessment:** The correction away from a false-precise constant is good and the doc labels these "illustrative, one spot." The "~2%" and "~118% IP" are real GTO-Wizard-type single-flop outputs but are tail values; anyone skimming could over-anchor on "20–40+ points" as typical. Keep the "never a global constant" warning adjacent to *every* instance. The K9o R≈60% / 35%→21% figure I verified matches GTO Wizard exactly (https://www.pokernews.com/strategy/how-to-adjust-against-3x-opens-in-live-poker-tournaments-51314.htm), so the anchor example is sound.

---

## 4. MINOR / nits

- **N1** — `01` §6.2 & `03` §1: TAG AF "~2–3", LAG/maniac "high/very high" are qualitative where the numeric columns invite a number; fine, but AF is notoriously sample-noisy and vendor-dependent. Bands match PokerTracker's classifier cutoffs (Nit VPIP <18, TAG 18–24, LAG 25–35, Maniac >35), so they're defensible. **confidence: high** they're in published range.
- **N2** — `01` §1.3: "AKo vs QQ ≈ 43/57" — precise value is 43.3/56.7 (offsuit; suited AK is ~46/54). Rounding is fine; just note suited differs.
- **N3** — `02` §5: "one solve checks back ~98%" (monotone QJT) — a real single-node solver output but printed with two-sig-fig precision on an illustrative spot; the `[SOURCED, illustrative]` tag covers it. Don't let it become a grading target.
- **N4** — `01` §3.9 / `02`: "heads-up **limit** essentially solved (Bowling 2015)" — correct and correctly scoped to *limit* (not NLHE). Good discipline; many docs get this wrong.
- **N5** — `02` §6 rake: `$5/$17 = 29.4%`, `$5/$37 = 13.5%` recompute exactly. The `[DERIVED-ASSUMPTION] 35–60 bb/100` is honestly labeled as an order-of-magnitude self-derivation; it's plausible but uncheckable — keep the "not a cited figure" flag loud.
- **N6** — `02` §4: 3-bet combinatorics share-of-1326 recompute exactly (KK+ = 12/1326 = 0.905%; QQ+/AK = 34/1326 = 2.56%; TT+/AQ+ = 62/1326 = 4.68%). ✔

---

## 5. Tried to break, could NOT (high-value negative results)

- **MDF / alpha / break-even-to-call / break-even-bluff tables** — recomputed all six sizes; exact. **high**
- **Polar river bluff fraction f/(1+2f) and value:bluff (1+f):f** — all five sizes exact, including the 2× overbet 40%/1.5:1. **high**
- **EV(bet) and shove-EV formulas** — the `E·(P+B)−(1−E)·B` form (doc 02 §3/§7) is algebraically identical to `E·(P+2B)−B` (doc 01 §2.3); both correct. **high**
- **EQR = pot-share/equity, 175% worked example** — verbatim match to GTO Wizard glossary. **high**
- **Multiway n-th-root arithmetic** — √0.33 = 57.45%, defense 42.55%; root correctly taken of alpha not MDF; the previously-caught "58% is a fold not continue rate" defect is fixed. **high**
- **~70%→~35% c-bet halving HU→3-way** — corroborated as a solver-aggregate rule of thumb, correctly labeled secondary-aggregator. **med** (it's a real pattern; the specific numbers are illustrative, which the doc admits)
- **K9o 35%→21% realized (R≈60%)** — matches GTO Wizard's published example. **high**
- **Risk-premium = ReqEq(ICM)−ReqEq(cEV), tournament-only** — matches GTO Wizard glossary; the cash-mislabel correction is right. **high**
- **Player-type VPIP/PFR bands** — inside PokerTracker/coaching published ranges. **high**
- **Geometric sizing definition** ("same pot-fraction each street → all-in by river, maximizes value") — matches GTO Wizard/Upswing. **high**
- **Combinatorics** (1326 combos; 6/4/12/16; 169 classes; blocker AA 6→3, AK 16→12, and the 4-bet Axs AA 6→3 / AK 12→8) — all exact. **high**

---

## 6. Sources (URLs)

- GTO Wizard — MDF & Alpha: https://blog.gtowizard.com/mdf-alpha/
- GTO Wizard — Mathematical Misconceptions in Poker: https://blog.gtowizard.com/mathematical-misconceptions-in-poker/
- GTO Wizard — Equity Realization (EQR) glossary: https://gtowizard.com/en/glossary/equity-realization-eqr/
- GTO Wizard — Risk Premium glossary: https://pages.gtowizard.com/glossary/risk-premium/
- GTO Wizard — Pot Geometry (geometric sizing): https://blog.gtowizard.com/pot-geometry/
- GTO Wizard / PokerNews — K9o BB-vs-open equity realization example (35%→21%, R≈60%): https://www.pokernews.com/strategy/how-to-adjust-against-3x-opens-in-live-poker-tournaments-51314.htm
- PokerTracker player-type classifier cutoffs & VPIP/PFR bands: https://www.pokertracker.com/ ; PokerCoaching HUD stats: https://pokercoaching.com/blog/poker-stats/
- Upswing Poker — geometric bet sizing: https://upswingpoker.com/geometric-bet-sizing/
- Brown & Sandholm, *Superhuman AI for multiplayer poker*, Science 2019 (Pluribus; multiway non-uniqueness): https://noambrown.com/papers/19-Science-Superhuman.pdf
- Survey on GTO Poker (multiway equilibrium complexity): https://arxiv.org/html/2401.06168
- ThinkGTO — multiway ranges / HU→3-way c-bet: https://thinkgto.com/blog/understanding-multiway-ranges-with-gto-ranges
