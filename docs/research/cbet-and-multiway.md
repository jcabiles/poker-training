# C-Bet Frequency & Sizing by Board Texture, and Multiway Adjustments

Research note for NLHE cash-game calibration (~100bb effective, single-raised pots unless noted). Compiled 2026-07-21 from published solver-derived heuristics (GTO Wizard, Upswing Poker, GTOWarrior) and academic sources on multiplayer game theory. No numbers in this document are fabricated — every figure below is attributed to a specific source and tagged for confidence.

**Tags used throughout:**
- **[SOLVED/derivable]** — a direct solver output number, reproducible from a named solve.
- **[SOURCED estimate]** — a published aggregate/heuristic from a credible site, not a raw solver dump, but traceable to a specific article.
- **[HEURISTIC/uncertain — multiway not solved]** — multiway numbers, which by construction are approximations (see §4).

---

## 1. Flop c-bet frequency & sizing by texture (heads-up, single-raised pot, ~100bb)

All figures in this section come from GTO Wizard's "Flop Heuristics" and "Mechanics of C-Bet Sizing" series, which run solver batches across board categories and report aggregate frequencies/sizings for the preflop raiser. These are BTN vs BB (IP) or similarly structured single-raised-pot solves unless noted.

### 1.1 Dry / high card boards (e.g., A72r, Q♥Q♣6♦-type)

