# Adversarial Review — Poker Math Comprehensive Reference (math-lens / re-derivation refuter)

**Reviewer role:** Independent second reviewer. Edge = re-deriving every formula from scratch, hunting internal contradictions, checking plain-language faithfulness, and finding omissions. Deliberately *not* web-sourcing-led.

**Read confirmation:** Read the target in full (557 lines) at
`/Users/johncabiles/Documents/Obsidian/John 2nd Brain - Mark III/Poker Math — Comprehensive Reference.md`
(the corrected path in the brief; the em-dash variant was not needed).

**Method:** Every formula and every by-size table entry was re-derived in Python from first principles. AKo vs QQ was verified by full 5-card-board enumeration (all 1,712,304 runouts). Rule-of-2/4 accuracy was checked exactly against `outs/47` and `1-(47-o)/47·(46-o)/46`.

---

## Bottom line up front

The **derivable-math core is essentially flawless.** Every algebraic formula and every number in every by-size table reproduces to the decimal. I found **zero** hard math errors in the formula sheet, the pot-odds/MDF/alpha/bluff-ratio tables, the combinatorics, or the flagship worked examples. The one genuine technical inaccuracy is a **mis-stated direction of the rule-of-2/4 approximation error** (imprecise, not catastrophic). The rest of my findings are omissions and a few plain-language imprecisions.

**Overall accuracy: A / A-minus. Overall completeness (for the stated modeling goals): B.**

---

## Per-part verdicts (with the actual algebra)

### Part 1 — Foundations — **SOUND**
- Deck `C(52,2)=1326` ✓. Pair `C(4,2)=6` ✓. Suited 4 ✓. Offsuit `4·4−4=12` ✓. Unpaired 16 ✓. 169 classes = 13+78+78 ✓, and `13·6+78·4+78·12 = 1326` ✓ (combos reconcile exactly).
- Flush draw 9 outs: next card `9/47 = 19.15%` → doc's **19.1%** ✓. By river `1−(38/47)(37/46) = 34.97%` → doc's **35.0%** ✓.
- **AKo vs QQ**: full enumeration = **42.84% / 57.16%** → doc's **43/57** ✓ (well-chosen example; note this is specifically the *offsuit, Q-blocks-nothing* case — AKs or AK vs a pair that shares a suit runs closer to 46/54, but the doc says AKo and is exactly right).
- Equity-realization section (§1.4) is conceptually correct; see Omission O1 (no formula/anchor for R beyond "~5–10%").

### Part 2 — Economic engine — **SOUND**
- Pot-odds break-even `B/(P+2B)`: re-derived from "caller's equity is a share of the final pot `P+2B`, must cover risk `B`." Table exact: ⅓→**20.00%**, ½→**25.00%**, ¾→**30.00%**, pot→**33.33%**, 2×→**40.00%** ✓ (all match).
- Worked example (P=100, B=50 → 25%) ✓.
- EV(bet) `= f·P + (1−f)·[eq·(P+2B) − B]`: re-derived, correct (final pot includes own B; subtract invested B). Pure-bluff reduction `f·P > (1−f)·B ⟹ f > B/(P+B)` ✓.
- Break-even pure-bluff `B/(P+B)`: ⅓→**25%**, ½→**33.33%**, pot→**50%**, 2×→**66.67%** ✓.

