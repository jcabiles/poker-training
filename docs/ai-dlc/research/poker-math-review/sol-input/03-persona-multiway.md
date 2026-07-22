---
title: Poker Math — Persona & Multiway Modeling (Estimates)
tags: [poker, gto, poker-math, personas, multiway, modeling, poker-coach]
created: 2026-07-21
companion_to: "Poker Math — Comprehensive Reference"
scope: NLHE cash — the parts of poker with NO single solved-correct answer
status: draft — built from vetted research, pending final review
---

# Poker Math — Persona & Multiway Modeling (Estimates)

> [!abstract] What this document is (plain terms)
> The other two docs hold math with correct answers. **This one holds the parts that don't have one.** Two things in poker cannot be "solved" to a single right number: (1) how a specific *type* of player deviates from perfect play, and how hard to punish them, and (2) how to play a pot with **three or more** players (there is provably no unique optimal strategy). Everything here is therefore a **research-backed estimate with a range**, never a derived constant — and it's all labeled that way. This is the honest home for the numbers that make the bots feel like *people* rather than solvers.

> [!warning] Governing rule for this whole document
> **Nothing here is solved.** Exploitative deviations depend on the actual opponent (no game-theoretic unique answer), and multiway pots have **infinitely many equilibria** even in toy 3-player games (Brown & Sandholm, *Science* 2019 — Pluribus used self-play + search, not an exact solve). Every figure below is tagged **[SOURCED estimate]** (a real published band) or **[HEURISTIC — not solved]** (direction only). Treat all of it the way the app already treats its EVs: *approximate.*

---

## 1. Player-type stat profiles

> [!note] In plain terms
> Tracking software sorts players by a few numbers — how many hands they play (VPIP), how often they raise preflop (PFR), how aggressive they are after the flop (AF), and how often they show down (WTSD). These bands are how you'd label a bot's "type" and check it behaves like one. The looseness/aggression numbers agree well across sources; the showdown and fold-to-c-bet numbers genuinely disagree between sources, so those are shown as ranges, not cutoffs.

- **Representative 6-max bands** (fuzzy boundaries; era/sample-dependent). **[SOURCED estimate — HUD-vendor + coaching tables; ranges vary by source]**

  | Type | VPIP | PFR | 3-bet% | AF | Notes |
  |---|---|---|---|---|---|
  | Nit | ~12–16 | ~10–13 | low | low | tight-passive; big bets = nuts |
  | TAG | ~18–24 | ~15–20 | ~6–9 | ~2–3 | the winning baseline |
  | LAG | ~26–32 | ~22–27 | ~9–12 | high | high pressure, higher variance |
  | Calling station | ~40+ | low | very low | <1 | calls too much, rarely raises |
  | Passive fish | ~35–50 | low | very low | low | limps/calls, low aggression |
  | Maniac | ~50+ | very high | high | very high | raises/re-raises constantly |

- **Full-ring** runs a few points tighter across the board; full-ring per-type tables are thinner in the literature. **[SOURCED — noted gap]**
- **AFq definition** (frequently conflated with AF): **AFq = (bets + raises) / (bets + raises + calls + folds) × 100** — the % of postflop actions that are aggressive; distinct from the **AF ratio** = (bets+raises)/calls. **[SOURCED — Upswing]**
- **WTSD / fold-to-c-bet / cbet% "good" bands show real cross-source disagreement** (e.g. WTSD "good" is quoted anywhere ~25–35% depending on author) — use a range like "high-20s to low-30s," never a hard cutoff. **[SOURCED estimate — disagreement documented]**

## 2. Exploitative adjustments (direction only — no solved magnitudes)

> [!note] In plain terms
> Once you know the type, you tilt your play to punish their specific mistake. The *directions* are well-established and sourced. The *magnitudes* — exactly how much wider to call, how much bigger to bet — are NOT published anywhere as numbers, because they depend on the specific opponent. So this section gives you the correct move and honestly refuses to invent a percentage.

