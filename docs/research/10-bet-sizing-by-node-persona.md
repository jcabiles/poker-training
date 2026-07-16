# 10 — Bet Sizing by Node × Persona (Live $2/$3, Fixed)

**Purpose:** Give a defensible **fixed** bet size for every *node × persona* cell so bots (and later hero) act at realistic live-$2/$3 prices, and enumerate the nodes where hero should be offered **two** size options. Stakes anchor: live $2/$3 NLHE, 9-handed, ~100BB effective (`$3` = 1 BB; a "3bb open" = $9). Preflop sizes are in **bb**; postflop sizes are **frequency-weighted pot-fraction bucket weights** (the existing persona lever shape), sampled independently of hand strength so the anti-sizing-tell rule holds. All sizes are **heuristic + live-$2/$3-research-grounded, never solver tables**; every EV/price reasoning stays labeled *approximate*.

**Source / full decision doc:** `docs/ai-dlc/research/RES-B-bet-sizing.md` (RES-B). This entry captures the size tables and the two-option node list; the full spike also carries the "sizes differ by level?" resolution, the node-agnostic-limitation decision (Option A vs B), and the exact R2/R3 hand-off. **Consumed by build slices R2** (realistic persona-flavored fixed sizes) **and R3** (hero two-option sizing). No app code was edited by the research.

---

## 1. The framing question — resolved

**User intuition:** "sizes differ by level." **Resolution: sizes are stakes-calibrated to $2/$3, persona-flavored, and FIXED.** Two readings of "level," both resolved:
- **"level" = stakes** — *confirmed as the calibration target, refuted as a per-hand dial.* Live $2/$3 opens run larger than online/GTO baselines (3bb standard vs 2.25–2.5bb) and 3-bets/4-bets skew value-heavy because the pool under-bluffs. The app is calibrated to the $2/$3 point and exposes **no** stakes slider.
- **"level" = hand strength → size** — *refuted for bots.* Letting a bot pick size from hand strength creates a **sizing tell**. Postflop bot sizes stay a frequency-weighted distribution per persona × node, sampled independently of the made-hand bucket (§5). Hero is different — R3 lets hero choose and grades it (a training feature, not a bot tell).

**Net:** one fixed, $2/$3-calibrated size menu per persona per node. No sliders, no stakes dial, no strength→size leak for bots.

---

## 2. Persona sizing personalities (the skew axes)

| Persona | Preflop skew | Postflop skew |
|---|---|---|
| **TAG** | Textbook: 3bb open, 3–3.5x 3-bet, ~2.4x 4-bet | Balanced, texture-matched; modest overbets only with nut advantage |
| **Nit** | Same textbook sizes, **far fewer** raising hands; slightly smaller postflop | Small/standard, value-only, polarized-but-tight |
| **LAG** | 3bb open, 3.5x 3-bet, applies pressure wider | **Polarized**: more big/overbet on wet + more small range-bets; widest spread |
| **Maniac** | **Oversized**: ~4.5bb open, ~5.5x 3-bet | **Overbets** frequently (0.75–1.5x pot), value and bluff alike, position-unaware |
| **Calling Station** | Limps/min-raises; rarely raises (only monsters); slightly larger iso when it does | Passive: **small** sizes, tiny raise frequency, leans 0.33 pot |
| **Passive Fish** | **Limps** huge; over-limps; slightly oversized opens with its few raising hands | Passive-but-loose: small sizes, leans 0.33 pot |

> **Fish "sizing tell" deliberately NOT reproduced.** Real fish leak strength through size; reproducing that would teach the wrong lesson and violate the anti-sizing-tell rule. The fish persona uses a *small-leaning fixed bucket distribution* (0.33 weighted heavily) sampled independently of strength.

---

## 3. Preflop size table (bb)

Multipliers match the existing `sizing: {open_bb, threebet_mult, fourbet_mult}` lever. `threebet_mult` = multiple of the open; `fourbet_mult` = multiple of the 3-bet. 5-bet is always a **jam** to effective stack (`vs_4bet.json` `sizing_bb: 100.0` overridden to the stack by the sampler).

| Node | TAG | Nit | LAG | Maniac | Calling Station | Passive Fish |
|---|---|---|---|---|---|---|
| **Open (RFI)** `open_bb` | 3.0 | 3.0 | 3.0 | 4.5 | 3.5 | 4.0 |
| **3-bet** `threebet_mult` | 3.5 | 3.5 | 3.5 | 5.5 | 3.0 | 3.0 |
| **4-bet** `fourbet_mult` | 2.4 | 2.3 | 2.4 | 3.0 | 2.2 | 2.2 |
| **5-bet / jam** | shove | shove | shove | shove | shove | shove |

