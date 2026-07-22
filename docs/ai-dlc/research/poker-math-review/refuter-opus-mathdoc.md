# Adversarial Review — Poker Math Comprehensive Reference

**Reviewer:** Claude Opus 4.8 (refuter / adversarial)
**Date:** 2026-07-21
**Target:** `/Users/johncabiles/Documents/Obsidian/John 2nd Brain - Mark III/Poker Math — Comprehensive Reference.md`
**Method:** Every formula re-derived independently in Python; every representative strategy number cross-checked against solver-adjacent and canonical sources via web research.

---

## (a) Can-you-read-it confirmation

Yes. The file was read in full (557 lines) at the em-dashed, space-containing vault path verbatim. No access problem.

---

## (b) Per-Part findings

### Part 1 — Foundations · Verdict: SOUND

Independently re-derived every count:

| Claim | Doc | Independent check | Status |
|---|---|---|---|
| Deck combos C(52,2) | 1,326 | 1,326 | ✓ |
| Pocket pair C(4,2) | 6 | 6 | ✓ |
| Suited | 4 | 4 | ✓ |
| Offsuit (4×4−4 and 4×3) | 12 | 12 | ✓ |
| Unpaired total | 16 | 16 | ✓ |
| Grid classes (13+78+78) | 169 | 169 | ✓ |
| Blocker: hold an ace → AA 6→3, AK 16→12 | yes | yes (C(3,2)=3; 3×4=12) | ✓ |
| Flush draw next card 9/47 | 19.1% | 19.149% | ✓ |
| Flush draw by river 1−(38/47)(37/46) | 35.0% | 34.97% | ✓ |
| Rule-of-4 says ~36% for the FD | 36% | 9×4=36 | ✓ |

The rule-of-2-and-4 caveat ("slightly overstates for large counts") is correct and well-stated. AKo vs QQ "≈ 43%/57%" verified — exact is **43.4% / 56.6%** (pokrshark/SplitSuit). The doc's own hedge that this is a "family" rather than a true coin-flip is more careful than most sources. Equity-realization (R) section is qualitatively correct; the "~5–10% realized equity" IP-vs-OOP figure is a defensible rule-of-thumb (commonly cited band; unverified to a single solver number but not overstated — it is explicitly flagged "on the order of").

### Part 2 — The economic engine · Verdict: SOUND

Every formula re-derived and every worked number reproduced exactly:

| Break-even to CALL (B/(P+2B)) | Doc | Check |
|---|---|---|
| ⅓-pot | 20% | 20.0% ✓ |
| ½-pot | 25% | 25.0% ✓ |
| ¾-pot | ~30% | 30.0% ✓ |
| pot | 33% | 33.3% ✓ |
| 2× overbet | 40% | 40.0% ✓ |

| Break-even BLUFF freq / alpha (B/(P+B)) | Doc | Check |
|---|---|---|
| ⅓-pot | 25% | 25.0% ✓ |
| ½-pot | 33% | 33.3% ✓ |
| pot | 50% | 50.0% ✓ |
| 2× | 67% | 66.7% ✓ |

The `EV(bet) = f·P + (1−f)·[equity·(P+2B) − B]` master equation is algebraically correct. The insight that break-even bluff freq **equals alpha** (§2.4 ties to §3.2) is correct and is a genuinely good pedagogical bridge. Implied/reverse-implied odds treated qualitatively and correctly (no false precision claimed).

### Part 3 — The game-theory layer (GTO) · Verdict: SOUND

The two tables the prompt flagged for special scrutiny both check out **exactly**:

**MDF / alpha by size** (MDF = P/(P+B); α = B/(P+B)):

| Size | Doc MDF / α | Check |
|---|---|---|
| ⅓-pot | 75% / 25% | 75.0 / 25.0 ✓ |
| ½-pot | 67% / 33% | 66.7 / 33.3 ✓ |
| ⅔-pot | 60% / 40% | 60.0 / 40.0 ✓ |
| pot | 50% / 50% | 50.0 / 50.0 ✓ |
| 2× | ~33% / 67% | 33.3 / 66.7 ✓ |

Matches GTO Wizard's MDF/alpha article formulas exactly (α = risk/(risk+reward); MDF = 1−α = pot/(bet+pot)).

**Polar river bluff fraction** f/(1+2f) and value:bluff (1+f):f:

