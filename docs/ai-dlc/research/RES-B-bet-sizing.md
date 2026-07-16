# RES-B — Bet-Sizing Research: Realistic Fixed $2/$3 Sizes, Persona-Flavored

**Status:** research spike — decision doc + size table only, **NO app code**. Feeds build slice **R2** (realistic persona-flavored fixed sizes) and **R3** (hero two-option sizing).
**Stakes anchor:** live $2/$3 NLHE, 9-handed, ~100BB effective. (`$3` = 1 BB; a "3bb open" = $9.)
**Roadmap:** `docs/ai-dlc/roadmap/simulate-table.md` → Epic 2 → RES-B (~line 310), consumed by R2 (~line 375) / R3 (~line 386).

---

## 1. Goal, scope, out-of-scope

**Goal.** Give R2 a defensible **fixed** bet size for every *node × persona* cell so bots (and later hero) act at realistic live-$2/$3 prices, and flag every node where hero should be offered **two** size options (R3). Preflop sizes are expressed in **bb**; postflop sizes are expressed as **frequency-weighted pot-fraction bucket weights** (the existing persona lever shape) so the anti-sizing-tell no-go holds (§8).

**In scope.** Preflop open (RFI), 3-bet, 4-bet, 5-bet/jam; postflop c-bet (flop), turn barrel, river value/barrel, check-raise, and facing-a-bet raise. Six persona archetypes: `tag`, `nit`, `lag`, `maniac`, `calling_station`, `passive_fish`.

**Out of scope.** No app code (R2/R3 own the edits). No bet-size sliders. No rake/ante math. No per-hand randomization *beyond* the existing frequency-sampling of the postflop bucket map. No solver tables — all sizes are heuristic + live-$2/$3-research-grounded; every EV/price reasoning stays labeled **approximate**. Turn/river *engine* is deferred per Epic-2 header, so turn/river rows below are a **forward spec** for when those nodes exist (river value/barrel and turn barrel do not yet have a live sampling node — see §6 hand-off).

---

## 2. The "sizes differ by level?" question — resolved

**User intuition:** "sizes differ by level" (i.e. by *hand strength* or by *stakes level*). **Resolution (locked at the 2026-07-14 interview, grounded here): sizes are stakes-calibrated to $2/$3, persona-flavored, and FIXED.** Two distinct readings of "level," both resolved:

