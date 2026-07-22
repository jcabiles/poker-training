# Preflop 3-Bet / 4-Bet / 5-Bet Calibration Research

Scope: NLHE cash, ~100bb effective, 6-max unless noted. Compiled from public poker-training
content (Upswing Poker, SplitSuit/Red Chip family, GTO Wizard blog, PokerCoaching, GipsyTeam,
Poker.pro) rather than raw solver output — no solver was run directly for this document. Every
claim below is tagged:

- **[SOLVED/derivable]** — a number a solver would actually output at equilibrium, sourced from
  a site that says it ran/reports solver output (GTO Wizard blog, or an author explicitly citing
  a solver run).
- **[SOURCED estimate]** — a specific number published by a credible training site, but the
  underlying solver/methodology isn't fully disclosed (stakes, rake, exact stack depth, or
  solver identity is vague or unstated).
- **[HEURISTIC/uncertain]** — a rule-of-thumb, qualitative claim, or a number that's plausible
  but not solver-verified in the sources found.

**Standing caveat (applies to nearly every number in this doc):** GTO Wizard's flagship preflop
solutions are solved for the **PokerStars 500 Zoom rake structure — 5% rake capped at 0.6bb**,
not a rake-free game [SOLVED/derivable, source: GTO Wizard]. GTO Wizard does also publish
lower-rake and ChipEV (rake-free) variants, but the numbers below drawn from secondary
commentary don't always specify which rake structure was used. Rake pulls both 3-bet and
4-bet frequencies *tighter/more value-heavy* than a truly rake-free (theoretical) game, and live
low-stakes rake (often higher % + lower/no cap than online) would pull them tighter still. Live
opponent pools also fold less to 3-bets and over-fold to 4-bets versus solver-calibrated villains,
which independently pushes exploitative ranges wider/looser than pure equilibrium. Treat every
percentage below as an anchor, not a rule.

---

## 1. 3-bet ranges: frequency, composition, sizing

### 1.1 General frequency/value-bluff ratio math [SOLVED/derivable]

SplitSuit's breakdown of 3-bet range "purity" (i.e., what fraction of a stated 3-bet % is genuine
value) gives the clearest quantitative skeleton found:

- Value-only benchmarks by hand-count: **KK+ = 0.9%** of all starting hands, **QQ+/AK = 2.6%**,
  **TT+/AQ+ = 4.7%** of the 1,326-combo deck.
- If a player 3-bets **3.5%** total with a **QQ+/AK (2.6%)** value core, **74%** of that range is
  "very strong" value (2.6/3.5) — implying a small residual bluff/mixing component.
- If a player "resteals" **12%** with a **TT+/AQ+ (4.7%)** value core, only **39%** of the range is
  strong value — the rest (61%) is bluffs/thin value, characteristic of a wide, aggressive
  (often blind-vs-steal) 3-bet.
