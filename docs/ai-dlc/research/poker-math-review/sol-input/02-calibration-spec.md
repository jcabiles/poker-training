---
title: Poker Math — Calibration & Numbers (Spec)
tags: [poker, gto, poker-math, calibration, spec, poker-coach]
created: 2026-07-21
companion_to: "Poker Math — Comprehensive Reference"
scope: NLHE cash, ~100bb, live $2/$3 focus
status: draft — built from vetted research (docs/research/_vetting-verdict.md), pending final review
---

# Poker Math — Calibration & Numbers (Spec)

> [!abstract] What this document is (plain terms)
> The [[Poker Math — Comprehensive Reference|explainer]] teaches the *concepts*. This one holds the **actual numbers** you'd use to build and test the bots: how often to defend against a given bet, how much of your equity you really collect, canonical bet sizes, rake, and so on. Every number here is tagged so you know how much to trust it: **[SOLVED]** = provable arithmetic, **[SOURCED]** = verified against a credible source (cited), **[DERIVED-ASSUMPTION]** = we computed it ourselves because no source publishes it (use with care). Numbers that had *no* trustworthy value were deliberately left out and pushed to the [[Poker Math — Persona & Multiway Modeling (Estimates)|modeling note]].

> [!warning] Provenance
> Built from seven research dumps (`docs/research/`) that were adversarially vetted for usability (`docs/research/_vetting-verdict.md`). Only claims rated **USE-AS-IS** or **USE-WITH-CAVEAT** made it in; **DROP** and **DOWNGRADE** items were excluded or moved to the modeling note. Citations are inline.

---

## 1. Faced a bet → how much to continue (the core validation computation)