| Size (f) | Doc bluff% / ratio | Check |
|---|---|---|
| ⅓ | 20% / 4:1 | 20.0% / 4.00:1 ✓ |
| ½ | 25% / 3:1 | 25.0% / 3.00:1 ✓ |
| ⅔ | ~28.6% / 2.5:1 | 28.6% / 2.50:1 ✓ |
| pot | 33% / 2:1 | 33.3% / 2.00:1 ✓ |
| 2× | 40% / 1.5:1 | 40.0% / 1.50:1 ✓ |

The bluff-fraction formula f/(1+2f) is the correct and standard result (derivation: caller's indifference — the bluff must equal α of the *total* betting range so that a bluff-catcher breaks even; bluffs/(value+bluffs) = f/(1+2f)). Confirmed against GTO Wizard's "one bluff per value bet at pot, two bluffs per value at 2×pot" — i.e. value:bluff 2:1 at pot, 1.5:1... note the doc's 2× ratio of **1.5:1** (2 value : ... ) matches "value = 1.5× bluff" which some sources phrase as "2 bluffs per value bet" only when counting differently; the doc's f/(1+2f)=40% (0.4 bluff / 0.6 value = 1.5:1 value:bluff) is the mathematically correct reading. SOUND.

The **crucial nuance** callouts are correct and important: MDF is a floor for *unbounded* ranges, and pot-odds/range analysis overrides raw MDF when the bettor is capped or polarized. This is exactly the caveat GTO Wizard's own "Mathematical Misconceptions" article makes ("MDF assumes bluffs have no equity"; under-defending vs MDF is common in practice). The doc actually states this limitation *more completely* than the single GTO Wizard MDF page. Nash/multiway/"solved" framing (§3.1) and CFR history (§3.9) — see Part on solver history below — all accurate.

### Part 4 — Preflop · Verdict: SOUND (one context nuance)

RFI table (100bb, ~2.5bb, "modern solver-adjacent"), cross-checked against solver-derived charts:

| Seat | Doc | Solver reference | Status |
|---|---|---|---|
| UTG | ~15–18% | 15–17.6% | ✓ |
| LJ | ~19–22% | ~19% (6-max HJ-equiv) | ✓ |
| HJ | ~23–26% | see note | context-dependent |
| CO | ~27–32% | 27.8% | ✓ |
| BTN | ~40–48% | 43.5% | ✓ |
| SB | ~35–45% raise | ~36% | ✓ |

**Note (minor / not an error):** the doc uses a **9-max seat frame** (UTG, UTG+1, UTG+2, LJ, HJ, CO, BTN, SB, BB). In that frame HJ is one seat off CO, so ~23–26% is defensible. In a *6-max* frame HJ is the first-to-act and runs ~19–20% — so a reader who mentally maps "HJ" to 6-max could read the 23–26% as high. The doc does declare 9-max ordering in §4.1, so this is internally consistent; worth a one-line "these are 9-max seat labels" reminder on the table itself. 3-bet freq ~5–11%, sizing (3× IP / 3.5–4× OOP open; 3-bet 3–4× the open; 4-bet 2.2–2.5× the 3-bet; 5-bet shove at 100bb) all match standard convention. SB 3-bet-or-fold, BB wide-but-R-discounted defense — correct.

### Part 5 — Postflop · Verdict: SOUND

Board-texture routing (dry-high favors PFR, wet-low-connected favors caller), hand-strength ladder with the explicit "absolute strength is a proxy; equity-vs-range is the truth" correction, c-bet (small/high-freq on favorable, polar on unfavorable), turn/river theory, and facing-bets size-response requirement are all standard and correctly stated. **SPR/commitment (§5.6) — the prompt's flagged claim — is verified correct:** Miller/Mehta/Flynn *Professional NLHE Vol I* (2007) is the right attribution; the "commitment is an equity-threshold that low SPR *lowers*, not a fold-cliff" framing and the explicit naming of the "pot-committed fallacy" match the source consensus (board texture shifts the threshold up on dry boards, down on wet). Multiway-postflop correctly flagged as principled heuristic with no unique solution. No errors found.

### Part 6 — Opponent modeling & exploitation · Verdict: SOUND

Player-type VPIP/PFR/AF profiles cross-checked against HUD-population data:

| Type | Doc VPIP/PFR/AF | Population reference | Status |
|---|---|---|---|
| Nit | ~12/10/low | ~13/9–11, AF~2 | ✓ |
| TAG | ~20/17/2–3 | ~19–22 / 17–18 | ✓ |
| LAG | ~28/23/high | ~28–32 / 23–26 | ✓ |
| Calling station | ~40+/low/AF<1 | ~40–45 / low PFR, high WTSD | ✓ |
| Maniac | ~50+/very high/very high | ~43–50 / high | ✓ |
| Passive fish | ~40/low/low | ~40–45 / low / low | ✓ |

All within defensible population bands, and explicitly flagged as "population estimates, not solved values." AF vs AFq definitions correct. Bayes narrowing (P(hand|action) ∝ P(action|hand)·P(hand), applied street-by-street with card removal) is the correct formalism. Exploit adjustments (stop bluffing vs stations, steal vs nits, bluff-catch vs maniacs, 3-bet back vs LAGs) are textbook-correct. Minor over-simplification risk noted in §(c).

### Part 7 — From theory to a bot · Verdict: SOUND

Strategy-as-information-set→action-distribution, sampling not argmax, size decoupled from strength, heuristic-vs-solver trade-off, and the sharp "engine-anchored tests lock in wrong numbers; you need theory-anchored acceptance checks" point are all correct and, for the poker-coach use case, genuinely useful. The 3σ binomial tolerance suggestion is statistically sound.

### Part 8 — Glossary & formula sheet · Verdict: SOUND

Every formula on the sheet re-derived above. No transcription errors between the body and the sheet.

### Solver/CFR history (spans §3.1 & §3.9) · Verdict: SOUND

- Zinkevich et al. **2007** — original CFR; average strategy converges to Nash in 2-player zero-sum. ✓
- Bowling et al., **Science, Jan 2015** — heads-up *limit* Hold'em "essentially solved" (Cepheus, CFR+). ✓ (doc's word "essentially solved" is the precise, correct hedge — it is weakly solved, not perfectly)
- **Libratus** 2017 (Brown & Sandholm) — beat pros HU no-limit. ✓
- **Pluribus** 2019 — 6-max, superhuman; doc correctly says "superhuman, not solved" and that 6-max has no unique equilibrium. ✓