- A **6%** 3-bet range built on **TT+/AQ+ (4.7%)** value is **78%** value-weighted.

  Source: [Understanding 3-Bet Ranges In 2026](https://www.splitsuit.com/understanding-3-bet-ranges) (SplitSuit/Red Chip Poker).

This shows the general shape rather than one canonical number: **total 3-bet % and value/bluff
split move together** — tighter total 3-bet frequencies are automatically more value-heavy even
with an unchanged value-hand definition, and looser total frequencies (e.g., blind-vs-button
resteal spots) necessarily carry much more bluff/air weight to stay balanced.

### 1.2 Representative position-pair frequency [SOURCED estimate]

- **BTN vs MP** (open from MP, BTN 3-bets): value 3-bet range **0.9%**, bluff 3-bet range
  **2.11%**, total 3-bet range **≈3.01%**. Source doesn't specify exact solver/rake/stack depth,
  but is presented as a representative GTO-informed figure.
  Source: search-aggregated citation traced to 3-bet range discussion (Upswing Poker /
  SplitSuit-adjacent content); treat the exact percentages as indicative rather than a directly
  verified single-page citation — flagged **[SOURCED estimate, weak provenance]**.
- **BTN vs CO** (50–60bb effective, per SplitSuit-linked commentary): polar 3-bet built from
  **QQ+, AK, plus A5s/A4s** as the bluff candidates, while **TT–JJ, AQ, KQs/QJs/JTs** are
  flatted rather than 3-bet. This is a qualitative composition claim, not a %.
  Source: [Understanding 3-Bet Ranges In 2026](https://www.splitsuit.com/understanding-3-bet-ranges).
- **BTN 3-bets a CO open**, response-side data point: the **Cutoff folds only ~33%**, calls
  **~50%**, and 4-bets the rest, at **50bb effective**, using a Lucid Poker preflop-chart
  visualization (3-bet sized to **6.6bb**). This is villain-response data, useful for calibrating
  how a 3-bettor's bluff frequency should scale against a given fold%.
  Source: [3-Bet Bluff Range Construction, Strategy & Charts](https://upswingpoker.com/building-bluffing-ranges-smarter-3-bets/) (Upswing Poker, Leo Song-Carrillo, Aug 22 2025).

### 1.3 Linear/merged (IP) vs polarized (OOP) construction [HEURISTIC/uncertain, but near-universal consensus across sources]

- **Rule of thumb repeated across every source checked:** "OOP vs a wide range → linear
  (merged); IP vs a tight range → polarized." A **linear** range (premium + strong broadways,
  no explicit air) performs best against opponents who don't fold enough to 3-bets (calling
  stations, or spots where players remain to act behind, e.g. **SB vs BTN** commonly plays as a
  strong linear range). A **polarized** range (nuts + bluffs, with a gap in the middle) performs
  best when facing/being a tight range with folding tendencies and no players left to act behind
  the 3-bettor, e.g. **BTN vs CO/MP** closing the action.
  Sources: [Polarized Ranges vs Linear (Merged) Ranges Explained](https://upswingpoker.com/polarized-vs-linear-ranges/) (Upswing);
  [How to Size Your 3-Bets Correctly in Poker](https://www.poker.pro/strategy/how-to-size-your-3-bets-correctly-in-poker-the-gto-and-live-player-guide/) (Poker.pro, Aytan Eldarova, Dec 20 2025).
- **SB 3-betting vs BTN open, 100bb:** SB plays a "very good linear range"; **BB 3-betting vs
  BTN open** plays a more **polarized** range built from **AQo+, ATs+, KQo, KTs+, 66+** as value,
  with **A3o–A7o "in certain frequencies"** as bluffs. Also noted: SB should 3-bet **roughly
  twice as often** as it flat-calls a BTN open, at 100bb.
  Source: [Constructing 3-Bet And vs. 3-Bet Ranges](https://www.poker.pro/strategy/constructing-3-bet-and-vs-3-bet-ranges-33/) (Poker.pro Team, Jun 22 2020) — **[SOURCED estimate, dated 2020, no explicit solver/rake citation]**.

### 1.4 3-bet sizing: multiplier and position table [SOURCED estimate]

Two independently-sourced tables roughly agree on shape (IP smaller, OOP bigger, size grows
as stacks/position worsen for the 3-bettor):

| Source | IP 3-bet size | OOP 3-bet size |
|---|---|---|
| SplitSuit (100bb, standard) | 2.5x–3x open | 3x–4x open |
| SplitSuit, short-stacked (<40bb) | 2.2x–2.5x open | 2.2x–2.5x open |
| SplitSuit, deep (150bb+) | "standard sizing maintained" (i.e., ~2.5-3x, no further detail given) | — |
| Upswing (100bb, non-ante) | ~3x open | ~4–4.5x open |
| Poker.pro (Aytan Eldarova, Dec 2025), 100bb | 3x open | 4–5x open |
| Poker.pro, 40–60bb | 2.5–3x open | 3.5–4x open |
| Poker.pro, 20–30bb | 2.2–2.5x open or jam | 2.5–3x open or jam |

Position-pair examples from Poker.pro (vs a 2.5x open, 100bb, framed as GTO-Wizard-informed
commentary rather than a raw solver export — **[SOURCED estimate]**):

| Matchup | 3-bet size | Approx. multiple of open |
|---|---|---|
| BTN vs CO | 6–7bb | ~2.5x |
| SB vs BTN | 9–10bb | ~4x |
| BB vs BTN | 9–10bb | ~4x |
| HJ vs UTG | 8–9bb | ~3.5x |

Sources: [Understanding 3-Bet Ranges In 2026](https://www.splitsuit.com/understanding-3-bet-ranges) (SplitSuit);
[3-Bet Preflop Strategy & Range Charts](https://upswingpoker.com/3-bet-strategy-aggressive-preflop/) (Upswing Poker);
[How to Size Your 3-Bets Correctly in Poker](https://www.poker.pro/strategy/how-to-size-your-3-bets-correctly-in-poker-the-gto-and-live-player-guide/) (Poker.pro, Dec 2025).

**Core mechanism cited for why OOP sizes bigger [HEURISTIC/uncertain, but consistently repeated]:**
"In position, the caller can realize more equity for the same price, so IP 3-bettors must charge
relatively less to keep calling ranges honest; OOP 3-bettors must charge more because their
opponent's positional advantage lets them profitably continue wider at a given price." Source:
[How to Size Your 3-Bets Correctly](https://www.poker.pro/strategy/how-to-size-your-3-bets-correctly-in-poker-the-gto-and-live-player-guide/); also stated in GTO Wizard's own framing: "OOP uses relatively bigger sizes, while IP uses relatively smaller ones... in position is able to call more hands compared to out of position versus the same size." [SOURCED estimate — GTO Wizard-attributed principle, not a direct blog-post quote verified against the live blog].

---

## 2. 4-bet ranges: value core, Axs blocker bluffs, sizing

### 2.1 Value composition [SOURCED estimate / HEURISTIC blend]

- **AA/KK: always 4-bet.** **QQ/AK: mix**, frequency depending on position and opponent
  tendencies. Against earlier positions / tighter players, the value 4-bet core is typically
  **QQ+, AK, sometimes JJ**. In loose spots (blind-vs-blind, BTN vs SB) value can widen to
  **AQ and 99** or wider. In live/rec-heavy games, some regs shrink value all the way to
  **KK+ only**.
  Source: [Mastering the 4-Bet](https://pokercoaching.com/blog/4-betting-strategy/) (PokerCoaching, Jonathan Little, Dec 4 2025); [There's Big Money in 4-Bet & 5-Bet Pots](https://upswingpoker.com/4-bet-5-bet-preflop-strategy/) (Upswing Poker, Ryan Fee, Oct 14 2016).
- A GTO-solver-referencing example (specific hand, not a generic position pair) found via
  a Medium writeup of a solved 4-bet-pot spot: the 4-bet range totaled **46 combos (≈3.5%** of
  1,326 preflop combos), while the *opponent's calling/broader continuing range* (suited
  broadways + Ax-suited) ran **77 combos (≈6%)**. In that specific solve, **JJ 4-bet/raises
  37% of the time**, else calls — i.e., JJ is a mixed, not pure, 4-bet in the solved spot. Note:
  this is one hand-specific solver export from a third-party blog, not a general position-pair
  table — treat as illustrative of *mixing near the bottom of a 4-bet range*, not as a canonical
  frequency. **[SOLVED/derivable for that one specific spot; not generalizable without the
  underlying position/sizing context, which the source doesn't fully specify]**.
  Source: [Poker: 4-bet pots](https://mikefowlds.medium.com/poker-4-bet-pots-aff8f9149d39) (Mike Fowlds, Medium).

### 2.2 Bluff composition: Axs/blockers [SOLVED/derivable for the mechanism; specific % is SOURCED estimate]

- **Best 4-bet bluffs: suited wheel aces, A5s down to A2s.** Rationale given everywhere: they
  block combos of AA/AK (the hands most likely to continue over a 4-bet) while leaving the
  villain's *folding* range (broadway offsuit, weaker suited kings, etc.) intact — i.e., they
  **block calls, unblock folds**. A5s specifically is favored over A2s–A4s because it retains
  **backdoor straight (wheel) and flush equity when called**, whereas A2s "is less promising"
  because unpaired-low-card removal has a smaller effect and it has less residual equity when
  called.
  Sources: [Blockers & Unblockers: The Secret to Picking Great Bluffs](https://blog.gtowizard.com/blockers-unblockers-the-secret-to-picking-great-bluffs/) (GTO Wizard blog);
  [Why Do Poker Solvers Love Ace Five Suited So Much?](https://www.gipsyteam.com/news/27-11-2024/why-do-poker-solvers-love-ace-five-suited) (GipsyTeam, Nov 27 2024);
  [There's Big Money in 4-Bet & 5-Bet Pots](https://upswingpoker.com/4-bet-5-bet-preflop-strategy/) (Upswing, Ryan Fee).
- **Quantified example (one specific solved spot, BTN facing a 3-bet from UTG, deep stack,
  cited by GipsyTeam):** solver **4-bets A5s 70% of the time** (mixed, not pure) in that spot.
  In a separate spot (BTN vs UTG open, deep), the same source states BTN **3-bets A5s 60%** and
  **calls 40%**. In a 40bb MTT-style spot (BTN vs SB 3-bet), A5s becomes a **100% 4-bet-jam**.
  These are all single illustrative solved nodes from one article, not a generalized
  frequency table across all position pairs — **[SOLVED/derivable for the specific cited nodes;
  do not extrapolate the exact % to other matchups without re-solving]**.
  Source: [Why Do Poker Solvers Love Ace Five Suited So Much?](https://www.gipsyteam.com/news/27-11-2024/why-do-poker-solvers-love-ace-five-suited) (GipsyTeam, Nov 27 2024).
- Other bluff candidates mentioned secondarily: **suited connectors with playability (e.g.
  76s)** and **offsuit broadways (e.g. AJo)** — hands "just barely not strong enough to profitably
  call the 3-bet," repurposed as 4-bet bluffs instead of flats. **[HEURISTIC/uncertain]**.
  Source: [There's Big Money in 4-Bet & 5-Bet Pots](https://upswingpoker.com/4-bet-5-bet-preflop-strategy/).

### 2.3 4-bet sizing [SOURCED estimate — thin]

None of the sources found gave a clean "x the 3-bet" multiplier table comparable to the 3-bet
sizing table above. The only concrete number found was from the single solved-spot Medium
example: the solver's 4-bet sizing there was **~28bb** against a specific 3-bet, framed by the
author as "GTO raise size." No general multiplier (e.g., "2.2–2.5x the 3-bet IP, 2.5x+ OOP" — a
commonly *repeated* heuristic in the wider poker-training world) was found explicitly stated
with a citation in this search pass. Flag: **the 4-bet-sizing-multiplier claim commonly seen in
community charts (roughly 2.2x–2.5x the 3-bet) was NOT independently verified with a citable
source in this research pass — do not treat it as confirmed.** [HEURISTIC/uncertain, unsourced
in this pass].

---

## 3. 5-bet / all-in ranges at 100bb

### 3.1 Composition [HEURISTIC/uncertain — could not find a solver-sourced numeric table]

- General consensus across sources: 5-bets at 100bb are **"usually shoves," "mainly restricted
  to value hands"** — commonly cited informally elsewhere in the training-content ecosystem as
  roughly **QQ+/AK**, but this exact "QQ+/AK" framing was **not found stated with a citation in
  this research pass**; the sources fetched only confirmed the *shape* (value-heavy, occasional
  blocker bluff) without giving a hand-by-hand table for 100bb specifically.
  Source: [There's Big Money in 4-Bet & 5-Bet Pots](https://upswingpoker.com/4-bet-5-bet-preflop-strategy/) (Upswing, Ryan Fee) — notes 5-bets are shove-dominant and value-heavy but gives only one concrete example (below), not a range table.
- **One cited real-hand example, not a general range statement:** Isaac Haxton jamming **A5s**
  as a 5-bet bluff at **100bb effective** in a real high-stakes hand — used by the source purely
  to illustrate that *some* suited-wheel-ace 5-bet bluffing exists at 100bb in practice, not as
  a frequency claim. **[anecdotal, not solver-sourced]**.
- SplitSuit/Red Chip has video content specifically on "Going All-In Preflop With AK & QQ,"
  but the actual numeric content is paywalled (Red Chip Poker PRO membership) and was not
  accessible in this research pass — **flag as unverified**, only the existence of the
  training material was confirmed.
  Source: [Going All-In Preflop With AK & QQ In 2026](https://www.splitsuit.com/all-in-preflop-with-ak-qq) (SplitSuit/Red Chip Poker) — paywalled.

### 3.2 How stack depth changes the range [HEURISTIC/uncertain]

- Community/forum-level commentary (Run It Once forum, not a primary solver source) suggests
  that at very deep stacks (**200–300bb**), many strong players believe **shoving QQ or AK is no
  longer good, and even KK becomes questionable** as a pure jam — implying the 5-bet-shove
  value threshold tightens as effective stacks grow, converging toward AA/KK(mixed) only. This
  is **forum opinion, not a solver citation** — **[HEURISTIC/uncertain, weak provenance]**.
  Source: [Deep stack 5betting range / size?](https://www.runitonce.com/nlhe/deep-stack-5betting-range-size/) (Run It Once forum).
- At shallower stacks (sub-40bb, MTT-style), the GipsyTeam A5s example above showed a
  bluff 5-bet-equivalent (4-bet-jam) hand going from a **mixed 60–70%** strategy at 100bb-ish
  depth to a **100% jam** at **40bb** — consistent with the general principle that **shove/fold
  simplification increases and bluff-hand jamming frequency increases as effective stacks
  shrink**, because fold equity and pot odds math both favor wider shoving at lower depths.
  **[SOLVED/derivable for that one specific cited spot only]**.
  Source: [Why Do Poker Solvers Love Ace Five Suited So Much?](https://www.gipsyteam.com/news/27-11-2024/why-do-poker-solvers-love-ace-five-suited) (GipsyTeam).

**Net assessment for §3:** this was the weakest-sourced section. No source found in this pass
published a clean "5-bet range at 100bb = X%/these hands" table with a disclosed solver/rake/
stake. Any "QQ+/AK is the 100bb 5-bet range" heuristic commonly used in casual poker discussion
should be treated as **[HEURISTIC/uncertain]** until verified against an actual solver run or a
source that discloses its methodology.

---

## 4. Blocker logic for bluff selection

### 4.1 Card removal mechanics [SOLVED/derivable — combinatorics is exact math, not solver opinion]

- In a single-raised pot (no blockers), a villain's continuing range can hold **6 combos of AA**
  and **12 combos of AK** (any two, before removal). If the 3-bettor/4-bettor **holds one Ace**,
  those drop to **3 combos of AA** and **8 combos of AK** — i.e., holding any Ace **halves AA
  combos and reduces AK combos by a third**. This directly lowers the probability the bluff runs
  into a hand that will never fold, which is exactly why Ax hands (suited or not) are structurally
  favored as bluff-3-bet/4-bet candidates over otherwise-similar non-Ax hands.
  Source: [Card Removal in Poker: What It Means & Why It Matters](https://beyondgto.com/glossary/card-removal) (BeyondGTO); corroborated qualitatively by [Blockers & Unblockers](https://blog.gtowizard.com/blockers-unblockers-the-secret-to-picking-great-bluffs/) (GTO Wizard blog).

### 4.2 Why A5s specifically (not A2s–A4s, not AJo/AQo) [SOLVED/derivable mechanism; HEURISTIC ranking of A2s-A5s]

Two distinct properties combine, repeated consistently across GTO Wizard and GipsyTeam:

1. **Blocks calls:** Any Ax blocks 3 (not 6) AA combos and 8 (not 12) AK combos, per §4.1 — this
   is the "blocker" half.
2. **Unblocks folds:** A5s does **not** remove cards from the villain's *folding* range — hands
   like **K9s–K5s, QTs–Q8s** (suited kings/queens that fold to a 4-bet) remain fully live in the
   villain's range, because A5s doesn't overlap with K- or Q-high suited holdings. This is the
   "unblocker" half — a good bluff blocks what would call and leaves untouched what would fold.
3. **Residual equity when called:** among suited wheel aces, **A5s (and to a lesser extent
   A4s/A3s) retains backdoor straight (wheel: A-2-3-4-5) and flush equity** if called by AA/KK/AK,
   giving it a non-zero floor even when the bluff is snapped off. **A2s is considered weaker**
   for this role because it has one fewer wheel-card synergy consideration and because holding
   the deuce has comparatively less impact on the specific combos most likely to continue
   (i.e., its removal effect on AA/AK is identical to any other Ax, but its backup equity is
   judged slightly worse).
   Source: [Blockers & Unblockers: The Secret to Picking Great Bluffs](https://blog.gtowizard.com/blockers-unblockers-the-secret-to-picking-great-bluffs/) (GTO Wizard blog); [Why Do Poker Solvers Love Ace Five Suited So Much?](https://www.gipsyteam.com/news/27-11-2024/why-do-poker-solvers-love-ace-five-suited) (GipsyTeam, Nov 27 2024).

**Note on A2s vs A5s ranking:** the exact solver-verified ranking among A2s/A3s/A4s/A5s as
bluff candidates (i.e., which combo the solver prefers *first* when only some of them are used)
was described qualitatively ("A5s is the classic choice, A2s is less promising") but **no source
in this pass gave the actual frequency-by-frequency solver comparison across all four
suited-wheel-ace combos in one table** — treat the A5s > A2s preference ordering as
**[HEURISTIC/uncertain]**, even though the underlying blocker/unblocker mechanism itself is
solid combinatorics **[SOLVED/derivable]**.

---

## 5. Bet-size → preflop bluff-frequency relationship

### 5.1 General (any street) sizing/bluff-ratio math [SOLVED/derivable — this is closed-form game theory, not solver opinion]

- **Alpha (α) = risk / (risk + reward)** — the fold frequency a 0%-equity bluff needs to
  break even. Example: betting 5 into a pot of 10 → α = 5/(5+10) = **33%**; villain must fold at
  least a third of the time for a zero-equity bluff at that sizing to break even.
- **Minimum Defense Frequency (MDF) = 1 − α = 1/(1 + bet-size-as-fraction-of-pot)** — how often
  the *defender* must continue to prevent the bettor from profitably bluffing any two cards.
- Corollary bluff:value ratio: a **pot-size bet** should carry roughly **1 bluff for every 2
  value bets (33% of the betting range is bluffs)**; bigger bets require a *higher* bluff ratio
  (proportionally more bluffs relative to value) to stay balanced, smaller bets require fewer.
  Source: [MDF & Alpha](https://blog.gtowizard.com/mdf-alpha/) (GTO Wizard blog).

### 5.2 Applying this preflop [HEURISTIC/uncertain — no source found doing this arithmetic explicitly for 3-bet/4-bet sizes]

- The α/MDF framework is postflop-general math and applies mechanically preflop too (a 3-bet or
  4-bet is just a bet with a specific risk/reward), but **no source found in this research pass
  explicitly published a preflop-specific bluff-frequency table derived from 3-bet or 4-bet
  sizing** (e.g., "at a 4x OOP 3-bet size, the theoretically balanced bluff:value ratio is X:1").
  The closest concrete data point found is the **Cutoff's response to a BTN 3-bet at 50bb**
  (folds 33%, calls 50%, 4-bets the rest) from §1.2 — that is a *villain response frequency*,
  useful for reasoning about what 3-bet size/bluff ratio would be profitable against that
  villain, but it is not itself a bluff-frequency prescription.
  Source: [3-Bet Bluff Range Construction, Strategy & Charts](https://upswingpoker.com/building-bluffing-ranges-smarter-3-bets/) (Upswing Poker).
- **Net assessment:** the *mechanism* (bigger bet size → solver wants a higher bluff:value
  ratio in the betting range, all else equal) is standard, well-established solver theory and
  applies preflop by extension, but a **directly-cited preflop-specific numeric table (e.g., "3x
  3-bet = X% bluffs, 4x 3-bet = Y% bluffs") was not found and should be treated as
  unconfirmed/derivable-but-not-sourced** rather than fabricated to fill the gap.

---

## Sources

1. [Understanding 3-Bet Ranges In 2026](https://www.splitsuit.com/understanding-3-bet-ranges) — SplitSuit / Red Chip Poker.
2. [3-Bet Preflop Strategy & Range Charts](https://upswingpoker.com/3-bet-strategy-aggressive-preflop/) — Upswing Poker.
3. [Polarized Ranges vs Linear (Merged) Ranges Explained](https://upswingpoker.com/polarized-vs-linear-ranges/) — Upswing Poker.
4. [3-Bet Bluff Range Construction, Strategy & Charts](https://upswingpoker.com/building-bluffing-ranges-smarter-3-bets/) — Upswing Poker, Leo Song-Carrillo, Aug 22 2025.
5. [There's Big Money in 4-Bet & 5-Bet Pots](https://upswingpoker.com/4-bet-5-bet-preflop-strategy/) — Upswing Poker, Ryan Fee, Oct 14 2016.
6. [How to Size Your 3-Bets Correctly in Poker: The GTO and Live Player Guide](https://www.poker.pro/strategy/how-to-size-your-3-bets-correctly-in-poker-the-gto-and-live-player-guide/) — Poker.pro, Aytan Eldarova, Dec 20 2025.
7. [Constructing 3-Bet And vs. 3-Bet Ranges](https://www.poker.pro/strategy/constructing-3-bet-and-vs-3-bet-ranges-33/) — Poker.pro Team, Jun 22 2020.
8. [Mastering the 4-Bet: A Poker Coach's Guide to Dominating Preflop Aggression](https://pokercoaching.com/blog/4-betting-strategy/) — PokerCoaching, Jonathan Little, Dec 4 2025.
9. [Blockers & Unblockers: The Secret to Picking Great Bluffs](https://blog.gtowizard.com/blockers-unblockers-the-secret-to-picking-great-bluffs/) — GTO Wizard blog.
10. [MDF & Alpha](https://blog.gtowizard.com/mdf-alpha/) — GTO Wizard blog.
11. [All you need to know about our solutions](https://blog.gtowizard.com/all-you-need-to-know-about-our-solutions/) — GTO Wizard blog (rake/stakes/solve methodology).
12. [Why Do Poker Solvers Love Ace Five Suited So Much?](https://www.gipsyteam.com/news/27-11-2024/why-do-poker-solvers-love-ace-five-suited) — GipsyTeam, Nov 27 2024.
13. [Card Removal in Poker: What It Means & Why It Matters](https://beyondgto.com/glossary/card-removal) — BeyondGTO.
14. [Poker: 4-bet pots](https://mikefowlds.medium.com/poker-4-bet-pots-aff8f9149d39) — Mike Fowlds, Medium (single solved-spot example).
15. [Going All-In Preflop With AK & QQ In 2026](https://www.splitsuit.com/all-in-preflop-with-ak-qq) — SplitSuit/Red Chip Poker (content paywalled; existence only confirmed).
16. [Deep stack 5betting range / size?](https://www.runitonce.com/nlhe/deep-stack-5betting-range-size/) — Run It Once forum (community opinion, not solver-primary).

---

## Explicitly unsourced / not found in this pass — do not treat as fact

- A clean, disclosed-methodology **5-bet/all-in range table at 100bb** (e.g., exact combo list
  for "QQ+/AK shoves"). Only anecdotal and forum-level commentary was found.
- A **4-bet sizing multiplier table** (x the 3-bet) analogous to the 3-bet sizing table in §1.4.
- A **preflop-specific bluff-frequency-by-bet-size table** translating the general α/MDF formula
  into concrete 3-bet/4-bet numbers.
- A **verified, single-source frequency table for BTN vs CO / BB vs BTN / SB vs BTN 3-bet %**
  broken out cleanly by value% / bluff% / total% with disclosed rake and stake — the closest
  found (BTN vs MP: 0.9% value / 2.11% bluff / 3.01% total) had weak page-level provenance and
  should be re-verified against a primary GTO Wizard or Upswing chart export before being
  hard-coded into any calibration spec.
