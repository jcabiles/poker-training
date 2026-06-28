# Preflop Strategy Framework: Live NL Hold'em $1/$2 → $2/$3

**Scope:** Live No-Limit Texas Hold'em cash games only. 9-handed (full ring). Competent winning player at $1/$2, targeting $2/$3 move-up. Simplified-but-sound framework grounded in modern (solver-era) theory; practical over exhaustive.

**Last updated:** 2026-06-27  
**Research agent:** preflop-strategy v1

---

## Table of Contents

1. [Core Philosophy](#1-core-philosophy)
2. [Position Map (9-Handed)](#2-position-map-9-handed)
3. [RFI Ranges by Position (Opening Raise First In)](#3-rfi-ranges-by-position)
4. [Preflop Sizing Conventions](#4-preflop-sizing-conventions)
5. [3-Bet Strategy](#5-3-bet-strategy)
6. [Responding to 3-Bets (4-Bet / Call / Fold)](#6-responding-to-3-bets)
7. [4-Bets and 5-Bets](#7-4-bets-and-5-bets)
8. [Blind Defense](#8-blind-defense)
9. [Live-Specific Realities](#9-live-specific-realities)
10. [Straddled Pots](#10-straddled-pots)
11. [Multiway Pots Preflop](#11-multiway-pots-preflop)
12. [Exploitative Deviations for Soft Live Pools](#12-exploitative-deviations-for-soft-live-pools)
13. [$1/$2 → $2/$3 Key Adjustments](#13-12--23-key-adjustments)
14. [What to Drill and How](#14-what-to-drill-and-how)
15. [Sources](#15-sources)

---

## 1. Core Philosophy

### The Three Pillars

1. **Position dominates.** Most of your profit comes from hands played in position (CO, BTN, SB stealing). Most of your losses come from hands played out of position (EP, SB calls). Act accordingly.
2. **Raise or fold; rarely limp.** At $1/$2 and above: open-limp is a leak. When first to act, raise or fold. Never be the first player to limp into a pot.
3. **Exploit before you GTO.** At these stakes, opponents deviate so far from GTO that pure balance is lower EV than exploiting population tendencies. Know the baseline (GTO-informed), then deviate intentionally.

### Range-Based Thinking

Think in ranges, not hands. Each position has a range of hands you play; the goal is to execute the right actions with each hand category consistently, not to "play your hand." Range morphology framework (from GTO Wizard):

- **Linear range:** Filled top-down with best hands—no large gaps. Standard for RFI.
- **Polarized range:** Very strong hands + bluffs; skips middle. Common for 3-betting IP late position.
- **Merged range:** Wide value hands with fewer bluffs. Use against calling stations or from OOP 3-bet spots.
- **Condensed range:** Medium-strength only. Rare preflop, but describes cold-call ranges.

### The Rake Reality

Live $1/$2 takes ~10% rake (typically 5+1 structure, capped ~$5-7). This has two consequences:
- Tighten opening and calling ranges vs. online equivalents—rake eats marginal profits.
- Win pots *preflop* when possible (most live rooms only rake after the flop)—increasing 3-bet frequency nets rake-free wins.

---

## 2. Position Map (9-Handed)

```
Seat:   UTG  UTG+1  LJ    HJ    CO    BTN   SB    BB
Label:  EP    EP    MP    MP    CO    BTN   SB    BB
VPIP%:  ~10%  ~12%  ~15%  ~18%  ~25%  ~40%  ~20%  ~30%*
```

*BB VPIP is high because you get a discount (already invested 1bb); your *voluntary* entry rate is lower.

**Position labels used in this document:**
- EP = UTG + UTG+1 (8-9 players remaining to act)
- MP = LJ + HJ (5-6 players remaining)
- CO = Cutoff (3 players remaining: BTN, SB, BB)
- BTN = Button (best seat; 2 players remaining: SB, BB)
- SB = Small Blind
- BB = Big Blind

---

## 3. RFI Ranges by Position

These are simplified, memorizable tiers based on consolidated sources (Red Chip Poker full-ring exploitative ranges, Upswing Poker Preflop Prodigy, Jonathan Little small-stakes charts, BlackRain79, FreeBetRange 9-max charts). Adjusted for live play: rake-aware, opponent-pool-realistic, designed for easy memorization.

**How to use the tiers:** Learn the "range floor"—the weakest hand type allowed in each category. Everything above that threshold is auto-include.

---

### 3A. UTG / UTG+1 (Early Position — EP)

**Open ~10-12% of hands. 7-8 players yet to act.**

| Category | Hands | Notes |
|---|---|---|
| Premium pairs | AA, KK, QQ, JJ, TT | Always open |
| Strong broadway offsuit | AKo, AQo, AJo | Always open |
| Strong broadway suited | AKs, AQs, AJs, ATs | Always open |
| Medium pairs | 99, 88, 77 | Open; be prepared to face aggression |
| Suited broadway connectors | KQs, KJs, QJs | Open |
| Suited aces | A9s, A8s, A7s, A5s | These specific combos (not A6s/A4s/A3s/A2s unless studying blockers) |
| Offsuit aces | ATo | Marginal; can fold vs aggressive tables |

**EP Floor Rule:** If it's not a pair 77+, a suited broadway, AKo/AQo/AJo, or ATs+, default-fold from UTG/UTG+1 in live games.

**What to EXCLUDE from EP:**
- KQo, KJo (too dominated, multiway nightmare)
- Small pairs 22-66 (implied odds insufficient when you're capped preflop)
- Suited connectors below JTs (equity realization suffers from 8 opponents)
- Weak suited aces A2s-A4s (save for 4-bet bluff candidates, not first-in)

---

### 3B. LJ / HJ (Middle Position — MP)

**Open ~15-20% of hands. 4-5 players yet to act.**

Add to EP range:

| Category | Hands Added | Notes |
|---|---|---|
| More pairs | 66, 55 | Now have better implied odds with fewer opponents |
| Offsuit broadway | KQo, KJo | Playable; position advantage grows |
| More suited aces | A6s, A4s, A3s, A2s | Full Ax suited range now |
| Suited connectors | JTs, T9s, 98s | High-end suited connectors enter |
| More suited broadway | KTs, QTs, J9s | Add from HJ |

**MP Floor Rule (LJ):** Offsuit J-X and suited 8-X mark your range floor. (Anything stronger = play.)

**MP Floor Rule (HJ):** Offsuit T-X and suited 7-X mark your range floor.

---

### 3C. CO (Cutoff)

**Open ~25-28% of hands. 2-3 players yet to act.**

Add to MP range:

| Category | Hands Added | Notes |
|---|---|---|
| More pairs | 44, 33, 22 | Small pairs viable now with BTN/blinds behind |
| Offsuit broadway | QJo, QTo, JTo | Playable in position |
| More suited connectors | 87s, 76s, 65s, 54s | Full suited connector range |
| Offsuit Ax | A9o, A8o | Marginal but viable |
| Weak suited broadway | K9s, Q9s, J9s | Add suited gappers |
| KTo, QJo | Offsuit broadways | Continue to widen |

**CO Floor Rule:** Offsuit J-X and suited 5-X. (Anything stronger than that from CO = play.)

---

### 3D. BTN (Button)

**Open ~40-45% of hands. Only SB + BB remaining.**

Add to CO range:

| Category | Hands Added | Notes |
|---|---|---|
| All offsuit broadways | KTo down, QJo, JTo, J9o | Steals profitably |
| Weak suited hands | 43s, 53s, 64s, 74s, 85s | Suited trash with steal equity |
| Offsuit connectors | T9o, 98o, 87o | Marginal; fold to aggressive opponents |
| Any pair | All pocket pairs | 22-AA all open |
| Weak offsuit aces | A7o-A2o | Steal equity driven |
| Broadway Kx, Qx | K8o, K7o, Q9o | Fold to 3-bet easily |

**BTN Floor Rule:** Memorize "I can open almost anything with fold equity; I fold to 3-bets most of the weakest additions."

**Live BTN adjustment:** Tighten slightly vs. aggressive BB players (frequent 3-bettors make BTN stealing less profitable). Widen vs. passive/tight blinds.

---

### 3E. SB (Small Blind)

**Open ~35-40% when folded to. Worst position postflop.**

SB is the trickiest position: you act last preflop (vs. BB only) but *first* every postflop street. Key principle: raise or fold—do not complete/limp unless it's a very specific exploitative situation.

| Category | Recommendation |
|---|---|
| Premium pairs TT+ | Always raise |
| AK, AQ, AJ, ATs, KQs | Always raise |
| 77-99, KJs, QJs, JTs | Raise |
| Medium suited aces A2s-A9s | Raise (mostly) |
| Small pairs 22-66 | Raise or fold depending on BB aggression |
| Suited connectors | Raise most to CO level |
| Weak offsuit hands | Fold (ATo, KQo borderline at most) |
| Limping SB | Generally avoid—rake compounds OOP cost |

**SB vs BB steal sizing:** Use 3bb (larger than standard). A small size gives BB excellent pot odds. In live games, many coaches recommend 3.5-4bb from SB to make BB defense more expensive.

**Note:** Some solvers show AA/KK occasionally limp-completing from SB to trap (balanced strategy). At live $1/$2-$2/$3, this is unnecessary complexity—just raise.

---

### 3F. BB (Big Blind) — Facing RFI

You already have 1bb invested. This improves your calling odds dramatically vs. any position except SB.

**Pot odds formula:** Facing 3bb open, you call 2bb to win 4.5bb pot = need ~30% equity to continue.

**BB defense frequencies by raiser's position:**

| Opener Position | BB Defend Range | Notes |
|---|---|---|
| UTG (EP) | ~25-30% | Tight; EP range is strong |
| MP | ~30-35% | Slightly wider |
| CO | ~35-40% | Good defense frequency |
| BTN | ~40-45% | Widest; BTN range is wide |
| SB | ~50-60% | Very wide; SB range is weakest |

**What to do from BB:**

- **3-bet:** AA, KK, QQ, AKs/AKo (always), plus bluff 3-bets: A5s, A4s, A3s, A2s (blocker value), selected suited connectors
- **Call:** JJ, TT, 99-22 (pairs), AJ-AT, KQ, KJ, QJ, most suited aces, suited connectors and gappers, select offsuit hands based on odds
- **Fold:** Weak offsuit hands without equity (e.g., 72o, 83o, 94o)

**Key BB principle:** The BB is the only position where you're allowed a very wide calling range because of the discount. Don't over-fold to steals.

---

## 4. Preflop Sizing Conventions

### $1/$2 Standard Sizes

| Action | Size | Formula |
|---|---|---|
| RFI (EP/MP) | $8-10 | 4-5bb |
| RFI (CO/BTN) | $6-8 | 3-4bb |
| RFI (SB) | $6-8 | 3-4bb |
| Iso-raise vs 1 limper | $12-15 | 4bb + 1bb per limper |
| Iso-raise vs 2 limpers | $14-18 | 4bb + 1bb per limper |
| Iso-raise OOP | Add $2-4 | Extra size for OOP disadvantage |
| 3-bet IP | 3x the open | e.g., 3x $8 = ~$24 |
| 3-bet OOP | 3.5-4x the open | e.g., 4x $8 = ~$32 |
| 4-bet | ~2.3-2.5x the 3-bet | e.g., vs $24 3-bet → $55-60 |

**Key live rule:** +$1 per limper already in the pot, added to your raise size.

### $2/$3 Standard Sizes

| Action | Size | Formula |
|---|---|---|
| RFI (EP/MP) | $12-15 | 4-5bb (bb=$3) |
| RFI (CO/BTN) | $10-12 | 3.5-4bb |
| RFI (SB) | $10-12 | 3.5-4bb |
| Iso-raise vs 1 limper | $18-21 | 4bb + 1bb per limper |
| 3-bet IP | ~$40-45 | 3x a $12 open |
| 3-bet OOP | ~$50-55 | 4x a $12 open |

### Sizing Rationale

- Live players call wider than online equivalents → use larger sizes to extract more value per combo
- Larger sizes also thin the field → fewer multiway pots, better equity realization
- Don't vary size by hand strength—this is a major live tell and exploitable leak
- From BTN/SB with steal intent: can reduce to 2.5-3x since steal equity compensates for smaller pot

---

## 5. 3-Bet Strategy

### Core Principle: Linear vs. Polarized

**Linear 3-bet range (merged):** Use when
- Players remain to act behind you (EP/MP opens)
- Opponent is a calling station who rarely 4-bets
- You're OOP (prevents bluff from working; need hands that have value at showdown)
- Live games generally: most low-stakes players call 3-bets wide → lean merged

**Polarized 3-bet range:** Use when
- You're IP in late position vs. late position opener
- Opponent folds frequently to 3-bets (tight players)
- Opponent has low 4-bet frequency

### Value 3-Bet Hands (by position)

| Your Position | Core Value 3-Bet Hands |
|---|---|
| EP vs EP opener | QQ+, AKs, AKo |
| EP vs MP/CO opener | QQ+, JJ, AKs, AKo, AQs |
| MP vs earlier opener | QQ+, JJ, AKs, AKo, AQs |
| CO vs EP/MP opener | QQ+, JJ, TT, AKs, AKo, AQs, AJs |
| BTN vs any opener | JJ+, TT, 99, AKs, AKo, AQs, AJs, KQs |
| SB vs BTN/CO | JJ+, TT, AKs, AKo, AQs |
| BB vs BTN/SB | QQ+, JJ, TT, AKs, AKo, AQs, AJs |

### Bluff/Semi-Bluff 3-Bet Hands

Ideal bluff 3-bets must satisfy at least 2 of 3: (1) block opponent's calling range (Ax/Kx blockers), (2) have fold equity if called (strong equity when called), (3) play poorly in multiway pots.

| Hand Category | Reason | Notes |
|---|---|---|
| A5s, A4s, A3s, A2s | Ace blocker; fold AK/AA; nut flush potential | Best bluff 3-bets universally |
| KQs (BTN/CO) | Strong hand, folds out weaker EP openers | Also value vs. some ranges |
| 76s, 65s, 54s | Playable; bad to call multiway | Best from BTN vs. CO/BTN |
| QJs, JTs | Solid equity if called; pushes out dominated hands | More merged than pure bluff |
| AJo (BTN) | Marginal; blocks AK, may dominate AQ | Position-dependent |

### Live-Specific 3-Bet Adjustment

Most $1/$2-$2/$3 players:
- Call 3-bets too wide (don't fold dominated hands)
- Almost never 4-bet bluff
- Have low 3-bet frequencies themselves (5-8% vs. 9-12% in studied games)

**Therefore:**
1. Use **more merged** 3-bet ranges (value-heavy) rather than polarized
2. Reduce pure bluff frequency—opponents don't fold enough to justify them
3. 3-bet *more often* (not necessarily wider hands) since it forces preflop wins that skip rake
4. When you 3-bet-bluff at all, make it Ax suited hands that have strong fallback equity

---

## 6. Responding to 3-Bets

When facing a 3-bet, three decisions: 4-bet, call, fold.

### Decision Framework

**Key inputs:**
- Opponent's 3-bet range (tight = strong; loose = bluffing more)
- Your position (IP = wider continuing range; OOP = tighter)
- 3-bet size (larger = fold more; smaller = call/4-bet more)
- Effective stack depth (deeper = more calls with speculative hands)

### General Continuing Ranges vs. 3-Bet

**When IP (e.g., you opened BTN, BB 3-bets):**

| Action | Hands |
|---|---|
| 4-bet value | AA, KK, QQ (always), AK (always) |
| 4-bet bluff | A5s, A4s, A2s (blocker/equity) |
| Call | JJ, TT, 99, 88, AQs, AJs, ATs, KQs, QJs, JTs, T9s |
| Fold | 77 and below (mostly), offsuit aces below AQ, suited connectors 87s and below |

**When OOP (e.g., you opened CO, BTN 3-bets):**

| Action | Hands |
|---|---|
| 4-bet value | AA, KK, QQ (always), AK (always) |
| 4-bet bluff | A5s, A4s (fewer bluffs OOP; need IP to run bluffs well) |
| Call | JJ, TT, AQs, AJs, KQs |
| Fold | 99 and below (mostly), JTs and below, most offsuit hands |

**OOP = call much tighter** because you'll play every postflop street out of position.

### Live Exploitative Adjustment to 3-Bets

At $1/$2-$2/$3, most 3-bets are **strong** (players don't bluff 3-bet enough):
- When a tight player 3-bets from EP/MP: fold JJ, TT, AQ; call or 4-bet only with AA/KK/AK/QQ
- When an obvious recreational player 3-bets: widen continuation; they often have random hands
- **Do NOT over-call 3-bets OOP with speculative hands** (pairs 22-77, suited connectors). These require perfect postflop play to realize equity—a common leak at low stakes.

---

## 7. 4-Bets and 5-Bets

### When to 4-Bet

**Always 4-bet for value:**
- AA, KK: No exceptions. Getting it in preflop is almost always correct at 100bb.
- AK: 4-bet ~70-80% of combos (mix some calls when deep/IP vs. balanced 3-bettors)
- QQ: 4-bet most combos; occasionally flat IP vs. BTN if very deep

**Sometimes 4-bet:**
- JJ: 4-bet OOP (deny equity, avoid tough spots); call IP when deep
- AQs: Mix 4-bet/call IP depending on opponent's range
- AQo: 4-bet OOP as semi-value; call IP in position

**4-bet bluffs (use sparingly at $1/$2-$2/$3):**
- A5s, A4s, A3s, A2s: Best suited wheel aces (ace blocks AA/AK, has equity)
- Live specific: Most opponents don't 3-bet bluff enough to warrant 4-bet bluffs at all. Prioritize value 4-bets. Only include 4-bet bluffs if the player has demonstrated they 3-bet light.

### 4-Bet Sizing

- **IP vs. 3-bet:** 2.3x the 3-bet size (e.g., vs. $24 3-bet → $55)
- **OOP vs. 3-bet:** 2.5-2.7x the 3-bet size (e.g., vs. $24 3-bet → $60-65)
- **5-bet shove:** When a 4-bet would put you in for >50% of stack anyway, just shove. Typically occurs in $1/$2 if effective stacks are $200-300.

### Facing a 4-Bet

**Fold range:** Everything except AA, KK, AKs (and sometimes AKo/QQ depending on stack depth and opponent's 4-bet range).

**At $1/$2-$2/$3:** Almost no one 4-bet bluffs. When you face a 4-bet, assume you're against KK+ or AK. Fold QQ-JJ unless the opponent has demonstrated 4-bet light tendencies or effective stacks are deep enough to setmine.

---

## 8. Blind Defense

### BB Defense Strategy

**vs. BTN open (widest range):**
- 3-bet: AA-QQ, AKs, AKo, AQs—plus bluffs: A5s-A2s, select suited connectors
- Call: JJ-22 (most pairs), AJs-A2s, KQs-K7s, QJs-86s (suited broadways and connectors), KQo, KJo, QJo
- Fold: Weak offsuit hands (J5o, 83o, etc.), truly dominated unplayable combos

**vs. CO open:**
- 3-bet: Same value range; slightly fewer bluffs (CO is tighter than BTN)
- Call: Slightly tighter—drop weakest suited connectors and weakest offsuit pairs

**vs. EP open:**
- 3-bet: AA-QQ, AKs/AKo only (EP range is strong; 3-betting JJ is risky)
- Call: JJ-99, AQs, AJs, ATs, KQs, JTs, T9s
- Fold: Much wider—fold most suited gappers, most offsuit broadway, 22-77 (poor implied odds vs. strong EP range)

**Key BB principle:** You get ~30% pot odds on a call vs. 3bb open. This justifies calling with most hands that have reasonable equity AND playability. Don't over-fold. But also: calling OOP with junk just delays losing.

### SB Strategy

**When folded to you (steal vs. BB):**
- Raise ~35-40% (CO range or slightly wider)
- Size: 3-4bb (live default)
- Do NOT complete/limp-in—this is a losing play at $1/$2+ unless BB is extremely aggressive and trapping frequently
- 3-bet or fold when facing a BTN open

**When facing an EP/MP/CO open:**
- SB is the worst seat to call from (OOP for entire hand)
- 3-bet or fold only—rarely flat-call (you'll play every postflop street in the worst position)
- 3-bet value: QQ+, AKs, AKo, AQs
- 3-bet bluff: A5s, A4s (slim selection)
- Flat: JJ-TT sometimes IP squeeze opportunities; generally resist

### Blind vs. Blind (SB vs. BB)

When SB opens, BB is in best position (IP postflop) and gets wide calling odds:
- BB can defend very wide (50-60% of hands) with 3-bets and calls
- If SB completes: BB should raise (isolation) aggressively—SB's limp range is capped/weak

---

## 9. Live-Specific Realities

### The Limper Problem

Live $1/$2 tables average 2-4 limpers per orbit. Strategy:

**Never be the first limper** (as opener): Always raise first in.

**With limpers already in:**
- Iso-raise with strong hands (pairs 77+, suited broadway, AJs+, ATs) to play heads-up
- Use formula: **4bb + 1bb per limper** from position; **add 1-2bb extra if OOP**
- Example: 2 limpers in $1/$2, you're on BTN → raise to $10 ($8 + $2 for 2 limpers)
- OOP iso example: 2 limpers, you're in SB → raise to $12-14

**When NOT to iso-raise:**
- Your hand is speculative (small pair 22-55, weak suited connector) and there are 3+ callers likely → over-limp instead (you have implied odds in multiway pot, but not isolation odds)
- You have no position and expect multiple callers who won't fold even to large raises

**Over-limping:** Only with speculative hands in multiway situations where you expect 4+ players and deep stacks (200bb+). Example: 33 with 4 limpers in a $1/$2 game where everyone covers $400—fine to over-limp.

### Larger Opening Sizes Are Normal

Live games use 4-6bb opens as standard (online uses 2-2.5bb). This is correct given:
- Live players call wider regardless of size
- Larger sizes extract more value per combo
- Sizing discipline prevents multiway disaster

### Deeper Effective Stacks

At $1/$2 with $400 max buy-in, stacks are often 150-200bb. At $2/$3 with $500-600 cap, similar depth.

**Deeper stacks implications:**
- Implied odds improve for speculative hands (small pairs, suited connectors) → can play slightly wider
- 3-bet pots create SPRs that allow more postflop maneuverability → can call 3-bets wider
- However: losing a big pot hurts more—don't get married to QQ/JJ preflop when facing massive resistance from tight players

### Straddles

See Section 10 for full coverage. Brief summary:
- Treat the straddle as the new BB for sizing purposes
- Open-raise ranges contract by one position (BTN plays CO range; CO plays HJ range)
- 3-bets shrink to ~2.5x the open vs. 3.5x normally

### Slower Pace = Better Reads

Live games run 20-30 hands/hour vs. 80+ online. Use the extra time:
- Classify opponents in first 30 minutes (tight/loose, passive/aggressive, fish profile)
- Adjust preflop strategy based on observed tendencies, not just position
- Exploit known tendencies aggressively; live players rarely adjust

---

## 10. Straddled Pots

### What Changes with a Straddle

A straddle (typically 2x BB) creates a third blind and shifts action. The straddler acts last preflop (after BB), making it effectively a 3-player blind structure.

**Key adjustment rule:** Shift your range back one position.
- BTN plays CO range (not BTN range)
- CO plays HJ range
- HJ plays LJ range
- LJ/UTG tighten further

**Sizing adjustments:**
- Open-raise: To ~2.5x the straddle size (not 3x of normal BB)
  - Example: $1/$2 game, $4 straddle → open to $10-12 (2.5-3x the $4 straddle)
- 3-bet: ~2.5x the open (smaller than usual because SPR is already compressed)
- 4-bet: Proportionally smaller

**Why smaller sizes in straddle pots:**
- Effective stacks are halved relative to pot (straddle bloats pot without adding depth)
- SPR starts lower → less postflop maneuvering room
- Larger sizes commit you too early

**Premium hands:** Even KK/QQ may call rather than 4-bet when 3 players remain behind with deep stacks in a straddled pot—implied odds change the calculus.

**SB in straddled pots:** Play tight (CO-level range). Only raise, never complete.

---

## 11. Multiway Pots Preflop

### The Multiway Reality

25-40% of live cash hands play multiway. This fundamentally changes preflop decisions.

**Equity changes multiway:**
- Your hand's *raw equity* increases as players enter (more equity vs. each opponent)
- But *equity realization* drops sharply (you'll face multiway aggression, worse position)
- Net result: **Speculative hands drop in value**; **nutted hands (sets, flushes) increase in value**

### What Plays Well Multiway (Call/Over-limp justified):
- Small pairs (22-55): Set mining value improves with more players
- High implied odds: suited connectors that can make straights/flushes **to the nuts**
- Premium hands (still better to raise, but calling is less terrible)

### What Plays POORLY Multiway (Don't call/over-limp):
- Top-pair hands: KQ, AJ, ATo—you'll make top pair but be dominated or face multiple opponents drawing against you
- Weak suited connectors in multiway: 54s, 43s OOP—can't realize equity against 3+ opponents
- Offsuit Broadway cards generally: KQo, QJo in multiway pots suffer from dominated situations

### Squeezing Multiway

When there's an open + 1-2 callers and you're in the blinds or late position:

**Squeeze range:**
- Value: JJ+, AK, AQs (always squeeze these)
- Bluff: A5s, A4s, KQs, QJs (hands that play poorly multiway but well heads-up)

**Squeeze sizing:** ~4-5x the open (to account for callers' dead money)
- Example: BTN opens $8, two callers → squeeze to ~$40-45 from SB

**Why squeeze:** Callers have capped ranges (they didn't 3-bet); their dead money makes your squeeze profitable, and they're likely to fold vs. the large size.

**When NOT to squeeze:** You have a strong hand that wants multiway action (sets, big draws) and players are certain to call regardless.

---

## 12. Exploitative Deviations for Soft Live Pools

### Population Tendencies at $1/$2-$2/$3 Live

| Tendency | Exploit |
|---|---|
| Open-limp too often | Iso-raise wider; size up more |
| Call preflop raises too wide | Value raise more, use larger sizes, reduce bluffs |
| 3-bet only premiums (rarely bluff) | Over-fold to 3-bets; remove most bluff-catchers |
| Rarely 4-bet bluff | 4-bet light only vs. known aggressors |
| Fold too much to BTN/CO steals | Widen BTN/CO range; steal more frequently |
| Tighten late in session (scared money) | Steal more relentlessly |
| Don't adjust to 3-bets | Merge 3-bet range (value-heavy) |

### Specific Exploitative Plays

**Play 1: Widen BTN opens vs. passive/tight blinds**
If SB/BB fold to steals >70% of the time, open BTN to 50%+ of hands. The math makes nearly everything profitable.

**Play 2: Larger iso-raises vs. weak limpers**
If a fish limps and you know they'll call regardless, go to 6-8x BB (not 4x). They'll call anyway—get more money in with your edge.

**Play 3: Value-only 3-betting**
Against calling stations: 3-bet only QQ+/AK/AQs type hands. You don't need balance when opponents never fold. Skip the bluff 3-bets entirely.

**Play 4: Over-fold vs. tight player 3-bets**
If a rock who only plays AA/KK re-raises you, fold JJ, TT, AQ without hesitation. Don't "look him up." These players don't bluff enough for your call to be correct.

**Play 5: Attack tight passive players' blinds aggressively**
Players who rarely defend or 3-bet their blinds lose money automatically. Steal every time you're in CO/BTN with these players in the blinds.

**Play 6: Reduce 3-bet bluff frequency**
The standard GTO bluff-to-value ratio assumes opponents fold at theoretical frequencies. Live opponents call 3-bets much wider. Remove the thin bluff 3-bets; keep only the ones with strong equity (suited Ax, top of suited connectors).

### Opponent Profiles and Preflop Adjustments

**vs. Loose-Passive (Fish / Calling Station):**
- Widen value range (more thin value is profitable)
- Remove all bluffs preflop (they won't fold to 3-bets/raises)
- Size up raises and 3-bets (they'll call anyway; make them pay more)
- Iso-raise aggressively to play heads-up against them

**vs. Tight-Passive (Nit / Rock):**
- Widen steal attempts (they fold blinds too often)
- Narrow value range vs. their 3-bets (only premiums get through)
- Do NOT iso-raise their limps as aggressively—they might have AA limping
- Call their raises only with strong hands

**vs. Loose-Aggressive (LAGG / Maniac):**
- Tighten range vs. their opens (they open wide; 3-bet them with strong hands)
- 4-bet light (they 3-bet too wide; 4-bet with JJ, AQ when they're the aggressor)
- Don't try to bluff them off hands preflop
- Trap with premium hands from OOP rather than 3-betting

---

## 13. $1/$2 → $2/$3 Key Adjustments

### What Changes in the Player Pool

| Factor | $1/$2 | $2/$3 |
|---|---|---|
| Average VPIP | 28-35% | 22-28% |
| Open-limp frequency | High (3-5/orbit) | Lower (1-2/orbit) |
| 3-bet frequency | Very low (3-6%) | Low-moderate (6-10%) |
| 4-bet frequency | Near zero | Rare but present |
| Fold to steal | High (60-75%) | Moderate (50-65%) |
| Player sophistication | Wide variance | More aware/aggressive |
| Stack depth | 100-200bb | 100-200bb (similar) |
| Sizings | 4-6x opens common | 3-5x; slightly more standard |

### Preflop Adjustments Going From $1/$2 to $2/$3

**1. Tighten the middle of your range**
The hands most hurt by tougher competition are borderline mid-position hands (88-77, KJo, A8o). These hands require postflop edges that $2/$3 opponents are better at denying. Fold these more from EP/MP.

**2. Reduce open-limp exploitation frequency**
Fewer limpers at $2/$3. Your iso-raise opportunities decrease. Don't force iso-plays when the table isn't limping.

**3. Add bluff 3-bets selectively**
At $1/$2, bluff 3-bets are rarely justified. At $2/$3, some regulars are sophisticated enough that you need balance. Add A5s-A2s as 3-bet bluffs in LP vs. LP spots.

**4. Reduce steal sizing slightly**
$2/$3 regulars use 3-3.5x more than 4-5x. Open-raising to $15+ from BTN in $2/$3 marks you as a live fish. Use $10-12 as your BTN steal size.

**5. Expect and navigate more 3-bets**
$2/$3 has more 3-betting. Develop your response tree (Section 6) actively, not just theoretically. Know which hands you 4-bet, call, fold before you sit down.

**6. Respect 3-bets more than at $1/$2**
At $1/$2, ignore almost all 3-bets unless the player is known aggressive. At $2/$3, a 3-bet from an unknown can be a semi-bluff—widen your continuing range slightly vs. IP 3-bets.

**7. Attack passive tight players**
$2/$3 still has nitty regulars. Identify them quickly and widen BTN/CO steals vs. their blinds. This is still a massive source of EV.

**8. Fix EP range leaks**
The most common $1/$2 leak that kills at $2/$3: playing KJo, KTo, QJo from EP/MP. These hands face strong resistance and lose significant value against $2/$3 ranges. Tighten EP to the framework in Section 3A.

**9. Reduce calling frequency OOP**
$1/$2 players get away with bad calls OOP because opponents play poorly postflop. $2/$3 opponents apply more pressure. Fold hands that need postflop skill to realize equity when OOP.

**10. Balanced 4-bet range**
At $1/$2, 4-betting is essentially always AA/KK. At $2/$3, capable players will notice and exploit pure value 4-bets by never stacking off vs. your 4-bets. Add A5s/A4s 4-bet bluffs occasionally when your image is tight and the spot is right.

### Sizing Conversion ($1/$2 to $2/$3)

| $1/$2 | $2/$3 | Notes |
|---|---|---|
| Open to $8 (EP) | Open to $12-15 | 4-5bb of $3 |
| Open to $6 (BTN) | Open to $10-12 | 3.5x of $3 |
| Iso $12 (1 limper) | Iso $18-21 | Same formula |
| 3-bet $24 | 3-bet $36-42 | 3x the open |
| 4-bet $55 | 4-bet $90-100 | 2.3-2.5x the 3-bet |

---

## 14. What to Drill and How

### The 5 Core Preflop Drills

**Drill 1: RFI Range Recall by Position (Foundation)**

*What:* For each position (EP, MP, CO, BTN, SB), instantly recall: (a) the hand categories you play, (b) the range floor (weakest hand), (c) approximate % of hands.

*How:* Flashcard system. One card per position; front = position name; back = range floor + key adds. Use spaced repetition (Anki or paper). Session: 10 minutes/day until all 6 positions instant-recall.

*Why it works:* "The best way to memorize ranges is to remember the weakest hand in each category—then everything stronger is auto-include." (bitB Spins, PokerCoaching)

*Metric for mastery:* Can state all 6 positions' range floors in under 60 seconds without hesitation.

**Drill 2: Interactive Preflop Decision Trainer (RFI + 3-bet response)**

*What:* A hand is presented + position + action context → you decide: fold, call, raise. Instant feedback with whether you were correct and why.

*How:* Use Preflop Trainer (prefloptrainer.com) or Preflop Dojo. Set to 9-handed live cash, 100bb depth. Run 50-100 decisions per session.

*Why it works:* "Looking up a chart and recalling the answer under pressure are completely different skills. Drilling builds automatic recall through structured repetition." (Preflop Dojo)

*Metric for mastery:* >85% accuracy across all positions in session.

**Drill 3: 3-Bet Spot Recognition**

*What:* Given an opener's position + your position + your hand, decide: 3-bet value / 3-bet bluff / call / fold. Practice identifying the key variables: IP vs. OOP, opponent range estimate, hand category.

*How:* Scenario cards or trainer software filtering for "vs. raise" spots. Focus on CO vs. BTN and BB vs. BTN as the highest-frequency spots.

*Why it works:* 3-bet spots are high-frequency and high-EV—errors here compound over sessions.

*Metric for mastery:* Can categorize any hand into 3bet/call/fold from any position in <3 seconds.

**Drill 4: Sizing Calculations (Live Math)**

*What:* Given limpers/callers/stacks, calculate the correct raise size in under 5 seconds.

*How:* Mental math drill. Create a set of 20 scenarios:
- "2 limpers, $1/$2, you're on BTN → what's your iso-raise?"
- "Opponent opens $8, you 3-bet from BB → what's your size?"
- "Facing $24 3-bet, you 4-bet → what's your size?"

Practice until sizing is reflexive—you should never be calculating at the table.

*Why it works:* Live poker has enough time between actions; sizing should require zero cognitive load to free up reads.

*Metric for mastery:* 20/20 correct within 3 seconds each.

**Drill 5: Opponent Profile → Preflop Adjustment**

*What:* Given an opponent profile (loose-passive, tight-passive, LAG), identify 3 specific preflop adjustments to make. Decision mapping.

*How:* Create 10 scenario cards with player descriptions and table situations. No software needed—this is conceptual drilling.

*Format example:*
- "The BTN has been limping 80% of hands and folded to your 3-bets twice. He open-raises to $8 UTG. Action: fold/call/3-bet with JJ?"
- Answer: 3-bet (he limps weak hands + his UTG raise = strong, but JJ is top of calling range here)

*Why it works:* Exploitative adjustments are where live low-stakes EV lives. Systematic opponent-profiling to preflop-adjustment mapping is a skill that must be drilled.

*Metric for mastery:* Can state 3 correct exploitative adjustments for any described player profile in <30 seconds.

### Recommended Study Framework

**Week 1-2 (Foundation):** Drill 1 exclusively. Get all 6 positions memorized cold.

**Week 3-4 (Decision Quality):** Drills 1 + 2. Add interactive decision trainer.

**Week 5-6 (3-Bet System):** Drills 2 + 3. Study value/bluff 3-bet hand categories.

**Week 7-8 (Live Integration):** All drills, emphasizing Drills 4 + 5. Simulate live table situations.

**Ongoing:** 15-20 minutes preflop trainer before any live session. Review hands after session focusing on preflop decisions only.

### Training Tools

| Tool | Use Case | Cost |
|---|---|---|
| [Preflop Trainer](https://prefloptrainer.com/) | RFI + vs. raise decisions, 9-handed, multiple stack depths | Free tier available |
| [Preflop Dojo](https://preflopdojo.com/) | Structured katas building automatic recall | Paid |
| [FreeBetRange](https://freebetrange.com/) | Range visualization, preflop charts hub | Free |
| [Chasing Poker Greatness Live Cash Bootcamp](https://chasingpokergreatness.com/) | 88 live-specific preflop ranges, 67 flashcard decks, AI-adaptive | Paid course |
| [GTO Wizard](https://gtowizard.com/) | Solver for spot analysis, live cash 8-max solutions | Subscription |
| Anki (free) | Spaced repetition for range floor memorization | Free |

---

## 15. Sources

### Primary Sources (fetched/reviewed)

- **Upswing Poker — Preflop Charts & Ranges:** [https://upswingpoker.com/charts/](https://upswingpoker.com/charts/)
- **Upswing Poker — RFI Strategy:** [https://upswingpoker.com/preflop-open-strategy-rfi-explained/](https://upswingpoker.com/preflop-open-strategy-rfi-explained/)
- **Upswing Poker — 3-Bet Strategy:** [https://upswingpoker.com/3-bet-strategy-aggressive-preflop/](https://upswingpoker.com/3-bet-strategy-aggressive-preflop/)
- **Upswing Poker — 4-Bet & 5-Bet Strategy:** [https://upswingpoker.com/4-bet-5-bet-preflop-strategy/](https://upswingpoker.com/4-bet-5-bet-preflop-strategy/)
- **Upswing Poker — vs. 3-Bet Strategy:** [https://upswingpoker.com/vs-3-bet-pre-flop-position-strategy-revealed/](https://upswingpoker.com/vs-3-bet-pre-flop-position-strategy-revealed/)
- **Upswing Poker — Live Preflop Rake Adjustments:** [https://upswingpoker.com/live-preflop-rake-adjustments/](https://upswingpoker.com/live-preflop-rake-adjustments/)
- **Upswing Poker — SB Strategy:** [https://upswingpoker.com/small-blind-poker-strategy-tips/](https://upswingpoker.com/small-blind-poker-strategy-tips/)
- **Upswing Poker — BB vs SB:** [https://upswingpoker.com/defend-big-blind-vs-small-blind/](https://upswingpoker.com/defend-big-blind-vs-small-blind/)
- **Upswing Poker — Multiway Pots & Squeezing:** [https://upswingpoker.com/multiway-pot-preflop-squeezing-leaks/](https://upswingpoker.com/multiway-pot-preflop-squeezing-leaks/)
- **GTO Wizard — Preflop Range Morphology:** [https://blog.gtowizard.com/preflop-range-morphology/](https://blog.gtowizard.com/preflop-range-morphology/)
- **GTO Wizard — Live Cash Solutions:** [https://blog.gtowizard.com/live-cash-solutions-and-4000-new-scenarios-for-cash-mtt-formats/](https://blog.gtowizard.com/live-cash-solutions-and-4000-new-scenarios-for-cash-mtt-formats/)
- **GTO Wizard — Straddled Pots:** [https://blog.gtowizard.com/preflop-strategy-in-straddled-pots/](https://blog.gtowizard.com/preflop-strategy-in-straddled-pots/)
- **PokerCoaching.com — Best Preflop Strategy for Cash Games:** [https://pokercoaching.com/blog/the-best-preflop-strategy-to-crush-cash-games/](https://pokercoaching.com/blog/the-best-preflop-strategy-to-crush-cash-games/)
- **PokerCoaching.com — 3-Bet Strategy:** [https://pokercoaching.com/blog/3-bet-poker-strategy/](https://pokercoaching.com/blog/3-bet-poker-strategy/)
- **PokerCoaching.com — 4-Bet Strategy:** [https://pokercoaching.com/blog/4-betting-strategy/](https://pokercoaching.com/blog/4-betting-strategy/)
- **PokerCoaching.com — Punishing Limpers:** [https://pokercoaching.com/blog/3-deadly-techniques-to-punish-limpers-in-live-cash-games/](https://pokercoaching.com/blog/3-deadly-techniques-to-punish-limpers-in-live-cash-games/)
- **PokerCoaching.com — Most Profitable Preflop Adjustments:** [https://pokercoaching.com/blog/most-profitable-preflop-adjustments-for-small-stakes-poker/](https://pokercoaching.com/blog/most-profitable-preflop-adjustments-for-small-stakes-poker/)
- **PokerCoaching.com — How to Study Preflop Ranges:** [https://pokercoaching.com/blog/how-to-study-preflop-ranges-and-poker-strategies/](https://pokercoaching.com/blog/how-to-study-preflop-ranges-and-poker-strategies/)
- **Jonathan Little — Small Stakes Cash Charts:** [https://jonathanlittlepoker.com/smallcashcharts/](https://jonathanlittlepoker.com/smallcashcharts/)
- **SplitSuit — Live Cash Game Truths:** [https://www.splitsuit.com/live-poker-cash-game-truths](https://www.splitsuit.com/live-poker-cash-game-truths)
- **SplitSuit — Cash Game Strategy $1/$2-$2/$5:** [https://www.splitsuit.com/cash-game-poker-strategy](https://www.splitsuit.com/cash-game-poker-strategy)
- **BlackRain79 — Full Ring Strategy:** [https://www.blackrain79.com/2018/02/full-ring-poker-strategy.html](https://www.blackrain79.com/2018/02/full-ring-poker-strategy.html)
- **BlackRain79 — Preflop Cheat Sheet:** [https://www.blackrain79.com/2023/05/preflop-poker-strategy.html](https://www.blackrain79.com/2023/05/preflop-poker-strategy.html)
- **Red Chip Poker — Preflop Charts:** [https://redchippoker.com/preflop-poker-charts/](https://redchippoker.com/preflop-poker-charts/)
- **FreeBetRange — 9-Max Preflop Charts:** [https://blog.freebetrange.com/article/9-max-poker-preflop-charts-for-texas-holdem](https://blog.freebetrange.com/article/9-max-poker-preflop-charts-for-texas-holdem)
- **Chasing Poker Greatness — Live Cash Preflop Bootcamp:** [https://chasingpokergreatness.com/live-cash-preflop-bootcamp-poker-course/](https://chasingpokergreatness.com/live-cash-preflop-bootcamp-poker-course/)
- **Preflop Trainer:** [https://prefloptrainer.com/](https://prefloptrainer.com/)
- **Preflop Dojo:** [https://preflopdojo.com/](https://preflopdojo.com/)
- **PokerAtlas — Transitioning 1/2 to 2/5:** [https://www.pokeratlas.com/table-talk/poker-strategy-and-advice/transitioning-from-1-2-no-limit-to-2-5-no-limit-by-resident-pro-benton-blakeman/](https://www.pokeratlas.com/table-talk/poker-strategy-and-advice/transitioning-from-1-2-no-limit-to-2-5-no-limit-by-resident-pro-benton-blakeman/) (403 returned but data sourced from search summary)

### Expert Consensus vs. Disagreement

**Consensus across sources:**
- Raise-or-fold from all positions (no limping when first in)
- Position is the primary determinant of range width
- Live games warrant larger sizing than online equivalents
- Exploit pool tendencies rather than balance for GTO at low stakes
- BB gets a very wide calling range due to pot odds

**Where experts disagree:**
- SB strategy: Some coaches (Jonathan Little) suggest premium hands can limp from SB to trap; most (Upswing, SplitSuit, GTO Wizard) recommend raise-or-fold. At live $1/$2-$2/$3, the raise-or-fold approach is safer and simpler.
- 3-bet bluff frequency: More aggressive coaches (Upswing) suggest including more bluffs even live; conservative coaches (SplitSuit, BlackRain79) recommend value-only 3-betting at low stakes. The truth: start value-heavy; add bluffs as you gain reads.
- Suited connector play: Some coaches include more suited connectors from EP at live games (implied odds argument); GTO Wizard solutions and solver-era coaches recommend folding most below JTs from EP even live, citing equity realization problems.