### Part 3 — GTO layer — **SOUND**
- MDF `P/(P+B)` / alpha `B/(P+B)`: ⅓→**75/25**, ½→**66.67/33.33**, ⅔→**60/40**, pot→**50/50**, 2×→**33.33/66.67** ✓ (all match, doc's "~33/67" tilde is appropriate).
- Polar river bluff fraction `f/(1+2f)`, value:bluff `(1+f):f`: ⅓→**20% (4:1)**, ½→**25% (3:1)**, ⅔→**28.57% (2.5:1)**, pot→**33.33% (2:1)**, 2×→**40% (1.5:1)** ✓. Internal consistency verified: `value_frac/bluff_frac` from `f/(1+2f)` equals `(1+f)/f` at every size ✓.
- §2.4↔§3.2 identity ("break-even bluff freq is *exactly* alpha") ✓ — both `B/(P+B)`.
- CFR/solver history (§3.9): Zinkevich 2007, Bowling 2015 (HU limit), Libratus 2017, Pluribus 2019, and the "6-max has no unique equilibrium / superhuman ≠ solved" caveat are all stated correctly.

### THE REQUESTED DENOMINATOR CHECK — **CONFIRMED CORRECT, NOT A CONTRADICTION**
The doc uses `B/(P+2B)` for break-even-**call** but `B/(P+B)` for MDF/alpha and break-even-**bluff**. This is **legitimate**, not an inconsistency:
- **Call** `B/(P+2B)`: the *caller's* equity is a fraction of the **whole final pot** `P+2B` (original `P` + bettor's `B` + caller's own `B`). His equity share of that pot must at least return his risk `B`: `eq·(P+2B) ≥ B ⟹ eq ≥ B/(P+2B)`.
- **Bluff / alpha** `B/(P+B)`: the *bettor's* fold-EV question involves **no equity share of a pot**. He risks `B` to win the **current** pot `P`; profit `f·P − (1−f)·B > 0 ⟹ f > B/(P+B)`. The reference is `P` (already there) and risk `B`, so the ratio is `B/(P+B)`.
They differ because they answer different questions from different seats. At a pot-sized bet they correctly diverge (33.3% vs 50%). **No error.**

### Part 4 — Preflop — **SOUND (strategy numbers representative, correctly flagged)**
RFI bands (UTG 15–18%, LJ 19–22%, HJ 23–26%, CO 27–32%, BTN 40–48%, SB 35–45%) sit squarely inside solver-adjacent consensus. 3-bet ~5–11%, 4-bet core QQ+/AK with Axs blocker bluffs, 5-bet QQ+/AK at 100bb — all canonical and explicitly labeled representative. Sizing conventions correct.

### Part 5 — Postflop — **SOUND (heuristic, correctly labeled)**
Texture routing, SPR framing, and — notably good — the explicit rebuttal of the **pot-committed fallacy** (§5.6: low SPR *lowers the equity threshold*, not "never fold") are correct and unusually careful. Multiway is correctly demoted to heuristic with the "no unique equilibrium" caveat. C-bet "roughly halves HU→3-way" is a labeled rule of thumb (not derivable; fine).

### Part 6 — Opponent modeling — **SOUND (stat bands representative)**
VPIP/PFR/AF profiles are population estimates, labeled as such. Bayesian narrowing `P(hand|action) ∝ P(action|hand)·P(hand)` is stated correctly with street-by-street renormalization and card removal.

### Parts 7–8 — Bot/glossary — **SOUND**
Formula sheet reproduces every formula above with no transcription drift.

---

## Ranked list of confirmed math errors

**1. (MINOR / imprecise) Rule-of-2-and-4 error-direction is mis-stated (§1.2).**
Doc: *"Accurate for small out counts; slightly overstates for large counts."* Exact check:
- **Rule of 2** (next card, `outs·2` vs `outs/47`): **UNDERstates at every out count** (9 outs: 18% vs 19.1% exact; 15 outs: 30% vs 31.9%). It never overstates.
- **Rule of 4** (two cards, `outs·4` vs exact): understates for small counts (≤~7) and **overstates only for large counts** (8 outs: 32% vs 31.5%; 9: 36% vs 35.0%; 15: 60% vs 54.1%).

So the "overstates for large counts" claim is true **only for the ×4 branch**, and the "accurate for small counts" gloss hides that the ×2 branch is a *systematic slight undercount*. **Corrected wording:** "The ×2 rule slightly *under*states (one card); the ×4 rule is close for small out counts but increasingly *over*states as outs climb past ~8 (e.g. 15 outs: 60% vs ~54% true)." This is the only genuine technical inaccuracy in the document, and it's in the plain-terms/prose, not in a formula.

*(No other math errors found. The formula sheet, all five by-size tables, combinatorics, flush-draw equities, and AKo-vs-QQ are all exact.)*

---

## Ranked list of internal contradictions / misleading plain-language

**1. (MINOR) §1.2 plain-terms vs exact — "rule of 2 and 4 is the fast shortcut for that percentage"** understates that the shortcut has a *direction-dependent* bias (see error #1). A reader trusting the callout will slightly misprice large-out draws in the value-losing direction (thinks 15-out combo draw is 60% by river; it's ~54%). Faithfulness gap, same root as error #1.

**2. (VERY MINOR) §6.2 AFq definition ambiguity.** "AFq = aggressive actions / total actions" — the standard definition is aggressive/(aggressive+calls), i.e. it *excludes* checks and folds. "Total actions" read literally (including checks/folds) yields a different number. Not wrong per se, but under-specified for a document meant to be a bot-calibration yardstick.

**3. (NOT a contradiction — cleared)** The `(P+2B)` vs `(P+B)` denominator split (the brief's flagged suspicion) is **correct** — see the dedicated section above. I also confirmed §5.5 does **not** conflate the per-hand pot-odds threshold with the range-level MDF (a common authorial error the doc correctly avoids). All §x.y cross-references I traced (§1.4, §2.4, §3.2, §3.4, §3.5, §3.7) resolve to the right concept — no misdirected pointers.

---

## Ranked list of omissions (for the stated goals: ranges across positions, decisions after raises/3-bets/4-bets/shoves, play vs personality types)

**O1. No formula or table for the realization factor R.** R is declared "a first-class variable, not a footnote" (§1.4) yet is given only one anchor ("~5–10% for IP vs OOP"). To *model* blind-defense/flatting the way §4.4 demands, a bot needs at least representative R multipliers by hand-class × position (e.g. SC ~1.05–1.15 IP, offsuit gappers ~0.85 OOP). The doc names the lever but supplies no values to turn it.

**O2. Rake is dismissed too fast (Appendix) but actually breaks the pot-odds identity.** Rake doesn't just "tighten marginals slightly" — with a capped rake it changes the *effective* pot the caller wins (`P+B−rake`), so break-even-to-call becomes `B/(P+2B−rake)` in the relevant regime, and it lifts the minimum-defense/RFI thresholds materially in small live pots (the doc's own $2/$3 target). A yardstick doc should give the rake-adjusted call formula, not wave it off.

**O3. No 4-bet/5-bet *bluff quantities* or shove EV math.** §4.3 names "Axs blocker 4-bet bluffs" and "QQ+/AK 5-bet" but gives no *frequencies* and no risk-premium / shove-EV formula (`EV(shove) = fold_eq·P + (1−fold)·[eq·(2S+P)−S]`). The ladder is described qualitatively; a bot can't calibrate 4-bet-bluff freq or a 5-bet threshold from what's here.

**O4. No "risk premium" / MDF-vs-a-raise treatment.** Facing a 3-bet or a check-raise is different from facing a bet into an unbuilt pot (dead money already invested, changed effective SPR). The doc's MDF/pot-odds machinery is presented for a single bet into pot `P`; it never adapts the identity for *facing a raise* (where your prior bet is part of the reference), which is exactly the "decisions after raises/3-bets" spot family the brief asks about.

**O5. Blocker effects are qualitative only.** §3.8 explains blockers well but gives no worked combinatorial example (e.g. "holding the A♠ on a spade river drops villain's nut-flush combos from N to M, shifting your break-even bluff-catch by X%"). For the value:bluff math to be *implementable* at the combo level (as §3.8 claims), one numeric worked case is needed.

**O6. Personality play is one-directional (how *I* adjust), never the *inverse model*.** Part 6 tells you how to exploit each type, but for a *persona-driven bot* (the stated purpose) it omits the generative spec: the concrete per-node frequency *deltas* that make a bot behave like a station/nit/maniac (e.g. "station: fold-to-cbet 15% vs GTO ~55%; never-raise-flop; call-down threshold −20% equity"). §6.4 says a persona "is" a range+frequency object but supplies no example frequency vector.

**O7. Multiway "MDF is distributed" is asserted but not quantified.** §5.7 says collective defense replaces per-player MDF, but gives no even a rough split rule (e.g. each defender covers ~MDF/n, or the range-weighted version). For loose live multiway — the doc's own emphasis — this is the spot where guidance is thinnest.

**O8. No minimum-defense-vs-a-polar-vs-linear caveat table.** §3.2 correctly warns MDF is a floor that's overridden vs capped/polar ranges, but never gives the *replacement* rule (vs a purely polar bettor, defend by pot-odds bluff-catch math, not MDF). The reader is told MDF can be wrong but not what to use instead.

---

## Grades

| Dimension | Grade | Basis |
|---|---|---|
| Derivable-math accuracy | **A (99%+)** | Every formula and every by-size table exact to the decimal; AKo/QQ exact by enumeration; denominator split correct. Only blemish: rule-2/4 error-direction prose. |
| Strategy-number fidelity | **A−** | RFI/3-bet/4-bet/stat bands all in-consensus and correctly flagged representative. |
| Internal consistency | **A** | No contradictions; cross-refs resolve; pot-odds vs MDF not conflated. |
| Plain-language faithfulness | **A−** | One imprecise callout (rule 2/4); AFq under-specified. |
| Completeness for stated modeling goals | **B** | R has no values, rake/4-bet-bluff-freq/shove-EV/risk-premium/persona-frequency-deltas all missing (O1–O8). |

**Verdict: the math you can prove is proven and correct. The gaps are in *quantifying* the levers the doc correctly names (R, rake, 4-bet/5-bet bluff freq, persona deltas) — i.e. it's a superb *conceptual* yardstick and an incomplete *numeric* one for bot calibration.**
