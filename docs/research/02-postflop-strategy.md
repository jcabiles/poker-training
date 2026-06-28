# Postflop Strategy Framework: Live $1/$2 → $2/$3 NL Cash

**Scope:** Live NLHE cash games only. Postflop play. Simplified-but-sound, modern (solver-era) heuristics.
**Player profile:** Winning $1/$2 player (~200bb effective), targeting $2/$3 move-up.

---

## Table of Contents
1. [Core Postflop Framework: The Three Advantages](#1-core-postflop-framework-the-three-advantages)
2. [Board Texture Classification](#2-board-texture-classification)
3. [Flop Play: C-Betting](#3-flop-play-c-betting)
4. [Facing C-Bets: Defense, Floating, Raising, Donk Betting](#4-facing-c-bets-defense-floating-raising-donk-betting)
5. [Turn Play: Barreling, Check-Raising, Equity Realization](#5-turn-play-barreling-check-raising-equity-realization)
6. [River Play: Value Betting, Bluffing, Bluff-Catching](#6-river-play-value-betting-bluffing-bluff-catching)
7. [Bet Sizing Theory Simplified](#7-bet-sizing-theory-simplified)
8. [Simplified Math Cheat-Sheet](#8-simplified-math-cheat-sheet)
9. [Multiway Adjustments](#9-multiway-adjustments)
10. [Live $1/$2 Leaks and Exploiting Passive/Sticky Opponents](#10-live-12-leaks-and-exploiting-passivezsticky-opponents)
11. [$1/$2 → $2/$3 Adjustments](#11-12--23-adjustments)
12. [What to Drill](#12-what-to-drill)
13. [Sources](#13-sources)

---

## 1. Core Postflop Framework: The Three Advantages

Every postflop decision flows from one master question: **"Who has the advantage here?"** Three overlapping advantages determine the answer:

### 1.1 Positional Advantage
Acting last gives you information every street. This is the most durable advantage in poker:
- **In position (IP):** Act more aggressively. You see what opponent does before deciding. Value-bet and bluff at higher frequency.
- **Out of position (OOP):** Play more defensively and passively. C-bet less, check more, use smaller and more uniform sizes. The OOP disadvantage is permanent and must be respected.

**Heuristic:** IP c-bet frequency is often 15–25% higher than OOP on identical boards. If you're OOP and unsure, checking is usually safe.

### 1.2 Range Advantage
The player whose entire range of possible hands has more equity on the board has range advantage. This is about *ranges*, not individual hands.

- **High, dry boards (A-K-2 rainbow, K-7-3 rainbow):** The preflop raiser almost always has range advantage. Their tight opening range contains more A-x, K-x, and premium pairs.
- **Low, connected boards (8-7-6, 9-7-5):** The caller (often BB) has range advantage. Wider calling ranges contain more two-pair and straight combos.
- **Middle boards (J-8-4, T-7-3):** Contested—board texture determines which range connects better.

**Heuristic:** Ask before every postflop decision: *"Who has range advantage here?"* If you do, bet more. If you don't, check more or size down.

### 1.3 Nut Advantage
Nut advantage is about who holds the *strongest* hands—not average equity but top-end holdings (two pair or better). You can have range advantage without nut advantage and vice versa.

- **You have nut advantage:** Use large sizes. Your opponent faces a dilemma: fold too often (get exploited by your bluffs) or call too often (get crushed by your value).
- **Opponent has nut advantage:** Reduce aggression, check-raise less, size down, or check your medium-strength hands.
- **Neither has clear nut advantage (e.g., paired boards):** Use smaller bet sizes since trips are distributed across both ranges.

**Integration:** When position + range + nut advantage all point your way, be maximally aggressive. When none align, play passively. Mixed signals call for middle-ground frequencies.

---

## 2. Board Texture Classification

Categorize every flop along two axes:

### Axis 1: Connectedness (Static → Dynamic)
| Category | Example | Properties |
|----------|---------|------------|
| Dry/Static | K♦ 7♥ 2♠ rainbow | Few draws possible; hand values mostly fixed; favors preflop raiser |
| Semi-connected | J♠ 8♣ 4♦ | Some straight draws; moderate draw density |
| Wet/Dynamic | J♥ T♥ 7♣ | Many draws; two-pair/straight/flush possibilities; ranges interact heavily |

### Axis 2: High-Card vs. Low-Card
- **High-card boards** (contain A, K, Q, J): Generally favor the preflop raiser's tight opening range.
- **Low-card boards** (below J): Generally favor the caller's wider speculative range, especially the BB.

### Special Textures

**Paired boards (J-J-4, 9-9-2):**
Fewer combos of strong hands exist. Bet frequently but with smaller sizing. Limited nut advantage since trips are in both ranges.

**Monotone boards (A♥-T♥-4♥):**
Drastic reduction in c-betting. Check all medium-strength hands. Value-bet only flushes, sets. Never bluff without a flush draw or redraw.

**Ace-high boards:**
Counter-intuitively, bet *less* often than other high-card boards. The BB can defend more of their Ax hands profitably, check-raise frequency increases, and marginal Ax hands from the raiser's range (A-7, A-6) prefer to check back.

### Who Has Range Advantage: Quick Reference
| Board Type | Range Advantage |
|------------|----------------|
| A-K-x, K-Q-x (high dry) | Preflop raiser |
| K-7-2, A-9-2 (high rainbow uncoordinated) | Preflop raiser (strong) |
| 8-7-6, 9-7-5 (low connected) | BB caller |
| J-T-7 (mid wet) | Contested; closer to 50/50 |
| Paired boards | Raiser slight edge |
| Ace-high with low kickers | Raiser (but contested on Ax combos) |

---

## 3. Flop Play: C-Betting

### 3.1 When to C-Bet vs. Check

**C-bet when:**
- You're in position on a board where you have range advantage and/or nut advantage
- The board is dry and unlikely to hit the caller's range (K-7-2, A-9-3)
- You have a strong hand that wants to build the pot
- You have a draw or equity that benefits from fold equity
- You're in a single-raised pot (SRP) heads-up

**Check when:**
- You're out of position, especially on boards that favor caller's range (low, connected)
- The board is monotone and you lack a flush
- You lack both fold equity and significant equity vs. opponent's calling range
- You have a medium-strength hand (one pair, mediocre kicker) that wants pot control
- It's multiway (3+ players—see Section 9)
- You want to protect your checking range against aggressive opponents

**OOP raisers check more on:** Low boards (below J), connected boards, monotone boards, and whenever the caller will have nut advantage (e.g., 6-5-4 in BB vs BTN spot).

### 3.2 C-Bet Sizing Strategy

Modern solver-era approach: **match size to texture**.

| Situation | Size | Rationale |
|-----------|------|-----------|
| Dry, static, high-card board (K-7-2 rainbow) | 25–33% pot | Small size still applies pressure; range advantage means you c-bet wide; opponent folds many hands cheaply |
| Semi-connected (J-8-4, T-7-3 two-tone) | 40–55% pot | Balance between coverage and draw charging |
| Wet, dynamic, draw-heavy (J-T-9, 8-7-6 two-tone) | 55–75% pot | Charge draws; protect made hands; semi-bluffs need to build pot |
| Monotone board | Mostly check; 33–50% when betting | Very selective value-only betting |
| OOP in 3-bet pots | 25–40% pot | Use smaller, more frequent c-bets to keep ranges balanced |
| IP in 3-bet pots | 33–66% pot depending on texture | Similar principles but can lean larger with nut advantage |
| Multiway (3+ players) | Avoid bluffs; 33–50% for value | Bet sizing should be smaller; bluffing largely cut |

**Key insight (GTO Wizard):** C-bet more on high-card boards, paired boards, and disconnected boards. C-bet less on connected and monotone boards. Polarize (larger, less frequent bets) when draws are present but not completed.

### 3.3 Range Bet vs. Polar C-Bet
- **Small/range bet (25–33%):** Bet almost your entire range for a tiny size. Works on boards where you have overwhelming range advantage and the board is dry. Opponent has few profitable calls and even fewer profitable raises.
- **Polar/large bet (55–75%+):** Bet with your strong hands (value) and your best bluffs. Check your medium-strength hands. Works on wet boards where draws are common and opponents need to pay to continue.

**At $1/$2, a simplified default:** Bet 33–40% on dry boards with your whole range. Bet 60–75% on wet boards with only strong hands and good draws. Check everything else. This captures most of the EV without needing to memorize complex frequency tables.

### 3.4 Hands to Check Back (IP) vs. C-Bet

**Usually check back IP:**
- Top pair weak kicker on wet boards (can be overwhelmed by draws and two-pairs)
- Overpairs (KK-JJ) on ace-high boards where you're capped
- Mediocre ace-x hands (A-6, A-7 with no good kicker) on ace-high boards
- Low flushes on monotone boards (check flop, bet ~50% turn, large river)
- Most hands on monotone boards without a flush

**Usually c-bet IP:**
- Strong top pair (TPTK) or better on dry boards
- Overpairs on low boards where you have nut advantage
- Good draws (flush draws, OESDs) on wet boards—semi-bluff charging draws
- Strong made hands that need to protect against draws

---

## 4. Facing C-Bets: Defense, Floating, Raising, Donk Betting

### 4.1 How Wide to Defend
Use Minimum Defense Frequency (MDF) as a floor guide (see math section). Against a 33% pot c-bet, you need to defend ~75%. Against a 66% pot c-bet, defend ~60%. Against a pot-sized bet, defend ~50%.

**Key live $1/$2 adjustment:** Your opponents almost never bluff optimally, so you can fold slightly more than MDF without being exploited. However, drastically over-folding makes you a target for anyone who notices.

**Defend by calling when:**
- You have top pair or better
- You have a strong draw (flush draw, OESD): call or raise
- You have pair + draw combo
- Your hand has strong equity vs. their entire c-betting range (>33% equity against 33% bet, etc.)

**Fold when:**
- You have no pair and no meaningful draw on a dry board
- You have weak pairs on a wet board (third pair, no draws)
- Pot odds don't justify continuing given your equity

### 4.2 Defending from the BB vs. BTN
The BB is the hardest spot to defend correctly:
- Your range is wide (you closed preflop action), so many hands miss flops
- You're always OOP postflop
- Defend your strongest draws aggressively (raise or call)
- Check-raise more liberally as the BB to protect your range from being exploited
- On low connected boards, you often have range advantage—use it

### 4.3 Floating (Calling with the Intent to Take Away Later)
Floating works when:
1. You have position (IP only in most cases)
2. The c-bettor shows weakness (bets small, has high c-bet frequency)
3. You have some equity to fall back on (backdoor draws, overcards)
4. Turn or river is likely to be checked to you

**Against live $1/$2 players:** Pure floating (zero equity) works occasionally against very high c-bet frequency players who shut down on the turn. But at this level, most players who c-bet large have real hands. Float carefully.

### 4.4 Raising the C-Bet (Check-Raising and Re-Raising)
**Raise with:**
- Sets and two pair (for value, protect against draws)
- Strong draws on wet boards: OESD + flush draw, OESD + pair combos
- Combo draws (max equity semi-bluffs)
- Gutshots with additional equity (pair, backdoor draws) on connected boards

**Check-raise sizing:** Make it 2.5–3x the c-bet on the flop. Larger raises (3–3.5x) on wet boards to deny equity.

**BB check-raise bluffs:** Best on low-connected two-tone boards where your range legitimately contains two-pair, straights, and strong draws. On rainbow dry boards, check-raise bluffs are rare and risky.

**Do NOT check-raise:**
- Air with zero equity
- Weak pairs without draws
- Against very tight c-bettors who rarely bluff (live $1/$2 nit opponents)

### 4.5 Donk Betting (Leading into the Preflop Raiser)
Donk betting is generally weak in online poker but has niche live applications:

**When donk betting may be justified in live $1/$2:**
1. **Multi-way family pots:** The raiser is unlikely to c-bet bluff into 3+ players. If you flop a strong hand, leading can generate immediate value.
2. **Strong live read:** You flopped a monster (set) and notice an interest tell from the raiser—donk betting looks weaker and may extract more.
3. **Passive opponent profiles:** Against players who never c-bet bluff, checking to them generates no action; donk betting forces them to interact.
4. **Semi-bluff in multi-way where others have checked:** Can fold out 1-2 remaining players before the raiser acts.

**Default:** Do not donk bet as a standard line. Check to the aggressor, defend or raise based on your hand.

---

## 5. Turn Play: Barreling, Check-Raising, Equity Realization

### 5.1 Double Barrel Logic (When to Fire Turn)
Firing the turn is one of the most important and complex postflop decisions. The key framework:

**Fire the turn when:**
- The turn card is a **scare card** that weakens their flop calling range (overcard to their pair, completes a draw that hits your range, pairs a card that's good for your range)
- You **picked up equity** (now have a draw, pair + draw combo)
- You have a strong hand that needs to build the pot or protect
- Your opponent has a capped range (cannot have the nuts after their flop call)
- You're in position and their flop call range is heavily draw-dependent

**Give up on the turn when:**
- The turn is a **brick** that doesn't help your range or hurt theirs (e.g., rainbow low card when you were semi-bluffing draws they don't have)
- Your bluff was too weak on the flop (no equity, no scare card)
- You're OOP and opponent has shown strength
- You have medium showdown value better realized by checking (pot control)
- The board texture has become too good for their range

**Best double barrel hands:**
- Draws that picked up more equity (combo draws)
- Air hands with good blockers that can credibly represent the turn card
- Top pair that became vulnerable to draws (continue betting to protect)
- Overpairs on dynamic boards

**Best give-up hands:**
- Pure air that didn't pick up equity
- Weak one-pair hands on boards where opponent's range improved
- Ace-high without strong backdoors when turn card helps them

### 5.2 Turn Scare Cards (Fire Frequencies)
| Turn Card Type | Action | Rationale |
|---------------|--------|-----------|
| Overcard to board (hits raiser's range) | Often barrel | Weakens opponent's pair hands; improves your range |
| Flush card (you have flush blockers) | Often barrel | Represents completed flush; blocks their nuts |
| Flush card (you don't have flush blockers) | Often check | Their range improved; you're unprotected |
| Pairing card | Often barrel (if paired card was already in your range) | Strengthens your story |
| Low brick (disconnected) | Often check with air | Doesn't help either range meaningfully |
| Straight card completing OESD | Context-dependent; barrel if it hits your range more |

### 5.3 Turn Check-Raise Heuristics
(Source: GTO Wizard blog on turn check-raises)

**Avoid turn check-raising when:**
- The turn is a pure brick and opponent's bet range is highly polarized
- Opponent bets large (leaves minimal room behind; stack-to-pot ratio too low)
- You're out of position vs. a tight, value-heavy range

**Good spots for turn check-raises:**
- **Wet turns** with multiple draws completing: You have equity in your check-raise range
- Opponent's range contains many drawing hands; your check-raise can fold out marginal value
- **Deep stacks (100bb+):** Non-all-in check-raises with top of value range; use draws with good equity as semi-bluffs
- **Shallow stacks (30bb):** Check-raise all-in with vulnerable two pairs and pair+draw; slow-play nuts

**Live $1/$2 simplified rule:** Turn check-raise mainly for protection with vulnerable strong hands (two pair on wet boards) or strong semi-bluffs (OESD with flush draw). Do not turn-check-raise as pure air.

### 5.4 Equity Realization
Not all equity is realized equally. Factors that affect how much of your theoretical equity you actually capture:

- **Position:** IP players realize more equity; OOP hands routinely have to fold before showdown
- **Hand type:** Flush draws realize equity better than gutshots (more outs, harder to be denied); pair + draw realizes more than pure draws
- **Opponent aggression:** Passive opponents allow more equity realization; aggressive opponents deny equity by betting and raising
- **Implied odds:** Strong hands that are not the nuts can still realize via big payoffs when they hit

**Live $1/$2 implication:** Against sticky/passive opponents, your draws realize more equity because they rarely apply pressure. This means you can call with draws slightly more liberally (but don't overdo it—pot odds still matter).

---

## 6. River Play: Value Betting, Bluffing, Bluff-Catching

### 6.1 River Value Betting
The river is the final street. Your hand is made; act accordingly.

**Core rule:** Your value bet must win more than 50% of the time when called in an all-in scenario. For non-all-in bets, you need a higher threshold since calling might reopen action.

**Thin value betting thresholds:**
- **IP:** Need strong hands; be cautious with marginal holdings (opponent can raise)
- **OOP:** Can bet slightly thinner because your bet doesn't reopen the action to a raise
- **Against calling stations:** Thin value is where the money is—second pair, third pair even, on dry boards where they'll call with worse

**Value sizing:**
- Make your largest value bet with your strongest hands when you have nut advantage
- Use smaller sizes when you might block their calling range or lack enough bluffs to justify big sizing
- Overbet (110–150% pot) when you have a very strong nut advantage on certain board textures

**When to slow-play rivers:** Almost never in live $1/$2. Opponents call too widely. Bet your strong hands.

### 6.2 River Bluffing
**When to bluff rivers:**
- You were semi-bluffing and missed (but have good blockers)
- You have a coherent story (your three streets of betting/checking represent a clear range)
- Opponent's range is capped (they cannot have nutted hands after prior streets)
- You have good blockers (see below)

**Bluff selection:** Pick hands that:
1. **Block their strong value hands** (you hold a card that reduces the frequency of their best holdings)
2. **Unblock their folding hands** (you DON'T hold a card that they'd fold—don't block their air)
3. Have little or no showdown value (don't bluff hands that beat some of their range)

**Practical examples:**
- A♣-5♣ on a bricked club draw board: blocks nut flush (A-high clubs), unblocks their K-high and Q-high clubs that miss
- 8-7 on a K-J-4-2-3 board: blocks the wheel straight possibility, strong if you represented a K or made a small straight

**Missed flush draws as river bluffs:** Context-dependent. Good when you have lots of value combinations to go with, your draw missed but blocks their best hands, and you checked the turn back first (range balance). Bad when your flush draw is on the same suit as the board and they can easily have better flushes.

**Live $1/$2 bluffing reality:** Most $1/$2 opponents call too much. Pure river bluffs against calling stations print money only in one direction—against them. Focus your bluffing on opponents who you've identified can actually fold. Against stickier opponents, reduce bluffing frequency dramatically.

### 6.3 River Bluff Sizing
- **Polar river bets:** 66–100% pot for value or bluff. Large sizes polarize your range and create the most pressure.
- **Small river bets:** 25–40% pot when you want to induce action (bet small with a strong hand to get called or raised), or as thin value where you're not sure if you're ahead.
- **Overbets (110–150%):** Only with significant nut advantage and a well-constructed bluffing range. Against live $1/$2 opponents, overbets for value against calling stations can be profitable even without the "right" bluffing range—they'll call with worse regardless.

### 6.4 Bluff-Catching
When to call a river bet as a bluff-catcher:
1. Your hand beats their bluffs but loses to their value
2. They're betting at a frequency that makes your call +EV (compare to required equity from pot odds)
3. You have blockers to their value hands (you hold a card that makes their value combos less likely)
4. The board texture is such that they have many missed draws in their range

**Key:** Calling because "they could be bluffing" is not enough. You need a logical reason to weight their range toward bluffs.

**Against live $1/$2 opponents:** Most players massively under-bluff rivers. When a passive opponent who has never shown aggression suddenly leads the river big, give them credit for a real hand. Reserve bluff-catches for opponents who have shown aggression patterns or you've seen bluffing.

---

## 7. Bet Sizing Theory Simplified

### 7.1 Core Principle
**Match size to polarization:**
- **Merged range** (betting wide with many medium-strength hands): Use small sizes (25–40% pot)
- **Polarized range** (betting only strong hands + bluffs, checking medium hands): Use large sizes (66–100%+ pot)

### 7.2 Three Sizing Situations
| Scenario | Size | Why |
|----------|------|-----|
| Dry board, high c-bet frequency | 25–33% | Keep opponent's entire weak range in; deny equity cheaply |
| Wet board, polarized range | 60–80% | Charge draws the correct price; extract max from strong hands |
| River with nut advantage | 66–100%+ | Maximize value; smaller bets leave money behind |

### 7.3 Geometric Sizing Intuition
When planning to bet three streets with a very strong hand, size your bets so each street is approximately the same fraction of the pot—this is geometric sizing. The goal: get stacks in by the river without a single street looking out of place.

**Simple formula:** If effective stacks are 100bb and pot is 10bb after preflop action, a rough three-street geometric plan to get all-in is approximately:
- Flop: ~33% (pot becomes ~16bb)
- Turn: ~50% (pot becomes ~24bb)
- River: ~66% or shove depending on remaining stack

For live $1/$2 at 200bb effective, just ask: "Do I want to get stacks in by the river?" If yes, think about sizing each street so the numbers work out by river.

### 7.4 IP vs OOP Sizing Tendencies
- **IP player** can vary sizes more aggressively; has more flexibility to overbet
- **OOP player** should use more consistent, balanced sizes—extreme sizing variations OOP are easier to exploit

---

## 8. Simplified Math Cheat-Sheet

### 8.1 Pot Odds (Required Equity to Call)
Formula: `Call Amount ÷ Final Pot × 100 = % equity needed`

| Bet Size (as % of pot) | Required Equity to Call |
|------------------------|------------------------|
| 25% pot | ~17% |
| 33% pot | ~20% |
| 50% pot | ~25% |
| 66% pot | ~29% |
| 75% pot | ~30% |
| 100% pot (pot-bet) | ~33% |
| 150% pot (overbet) | ~38% |

**Quick mental calculation:** When someone bets roughly half pot, you need ~25% equity. This is almost always met with a strong draw or a decent pair on the flop.

### 8.2 Rule of 2 and 4 (Outs to Equity)
- **Flop** (2 cards to come): Outs × 4 ≈ equity %
- **Turn** (1 card to come): Outs × 2 ≈ equity %

| Draw | Outs | Flop Equity | Turn Equity |
|------|------|-------------|-------------|
| Flush draw | 9 | ~36% | ~18% |
| Open-ended straight draw (OESD) | 8 | ~32% | ~16% |
| Gutshot straight draw | 4 | ~16% | ~8% |
| Two overcards | 6 | ~24% | ~12% |
| Flush draw + gutshot | 12 | ~48% | ~24% |
| Flush draw + OESD (combo draw) | 15 | ~60% | ~30% |

**Caveat:** Rule of 4 is accurate up to ~15 outs on the flop. Above 15 outs, it overestimates (20 outs ≈ 67%, not 80%). Only use Rule of 4 when all the money goes in on the flop; use Rule of 2 for single-street decisions.

### 8.3 Minimum Defense Frequency (MDF) and Alpha
**MDF:** The minimum % of your range you must defend (call or raise) to prevent any two cards from being a profitable bluff.
`MDF = Pot ÷ (Pot + Bet)`

**Alpha:** How often your opponent must fold for your bluff to break even.
`Alpha = Bet ÷ (Bet + Pot)`

Note: MDF + Alpha = 100%

| Bet Size | MDF (must defend) | Alpha (fold needed for bluff break-even) |
|----------|-------------------|------------------------------------------|
| 25% pot | 80% | 20% |
| 33% pot | 75% | 25% |
| 50% pot | 67% | 33% |
| 66% pot | 60% | 40% |
| 75% pot | 57% | 43% |
| 100% pot | 50% | 50% |

**Critical caveats:**
- MDF assumes bluffs have 0% equity, which is rarely true. Semi-bluffs need less fold equity.
- In live $1/$2, most opponents call too much (fold less than Alpha requires), so bluffing is often -EV. Reduce bluffing frequency accordingly.
- MDF is a floor, not an optimal frequency. Real defense is based on hand equity, not just frequency.

### 8.4 Break-Even Bluff Math
A river bluff breaks even when: `Fold Frequency > Bet ÷ (Bet + Pot)`

Example: You bet $60 into a $100 pot. You need opponent to fold more than 60/(60+100) = 37.5% of the time.

**Quick shortcut:** Against a 50% bet, you need >33% folds to break even. Against a pot-sized bet, you need >50% folds. Smaller bets need fewer folds.

### 8.5 Common Outs Reference
| Situation | Approximate Outs |
|-----------|-----------------|
| Flush draw | 9 |
| Open-ended straight draw | 8 |
| Two pair → full house | 4 |
| Set → full house or quads | 7 |
| Gutshot straight draw | 4 |
| One overcard | 3 |
| Two overcards vs. one pair | 6 |
| Pair + flush draw | 14-15 |
| Pair + OESD | 13-14 |

---

## 9. Multiway Adjustments

Multiway pots (3+ players) are the defining condition of live $1/$2 and require substantial strategy changes from heads-up play. Live games average ~4 players to the flop vs. ~2.7 online.

### 9.1 The Core Rule: Defense is Shared
When three players see the flop, no single player needs to defend as much because the burden of keeping opponents indifferent to bluffing is shared. But this cuts both ways: **bluffing becomes dramatically less profitable** because someone almost always calls.

Defense frequency needed per player against a pot-sized bet:
- Heads-up: ~50% each
- 3-way: ~29% each
- 4-way: ~21% each
- 6-way: ~13% each

**Implication:** You can fold more freely in multiway pots without being exploited. But your betting range must also be much stronger.

### 9.2 Tight Is Right (Multiway Betting Ranges)
In multiway pots:
- **Stop range-betting** (betting your entire range with a small size). This works heads-up but fails multiway because opponents defend very selectively, making your wide-range bet inefficient.
- **Value-bet only premium holdings:** Top pair top kicker or better is often the minimum for a profitable bet multiway. Against 3+ players, top pair weak kicker is often a check.
- **Bluffing almost never works:** Even tiny bets require very high fold equity that's unrealistic with 3+ opponents. Only bluff with hands that have genuine equity (draws with 8+ outs) and good blockers.
- **Nut potential is king:** Draws to second-best hands are worth much less multiway. Prioritize draws to the nut flush, nut straight.

### 9.3 Sizing in Multiway Pots
- Use smaller bet sizes than heads-up: reduce by 25–40% from your normal sizing
- Reserve overbets only if you have overwhelming nut advantage over all remaining players (rare)
- Smaller bets preserve the pot and allow you to play against opponents' tighter continuing ranges without over-committing

### 9.4 Specific Multiway Adjustments

**C-betting as the preflop raiser multiway:**
- Bet only strong made hands and powerful draws
- Default to checking with most marginal hands
- On dry boards with strong range advantage, a small c-bet (25–33%) can still work heads-up or 2-way but becomes marginal 3-way and unprofitable 4+-way unless you have a strong hand
- On wet boards, don't c-bet as a bluff at all multiway—only bet for value

**Calling multiway:**
- Require a stronger hand to continue vs. bets
- Focus on hands with nut potential (nut flush draws, strong straight draws)
- Fold weak pairs and weak draws that would be profitable calls heads-up
- Hands that can be dominated (middle pair, weak top pair) lose significant value multiway

**From the big blind in multiway pots:**
- Exercise extreme selectivity in defending
- Fold marginal hands like K-2, 9-4, off-suit garbage even at good pot odds
- Defend with hands that can improve to strong holdings and can withstand multiple opponents

**Donk betting multiway:**
- Slightly more justified than heads-up (raiser will c-bet bluff less often)
- Use for protection with strong made hands (sets, two pair) on wet boards
- Not a default strategy; only in specific spots

### 9.5 Check-Down Rule
When no one has bet by the river in a multiway hand that was checked down, the remaining players have weak ranges. The first bettor can profitably attack with more selective aggression than their hand might otherwise justify, because checking ranges are capped on multiple streets.

---

## 10. Live $1/$2 Leaks and Exploiting Passive/Sticky Opponents

### 10.1 Common $1/$2 Player Archetypes

**Calling Stations (most common):**
- Call too wide on the flop and turn; rarely fold after putting chips in
- Raise only with monsters (top set, nut flush, nut straight)
- Characteristically passive preflop: limp or call rather than raise
- Stats: Average Vegas $1/$2 player calls preflop raises 28% of the time (vs. 15.3% online), raises only 6% of hands

**Under-bluffing Players:**
- Never turn missed draws into bluffs
- Lead river only with very strong hands
- Their range is completely polarized toward value when they bet big, especially on the river

**Nits (less common at $1/$2 but present):**
- Play too tight; only bet strong hands
- Easy to bluff on scare cards but rarely a big profit source

### 10.2 Exploiting Calling Stations

1. **Isolate them preflop:** Raise larger when they limp to play heads-up. 5–7bb raises are appropriate if they're loose callers.
2. **Value bet relentlessly:** Top pair or better is worth 3 streets of value. Do not slow-play. Bet into them on every street.
3. **Overbet for value:** They often don't adjust to bet size. A $60 bet into a $30 pot with a set? They'll call. Use this.
4. **Minimize bluffing:** Against a station, bluffing is -EV. Channel all aggression into value.
5. **Bet thin:** Middle pair on a dry board, top pair on any board, two pair on wet boards—all worth at least 1-2 streets of value.
6. **Do not slow-play traps:** They won't build the pot for you; they'll check behind. You must bet your strong hands.

### 10.3 Exploiting Under-Bluffing Players

1. **Fold to their river aggression more than MDF suggests:** When a passive player who never bluffs leads river for large, they have it. Fold more liberally.
2. **Call them down light when they show previous weakness:** If they've checked or called multiple streets, their range is weak—a river bet from them is suspicious, but their entire trajectory suggests weakness.
3. **Over-fold to check-raises:** At $1/$2, check-raises almost universally mean a very strong hand. Unless you have a strong draw or big hand, fold.

### 10.4 Your Own $1/$2 Postflop Leaks (Common Winning Player Mistakes)

1. **Bluffing too frequently against the field:** The field at $1/$2 calls too much. Bluffing indiscriminately costs chips.
2. **Not value-betting thin enough:** Leaving money on table by not betting medium-strength hands that easily get called by worse.
3. **Auto c-betting without regard for texture or position:** Firing every flop regardless of OOP/multiway considerations.
4. **Slow-playing strong hands:** They won't build the pot for you. Bet your sets and two pairs.
5. **Not sizing up enough for value:** Betting $20 into a $60 pot when $40 would get called equally often.
6. **Calling too much on the turn and river:** Despite opponents calling widely, you also need to manage your own calls correctly.
7. **Failing to bet-fold:** Betting for value then calling a raise with one pair. A raise from a $1/$2 player usually means a very strong hand.

---

## 11. $1/$2 → $2/$3 Adjustments

Moving from $1/$2 to $2/$3 in a live casino context involves meaningful differences in player pool quality, game dynamics, and strategy requirements. The skill gap between $1/$2 and $2/$3 is real but not extreme—it's less than the gap between $2/$3 and $5/$10.

### 11.1 Player Pool Differences
| Factor | $1/$2 | $2/$3 |
|--------|-------|-------|
| Average player quality | Beginners to competent amateurs | Competent amateurs to semi-regulars |
| Fold frequency | Very low (calling stations dominate) | Slightly higher; more players who can fold |
| Bluff frequency | Very low (most players don't bluff) | Slightly higher; some regulars balance semi-bluffs |
| Check-raise aggression | Rare; almost always a monster | More frequent; some regulars use it as a tool |
| Awareness of your tendencies | Very low | Somewhat higher; regulars notice patterns |
| Preflop sizing | Often still limp-heavy; loose calls | Slightly tighter; fewer extreme loose calls |

### 11.2 Postflop Strategy Adjustments for $2/$3

**1. Balance value and bluffs more carefully:**
At $1/$2, pure value-betting without any balance works because opponents never exploit it. At $2/$3, regulars start noticing. Begin incorporating some bluffs into your aggression where you've only been value-betting. Still lean value-heavy (2:1 or 3:1 value-to-bluff ratio), but don't be pure.

**2. Thin value becomes slightly less reliable:**
Some $2/$3 players will fold second pair to a river bet where a $1/$2 calling station would call. Adjust your thin value targets. You still bet thin, but calibrate to the specific opponent (read the player).

**3. Respect check-raises more:**
At $1/$2, a check-raise is almost always a monster; fold anything less than two pair. At $2/$3, check-raises occasionally include semi-bluffs and protection bets. Still respect them, but some regulars use check-raises more dynamically—don't fold every strong draw to a check-raise.

**4. Bet sizing tightens slightly:**
$2/$3 opponents make fewer sizing mistakes. Betting $15 into a $60 pot still gets called, but some players will float you with appropriate ranges if you always bet small. Vary your sizing more based on texture and hand strength rather than defaulting to one size.

**5. Be more aware of your own image:**
$2/$3 regulars observe your play across sessions. If you've been value-betting the whole session, a river raise on a scare card from a regular has more credibility than you'd give a $1/$2 player. Start thinking about how you're perceived.

**6. Position becomes more important:**
$2/$3 players play back more often and have slightly better postflop fundamentals. Being OOP against a competent regular is harder than OOP against a calling station. Prioritize IP spots.

**7. Bluffing becomes marginally more profitable:**
Not dramatically so—the field still calls too much. But you'll encounter players who correctly fold to three-street aggression. Identify these players and run more sophisticated lines against them specifically.

**8. Line construction coherence matters more:**
$2/$3 regulars notice when your story doesn't make sense. "Why did they check-back the turn and bet pot on the river?" starts to matter against thinking opponents. Build coherent narratives across streets.

**9. Pot control with medium-strength hands:**
$2/$3 players occasionally have real hands behind. Top pair no kicker on a wet board deserves more caution than at $1/$2 where it's automatic call-down territory. Pot control becomes a tool, not a weakness.

**10. C-bet bluffing increases slightly:**
At $1/$2, c-bet bluffing vs. the field is often unprofitable. At $2/$3, on dry boards with good range advantage, c-betting has higher fold equity. Still be selective, but don't completely abandon bluff c-bets.

### 11.3 What Stays the Same
- Value betting strong hands aggressively: still the #1 profit driver
- Avoiding bluffing calling stations: they exist at every stake
- Multiway pot adjustments: still many family pots in live games
- Bet sizing based on board texture: dry = small, wet = large
- MDF and pot odds math: unchanged

---

## 12. What to Drill

This section outlines the most impactful postflop skills to train and the best methods to drill each.

### 12.1 Priority Drill List (Ranked by Impact)

**Drill 1: Equity Estimation Against Ranges**
- *Skill:* Given a board texture and a range, estimate your equity percentage accurately without a calculator
- *Why it matters:* Every pot odds decision and MDF calculation requires knowing your equity; imprecise estimates lead to systematic errors
- *Method:* Use Flopzilla Pro or PokerCruncher (mobile). Enter realistic opponent ranges, pick a hand, estimate equity, then check. Repeat 20-30 times per session. Focus on: top pair vs. paired board, draws vs. made hands, combo draws
- *Target:* Estimate within 5-7% on common draws and pair-based hands

**Drill 2: Board Texture Classification + Who Has Advantage**
- *Skill:* See a three-card flop, immediately classify it (dry/wet/connected/monotone/paired), identify who has range advantage and nut advantage
- *Why it matters:* Every postflop decision—c-bet or check, size big or small, bluff or give up—flows from this classification
- *Method:* Deal three random cards (physical deck or app), classify the board, name who benefits, and what c-bet frequency and size is appropriate. Do 15-20 boards per session
- *Target:* Classify instantly and correctly with reasoning; < 3 seconds per board

**Drill 3: Line Construction (Flop → Turn → River)**
- *Skill:* Given a hand and board runout, construct a coherent line (bet-bet-bet, check-bet-bet, etc.) and explain why each action is chosen
- *Why it matters:* Postflop profitability depends on multi-street coherence; individual street decisions don't exist in isolation
- *Method:* Use GTO Wizard trainer on specific spot types. Play full three-street hands, then review mistakes. Also: take past session hands and map out: "What was my plan, and did each street support it?"
- *Sub-drills:*
  - Value hand line construction (building the pot with strong hands over three streets)
  - Semi-bluff line construction (when to bet-bet-give up vs. bet-check-bluff)
  - Medium-strength hand lines (when to check flop, call turn, fold river vs. call down)

**Drill 4: Hand Reading / Range Narrowing**
- *Skill:* On the river, narrow opponent's range to a realistic subset based on all preflop and postflop action; decide whether to call, raise, or fold
- *Why it matters:* River decisions require accurate range assessment; wrong reads lead to bad calls and missed value
- *Method:* Use GTO Wizard Hand Analyzer or Flopzilla with range narrowing. Take a completed hand, re-construct opponent's range street by street. Ask: "What can they have after check-calling flop, check-calling turn, and leading river?" Then make the decision
- *Also:* Review session hand histories; write down what opponent's range was at each decision point

**Drill 5: Bet Sizing Selection by Texture**
- *Skill:* Given a board texture, effective stacks, and your position, select the correct bet size (25%, 33%, 50%, 66%, 75%, pot)
- *Why it matters:* Wrong sizing is money left on the table; too small on wet boards gives draws correct odds, too large on dry boards overbets your edge
- *Method:* Study GTO Wizard aggregate reports for specific board textures. See what size is used most frequently on K-7-2 rainbow vs. J-T-8 two-tone. Build a mental table: "This board type → this size"
- *Also:* Deliberate sizing practice in GTO Wizard trainer with "Only Close Decisions" filter on sizing nodes

### 12.2 Supporting Drills (Secondary Priority)

**Multiway Pot Decision Drills:**
- Deal 3+ player spots. Identify who should bet, what hands qualify as value, and what hands should check
- Focus: "Would I bet this hand heads-up? Now with two others in? What changes?"

**Pot Odds Flash Drills:**
- Opponent bets $X into $Y pot. Calculate required equity in 5 seconds or less
- Memorize the cheat sheet until it's automatic

**Blocker Identification:**
- On a given river board, identify: "Which cards block the nuts? Which cards in my hand help or hurt my bluff?"
- Drill by looking at boards and listing the top 3 bluffing hands and the top 3 hands to avoid bluffing with

**MDF and Alpha Quick Calculation:**
- Given a bet size, calculate MDF instantly
- Pair with actual hands: "They bet 2/3 pot. Do I need to call? What hands should I call with to reach 60%?"

### 12.3 Training Formats

| Format | Best For | Tools |
|--------|----------|-------|
| GTO Wizard Trainer (Custom Spot) | Drilling specific positions/boards repeatedly | GTO Wizard |
| GTO Wizard Trainer (Full Hand) | Line construction, whole-hand coherence | GTO Wizard |
| Flopzilla Pro | Board texture analysis, equity distribution | Flopzilla Pro |
| Hand history review | Real-game mistakes, apply concepts to live spots | Notepad + equity calc |
| Postflop+ (GTO bot) | Real-time postflop decisions with instant feedback | Postflop+ app |
| Physical deck drilling | Board texture classification speed | Deck of cards |
| SplitSuit Postflop Workbook | Structured 1,700+ exercise curriculum | Book/PDF |
| GTO Wizard Aggregate Reports | Build heuristics for entire board texture categories | GTO Wizard |

### 12.4 Study Session Structure (Recommended)
- **15 min:** Board texture classification flash drill (physical deck or app)
- **20 min:** GTO Wizard trainer on one specific spot type (e.g., BTN c-bet IP on dry boards only)
- **15 min:** Hand history review of previous session hands, identifying postflop errors
- **10 min:** Equity estimation drill (Flopzilla or PokerCruncher)

Total: ~1 hour per session. Prioritize consistency (daily 30-min sessions) over sporadic long sessions.

---

## 13. Sources

**GTO Wizard Blog:**
- [Flop Heuristics: IP C-Betting in Cash Games](https://blog.gtowizard.com/flop-heuristics-ip-c-betting-in-cash-games/)
- [10 Tips for Multiway Pots in Poker](https://blog.gtowizard.com/10-tips-multiway-pots-in-poker/)
- [Turn Check-Raise Heuristics](https://blog.gtowizard.com/turn-check-raise-heuristics/)
- [Principles of River Play](https://blog.gtowizard.com/principles-of-river-play/)
- [Blockers & Unblockers: The Secret to Picking Great Bluffs](https://blog.gtowizard.com/blockers-unblockers-the-secret-to-picking-great-bluffs/)
- [MDF & Alpha](https://blog.gtowizard.com/mdf-alpha/)
- [Why You're Bluffing the River Wrong With Bricked Flush Draws](https://blog.gtowizard.com/why_youre_bluffing_the_river_wrong_with_bricked_flush_draws_in_cash_games/)
- [How to Use Practice Mode in GTO Wizard](https://blog.gtowizard.com/how-to-use-practice-mode-in-gto-wizard-to-improve-your-game/)
- [Pot Geometry](https://blog.gtowizard.com/pot-geometry/)
- [Live Cash Solutions](https://blog.gtowizard.com/live-cash-solutions-and-4000-new-scenarios-for-cash-mtt-formats/)

**Upswing Poker:**
- [3 Concepts That Shape Postflop Strategy](https://upswingpoker.com/3-concepts-shape-postflop-strategy/)
- [C-Betting IP vs OOP](https://upswingpoker.com/continuation-bet-c-bet-strategy-position/)
- [10 Fundamental Tips for Common Flop Types](https://upswingpoker.com/board-texture-tips/)
- [4 Ways to Improve in Multiway Pots](https://upswingpoker.com/multi-way-pots-strategies-tips/)
- [How to Check-Raise Like a High Stakes Juggernaut](https://upswingpoker.com/check-raise-poker-strategy-flop-c-bet/)
- [Bet Sizing Strategy: 8 Rules](https://upswingpoker.com/bet-size-strategy-tips-rules/)
- [Geometric Bet Sizing](https://upswingpoker.com/geometric-bet-sizing/)
- [Pot Odds Step-by-Step](https://upswingpoker.com/pot-odds-step-by-step/)
- [How to Check Back: Strong Flop Check-Back Strategies](https://upswingpoker.com/check-back-bet-strategies/)
- [Nut, Range, and Positional Advantage](https://upswingpoker.com/nut-range-positional-advantage/)

**PokerCoaching.com:**
- [GTO Postflop Basics](https://pokercoaching.com/blog/gto-postflop-basics/)
- [How to Beat Calling Stations](https://pokercoaching.com/blog/calling-stations-in-poker/)
- [Range Advantage in Poker](https://pokercoaching.com/blog/range-advantage/)
- [MDF Poker](https://pokercoaching.com/blog/mdf-poker/)
- [Navigating Multiway Pots](https://pokercoaching.com/blog/navigating-multiway-pots/)

**PokerNews / Other:**
- [Donk Betting in Small-Stakes Live NL](https://www.pokernews.com/strategy/donk-betting-in-small-stakes-live-no-limit-hold-em-28638.htm)

**SplitSuit Poker:**
- [The Double Barrel Checklist](https://www.splitsuit.com/the-double-barrel-checklist)
- [Cash Game Strategy Guide: $1/$2 to $2/$5](https://www.splitsuit.com/cash-game-poker-strategy)
- [How to Practice Poker](https://www.splitsuit.com/how-to-practice-poker)

**VIP Grinders:**
- [Range Advantage in Poker](https://www.vip-grinders.com/poker-strategy/range-advantage/)

**BlackRain79:**
- [Postflop Bet Sizing Strategy](https://www.blackrain79.com/2022/08/postflop-bet-sizing.html)
- [$1/$2 Cash Game Strategy](https://www.blackrain79.com/2018/02/1-2-cash-game-strategy.html)