**These values are exactly what already ships in `content/personas/*.json` — RES-B confirms them as correct/defensible for $2/$3.** Live $2/$3 standard open = 3bb ($9); recs open larger (4–5x). 3-bet ≈ 3.5x the open (IP 3x / OOP ~3.5–4x); 4-bet ≈ 2.2–2.4x the 3-bet. Maniac oversizes across the board; station/fish compress the raise (passive types 3-bet tiny + rarely — labeled **heuristic**). **The preflop levers are already right; the unrealism the user reported is postflop (§5) plus missing turn/river sampling nodes (§6).**

**Position nuance (optional):** the `content/preflop/rfi.json` *baseline* path already varies open size by seat (UTG/LJ/SB 3.0; HJ/CO/BTN 2.5) for grading hero. The persona `open_bb` is a single per-persona number applied across seats. Recommendation: **leave it a single value** (matches lever shape); a per-seat `open_bb_by_position` is new schema work, not recommended for R2's appetite. An SB +0.5bb bump is textbook-justified but optional polish.

---

## 4. Postflop size table (pot-fraction bucket weights)

Format matches the existing `postflop.sizing: {"0.33":w, "0.5":w, "0.75":w, "1.0":w}` lever — each cell is a weight distribution over pot-fractions, **sampled independently of hand strength** (§7). The current pack has *one* `postflop.sizing` block per persona (node-agnostic), applied to c-bet, barrel, and raise sizing alike.

### 4.1 Standard node baselines (what the *node* wants — graded against by R3)

Anchored to `docs/research/06-postflop-reference-tables.md` (GTO Wizard aggregates) and `docs/research/02-postflop-strategy.md` §3/§7.

| Node | Standard size (pot-fraction) | Source |
|---|---|---|
| Flop c-bet — dry/paired | 0.33 (range-bet small) | doc-06 §2 (KK5 ~96% small; QQ6 33%) |
| Flop c-bet — wet two-tone | 0.75 (polarized, overbet possible) | doc-06 §2 (KJ7 75–125% pot) |
| Flop c-bet — monotone | 0.33 when betting (mostly check) | doc-06 §2 (QJT mono ~50% freq) |
| Turn barrel | 0.67 (scare-card value + best draws) | doc-06 §3 (≈67% on blank/scare) |
| River value/barrel — polar | 0.75–1.0 | doc-06 §5 (pot-size = 2:1 value:bluff) |
| River thin value / induce | 0.33–0.5 | doc-02 §6.3 |
| Check-raise (flop) | raise-to ≈ 2.5–3x the c-bet ⇒ ~1.0 of the new pot | doc-02 §4.4 |
| Facing-a-bet raise (non-c-r) | ~2.5–3x the bet ⇒ 0.75–1.0 bucket | 888poker/BlackRain79 |

### 4.2 Persona postflop distributions (fixed, node-agnostic — as shipped, confirmed)

| Persona | 0.33 | 0.5 | 0.75 | 1.0 | 1.5 | Center of mass | Verdict |
|---|---|---|---|---|---|---|---|
| **TAG** | 0.25 | 0.35 | 0.30 | 0.10 | — | ~0.55 pot | Keep — balanced, texture-spanning |
| **Nit** | — | 0.40 | 0.45 | 0.15 | — | ~0.63 pot | Keep — slightly bigger/polar, value-only |
| **LAG** | 0.15 | 0.30 | 0.35 | 0.20 | — | ~0.66 pot | Keep — widest spread incl. more 1.0 |
| **Maniac** | — | — | 0.40 | 0.35 | 0.25 | ~1.0 pot | Keep — overbet-heavy; adds a **1.5 bucket** (new pot-fraction key already in the pack) |
| **Calling Station** | 0.60 | 0.30 | 0.10 | — | — | ~0.42 pot | Keep — small-leaning, passive |
| **Passive Fish** | 0.60 | 0.30 | 0.10 | — | — | ~0.42 pot | Keep — small-leaning; sizing tell deliberately not reproduced |

**Postflop finding:** the persona distributions **as shipped are already defensible**. The user-reported "unrealistic sizes" is **not** primarily a wrong-weights problem — it is (1) the node-agnostic limitation below, and (2) missing turn/river sampling nodes (§6).

### 4.3 Node-agnostic limitation — R2 decision point

The single `postflop.sizing` block cannot express "small on dry flops, big on wet turns" — it blends them. Two options (RES-B recommends **A**):
- **Option A (no schema change, recommended):** keep one `sizing` block per persona; accept texture/street nuance is averaged. The distributions span 0.33–1.0 so some small and some big sizes appear, and frequency-sampling means no single hand's size is a tell. Ships R2 with zero schema change.
- **Option B (`sizing_by_node` lever):** add an optional per-node override map (`cbet_dry`, `cbet_wet`, `turn_barrel`, `river_value`) falling back to the flat block. Richer realism at the cost of a schema addition + engine plumbing.