- **Reading A — "level" = stakes.** *Confirmed as the calibration target, refuted as a per-hand dial.* Live $2/$3 sizing conventions differ meaningfully from online/GTO baselines (2.25–2.5bb opens) — live opens run larger (3bb standard, up to 5x at looser tables) and 3-bets/4-bets skew value-heavy because the pool under-bluffs. `docs/research/02-postflop-strategy.md` §11 documents the $1/$2→$2/$3 pool differences; the app is calibrated to the **$2/$3** point on that curve and does **not** expose a live stakes slider. Source: GTO Wizard *Preflop Raise Sizing* ([blog.gtowizard.com](https://blog.gtowizard.com/preflop-raise-sizing-examining-2-key-factors/)); Upswing *straddle/3-blind* ([upswingpoker.com](https://upswingpoker.com/straddle-pot-strategy-three-blind-cash-game/)).
- **Reading B — "level" = hand strength → size.** *Refuted for bots (deliberately).* Letting a bot pick its size from its hand strength creates a **sizing tell** (the anti-sizing-tell no-go, roadmap ~line 289). Postflop bot sizes must stay a frequency-weighted *distribution* per persona×node, sampled independently of the made-hand bucket. See §8. (Hero is different — R3 *does* let hero choose, and grades the choice; that's a training feature, not a bot tell.)

**Net:** one fixed, $2/$3-calibrated size menu per persona per node. No sliders, no stakes dial, no strength→size leak for bots.

---

## 3. Persona sizing personalities (the skew axes)

Each archetype skews the *standard* size in a characteristic, sourced direction. These personalities drive every cell below.

| Persona | Preflop skew | Postflop skew | Source |
|---|---|---|---|
| **TAG** | Textbook: 3bb open, 3–3.5x 3-bet, ~2.4x 4-bet | Balanced, texture-matched (small dry / big wet); modest overbets only with nut advantage | pokerology "TAG" ([pokerology.com](https://www.pokerology.com/poker/strategy/playing-styles/)); doc-02 §7 |
| **Nit** | Same textbook sizes but **far fewer** raising hands; slightly smaller postflop | Small/standard, value-only, almost never bluff-sizes; polarized-but-tight | pokerology "nit"; doc-02 §10.1 |
| **LAG** | 3bb open, 3.5x 3-bet, applies pressure wider | **Polarized**: more big/overbet on wet boards + more small range-bets; widest sizing spread | pokerology "LAG"; coinpoker "LAG" ([coinpoker.com](https://coinpoker.com/strategy/playing-style/)) |
| **Maniac** | **Oversized**: ~4.5bb open, ~5.5x 3-bet; wild | **Overbets** frequently (0.75–1.5x pot), value and bluff alike, position-unaware | pokerology "maniac"; pokerstrategy "5 player types" ([pokerstrategy.com](https://www.pokerstrategy.com/strategy/bss/five-player-types/)) |
| **Calling Station** | Limps/min-raises; **rarely raises** (only monsters); slightly larger iso-raise when it does | Passive: **small** sizes, tiny raise frequency, no bluff-sizing; leans 0.33 pot | pokerology "calling station"; doc-02 §10.1–10.2 |
| **Passive Fish** | **Limps** a huge range; over-limps; slightly oversized opens with its few raising hands | Passive-but-loose: small sizes, **telegraphs** (big=strong, small=weak) — mitigated here by fixed buckets; leans 0.33 pot | pokerology "fish tell"; 888poker bet-sizing ([888poker.com](https://www.888poker.com/magazine/strategy/bet-sizing-poker-comprehensive-guide)) |

> **Note on the fish "sizing tell":** real fish leak strength through size. We deliberately do **not** reproduce that leak — it would teach the wrong lesson and violates the anti-sizing-tell no-go. The fish persona instead uses a *small-leaning fixed bucket distribution* (`0.33` weighted heavily) sampled independently of strength. This is a conscious simplification, documented here.

---

## 4. Preflop size table (in bb)

Sizes are **multipliers/absolute bb** matching the existing `sizing: {open_bb, threebet_mult, fourbet_mult}` lever shape. `threebet_mult` = multiple of the last raise (open). `fourbet_mult` = multiple of the 3-bet. 5-bet is always a **jam** (shove to effective stack) at these stakes — the sampler already overrides 5-bet size to the stack (`vs_4bet.json` note; `sizing_bb: 100.0`).

| Node | TAG | Nit | LAG | Maniac | Calling Station | Passive Fish | Standard / source |
|---|---|---|---|---|---|---|---|
| **Open (RFI)** `open_bb` | **3.0** | **3.0** | **3.0** | **4.5** | **3.5** | **4.0** | Live $2/$3 standard = 3bb ($9); recs open larger (4–5x). GTO Wizard preflop-sizing ([blog.gtowizard.com](https://blog.gtowizard.com/preflop-raise-sizing-examining-2-key-factors/)); 888poker ([888poker.com](https://www.888poker.com/magazine/strategy/bet-sizing-poker-comprehensive-guide)). SB opens +0.5bb larger across the board (see §4.1). |
| **3-bet** `threebet_mult` | **3.5** | **3.5** | **3.5** | **5.5** | **3.0** | **3.0** | IP 3x / OOP ~3.5–4x the open; live default ~3.5x. Upswing 4-bet guide ([upswingpoker.com](https://upswingpoker.com/4-bet-size-strategy/)); GGPoker 3/4-bet ([ggpoker.com](https://ggpoker.com/blog/3-betting-and-4-betting/)). Maniac oversizes; station/fish 3-bet tiny + rarely (heuristic — passive types compress the raise). |
| **4-bet** `fourbet_mult` | **2.4** | **2.3** | **2.4** | **3.0** | **2.2** | **2.2** | IP ~2.2–2.4x / OOP ~2.6x the 3-bet. Upswing "2.2x" ([upswingpoker.com](https://upswingpoker.com/4-bet-size-strategy/)); BlackRain79 4-bet ([blackrain79.com](https://www.blackrain79.com/2020/06/4bet-sizing.html)). Maniac oversizes; passive types near the 2.2x floor. |
| **5-bet / jam** | shove | shove | shove | shove | shove | shove | Jam to effective stack — already handled: `vs_4bet` `sizing_bb: 100.0` is overridden to the stack by the sampler. Heuristic: at 100BB a 5-bet is always all-in at these stakes. |

**These are exactly the values already in `content/personas/*.json`** — RES-B **confirms** the current preflop `sizing` blocks as correct and defensible for $2/$3. R2 needs **no preflop lever change** except the SB open bump (§4.1), which is optional. This is the key preflop finding: the preflop levers are already right; the unrealism the user reported is **postflop** (§5) plus the missing turn/river sampling nodes (§6).

### 4.1 Position nuance (optional, heuristic)

Existing `content/preflop/rfi.json` already varies open size by seat (UTG/LJ/SB = 3.0bb; HJ/CO/BTN = 2.5bb) — that's the *baseline* content path used for grading hero and is independently sourced (doc-01). The **persona** `open_bb` is a single per-persona number applied across seats (the persona engine has no per-seat open size). Recommendation: **leave the persona `open_bb` as a single value** (simplest; matches lever shape). If R2 wants seat realism for bots, that's a *new lever* (`open_bb_by_position`) and should be called out as schema work — **not recommended for R2's appetite.** SB is the one seat where a +0.5bb bump is textbook-justified (deny BB a cheap flop, doc-01 rfi rationale); treat as optional polish, not required.

---

## 5. Postflop size table (frequency-weighted pot-fraction buckets)

Format matches the existing `postflop.sizing: {"0.33":w, "0.5":w, "0.75":w, "1.0":w}` lever: **each cell is a weight distribution over pot-fractions, sampled independently of hand strength** (§8). Weights per persona are a **single distribution applied across nodes today** — the current pack has *one* `postflop.sizing` block, not a per-node one. Below I give (a) the **standard per-node** distribution (what a solver-simplified $2/$3 player uses), then (b) each persona's fixed distribution, and (c) a **hand-off recommendation** on whether R2 needs a per-node override lever.

### 5.1 Standard (node baseline) — what the *node* wants, texture-blended

Anchored to `docs/research/06-postflop-reference-tables.md` (GTO Wizard aggregate figures) and doc-02 §3/§7. These are the **node baselines** hero's size choice is graded against (R3), not a persona.

| Node | Standard size (pot-fraction) | Source |
|---|---|---|
| **Flop c-bet — dry/paired board** | 0.33 (range-bet small) | doc-06 §2 (KK5 ~96% freq small; QQ6 33%); doc-02 §3.2 |
| **Flop c-bet — wet two-tone** | 0.75 (polarized, overbet possible) | doc-06 §2 (KJ7 75–125% pot); doc-02 §3.2 |
| **Flop c-bet — monotone** | 0.33 when betting (mostly check) | doc-06 §2 (QJT mono ~50% freq, small); doc-02 §2 |
| **Turn barrel** | 0.67 (scare-card value + best draws) | doc-06 §3 (≈67% optimal on blank/scare turns); doc-02 §5.1 |
| **River value / barrel — polar** | 0.75–1.0 (polarized) | doc-06 §5 (pot-size = 2:1 value:bluff); doc-02 §6.1/§6.3 |
| **River thin value / induce** | 0.33–0.5 | doc-02 §6.3 (small = thin value / induce) |
| **Check-raise (flop)** | raise-to ≈ 2.5–3x the c-bet ⇒ pot-fraction **~1.0** of the *new* pot | doc-02 §4.4 (2.5–3x c-bet); the sampler's RAISE formula makes a 1.0 bucket ≈ 3x a half-pot c-bet |
| **Facing-a-bet raise (non-check-raise)** | ~2.5–3x the bet ⇒ **0.75–1.0** bucket | 888poker/BlackRain79 "raise to 2.5–3x a bet" ([888poker.com](https://www.888poker.com/magazine/strategy/bet-sizing-poker-comprehensive-guide)) |

> The engine samples one pot-fraction `f` from `postflop.sizing` and applies it uniformly to *both* bets and raises (`personas_postflop.py` sizing draw). So a persona's single `sizing` distribution has to serve c-bet, barrel, and raise sizing at once. That's why the standard *per-node* baselines above differ but the *persona* distributions below are node-agnostic — see §5.3 for whether that's good enough.

### 5.2 Persona postflop `sizing` distributions (fixed, node-agnostic — as shipped, confirmed/adjusted)

| Persona | 0.33 | 0.5 | 0.75 | 1.0 | 1.5 | Center of mass | Verdict vs. personality (§3) |
|---|---|---|---|---|---|---|---|
| **TAG** | 0.25 | 0.35 | 0.30 | 0.10 | — | ~0.55 pot | ✅ **Keep.** Balanced, texture-spanning; matches "textbook, size to texture." Sourced: doc-02 §7 3-tier model. |
| **Nit** | — | 0.40 | 0.45 | 0.15 | — | ~0.63 pot | ✅ **Keep.** Slightly bigger/polar but value-only (low bluff_freq does the tightening). doc-02 §10.1. |
| **LAG** | 0.15 | 0.30 | 0.35 | 0.20 | — | ~0.66 pot | ✅ **Keep.** Widest spread incl. more 1.0 — matches "polarizes." coinpoker LAG. |
| **Maniac** | — | — | 0.40 | 0.35 | 0.25 | ~1.0 pot | ✅ **Keep.** Overbet-heavy (adds a **1.5 bucket** — a *new pot-fraction key* already present in the pack; §6 flags it for R2/schema). pokerstrategy maniac. |
| **Calling Station** | 0.60 | 0.30 | 0.10 | — | — | ~0.42 pot | ✅ **Keep.** Small-leaning, passive. doc-02 §10.1. (Its low aggression lever means it rarely bets/raises at all, so size matters little.) |
| **Passive Fish** | 0.60 | 0.30 | 0.10 | — | — | ~0.42 pot | ✅ **Keep.** Small-leaning; the real "sizing tell" is deliberately *not* reproduced (§3 note). |

**Postflop finding:** the persona `sizing` distributions **as shipped are already defensible** and match each personality. The user-reported "unrealistic sizes" is therefore **not** primarily a wrong-bucket-weights problem — it is (1) the **node-agnostic** limitation below (§5.3), and (2) **missing turn/river sampling nodes** (§6). R2 should treat the existing distributions as the confirmed baseline and focus effort on §5.3/§6.

### 5.3 The node-agnostic limitation — R2 decision point

The single `postflop.sizing` block cannot express "small on dry flops, big on wet turns" — it blends them. Two options for R2 (this is a **decision for R2's brief**, flagged, not decided here):

- **Option A (no schema change, recommended for R2 appetite):** keep one `sizing` block per persona. Accept that texture/street nuance is averaged. The distributions above already span 0.33–1.0 so *some* small and *some* big sizes appear; the frequency-sampling means no single hand's size is a tell. **Cheapest; ships R2 with zero schema change.**
- **Option B (new lever — `sizing_by_node`):** add an optional per-node override map, e.g. `postflop.sizing_by_node: {"cbet_dry": {...}, "cbet_wet": {...}, "turn_barrel": {...}, "river_value": {...}}`, falling back to the flat `sizing` when a node key is absent. Richer realism (small dry c-bets, big wet turns) at the cost of a schema addition + engine plumbing to pass a node key into `sample_postflop_decision`. **More faithful; larger R2.**

**Recommendation:** ship R2 with **Option A** (confirmed flat distributions), and log Option B as a follow-up if playtesting still reads as unrealistic. The flat distributions are individually defensible; the marginal realism of per-node sizing is real but not worth expanding R2's appetite blindly.

---

## 6. Hand-off to R2 / R3

### 6.1 R2 — exact lever values (what changes, to what)

**Preflop (`sizing` block):** **no change required** — the six packs already carry the confirmed values in §4:

| Persona | open_bb | threebet_mult | fourbet_mult | Status |
|---|---|---|---|---|
| tag | 3.0 | 3.5 | 2.4 | confirmed ✅ |
| nit | 3.0 | 3.5 | 2.3 | confirmed ✅ |
| lag | 3.0 | 3.5 | 2.4 | confirmed ✅ |
| maniac | 4.5 | 5.5 | 3.0 | confirmed ✅ |
| calling_station | 3.5 | 3.0 | 2.2 | confirmed ✅ |
| passive_fish | 4.0 | 3.0 | 2.2 | confirmed ✅ |

**Postflop (`postflop.sizing` block):** **no change required** — §5.2 confirms all six distributions. (If R2 wants the wider maniac tail, note the maniac pack **already** includes a `1.5` bucket, so the pot-fraction key set is `{0.33, 0.5, 0.75, 1.0, 1.5}` — the content model must permit `1.5` as a valid key. Verify `PersonaPack.postflop.sizing` accepts arbitrary float-string keys ≥1.0; if it validates against a fixed enum of `{0.33,0.5,0.75,1.0}`, that's a **required schema loosening** for the maniac's overbet bucket.)

**So R2's real work is not new numbers — it is:**
1. **Wire the confirmed levers through** to bot *and* hero predetermined sizing (the roadmap says today's sizes are "predetermined"; R2 makes them read the pack). Preflop already flows through `personas.py`; the `LegalAction`/`Decision` predetermined path for hero + any hard-coded bot sizes are what change.
2. **Confirm the `1.5` overbet key is schema-legal** (maniac).
3. **Decide §5.3 Option A vs B** (recommend A — no schema change).

### 6.2 Missing sampling nodes (turn barrel, river value/barrel) — R2/engine note

Per doc-06 §3/§5 and the Epic-2 "turn/river engine deferred" note, there is **no live turn-barrel or river-value sampling node** in `personas_postflop.py` today — the flat `sizing` block *is* already applied whenever a BET/RAISE is sampled on any street, so turn/river bets DO get a size, but there is no *node-specific* size (they inherit the flat distribution). **This is acceptable under Option A.** When the turn/river engine lands (deferred), revisit Option B. No R2 action required beyond awareness.

### 6.3 R3 — nodes that surface TWO hero size options

R3 offers hero exactly **two** context-specific sizes per supported node, graded against the §5.1 node baseline (approx EV). Every flagged node below names the two sizes + reasoning. **These are the R3 deliverable.**

| Node | Option 1 (default/small) | Option 2 (large/polar) | Why two — reasoning |
|---|---|---|---|
| **Flop c-bet** | **0.33 pot** (range-bet) | **0.75 pot** (polar) | The single most important sizing fork: small on dry range-advantage boards, big/polar on wet boards. doc-06 §2; doc-02 §3.2/§3.3. |
| **Turn barrel** | **0.5 pot** | **0.75 pot** | Scare-card barrels run ~⅔ pot; the fork is "keep SPR manageable (0.5)" vs "charge draws / set up river jam (0.75)". doc-06 §3. |
| **River value/barrel** | **0.5 pot** (thin value/induce) | **1.0 pot** (polar / overbet-lite) | Thin value vs polar value: small gets called by more worse hands / induces; pot maximizes vs a station's inelastic range. doc-02 §6.1/§6.3; doc-06 §5. |
| **Facing a 3-bet** | **Standard 4-bet (2.4x)** | **Shove (5-bet jam)** | The interview's canonical example. Re-raise-and-fold-able 4-bet vs commit-now jam. Upswing 4-bet ([upswingpoker.com](https://upswingpoker.com/4-bet-size-strategy/)). |
| **Facing a 4-bet** | **Call** *(non-size, but the fork exists)* | **Shove (5-bet jam)** | At 100BB the only two live "sizes" are flat vs jam; jam is the aggressive line. `vs_4bet.json`. *(If R3 wants strictly two* size *options, this node is jam-or-fold; may be excluded from the size-choice UI.)* |
| **Check-raise (flop)** | **2.5x the c-bet** (~0.75 new-pot) | **3.5x the c-bet** (~1.0+ new-pot) | Smaller on dry, larger on wet to deny equity. doc-02 §4.4 ("2.5–3x, 3–3.5x on wet"). |
| **Facing-a-bet raise (non-c-bet)** | **2.5x the bet** (0.75) | **3x the bet** (1.0) | Standard raise fork: pot-controlled value-raise vs commit/deny-equity raise. 888poker/BlackRain79 raise sizing. |
| **Preflop open** | *(no fork)* | — | Single size per seat/persona (§4). Opens are not a hero size-choice node — one $2/$3-standard open. Excluded from R3. |

**R3 two-option nodes (count = 7 with a fork; open excluded, vs-4bet is jam-or-fold):** c-bet, turn barrel, river value, vs-3bet (4-bet/shove), check-raise, facing-bet raise — plus vs-4bet as a call/jam fork. The **flagship pairs** the interview named — **vs-3bet: 4-bet OR shove** and **c-bet: 1/3 OR 2/3** — are both present and headlined.

---

## 7. Full node × persona coverage confirmation

Cells filled = **preflop 4 nodes × 6 personas = 24** (open, 3-bet, 4-bet, 5-bet/jam) + **postflop 6 nodes × 6 personas = 36** (c-bet, turn barrel, river value, river thin, check-raise, facing-bet raise — all served by each persona's flat `sizing` distribution) = **60 node×persona cells**, every one either sourced or explicitly heuristic-with-reasoning (§4, §5). Preflop cells: sourced (GTO Wizard / Upswing / GGPoker / 888poker / BlackRain79) with the passive-type compression labeled heuristic. Postflop cells: sourced (doc-06 GTO Wizard aggregates / doc-02) with the fish-tell suppression and station low-aggression labeled heuristic.

---

## 8. Anti-sizing-tell constraint — respected

Confirmed the deliverable does **not** introduce a strength→size leak for bots:

- **Postflop sizes are frequency-weighted bucket distributions** (§5.2), and `personas_postflop.py` samples the pot-fraction `f` **independently of the made-hand bucket** ("Sizing draw — independent of bucket (rule 3)", line ~328). A monster and a bluff on the same node draw from the *same* distribution — no size tell.
- **Preflop sizes are fixed per persona per node** (§4) — likewise no strength leak (a maniac opens 4.5bb with AA and 72s alike).
- The fish "sizing tell" (real fish leak strength via size) is **deliberately not reproduced** (§3 note) — reproducing it would both teach the wrong lesson and violate the no-go.
- R3's hero choice is a *graded training decision*, not a bot tell — out of scope for this constraint.

No per-hand randomization is introduced beyond the existing frequency-sampling of the bucket map. ✅

---

## 9. Sources

- GTO Wizard — [Preflop Raise Sizing: 2 Key Factors](https://blog.gtowizard.com/preflop-raise-sizing-examining-2-key-factors/)
- GTO Wizard (via doc-06) — [The Mechanics of C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/), [Turn Check-Raise Heuristics](https://blog.gtowizard.com/turn-check-raise-heuristics/), [Principles of River Play](https://blog.gtowizard.com/principles-of-river-play/), [MDF & Alpha](https://blog.gtowizard.com/mdf-alpha/)
- Upswing Poker — [What Top Pros Know About 4-Betting (2.2x)](https://upswingpoker.com/4-bet-size-strategy/), [Straddle / 3-Blind Pots](https://upswingpoker.com/straddle-pot-strategy-three-blind-cash-game/)
- GGPoker — [3-Bet and 4-Bet Secrets](https://ggpoker.com/blog/3-betting-and-4-betting/)
- BlackRain79 — [4bet Sizing](https://www.blackrain79.com/2020/06/4bet-sizing.html), [Optimal Bet Sizing](https://www.blackrain79.com/2017/11/bet-sizing.html)
- 888poker — [Bet Sizing: Rules, GTO Logic, Leaks](https://www.888poker.com/magazine/strategy/bet-sizing-poker-comprehensive-guide)
- pokerology — [Types of Poker Players: TAG, LAG, NIT, Calling Station](https://www.pokerology.com/poker/strategy/playing-styles/)
- pokerstrategy — [The Five Player Types](https://www.pokerstrategy.com/strategy/bss/five-player-types/)
- coinpoker — [Playing Styles](https://coinpoker.com/strategy/playing-style/)
- Internal — `docs/research/02-postflop-strategy.md` (§3, §5, §6, §7, §10, §11); `docs/research/06-postflop-reference-tables.md` (§2, §3, §5); `content/preflop/rfi.json`, `vs_3bet.json`, `vs_4bet.json`; `content/personas/*.json`; `backend/app/domain/personas_postflop.py` (sizing draw, rule 3).