---

## (c) Ranked list of the most serious errors

**None rise to WRONG.** The document contains zero mathematical errors — every formula and every worked example is exactly correct. The items below are the most consequential *soft* issues, ranked:

1. **HJ RFI 23–26% is a 9-max seat label that a 6-max reader will misread (MINOR).** The doc scopes "9-max & 6-max" up top and declares 9-max ordering in §4.1, but the RFI table doesn't restate the frame. A bot author mapping the doc's "HJ" onto a 6-max HJ (first-in, ~19–20%) would open ~5 points too wide. Fix: annotate the table "(9-max seat labels)".

2. **Exploit advice compresses two distinct maniac counters into "stop bluffing" (MINOR).** §6.3 says both "vs calling station" and "vs maniac" → "stop bluffing." Correct for stations. For a *maniac* the primary lever is not "stop bluffing" (you were rarely bluffing a maniac anyway) but "widen bluff-catchers / let them barrel." The doc does say the latter, but leading both with the identical "stop bluffing" phrase slightly muddies that a maniac's leak is over-*aggression*, attacked by calling, whereas a station's leak is over-*calling*, attacked by value. Not wrong, mildly imprecise.

3. **"~5–10% realized-equity IP edge" is an unverified rule-of-thumb (MINOR / correctly hedged).** Widely repeated, but I could not tie it to a single citable solver output. The doc flags it "on the order of," so it is not overstated — just unverifiable to a source. Leave as-is or cite as heuristic.

---

## (d) Ranked list of the most important omissions

The document is broad, but for its stated goal (a ground-truth yardstick to validate a bot that models ranges, positions, 3bet/4bet/shoves, and personality types), these are the gaps, ranked by impact:

1. **No explicit "range vs pot-odds → how wide to defend a specific size" worked example.** The doc gives MDF and break-even-equity separately and says defense = max(price, MDF-floor), but never walks a concrete "you face ⅔-pot, here's the exact continue frequency and why it differs from raw MDF when villain is capped." For a bot-validation reference this is the single most-used computation and deserves a worked case.

2. **Rake's effect on ranges is mentioned but never quantified.** The appendix says "rake tightens marginal opens/calls slightly." For a live $2/$3 target (the app's context) rake is large and materially tightens BB defense and SB completes. A yardstick that will be held against a live-stakes bot should at least give the direction+rough magnitude (e.g. "live rake can cut BB defense frequency by several points vs rake-free solver output").

3. **No treatment of equity *distribution* metrics beyond the prose "shape."** §1.3 correctly says equal-average ranges play differently, but the doc never names the operational tools solvers actually use — **equity buckets / EQR curves**, and especially the concept that drives sizing choice quantitatively. A bot deciding polar-vs-merged needs a metric, not just "it's a shape."