- **[SOURCED estimate]** On a dry, disconnected board, the PFR (preflop raiser) c-bets at **high frequency**, using a small sizing — typically **33% pot**. Example: BTN vs BB on Q♥Q♣6♦, BTN uses 33% pot as the primary size; BB folds ~37%, calls ~39%, raises ~24%. (GTO Wizard, [The Mechanics of C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/))
- **[SOURCED estimate]** High-card / paired dry boards are described elsewhere as bet "virtually always, regardless of position," with recommended sizing in the **25–33% pot** range. (Upswing Poker, [How Often Should You C-Bet? Level-Up #4](https://upswingpoker.com/podcast/ep4-c-bet-frequency/))
- **[SOURCED estimate]** Single-broadway disconnected boards (e.g., K72-type): c-bet essentially **100%** of the time. (Upswing Poker, same source)
- **[SOURCED estimate]** Low, disconnected boards (7-5-3, 5-4-3) from an EARLY position raiser facing the BB specifically: c-bet frequency collapses toward **0–20%** (e.g., "virtually never" on 7-5-3 UTG vs BB; ~0% on 5-4-3 UTG vs BB; ~20% on 6-4-3 CO vs BB). This is a range-advantage effect: the raiser's range doesn't dominate a low, disconnected board the way it does a high one. (Upswing Poker, same source)

### 1.2 Wet / connected boards (e.g., JT9ss-type, K♥J♥7♦)

- **[SOURCED estimate]** On a wet, connected two-tone board, the PFR bets **bigger** and **less often** than on dry boards: primary sizes of **75% pot and 125% pot (overbet)**. Example: BTN vs BB on K♥J♥7♦, BB folds ~62%, calls ~32%, raises ~5%; roughly 15% of BB's folds come from hands with 50–60% equity (a sign of the polarized/overbet approach pricing out live equity, not just air). (GTO Wizard, [Mechanics of C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/))
- **[SOURCED estimate]** Medium-connectivity boards (9-8-4, 8-6-3, 7-6-2 type): c-bet **~55–60%** of the time, sizing **50% pot or bigger**; BTN tends toward ~75% pot, earlier positions toward ~50% pot. (Upswing Poker, [Level-Up #4](https://upswingpoker.com/podcast/ep4-c-bet-frequency/))
- **[SOURCED estimate]** Double-broadway connected boards (Q-6-5, J-4-2 type): c-bet **~70%** of the time on average. A-high boards: also **~70%** on average. (Upswing Poker, same source)
- The umbrella heuristic across sources: the **"wetness parabola"** — bet small and often on dry boards, bet big (and somewhat less often) on wet/connected boards. (GTO Wizard, [The Mechanics of C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/))

### 1.3 Monotone boards

- **[SOURCED estimate]** Monotone flops see a **drastic decrease in both betting frequency and sizing** relative to two-tone/rainbow boards of similar connectivity — the flush possibility compresses both players' range advantage and increases variance of a big bet, so solvers favor smaller, more frequent small bets or outright checking over polarized big bets. (GTO Wizard, [Flop Heuristics: IP C-Betting in Cash Games](https://blog.gtowizard.com/flop-heuristics-ip-c-betting-in-cash-games/))
- **[SOURCED estimate]** On monotone boards specifically, later-street sizing on the turn tends toward **~50% pot** rather than overbetting, consistent with a capped, non-polarized approach on cards where the nut advantage is diffuse. (GTO Wizard, same source)

### 1.4 Super-wet boards (e.g., Q♦J♦T♦ — monotone + straight-heavy)

- **[SOLVED/derivable]** BTN vs BB on Q♦J♦T♦: BB **checks back 98%** as PFR faces essentially no incentive to bet big; when BTN (as PFR) does act, it is close to a **50/50 split between betting and checking**, and the bet size used is small, **33% pot** (not the overbet seen on merely "wet" two-tone boards). BB continuing range folds ~37%, calls ~53%, raises ~9%; nutted hands (straights/flushes) make up ~29.4% of BB's continuing range — a sign both sides are very capped/polarized simultaneously. (GTO Wizard, [The Mechanics of C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/))
- This confirms the "parabola" shape: betting frequency and size rise from dry → wet, then **fall again** on the very wettest textures (monotone straight-possible boards), because neither range has a durable nut/range edge there.

### 1.5 IP vs OOP asymmetry

- **[SOURCED estimate]** OOP c-bet frequency is materially lower than IP in aggregate. In a 100bb cash-game single-raised pot, the OOP preflop raiser (e.g., LJ vs BB after LJ's open gets flatted OOP) **c-bets less than ⅓ of the time on aggregate**, with a strong skew toward betting on less-connected/dry boards and checking connected ones far more than an IP raiser would. (GTO Wizard, [Flop Heuristics: OOP C-Betting in MTTs](https://blog.gtowizard.com/flop-heuristics-oop-c-betting-in-mtts/) — note: sourced from the MTT article; the cash-game OOP companion article exists but full text wasn't independently re-verified for this note, see caveat below)
- **[SOURCED estimate]** IP c-bet aggregate frequency in cash games tends to run notably higher than OOP's ~⅓, consistent with IP's positional information edge letting it profitably bet a wider range across textures. (GTO Wizard, [Flop Heuristics: IP C-Betting in Cash Games](https://blog.gtowizard.com/flop-heuristics-ip-c-betting-in-cash-games/))
- **Caveat:** I was not able to extract a single clean "IP c-bets X%, OOP c-bets Y%" aggregate pair from one article — the IP and OOP cash-game articles report per-texture frequency curves and sizing choices rather than one blended number each. Treat the ⅓ OOP figure as [SOURCED estimate] from an MTT-context article (structurally similar to cash at 100bb but not identical); do not treat it as a precise cash-game constant.

---

## 2. Turn barreling and river betting

Solver behavior on later streets is reported far less often as clean aggregate percentages (turn/river strategy is much more run-out-dependent), but GTO Wizard's "Principles of Turn Strategy" and "Principles of River Play" give representative worked examples.

### 2.1 Turn barreling

- **[SOLVED/derivable]** Worked example, K♠8♥4♦ turn Q♠, 100bb: after betting its entire range on the flop, the PFR (UTG) barrels the turn **barely 40% of the time**. Strong hands (two pair, sets) barrel **almost exclusively**; top/second/third pair mostly **check**. Turn sizing shifts to **overbet (>100% pot)**, a jump from the small flop c-bet size, because the range that continues to the turn is much more polarized than the flop c-betting range. (GTO Wizard, [Principles of Turn Strategy](https://blog.gtowizard.com/principles-of-turn-strategy/))
- **[SOLVED/derivable]** Worked example, 9♠8♠6♥ turn (texture not fully specified in extract), 100bb: PFR barrels **less than half** the flop-betting range, using **small sizing** (half-pot most common) rather than overbetting — the opposite sizing conclusion from the K84Q spot, because here the turn card didn't shift range equities as sharply in the PFR's favor. (GTO Wizard, same source)
- **[SOLVED/derivable]** Short-stack contrast: at **20bb**, the same K84Q line's most common turn bet size compresses to **50% pot** (vs. overbet at 100bb), because stack-to-pot ratio constraints change optimal sizing — a reminder that barreling numbers are stack-depth-specific and don't transfer directly between 20bb and 100bb play. (GTO Wizard, same source)
- **Takeaway (not a universal number):** there is no single canonical "turn barrel %" — GTO Wizard's own examples show ~40% and <50% barreling in two different specific run-outs. Barreling frequency is a function of (a) how the turn card shifts range advantage, and (b) effective stack depth. Any single-number turn-barrel heuristic used in the app should be presented as illustrative, not canonical.

### 2.2 River betting

- **[SOLVED/derivable]** Worked example, A♠T♥3♠8♣2♣ runout after an UTG flop barrel, 100bb: on the river, the out-of-position defender (BB) mixes **checks with small "blocking" bets (~10% pot)**, using a linear range (bluffs through top pair, two pair, sets all included) rather than a polarized one. Facing that 10%-pot block bet, the original bettor (UTG) **folds at a rate higher than MDF would suggest** — i.e., real play/solver output diverges from naive MDF math because of range and blocker considerations. (GTO Wizard, [Principles of River Play](https://blog.gtowizard.com/principles-of-river-play/))
- **[SOLVED/derivable]** Same board, alternate line where the turn checks through: BB's river betting frequency is **roughly 50%**, but the sizing shifts from the 10%-pot blocker toward **larger bets, including overbets**, and the value/bluff mix repolarizes accordingly (UTG uses a 275%-pot shove built around straights/most sets, and an 85%-pot bet with most two-pairs and remaining sets; BB counter-raises with 55%-pot and 222%-pot shove sizes in the reverse direction). (GTO Wizard, same source)
- **General principle (well-established, not just this example):** river bets tend to be the most **polarized** and often the **largest relative-to-pot** of any street, because no further cards are coming — hand values are fixed, so a bet is either pure value (targeting worse hands that call) or pure bluff (targeting better hands that fold), with little of the "protection"/equity-denial logic that shapes flop and turn sizing. (GTO Wizard, [All You Need to Know About Our Solutions](https://blog.gtowizard.com/all-you-need-to-know-about-our-solutions/); [Principles of River Play](https://blog.gtowizard.com/principles-of-river-play/))

---

## 3. Multiway pot adjustments

### 3.1 The "c-bet roughly halves HU→3-way" claim — verified, with the correct mechanism

**Verdict: directionally correct and well-supported, but the magnitude and mechanism need precision.** Multiple independent sources converge on "cut your multiway bluffing/c-bet frequency in half or more relative to heads-up," and the underlying math explains why:

- **[SOURCED estimate]** "You should cut your bluffing frequency in half (or more) compared to heads-up pots when playing multiway." The reasoning given: if a bluff needs one opponent to fold X% of the time to break even heads-up, in a 3-way pot you need **both** remaining opponents to fold, and if they fold independently at rate p each, the probability both fold is p². A bet that's break-even at 33% heads-up folds needs each of two opponents to fold at **~58%** each to hit the same combined fold-through rate — i.e., the bar for a profitable bluff rises sharply, not linearly, with each additional live opponent. (GTOWarrior, [The Big Difference Between Heads-Up and Multiway Poker](https://www.gtowarrior.com/articles/difference-heads-up-multiway-poker); math cross-checked independently)
- **[SOURCED estimate]** GTO Wizard's own worked comparison (T♠7♥4♠, CO opens, called by BTN, with BB also live) shows the mechanism in a real solve: **heads-up**, CO's ¼-pot c-bet to BTN alone gets ~73% calls, ~17% raises, ~10% folds. **Add the live BB (3-way)**, and BTN's response to the *same* ¼-pot c-bet shifts to ~39% calls, ~30% raises, ~31% folds — BTN plays a much wider raise-or-fold, narrower flat-calling strategy, because BTN also has to worry about BB behind. (GTO Wizard, [Monkey in the Middle: 3-Way Pot Heuristics](https://blog.gtowizard.com/monkey-in-the-middle-3-way-pot-heuristics/)) — note this is a *response* frequency shift, not a direct HU-vs-3-way c-bet frequency comparison from the raiser's seat, so it corroborates the mechanism (opponents must be individually more careful, betting ranges must tighten) rather than being the literal "70%→35%" source number.
- A separate, frequently-cited (but not independently re-verified in this pass) figure states c-betting frequency drops from **roughly 70% heads-up to around 35% three-way** in aggregate solver studies — i.e., very close to a literal halving. This number appeared consistently across secondary summaries of GTO Wizard multiway content but I could not trace it to one specific primary GTO Wizard article/URL with the exact 70%/35% figures stated verbatim during this research pass. **Tag this specific 70%→35% pairing as [HEURISTIC/uncertain — multiway not solved] pending a direct primary-source confirmation**, even though the general "roughly halves" direction and magnitude are corroborated by the independent fold-math above and by GTO Wizard's own MDF-distribution numbers in §3.3.

**Recommendation for the app's doc:** keep "c-bet frequency roughly halves HU→3-way" as the working heuristic — it's well-supported directionally and by the fold-probability math — but cite it as [SOURCED estimate]/[HEURISTIC], not [SOLVED], and avoid stating "70%→35%" as an exact solver output unless a primary citation with those exact numbers is located later.

### 3.2 Value betting tightens, bluffing range shrinks (mechanism, not just frequency)

- **[SOURCED estimate]** GTO Wizard's multiway tips: "Stop range betting" — don't bet your entire range the way you might heads-up; "give up more often with trash"; "tighten your value betting thresholds" — meaning hands that are good enough to bet for value heads-up (e.g., some two-pairs, some top-pairs) may need to move to check/call or give up multiway because a wider field of live hands drags down their equity faster than in a 2-way pot. Worked example: on A♣T♣2♠, an overpair that comfortably value-bets heads-up sees "some two-pair and strong top pairs falling *behind* calling ranges" once a third player is live — the same made-hand strength is relatively weaker multiway because more live hands can have you beat or be live draws. (GTO Wizard, [10 Tips for Multiway Pots in Poker](https://blog.gtowizard.com/10-tips-multiway-pots-in-poker/))
- **[SOURCED estimate]** In 3-way pots, raises (not just folds) become a bigger part of a defender's response mix than heads-up — in the T74 example above, BTN's raise frequency versus CO's c-bet rose from ~17% (HU) to ~30% (3-way present), which is a further reason the raiser must value-bet tighter and bluff less: a wider range of "raise as a bluff-catcher-denial move" appears from defenders who now also have to worry about the third player behind them. (GTO Wizard, [Monkey in the Middle](https://blog.gtowizard.com/monkey-in-the-middle-3-way-pot-heuristics/))

### 3.3 MDF distribution across multiple defenders

- **[SOLVED/derivable]** (this part is straightforward game-theory algebra, not a multiway-equilibrium claim) — for a bet of size b (fraction of pot), heads-up MDF is `pot / (pot + bet)`. When multiple defenders must collectively supply that same aggregate fold-equity denial, **each individual defender's required *average* folding frequency shrinks** roughly as the n-th root of the heads-up alpha, spreading the "defense burden" across the field:
  - **1%-pot bet:** heads-up requires ~99% defense; in a 9-way pot, average per-player defense drops to **~44%**. (GTO Wizard, [10 Tips for Multiway Pots in Poker](https://blog.gtowizard.com/10-tips-multiway-pots-in-poker/))
  - **10%-pot bet:** heads-up requires ~91% defense; in an 8-way pot, average per-player defense drops to **~26%**. (GTO Wizard, same source)
  - Formula as stated by GTO Wizard: average per-player folding frequency ≈ (heads-up alpha) raised to the (1/n) power, where n = number of defending players. This is a mathematical consequence of needing the *product* of survival probabilities to match the heads-up bar, not a solved-equilibrium claim about ranges/actions — it tells you the aggregate defense rate should roughly divide across defenders, not how any *individual* range should be constructed. **[SOLVED/derivable]** as arithmetic; how real ranges implement it is [HEURISTIC].

### 3.4 No unique game-theoretic solution in multiway — explicit citations

This is the most important caveat to carry into the app's doc: **every multiway number above is an approximation**, not output from a solved game in the way heads-up solves are.

- **[Explicit citation]** "There is no such thing as an unexploitable strategy in multiway scenarios." Multiplayer games can have **infinitely many Nash equilibria**, and reaching *some* Nash equilibrium doesn't guarantee good performance against opponents who aren't also playing that same equilibrium — unlike heads-up zero-sum poker, where any Nash equilibrium is unexploitable regardless of what the opponent does. GTO Wizard illustrates this with 3-player Kuhn poker, showing infinitely many equilibria exist even in that trivially small toy game. (GTO Wizard, [Quirks of Nash Equilibrium in Multiway](https://blog.gtowizard.com/quirks_of_nash_equilibrium_in_multiway/))
- **[Explicit citation]** Commercial multiway solves (e.g., GTO Wizard's multiway product) are explicitly described as **approximations**, referencing Noam Brown's research finding that the same CFR-based (counterfactual regret minimization) approximation methods that converge to a Nash equilibrium in 2-player poker still work "effectively in practice" for 6-player poker, even without a formal equilibrium guarantee. Brown and Sandholm's Pluribus bot (published in *Science*, 2019) beat human professionals in 6-player no-limit hold'em using self-play plus real-time search, without computing an exact Nash equilibrium — because none is guaranteed to exist uniquely, or to be tractable, in >2-player games. (GTO Wizard, [10 Tips for Multiway Pots in Poker](https://blog.gtowizard.com/10-tips-multiway-pots-in-poker/); Brown & Sandholm, ["Superhuman AI for multiplayer poker," *Science* 365(6456), 2019](https://noambrown.com/papers/19-Science-Superhuman.pdf))
- **Practical implication stated directly by GTO Wizard:** "In complex [multiway] spots, playing well is the priority" — i.e., the goal in multiway strategy content is *sound, hard-to-exploit play*, not *the* unique optimal strategy, because no such single unique optimal strategy is guaranteed to exist the way it does heads-up. (GTO Wizard, [Quirks of Nash Equilibrium in Multiway](https://blog.gtowizard.com/quirks_of_nash_equilibrium_in_multiway/))

**Bottom line for the app's content pack:** any multiway c-bet/value-bet/MDF number (including the "~halves HU→3-way" heuristic in §3.1) should be labeled in-app as an approximate heuristic, never presented as a solved-game frequency the way a heads-up single-raised-pot flop c-bet number can be.

---

## 4. Summary table

| Claim | Tag | Key number(s) | Source |
|---|---|---|---|
| Dry board (e.g. Q♥Q♣6♦) c-bet: high freq, 33% pot | [SOURCED estimate] | 33% pot size; BB folds ~37% | [GTO Wizard – Mechanics of C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/) |
| Wet board (K♥J♥7♦) c-bet: bigger, less often | [SOURCED estimate] | 75%/125% pot; BB folds ~62% | [GTO Wizard – Mechanics of C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/) |
| Super-wet monotone straight board (Q♦J♦T♦): small size, near 50/50 bet-check | [SOLVED/derivable] | 33% pot; BB checks back 98%; PFR ~50/50 bet-check | [GTO Wizard – Mechanics of C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/) |
| Medium-connectivity boards: ~55–60% c-bet, ≥50% pot | [SOURCED estimate] | 55–60% freq; 50–75% pot | [Upswing Poker – Level-Up #4](https://upswingpoker.com/podcast/ep4-c-bet-frequency/) |
| Low disconnected boards from early position: near-0% c-bet | [SOURCED estimate] | 0–20% | [Upswing Poker – Level-Up #4](https://upswingpoker.com/podcast/ep4-c-bet-frequency/) |
| OOP aggregate c-bet frequency ~⅓ (100bb) | [SOURCED estimate] | <33% | [GTO Wizard – OOP C-Betting](https://blog.gtowizard.com/flop-heuristics-oop-c-betting-in-mtts/) (MTT-context article) |
| Turn barrel example: ~40% continue, overbet sizing | [SOLVED/derivable] | ~40%; >100% pot | [GTO Wizard – Principles of Turn Strategy](https://blog.gtowizard.com/principles-of-turn-strategy/) |
| River bets most polarized/largest street | [Well-established principle] | n/a | [GTO Wizard – Principles of River Play](https://blog.gtowizard.com/principles-of-river-play/) |
| C-bet/bluff frequency "roughly halves" HU→3-way | [SOURCED estimate] (mechanism verified; exact 70%→35% pairing not independently re-traced to one primary source) | ~2x reduction; fold-through math requires ~58% per-opponent fold vs ~33% HU for 2 live opponents | [GTOWarrior](https://www.gtowarrior.com/articles/difference-heads-up-multiway-poker); [GTO Wizard – Monkey in the Middle](https://blog.gtowizard.com/monkey-in-the-middle-3-way-pot-heuristics/) |
| MDF divides across defenders (~n-th root of HU alpha) | [SOLVED/derivable] (arithmetic) | 1%-pot: 99%→44% (9-way); 10%-pot: 91%→26% (8-way) | [GTO Wizard – 10 Tips for Multiway Pots](https://blog.gtowizard.com/10-tips-multiway-pots-in-poker/) |
| No unique Nash equilibrium multiway; solvers approximate | [Explicit citation] | infinitely many equilibria (3-player Kuhn poker example) | [GTO Wizard – Quirks of Nash Equilibrium in Multiway](https://blog.gtowizard.com/quirks_of_nash_equilibrium_in_multiway/); [Brown & Sandholm, Science 2019](https://noambrown.com/papers/19-Science-Superhuman.pdf) |

---

## 5. Sources

- GTO Wizard, [The Mechanics of C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/)
- GTO Wizard, [Flop Heuristics: IP C-Betting in Cash Games](https://blog.gtowizard.com/flop-heuristics-ip-c-betting-in-cash-games/)
- GTO Wizard, [Flop Heuristics: OOP C-Betting in MTTs](https://blog.gtowizard.com/flop-heuristics-oop-c-betting-in-mtts/)
- GTO Wizard, [Flop Heuristics: IP C-Betting in MTTs](https://blog.gtowizard.com/flop-heuristics-ip-c-betting-in-mtts/)
- GTO Wizard, [Principles of Turn Strategy](https://blog.gtowizard.com/principles-of-turn-strategy/)
- GTO Wizard, [Principles of River Play](https://blog.gtowizard.com/principles-of-river-play/)
- GTO Wizard, [All You Need to Know About Our Solutions](https://blog.gtowizard.com/all-you-need-to-know-about-our-solutions/)
- GTO Wizard, [Monkey in the Middle: 3-Way Pot Heuristics](https://blog.gtowizard.com/monkey-in-the-middle-3-way-pot-heuristics/)
- GTO Wizard, [10 Tips for Multiway Pots in Poker](https://blog.gtowizard.com/10-tips-multiway-pots-in-poker/)
- GTO Wizard, [Quirks of Nash Equilibrium in Multiway](https://blog.gtowizard.com/quirks_of_nash_equilibrium_in_multiway/)
- GTO Wizard, [GTO Wizard AI Custom Multiway Solving](https://blog.gtowizard.com/gto-wizard-ai-custom-multiway-solving/)
- Upswing Poker, [How Often Should You C-Bet? Level-Up #4](https://upswingpoker.com/podcast/ep4-c-bet-frequency/)
- GTOWarrior, [The Big Difference Between Heads-Up and Multiway Poker](https://www.gtowarrior.com/articles/difference-heads-up-multiway-poker)
- Brown, N. & Sandholm, T., ["Superhuman AI for multiplayer poker,"](https://noambrown.com/papers/19-Science-Superhuman.pdf) *Science* 365(6456), 2019 — primary academic source for the "no guaranteed unique equilibrium in >2-player games" claim and Pluribus's self-play + search approximation approach.

## 6. Unsourced / needs follow-up

- The frequently-repeated **"70% HU → 35% 3-way c-bet frequency"** exact pairing could not be traced to one primary GTO Wizard article with those literal figures during this pass (search summaries referenced it, but direct article fetches did not surface the exact numbers verbatim). The *direction and rough magnitude* (roughly halving) is well corroborated by independent fold-probability math and by GTO Wizard's own T74 3-way worked example, so the heuristic itself is safe to keep — just don't cite "70%→35%" as a verbatim solver output without a firmer primary source.
- Could not obtain one clean blended "IP c-bets X%, OOP c-bets Y%" single-number pair for cash games from a single article; the OOP figure (~⅓) is sourced from an MTT-context article, which is structurally close to 100bb cash but not identical — flag as an approximation if used for exact calibration targets.
- Turn/river "canonical" frequencies are inherently run-out-specific in the source material (GTO Wizard presents worked examples, not aggregate universal percentages) — no single canonical turn-barrel % or river-bet % exists across all boards; only illustrative per-scenario numbers were found.