- **vs Calling station / Passive fish:** stop bluffing; value bet **thinner and bigger** (they pay off); isolate; never try to fold them out. **[HEURISTIC — direction sourced; magnitude not solved]**
- **vs Nit:** steal/bluff **more** (they over-fold); but **respect their aggression** — fold marginal hands to their raises. **[HEURISTIC — direction sourced]**
- **vs Maniac:** stop bluffing; **call down lighter / bluff-catch wider**; **trap** with strong hands and let them barrel into you. **[HEURISTIC — direction sourced]**
- **vs LAG:** **3-bet/4-bet back**, don't over-fold, deny their fold equity by continuing more. **[HEURISTIC — direction sourced]**
- **Illustrative-only figures** (do not hard-code): "bluff to ~0 vs a station that folds ~20%" — the 20% is an example, not a threshold. **[HEURISTIC — illustrative]**
- **Cost of exploiting:** you become exploitable yourself — correct vs a non-adapting bot/player, dangerous vs a thinker. **[SOURCED principle]**
- **Persona-as-model:** a persona bot *is* a starting range + deliberately-skewed action frequencies embodying a type's leaks. Its "distance from GTO" is a **design choice**, not a solved value — pick it to be recognizable and punishable, and label the resulting stats as targets, not truths.

## 3. Multiway play (3+ players — no unique solution)

> [!note] In plain terms
> With three or more players, there is no single "correct" strategy — provably. So this is all principled rules of thumb, not solved numbers. The reliable directions: bluff much less (you must get through everyone), value bet more selectively (someone probably has something), and remember the "defend enough" duty splits across the players still in.

- **No unique equilibrium:** even toy 3-player games have infinitely many equilibria; superhuman 6-max bots (Pluribus) use self-play + search, not an exact solve. **[SOURCED — Brown & Sandholm, Science 2019]**
- **Bluffing/c-bet frequency drops sharply** with each added opponent; c-bet roughly **halves from HU to 3-way (approx solver aggregate, ~70% → ~35%)** — a rule of thumb, not a solved constant. **[SOURCED estimate — ThinkGTO citing "GTO Ranges+"; secondary aggregator]**
- **Value betting tightens** (more players → more likely someone connects); thin value shrinks. **[HEURISTIC — direction sourced]**
- **Defense distributes:** a bluff must get through everyone, so each opponent's **fold ceiling** scales ~as the **n-th root** of the heads-up fold rate (α) — meaning each opponent individually **defends less** than heads-up (defense is *shared*; exact arithmetic in the [[Poker Math — Calibration & Numbers (Spec)|spec §9]]). *How* real ranges implement it is heuristic. **[SOLVED math / HEURISTIC implementation]**
- **Practical net:** in loose live $2/$3 (routinely multiway) the correct posture is value-lean + bluff-dampened — which is exactly the direction a persona engine should encode, labeled approximate.

## 4. Short-stack push/fold ranges (directional; out of the 100bb scope)

> [!note] In plain terms
> When stacks are short (≤ ~15 big blinds) play becomes shove-or-fold with published charts. The app runs at 100bb, so this is out of scope — kept here only as a directional pointer. The exact hand charts come from a single secondary source, so treat them as "roughly this shape," not gospel.

- Ranges **widen as stacks shorten**; the small blind is the natural shover (~50% of hands at 10bb, directional). **[DIRECTIONAL — single secondary source; out of 100bb scope]**
- The shove-EV math itself is solid and lives in the [[Poker Math — Calibration & Numbers (Spec)|spec §7]]; only the exact combos are untrustworthy here.

---

## Sources (curated from the vetted research)

- PokerTracker/Hold'em Manager reference tables, SplitSuit, smartpokerstudy, Natural8, Upswing — player-type stat bands (with documented cross-source disagreement).
- Upswing Poker — AFq definition; exploit directions.
- GTO Wizard — "Quirks of Nash Equilibrium in Multiway"; exploit (nodelock) examples.
- ThinkGTO — HU→3-way c-bet ~halving (attributing "GTO Ranges+" solver output; secondary aggregator).
- Brown & Sandholm, *Science* 2019 (Pluribus) — multiway has no unique equilibrium.
- Full per-claim provenance + DROP/DOWNGRADE rulings: `docs/research/_vetting-verdict.md` and `docs/research/player-types-and-exploits.md`, `docs/research/cbet-and-multiway.md`, `docs/research/pushfold-shove-ev.md`.