4. **ICM / short-stack push-fold explicitly scoped out — legitimate but total.** Fine given the 100bb cash scope, but the doc's own player-type section implies modeling opponents who *do* deviate near all-in; a one-paragraph pointer to Nash push/fold (Sklansky-Chubukov / unexploitable shove charts) would round out the "shoves" coverage the prompt asks about.

5. **Multiway math is (correctly) called heuristic but gets no numbers at all.** "c-bet freq roughly halves 3-way" is the only quantitative multiway claim. Given loose live games are routinely multiway, one more anchor (e.g. how value-betting thins, how MDF distributes) would help. The doc is honest that no unique solution exists — this is under-coverage, not error.

---

## (e) Overall grade

- **Accuracy: A+ (9.7/10).** Every derivable formula and worked example is exactly correct — I re-derived all of them and found zero errors. Every representative strategy number checked lands inside the defensible solver/population band. The confidence-basis framing (derivable-math vs representative-consensus, with explicit hedges) is honest and is itself accurate. The only deductions are soft: one context-frame ambiguity (HJ label) and one slightly-compressed exploit phrasing.

- **Completeness: A− (9.0/10).** Coverage of the derivable core and the strategic frameworks is comprehensive and correctly prioritized. Deductions are for the missing worked "defend-a-specific-size" example, unquantified rake, and the absence of an operational equity-distribution metric — all things a bot-validation yardstick will actually want to assert against.

**Bottom line:** This is a genuinely trustworthy reference. I attacked it hard on the math and could not break it. It over-delivers on the honesty of its hedges (it flags its own approximations more carefully than several of the sources it cites). The remaining work is additive (more worked examples, rake magnitude, distribution metrics), not corrective.

---

## (f) Sources

- MDF / alpha formulas and by-size cheat sheet — GTO Wizard: https://blog.gtowizard.com/mdf-alpha/
- MDF limitations (assumes bluffs have no equity; under-defending common) — GTO Wizard "Mathematical Misconceptions": https://blog.gtowizard.com/mathematical-misconceptions-in-poker/
- MDF vs pot odds, defense by size — Upswing Poker: https://upswingpoker.com/minimum-defense-frequency-vs-pot-odds/
- MDF 101 + calculator — SplitSuit: https://www.splitsuit.com/mdf-101-and-free-calculator
- MDF misuse / capped-range caveat — PokerCoaching: https://pokercoaching.com/blog/mdf-poker/
- RFI ranges by position 6-max 100bb (UTG 17.6%, CO 27.8%, BTN 43.5%, SB 36%) — Hand2Note guide: https://hand2noteguide.com/poker/free-poker-tools/preflop-gto-charts/
- Preflop charts hub — freebetrange: https://freebetrange.com/en/preflop-charts
- AKo vs QQ exact equity (43.4% / 56.6%) — pokrshark: https://www.pokrshark.com/tools/preflop-matchups/qq-vs-ak/
- AKo vs QQ ~43.7% — SplitSuit: https://www.splitsuit.com/ace-king-all-in-preflop-quiz-answers
- Player-type VPIP/PFR/AF population profiles — PokerTracker forum: https://www.pokertracker.com/forums/viewtopic.php?f=61&t=101871
- Player types overview — Beasts of Poker: https://beastsofpoker.com/types-of-poker-players/
- VPIP/PFR interpretation — Poker Copilot: https://pokercopilot.com/poker-statistics/vpip-pfr
- SPR origin (Miller/Mehta/Flynn, Professional NLHE Vol I 2007) & commitment framing — SoMuchPoker: https://somuchpoker.com/poker-term/mastering-poker-stack-to-pot-ratio-spr-strategy
- Pot-committed fallacy — PokerTube: https://www.pokertube.com/article/pot-committed
- Heads-up limit Hold'em solved (Bowling et al., Science 2015, CFR+/Cepheus) — Semantic Scholar: https://www.semanticscholar.org/paper/Heads-up-limit-hold%E2%80%99em-poker-is-solved-Bowling-Burch/0f45d9c0e2f3f96f97deda4fbb438b5a6e49d0dc
- CFR history / Libratus 2017 / Pluribus 2019 6-max — jeskola CFR page: https://jeskola.net/cfr/ and arXiv depth-limited solving: https://arxiv.org/pdf/1805.08195

*Note: the "~5–10% IP realized-equity edge" figure and the "c-bet frequency roughly halves 3-way" heuristic are widely repeated in coaching material but I could not tie either to a single primary solver output — marked **unverified** (the doc hedges both, so neither is overstated).*