---

## 5. R3 — nodes that surface TWO hero size options

R3 offers hero exactly **two** context-specific sizes per supported node, graded against the §4.1 baseline (approx EV). **Seven two-option nodes** (open excluded; vs-4bet is jam-or-fold):

| Node | Option 1 (default/small) | Option 2 (large/polar) | Why two |
|---|---|---|---|
| **Flop c-bet** | 0.33 pot (range-bet) | 0.75 pot (polar) | Small on dry range-advantage boards, big/polar on wet. The flagship c-bet fork. |
| **Turn barrel** | 0.5 pot | 0.75 pot | "Keep SPR manageable" vs "charge draws / set up river jam." |
| **River value/barrel** | 0.5 pot (thin value/induce) | 1.0 pot (polar) | Small gets called by more worse / induces; pot maximizes vs a station's inelastic range. |
| **Facing a 3-bet** | Standard 4-bet (2.4x) | Shove (5-bet jam) | The interview's canonical example — re-raise-and-fold-able 4-bet vs commit-now jam. |
| **Facing a 4-bet** | Call *(non-size fork)* | Shove (5-bet jam) | At 100BB the only two live "sizes" are flat vs jam; jam-or-fold, may be excluded from the size UI. |
| **Check-raise (flop)** | 2.5x the c-bet (~0.75 new-pot) | 3.5x the c-bet (~1.0+ new-pot) | Smaller on dry, larger on wet to deny equity. |
| **Facing-a-bet raise (non-c-bet)** | 2.5x the bet (0.75) | 3x the bet (1.0) | Pot-controlled value-raise vs commit/deny-equity raise. |
| **Preflop open** | *(no fork — excluded)* | — | Single $2/$3-standard open per seat/persona. |

The **flagship pairs** the interview named — **vs-3bet: 4-bet OR shove** and **c-bet: 1/3 OR 2/3** — are both present.

---

## 6. Missing sampling nodes (turn barrel, river value/barrel)

Per the "turn/river engine deferred" note, there is no *node-specific* turn-barrel or river-value sampling node today. The flat `sizing` block **is** applied whenever a BET/RAISE is sampled on any street, so turn/river bets do get a size — they just inherit the flat distribution (acceptable under Option A). When the turn/river engine lands, revisit Option B. No R2 action beyond awareness.

---

## 7. Anti-sizing-tell constraint — respected

- Postflop sizes are frequency-weighted bucket distributions (§4.2), sampled **independently of the made-hand bucket** — a monster and a bluff on the same node draw from the same distribution, so no size tell.
- Preflop sizes are fixed per persona per node — a maniac opens 4.5bb with AA and 72s alike.
- The fish "sizing tell" is deliberately not reproduced.
- R3's hero choice is a graded training decision, not a bot tell — out of scope for this constraint.

---

## 8. Sources

- GTO Wizard — [Preflop Raise Sizing](https://blog.gtowizard.com/preflop-raise-sizing-examining-2-key-factors/), and via doc-06: [C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/), [Turn Check-Raise Heuristics](https://blog.gtowizard.com/turn-check-raise-heuristics/), [Principles of River Play](https://blog.gtowizard.com/principles-of-river-play/)
- Upswing Poker — [4-Bet Sizing (2.2x)](https://upswingpoker.com/4-bet-size-strategy/), [Straddle / 3-Blind Pots](https://upswingpoker.com/straddle-pot-strategy-three-blind-cash-game/)
- GGPoker — [3-Bet and 4-Bet](https://ggpoker.com/blog/3-betting-and-4-betting/) · BlackRain79 — [4bet Sizing](https://www.blackrain79.com/2020/06/4bet-sizing.html) · 888poker — [Bet Sizing Guide](https://www.888poker.com/magazine/strategy/bet-sizing-poker-comprehensive-guide)
- pokerology — [Player Types](https://www.pokerology.com/poker/strategy/playing-styles/) · pokerstrategy — [Five Player Types](https://www.pokerstrategy.com/strategy/bss/five-player-types/) · coinpoker — [Playing Styles](https://coinpoker.com/strategy/playing-style/)
- Internal — `docs/research/02-postflop-strategy.md` (§3, §5, §6, §7, §10, §11); `docs/research/06-postflop-reference-tables.md` (§2, §3, §5); `docs/ai-dlc/research/RES-B-bet-sizing.md` (full decision doc); `content/personas/*.json`; `backend/app/domain/personas_postflop.py`.