> [!note] In plain terms
> This is the single most-used check for whether a bot defends correctly. When the bot faces a bet, two numbers say how much of its hands it should keep: **MDF** (the minimum share it must continue with so the bettor can't profit by bluffing any two cards) and the **pot-odds break-even** (the equity a pure bluff-catcher needs to call). Both change with the size of the bet — that's the whole point. The one twist: MDF assumes the bettor *could* be bluffing enough; against a weak player who under-bluffs, you're allowed to fold more than MDF.

- **MDF** = P / (P + B); **pot-odds break-even to call** = B / (P + 2B). **[SOLVED]**
- **Worked example** (pot P = 100, bet B = 75, i.e. ¾-pot):
  - MDF = 100/175 = **57.1%** → continue (call+raise) with ≥57% of range.
  - Break-even call equity = 75/250 = **30%** → a pure bluff-catcher needs ≥30% equity vs the betting range.
- **By size — the validation table** (a bot's fold frequency should track the α column against a balanced bettor):

  | Bet (× pot) | MDF (defend ≥) | α (may fold ≤) | Break-even call equity |
  |---|---|---|---|
  | ⅓ | 75% | 25% | 20% |
  | ½ | 67% | 33% | 25% |
  | ⅔ | 60% | 40% | ~28.6% |
  | ¾ | 57% | 43% | 30% |
  | pot | 50% | 50% | 33% |
  | 2× | 33% | 67% | 40% |

  **[SOLVED]** (closed-form; matches the explainer §2–§3).
- **Capped-range adjustment** *(the nuance MDF alone misses)*: MDF is the floor **against a bettor who is balanced/uncapped**. When the bettor is **capped** (can't hold the nuts on this line) or **under-bluffs** (typical weak/passive players), continue via **pot odds vs their *actual* value:bluff**, not MDF — you may fold **more** than MDF vs an under-bluffer, and should **defend more / raise** vs an over-bluffer. **[SOLVED-principle; magnitude is opponent-specific → see modeling note]**
- **Realization caveat:** the "call if equity ≥ break-even" test uses **realized** equity (§2), not raw — decisive OOP.

## 2. Equity realization (EQR / R)

> [!note] In plain terms
> You rarely collect your full equity — position and the betting lead change how much you actually win. This section gives the real formula and honest example numbers. Note the earlier "IP is worth ~5–10%" figure was wrong (too precise); the true gap swings widely by spot, which is exactly why we show examples rather than one constant.

- **EQR = realized-pot-share / raw-equity**; equivalently **realized EV ≈ raw equity × EQR × pot**. **[SOURCED — GTO Wizard glossary]** (worked: 70% pot-share on 40% equity → EQR = 175%).
- **Continue rule:** call iff **raw_equity × R ≥ pot-odds required equity** (not raw equity alone). **[SOLVED — direct consequence of the EQR definition]**
- **Illustrative single-flop values** (label each as one spot, never a global constant): **[SOURCED — GTO Wizard, illustrative]**
  - 9♠3♠2♦ flop: BB (OOP) R ≈ **79%** vs IP R ≈ **118%** (~39-point gap).
  - A capped/low-playability OOP hand can realize as little as **~2%**; gaps of 20–40+ points are normal when OOP is capped.
  - K9o defending BB vs a UTG open: 35% raw → ~21% realized (R ≈ 60%) — **directional illustration only**, not a calibration constant.
- **Do NOT** encode a single "IP vs OOP edge" scalar — it's spot-dependent (single-digits to ~15pts in shallow/high-playability spots; 20–40+pts when OOP is capped). **[correction vs the old base-doc "5–10%"]**

## 3. Pot odds / MDF / bluff-to-value — consolidated (reference)

> [!note] In plain terms
> The three price-and-frequency tables the bots must respect, gathered in one place for calibration. Full derivations live in the explainer; this is the lookup.

- **Break-even to call B into P** = B/(P+2B). **Break-even pure-bluff fold freq** = B/(P+B) = α. **[SOLVED]**
- **Polar-river bluff fraction** = f/(1+2f); **value:bluff** = (1+f):f (f = bet/pot): ⅓→20%(4:1), ½→25%(3:1), ⅔→~28.6%(2.5:1), pot→33%(2:1), 2×→40%(1.5:1). **[SOLVED]**
- **Shove/bet EV** = F·P + (1−F)·[E·(P+B) − (1−E)·B]; break-even fold F = Risk/(Pot+Risk). **[SOLVED]**

## 4. Preflop ranges & sizing

> [!note] In plain terms
> The hard, checkable preflop numbers: how a 3-bet range splits into value vs bluffs (pure combinatorics), the standard sizes, and the blocker logic for bluffs. A few upper-tree numbers (4-bet multiplier, 5-bet range) are conventions, not solved values — flagged as such so they aren't over-trusted.

- **3-bet value/bluff combinatorics** (share of all 1326 combos): KK+ = 0.9%, QQ+/AK = 2.6%, TT+/AQ+ = 4.7%. **[SOLVED — SplitSuit]** Use to build a target value:bluff at a chosen 3-bet %.
- **3-bet construction:** linear/merged when IP or facing wide (e.g. SB vs BTN); polarized (value + Axs blocker bluffs) when OOP-and-closing. **[SOURCED — consensus]**
- **3-bet sizing:** ~**3× the open IP**, ~**3.5–4× OOP**; shape agreed multi-source, exact multiple approximate. **[SOURCED, approximate]**
- **4-bet:** value core QQ+/AK (JJ mixes); **Axs blocker 4-bet bluffs** (holding an ace cuts opp AA 6→3 and AK 12→8). **[SOLVED — combinatorics]** Sizing "~2.2–2.5× the 3-bet" is a **convention, NOT solver-sourced** — do not treat as a solved target. **[CONVENTION]**
- **5-bet (100bb):** value-heavy, shove-dominant (~QQ+/AK commonly cited but **forum-level, not solver-sourced**). **[DOWNGRADED — qualitative]**
- **A5s > A2s** as the preferred wheel blocker-bluff is **qualitative** (residual wheel/flush equity when called), not a solved frequency ranking. **[QUALITATIVE]**

## 5. Flop c-bet by texture

> [!note] In plain terms
> How the preflop raiser should continuation-bet the flop, by board type. The pattern is a "wetness parabola": bet small and often on dry boards you own, bigger and less often on wet boards, then small again on the wildest (monotone) boards where nobody has a range edge. These are real solver outputs but from single example spots, so treat them as illustrative, not universal laws.

- **Dry/high (e.g. A72r):** small (~⅓-pot), high frequency. **Wet/two-tone:** larger (75–125% pot), lower frequency. **Monotone straight-y (e.g. QJT-mono):** back to ~⅓-pot and near-check-heavy (one solve checks back ~98%). **[SOURCED — GTO Wizard solver spots, illustrative]**
- **Wetness-parabola** shape is consistent across GTO Wizard + Upswing. **[SOURCED]**
- **Turn/river:** no universal barrel %; only run-out-specific solver examples exist (one turn barrels ~40% with overbet sizing; rivers are the most polarized/largest street). **[SOURCED, illustrative only — do not hard-code a constant]**
- IP can c-bet more often than OOP; a frequently-cited OOP aggregate ~⅓ comes from an MTT-context source → **approximate for cash**. **[USE-WITH-CAVEAT]**

## 6. Rake (live $2/$3)

> [!note] In plain terms
> Rake is the house's cut, and it quietly makes marginal hands unprofitable — so correct ranges tighten, especially the small blind, marginal cold-calls, and multiway pots. The mechanism and the direction are well-sourced; the one number nobody publishes (how many big blinds per 100 hands rake costs at live $2/$3) we derive ourselves and label clearly as an assumption.

- **Structure:** live $2/$3 ≈ **5–10% of pot, capped ~$4–6** (+ occasional $1 promo drop). **[SOURCED, representative]** "No flop, no drop" is **common but NOT universal** — some rooms rake every hand / use a flat drop. **[SOURCED — CA cardroom filing]**
- **Effect (well-sourced):** marginal/speculative hands cut first; order of impact ≈ **SB limps > marginal cold-calls/multiway > BB defense > RFI** (RFI shifts toward blocker-heavy hands rather than merely shrinking). **[SOURCED — Upswing]**
- **BB-defense equity-needed shift:** ~**30% → ~35%** raw-equity-needed under a **$5 cap** at $1/2 (single-cap example; a conflicting secondary figure says 30%→50% — use order-of-magnitude only). Rake as pot-fraction: $5 = **29.4%** of a $17 pot vs **13.5%** of a $37 pot (smaller pots hurt more). **[SOURCED — Upswing, approximate]**
- **[DERIVED-ASSUMPTION] live $2/$3 bb/100 rake cost** (no source publishes this): bb/100 ≈ (raked_hands_per_100 × avg_rake_$) / bb_$. With ~30–40 raked hands/100 (loose live, many see flops), avg rake ~$3.5–4.5 (pots often hit the cap), bb = $3 → **≈ 35–60 bb/100**. **This is our derivation, not a cited figure** — low-stakes live rake is structurally heavy; treat as an order-of-magnitude planning number only.

## 7. Push/fold & shove-EV (short-stack — beyond the app's 100bb scope)

> [!note] In plain terms
> When stacks get short (roughly 15 big blinds or less), poker collapses into a simple "shove or fold" game with its own clean math. The app runs at 100bb so this is out of its current scope — included for completeness and clearly labeled. The shove-EV formula itself is solid; the exact short-stack hand charts are not (single secondary source), so don't hard-code them.

- **Shove-EV** = F·Pot + (1−F)·[E_called·FinalPot − (1−E_called)·Risk]; break-even fold F = Risk/(Pot+Risk). **[SOLVED]**
- Push/fold becomes the correct frame at **≤ ~15–20bb** (dominant ≤10bb). **[SOURCED — Upswing/HRC]** Ranges widen as stacks shorten; SB is the natural shover (~50% at 10bb, directional). **[DIRECTIONAL — exact combos not hard-codeable; single secondary source]**
- Cash short-stack is **cEV** (not ICM); ICM push/fold is tournament-only. **[SOURCED]** *(All of §7 is out of the 100bb-cash scope.)*

## 8. "Risk premium" — a correction, not a number

> [!note] In plain terms
> A term to *stop* using in a cash context. "Risk premium" means the extra equity you need to call an all-in in a **tournament**, because busting costs you more than doubling helps (survival pressure near pay jumps). In a cash game, chips are just dollars, so risk premium does not exist. The cash effect people sometimes mislabel "risk premium" — needing to continue tighter when out of position — is just **equity realization** (§2). Use that name.

- **Risk premium = ReqEquity(ICM) − ReqEquity(cEV); tournament/ICM ONLY.** **[SOURCED — GTO Wizard glossary, O'Kearney, PokerCoaching]**
- **Cash OOP/range-disadvantage pricing = pot odds tempered by equity realization (§2), with MDF as a secondary floor.** Do **not** call this "risk premium." **[SOURCED — GTO Wizard cash 3-bet-pot article]**
- **No general "defend X% tighter OOP" constant exists** — only spot-specific solver examples. Don't fabricate one. **[SOURCED as a non-claim]**

## 9. Multiway defense arithmetic

> [!note] In plain terms
> With several players still to act, the "defend enough" burden splits among them — no single player has to defend as much as heads-up. The math is exact (an n-th-root relationship), even though *how* real ranges implement it is a heuristic (that part lives in the modeling note, since multiway isn't truly solved).

- A bluff must get through **all** opponents, so against **n** opponents each may **fold** up to the **n-th root** of the heads-up fold ceiling (α): e.g. a bet needing **33% folds heads-up** needs **~58% folds from each** of two opponents (√0.33 ≈ 0.574). Equivalently, each opponent's **defense (continue) requirement drops** multiway (~**42%** each here, vs the tighter heads-up figure) — defense is *shared*, so no single player defends as much as heads-up. **[SOLVED — verified arithmetic; the root is taken of the HU fold/α, not of the defense]**
- The **implementation** (how much each real range actually tightens/bluffs) is heuristic and lives in the [[Poker Math — Persona & Multiway Modeling (Estimates)|modeling note]] — multiway has no unique equilibrium.

---

## Sources (curated from the vetted research)

- GTO Wizard glossary — Equity Realization (EQR): gtowizard.com/en/glossary/equity-realization-eqr/
- GTO Wizard — cash 3-bet-pot OOP article; flop c-bet heuristics; "Quirks of Nash in Multiway"; risk-premium glossary.
- Upswing Poker — rake effect on ranges; push/fold; AFq definition.
- SplitSuit — 3-bet value/bluff combinatorics; MDF.
- ThinkGTO — HU→3-way c-bet ~halving (attributing "GTO Ranges+" solver output; secondary aggregator).
- Brown & Sandholm, *Science* 2019 (Pluribus) — multiway self-play, no unique equilibrium.
- Full per-claim provenance + the DROP/DOWNGRADE rulings: `docs/research/_vetting-verdict.md` and the seven `docs/research/*.md` dumps.
