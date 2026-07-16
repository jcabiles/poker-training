# RES-C — Postflop Range Research (call/fold/raise ranges by street & spot)

> Research spike output — **decision doc + spec only, NO app code.** Seeds build slice
> **R5** (an openable postflop call/fold/raise chart for hero's current spot) and the
> re-pointing of the shipped S6/S7 postflop graders. Every frequency and EV below is
> **approximate** — heuristic + published-strategy grounded, never solver-exact.

## 0. Goal, scope, out-of-scope

**Goal.** Produce a single `spot → {call/fold/raise or category-frequency}` spec that R5
can point BOTH the openable postflop range chart AND the existing postflop graders at, so
the chart and the grader read the same source of truth (the R5 "Reconciliation rule").

**Scope (node families specced here).** The seven shipped postflop grader node families,
HU and multiway-aware: flop **c-bet** (`CBET`) · flop **vs-c-bet** (`VS_CBET`) · flop
**vs-check-raise** (`VS_CHECK_RAISE`) · turn **barrel** (`TURN_BARREL`) · **vs-turn-bet**
(`VS_TURN_BET`) · river **value/bluff barrel** (`RIVER_BARREL`) · **vs-river-bet**
(`VS_RIVER_BET`). All at live $2/$3, ≈100–200bb, HU single-raised pot as the base shape,
with a multiway (3+) variant per family.

**Out of scope (explicitly "no baseline yet" — see §12).** Donk/lead lines, delayed
c-bet, probe bets, turn/river check-raise-as-defender (only the *facing*-check-raise node
is shipped), 3-bet-pot postflop, limped-pot postflop, all-in/short-SPR jam trees, blocker-
level combo selection, and any spot the S10 `grade_map` cannot canonically build (it maps
only preflop families + HU flop c-bet today). This spike does not widen `grade_map`
coverage — that is R5's build decision; it only specifies what the covered spots should say.

---

## 1. Representation choice: **category weights**, not combo strings

**Decision: the spec is a `(node family, board-texture context, hand category) → action-
frequency` table — CATEGORY WEIGHTS.** Not literal combo strings (e.g. not "call: 88+,
AQs+, …").

**Why category weights (justification).**

1. **Postflop range is board-conditioned, so a static combo string is a lie.** A preflop
   chart can list "raise: 77+, ATs+" because the decision context is fixed. Postflop, the
   *same* holding (say A♠5♠) is a nut-flush draw on one board, third pair on another, and
   air on a third. A combo-string chart would need one string per (board × prior-action)
   node — millions of nodes — which is exactly the solver table the project's no-go bans.
2. **The graders already ARE a category model.** `backend/app/domain/postflop.py::
   _hand_category()` collapses hero's exact hole+board into **four buckets**: `strong` |
   `weak_made` | `draw` | `air`. Every shipped grader scores those four buckets through a
   merit function, normalizes merits to per-action frequencies (`_frequencies()`), and
   emits `EvaluationResult`. If the chart speaks the SAME four categories, R5 can literally
   point the chart renderer and the grader at one spec with zero translation layer — which
   is the Reconciliation rule's whole point.
3. **It stays honest about approximation.** Category weights read as "value/strong-made →
   raise ~X% / call ~Y%", which is self-evidently a heuristic prior. Combo strings imply a
   solver-exact frontier the project explicitly does not have (`postflop.py` header: merit
   scores have "zero equity/frequency backing"; equity-backed range advantage was tried and
   reverted, see §2 note in code lines 90–96).

**The taxonomy (frozen to match the code — name the categories the code uses).**

| Category (code string) | `_hand_category()` definition (verbatim from code) | Chart-facing label |
|---|---|---|
| `strong` | made straight, made flush, set, two pair, overpair | **Value / strong made** |
| `weak_made` | top pair (any kicker) or a weaker single pair | **Medium made** |
| `draw` | flush draw **or** OESD, not yet made | **Draw** |
| `air` | none of the above (no pair, no 8-out draw) | **Air** |

Frozen extras the spec MUST honor because the graders do:
- **River busted-draw demotion:** on the river a `draw` has zero outs → both river graders
  demote it to `air` for merits AND tags (`_river_cat_effective`). The chart's river view
  must show a busted draw under **Air**, never Draw.
- **`weak_made` = plain top pair, deliberately NOT strong** (code comment, Phase 2e-0 T2:
  `made == 2` top pair was demoted out of "strong" to stop a "never fold TPTK vs a big
  c-bet" bug). The chart must not promote top pair into the value bucket.
- **Category granularity is coarse by design.** Kicker strength, exact draw quality
  (nut vs low flush draw), and blockers are **unmodeled** (doc-07 blocker math is
  explicitly out of the grader's model). The chart must not imply finer resolution than the
  four buckets — that is a stated approximation, not a bug.

---

## 2. How the numbers map onto the grader's machinery (so R5 has one dial)

Every shipped grader follows the identical pipeline. The spec below is authored as the
**target output frequencies** of that pipeline, so R5 can either (a) tune the merit
constants to hit them, or (b) read the frequencies directly from content — either way one
source:

```
category (+ texture/turn-class/river-class/price/adv) → merit(check|bet_small|bet_big)   [aggressor]
                                                       → merit(fold|call|raise)           [facing]
   → _apply_multiway() if is_multiway(spot)   → _frequencies() (drop negatives, normalize) → freq per action
```

- **Actions per family.** Aggressor families (`cbet`, `turn_barrel`, `river_barrel`) emit
  **check / bet-small / bet-big**. Facing families (`vs_cbet`, `vs_check_raise`,
  `vs_turn_bet`, `vs_river_bet`) emit **fold / call / raise**. The chart's "call/fold/raise
  view" for an aggressor node reads as **check/bet-small/bet-big** — R5 must render the
  aggressor triple, not force a fold/call/raise frame onto a betting node.
- **Sizing buckets are fixed (RES-B territory, not re-derived here).** `grade_map` authors
  the flop c-bet as small = 33% pot, big = 75% pot (`grade_map.py` lines 292–293). Turn/
  river sizes come from `spot.legal_actions`. This spec gives frequencies **per existing
  size bucket**; it does not introduce new sizes.
- **`range_advantage` context.** The spec's HU-vs-multiway split and its texture leans are
  expressed through the SAME `range_advantage()` / `range_advantage_defender()` label
  (`hero`/`neutral`/`villain` resp. `defender`/`neutral`/`aggressor`) the graders already
  compute — so "who has the edge" never needs a second, contradicting definition.
- **EV labeling.** Merit scores ARE the proxy-EV the grader reports as `ev_bb`; the code and
  this doc both label them **approximate** (`postflop.py` docstring: "documented PROXY EV").
  The chart must carry the same "≈ approximate" caption the preflop chart uses.

**All frequency figures below are approximate live-$2/$3 priors** rounded to readable
buckets (e.g. "~70%"), not solver outputs. They encode *direction and magnitude of the
swing between textures/categories*, which is the most a heuristic can honestly claim
(doc-06 §1 methodology note).

---

## 3. Flop C-BET (`CBET` / leak 200) — hero = preflop aggressor, BB checked to hero, HU SRP

**Sources:** doc-06 §2 (GTOWizard c-bet-sizing + IP-c-betting articles, 888poker texture
explainer), doc-02 §3.1–3.3, and the existing `grade_cbet` / `_merits` texture dials.

**HU frequency spec (approximate), by hand category × board texture:**

| Category | Dry/paired high (e.g. K72r, QQ6) | Wet two-tone (KJ7ss) | Monotone (QJTmono) |
|---|---|---|---|
| `strong` | bet ~90% (small-lean) / check ~10% | bet ~80% (**big**-lean) / check ~20% | bet ~55% (small) / check ~45% |
| `weak_made` | bet ~60% (small) / check ~40% | check ~65% / bet ~35% small | check ~75% / bet ~25% small |
| `draw` | bet ~65% (small) / check ~35% | bet ~70% (**big**-lean, semibluff) / check ~30% | check ~60% / bet ~40% small |
| `air` | bet ~45% (small range-bet) / check ~55% | check ~75% / bet ~25% big-only-if-nut-draw | check ~85% / bet ~15% |

Anchors: dry/paired boards → **range-bet small** (~33% pot), high frequency (KK5r ≈ 96%
c-bet, QQ6 bets most of range at 33%; 888poker/GTOW via doc-06 §2). Wet two-tone → **bet
big / polarize** (KJ7 75–125% pot), fewer bluffs. Monotone → **check most, small when
betting** (A93mono ≈ 26.6% freq, QJTmono ≈ 50%; doc-06 §2, the one texture the code was
flagged as under-differentiating). **Ace-high discount:** ace-high boards c-bet a notch
less than K/Q/J-high (BB over-continues any ace) — already in `range_advantage()` as the
`high_card == "A"` +0.5 vs +1.0 split.

**Multiway variant (3+):** shift the whole table toward **check**, value-only when betting,
**bluffs largely cut**. Concretely: `air` and `draw` bet frequencies roughly **halve**
(backdoor/overcard equity required to bet at all); `strong` leans **more** toward betting
for value/protection; sizes come **down a tier** (33–50%). Solver corroboration: 3-way
c-bet frequency drops from ~70% HU to ~35% 3-way; bluff frequency "drops dramatically";
value threshold rises to ~TPTK+ (ThinkGTO / PokerNews GTOW-AI, doc-02 §9.1–9.4). This is
exactly what `_apply_multiway(facing_side=False)` does: dampen `air`/`draw` aggressive merit
by `_MW_BLUFF_DAMPEN` (0.6), lift `strong` by `_MW_VALUE_LEAN` (1.15). **Consistent — keep.**

---

## 4. Flop VS-C-BET (`VS_CBET` / leak 201) — hero = BB defender facing the c-bet, HU SRP

**Sources:** doc-06 §2 (defender fold/call/raise splits per board), doc-02 §4.1–4.4, MDF
table doc-06 §6 / doc-02 §8, existing `_merits_vs_cbet`.

**HU frequency spec (approximate), by category × price (faced bet / pot):**

| Category | Small c-bet faced (≤~40% pot, price low) | Big c-bet faced (≥~66% pot, price high) |
|---|---|---|
| `strong` | raise ~45% / call ~50% / fold ~5% | raise ~35% / call ~60% / fold ~5% |
| `draw` | call ~55% / raise ~30% (semibluff) / fold ~15% | call ~45% / raise ~25% / fold ~30% |
| `weak_made` | call ~70% / fold ~25% / raise ~5% | call ~45% / fold ~50% / raise ~5% |
| `air` | fold ~80% / call ~10% / raise ~10% (only low-connected-wet) | fold ~90% / call ~5% / raise ~5% |

Anchors: MDF is a *floor sanity-check, not a per-hand rule* — vs 33% pot MDF ≈ 75%, vs pot
≈ 50% (doc-06 §6). Live $2/$3 defenders may fold **slightly more than MDF** because the
field under-bluffs (doc-02 §4.1, §10). Semibluff-raise draws on **wet** boards (OESD+FD,
combo draws); raise for value/protection with strong; do NOT check-raise weak made or pure
air except on low-connected-wet boards (doc-02 §4.4). **Paired-board raise bump:** paired
boards get check-raised ~2.5–5× more (24% on QQ6 vs 5–9% elsewhere; GTOW "Defending vs BB
Check-Raise on Paired Flops", doc-06 §4) — already wired as the `texture.pairing ==
"paired" and adv == "defender"` +0.5 raise merit.

**Multiway variant (3+):** defense **tightens sharply**; fold more, raise-bluff almost
never, continue only with nut-potential draws and strong made hands (doc-02 §9.4 "calling
multiway"). `weak_made` and `air` fold frequencies rise; raise frequencies collapse.
Matches `_apply_multiway(facing_side=True)`: tighten `air`/`weak_made` by raising fold
merit ×`_MW_CATCH_TIGHTEN` (1.3) and damping call/raise ×0.6. **Consistent — keep.**

---

## 5. Flop VS-CHECK-RAISE (`VS_CHECK_RAISE` / leak 202) — hero = the c-bettor, facing a raise, HU SRP

**Sources:** doc-02 §4.4, §10.3 (live check-raises rarely bluffs), doc-06 §4, existing
`_merits_vs_check_raise` (deliberately fold-heavy live-exploit prior).

**HU frequency spec (approximate), by category:**

| Category | vs check-raise (any normal size) |
|---|---|
| `strong` | raise/4-bet ~40% (value) / call ~55% / fold ~5% |
| `draw` | call ~60% / fold ~25% / raise ~15% (only low-connected-wet semibluff) |
| `weak_made` | fold ~65% / call ~35% / raise ~0% |
| `air` | fold ~90% / call ~5% / raise ~5% (only low-connected-wet) |

Live-exploit anchor: at $2/$3 a check-raise is **fresh strength news, stronger than the
static board read** — default to folding anything short of a strong made hand or real draw
(doc-02 §4.4 "Do NOT check-raise", §10.3 "over-fold to check-raises"). Encoded as the
`fold = 1.6` baseline (vs 0.6 vs a plain c-bet) in `_merits_vs_check_raise`. Texture
modulates bluff plausibility (`bluffy` term: low/connected/wet → fold a bit less; dry
rainbow → never rescues an air fold). **This is a deliberate deviation BELOW solver-optimal
continuing frequency** (solver bettor folds ≈40% = MDF; we fold more) — justified by live
read, labeled approximate. `[$5/$10: loosen →]` per doc-06 §4.

**Multiway variant (3+):** even more fold-weighted; the extra live opponent makes a raise-
into-two even more polarized to value. `_apply_multiway(facing_side=True)` applies as in §4.
**Consistent — keep.** (Note: the `raise_` merit intentionally gets NO paired-board bump
here — no solver data for hero's post-check-raise 4-bet on paired boards; code comment
CW-2b. The spec inherits that "no baseline" for the raise leg specifically.)

---

## 6. Turn BARREL (`TURN_BARREL` / leak 203) — hero = flop c-bettor deciding the 2nd barrel, HU SRP

**Sources:** doc-02 §5.1–5.2 (fire-frequency table), doc-06 §3 (barrel size/frequency),
GTOW "The Worst Turn Card" / "Turn Barreling" (search-confirmed magnitudes), existing
`_merits_turn_barrel` + `_TURN_BARREL_SCARE`.

**Turn-card class drives the barrel** (from `turn_card_class`): `over` | `pairing` |
`straight` | `flush` | `blank`. **HU frequency spec (approximate), category × turn class:**

| Category | Scare turn (`over`, `pairing`) | Draw-completing (`flush`, `straight`) | Brick (`blank`) |
|---|---|---|---|
| `strong` | bet ~85% (big-lean) / check ~15% | bet ~70% / check ~30% | bet ~75% / check ~25% |
| `draw` | bet ~70% (big semibluff) / check ~30% | check ~55% / bet ~45% | check ~55% / bet ~45% small |
| `weak_made` | check ~65% / bet ~35% small | check ~75% / bet ~25% | check ~70% / bet ~30% (pot-control) |
| `air` | bet ~40% (best bluffs, big) / check ~60% | check ~80% / bet ~20% | check ~85% / bet ~15% (give-up) |

Anchors: fire scare cards that weaken the caller's flop-continue range (overcards, board-
pairing), give up bricks with air, check medium showdown value for pot control, give up
more OOP (doc-02 §5.1–5.2). Barrel ~⅔ pot on scare turns with value + best draws. Magnitude
notes from search: brick turns → barrel range is **~85% no-draw / merged made** (a give-up-
air spot), i.e. air barrels collapse; deeper stacks barrel *less* than shallow (geometric/
SPR effect) — a stated simplification the fixed-size model does not vary on depth
(**approximate**). Encoded in `_TURN_BARREL_SCARE` (over +0.6, pairing +0.4, straight −0.2,
flush −0.4, blank −0.5) + turn-aware `range_advantage` decay.

**Multiway variant (3+):** barrel far tighter, value-lean, bluffs cut; `air`/`draw` bet
frequencies roughly halve. `_apply_multiway(facing_side=False)`. **Consistent — keep.**

---

## 7. VS-TURN-BET (`VS_TURN_BET` / leak 204) — hero = flop caller facing the barrel, HU SRP

**Sources:** doc-02 §5.4 (equity realization + pot-odds discipline), §8 (pot odds), existing
`_merits_vs_turn_bet` (pot-odds-first, fold base 0.8).

**HU frequency spec (approximate), category × turn class:**

| Category | Brick turn (`blank`) | Scare turn (`over`/`flush`/`straight`) |
|---|---|---|
| `strong` | raise ~35% / call ~60% / fold ~5% | raise ~30% / call ~65% / fold ~5% |
| `draw` | call ~65% (priced-in) / fold ~30% / raise ~5% | call ~55% / fold ~40% / raise ~5% |
| `weak_made` | call ~55% / fold ~40% / raise ~5% | fold ~65% / call ~35% |
| `air` | fold ~90% / call ~10% | fold ~92% / call ~8% |

Anchors: a 2nd barrel is **stronger news than a lone c-bet, weaker than a check-raise**
(fold base 0.8, between vs_cbet 0.6 and vs_check_raise 1.6). Price first: cheap barrel →
continue wider, expensive → fold marginal pairs. On **brick** turns nothing changed → keep
disciplined bluff-catches (`weak_made` +0.4 on blank); on **scare** turns the story is
credible → fold marginal hands (`_TURN_SCARE_FOLD_BONUS` +0.3). Draws continue if priced-in
on one card to come. Encoded in `_merits_vs_turn_bet`. `[$5/$10: tighten →]` per doc-06 §3.

**Multiway variant (3+):** tighter continue; fold more marginal made, raise almost never.
`_apply_multiway(facing_side=True)`. **Consistent — keep.**

---

## 8. River BARREL (`RIVER_BARREL` / leak 205) — hero = flop+turn aggressor, value/bluff, HU SRP

**Sources:** doc-02 §6.1–6.3 (value betting, bluff selection, sizing), doc-06 §5 (value:bluff
ratio by size), existing `_merits_river_barrel` + busted-draw demotion.

**HU frequency spec (approximate), category × river class** (note: `draw` arrives already
**demoted to air**):

| Category | Scare river (`over`, `pairing`) | Draw-completing (`flush`, `straight`) | Brick (`blank`) |
|---|---|---|---|
| `strong` | bet ~85% (big/polar) / check ~15% | bet ~70% / check ~30% | bet ~80% (big) / check ~20% |
| `weak_made` | check ~80% / bet ~20% thin | check ~85% / bet ~15% | check ~75% / bet ~25% thin value |
| `air` (incl. busted draw) | bet ~30% (bluff, story-credible) / check ~70% | check ~85% / bet ~15% | check ~85% / bet ~15% (give up) |

Anchors: river is the last bet — **strong hands size up and polarize**, marginal made hands
**check for a free showdown** (a third bet folds out worse, gets called by better), busted
draws bluff only where a **scare river keeps the story credible** (doc-02 §6.1–6.2).
Value:bluff by size (doc-06 §5): 33% pot ≈ 4:1 (20% bluffs), pot ≈ 2:1 (33% bluffs) — the
chart can surface this as the polar-size guidance, but the grader models it via the polar
`big += 0.5 for strong / big −= 1.0 otherwise` split. **Live under-bluff reality:** at $2/$3
you can skip most river bluffs and still print (doc-02 §6.2) — the low `air` bet frequencies
above reflect that. Encoded in `_RIVER_BARREL_SCARE` + `_merits_river_barrel`.

**Multiway variant (3+):** value only; `air` bet frequency → near zero. `_apply_multiway
(facing_side=False)` with `cat_effective` (post-demotion). **Consistent — keep.**

---

## 9. VS-RIVER-BET (`VS_RIVER_BET` / leak 206) — hero = flop+turn caller facing a river bet, HU SRP

**Sources:** doc-02 §6.4 (bluff-catching), §10.3 (under-bluffing), doc-06 §5–§6, existing
`_merits_vs_river_bet` (fold base 1.0, busted draws demoted to air).

**HU frequency spec (approximate), category × river class:**

| Category | Brick river (`blank`) | Scare river (`over`/`flush`/`straight`) |
|---|---|---|
| `strong` | raise ~30% / call ~65% / fold ~5% | raise ~25% / call ~70% / fold ~5% |
| `weak_made` | call ~55% / fold ~45% | fold ~75% / call ~25% |
| `air` (incl. busted draw) | fold ~95% / call ~5% | fold ~97% / call ~3% |

Anchors: **pot odds set the bar**, not the feeling of being bluffed (doc-02 §6.4). On
**brick** rivers the draws all busted → disciplined bluff-catch with marginal pairs keeps
value; on **scare** rivers the story is credible → fold bluff-catchers at a bad price. A
busted draw of your own has **zero showdown value → never a call** (demoted to air, fold).
**Live under-bluff exploit:** the population under-bluffs the third barrel badly, especially
from tight seats — pot odds must be exceptional before a pure bluff-catcher continues
(doc-02 §10.3). Fold base 1.0 > turn's 0.8 (a third barrel is the strongest bet-signal short
of a check-raise). Encoded in `_merits_vs_river_bet`. `[$5/$10: loosen bluff-catch →]`.

**Multiway variant (3+):** call even less; the extra opponent makes any river bet more
value-weighted. `_apply_multiway(facing_side=True)`. **Consistent — keep.**

---

## 10. Consistency notes vs S8 multiway merit-scaling and the S6/S7 graders

The spec was authored **onto the existing grader machinery**, so re-pointing R5 introduces
no contradiction. Explicit reconciliation points R5 must preserve:

1. **S8 multiway is a binary bucket, applied last.** `is_multiway(spot)` = 3+ live players
   (`players_in_pot > 2`), and `_apply_multiway()` runs AFTER base merits, BEFORE
   `_frequencies()`, HU output byte-identical. Every §-multiway row above is the *direction*
   S8 already moves: `_MW_BLUFF_DAMPEN`=0.6 (aggressor `air`/`draw`; facing `call`/`raise`),
   `_MW_VALUE_LEAN`=1.15 (aggressor `strong`), `_MW_CATCH_TIGHTEN`=1.3 (facing `air`/
   `weak_made` fold). The chart's multiway view must show the **dampened/tightened** numbers,
   i.e. read the post-`_apply_multiway` frequencies, not the HU ones. **Do not add a second
   multiway model in content that fights S8** — the tuning knobs live in code; the spec only
   states the resulting frequency *direction*.
2. **Scaling only touches POSITIVE merits** (scaling a negative merit toward zero would
   perversely raise it) — so the spec never promises a multiway frequency *increase* for a
   category whose base merit is already negative (e.g. air raises stay ~0 both HU and MW).
3. **River busted-draw demotion happens upstream of everything** (`_river_cat_effective`
   feeds BOTH merits and `_apply_multiway`'s `cat_effective`). The chart must classify a
   river draw as air before looking up the spec row.
4. **`range_advantage` decays by street** (flop baseline 1.0 → turn 0.5 → river 0.0; wet/
   low boards tilt further to the caller each street; river-card class re-credits or buries
   the barreler). The spec's per-street tightening of the aggressor's value-bet threshold is
   this same decay — do not re-encode it as a separate content dial.
5. **Frequencies come from merits via `_frequencies()`** (drop negatives, normalize). If R5
   authors target frequencies in content instead of tuning merits, it MUST reproduce the
   same normalization so a spot graded and a spot charted agree to the rounding the code
   already uses (freq 3dp, ev 2dp). This is the single highest-risk reconciliation seam
   (§13).

---

## 11. Source citations / heuristic-reasoning per node family

| Node family | Primary grounding |
|---|---|
| Flop c-bet | doc-06 §2 (GTOW c-bet-sizing + IP-c-betting; 888poker texture freq) · doc-02 §3 · **heuristic** for the exact per-category %s |
| Vs-c-bet | doc-06 §2 defender splits (37/39/24, 62/32/5, 37/53/9) · doc-06 §4 paired check-raise bump · doc-02 §4, §8 MDF · **heuristic** for %s |
| Vs-check-raise | doc-02 §4.4, §10.3 (live check-raise = value) · doc-06 §4 (bettor folds ≈40% = MDF; our fold-heavy prior is a labeled deviation) · **heuristic + live-exploit reasoning** |
| Turn barrel | doc-02 §5.1–5.2 fire table · doc-06 §3 barrel size/freq · GTOW "The Worst Turn Card"/"Turn Barreling" (search-confirmed: brick barrel ≈85% no-draw, deep barrels less) · **heuristic** for %s |
| Vs-turn-bet | doc-02 §5.4, §8 pot odds · **heuristic + pot-odds reasoning** |
| River barrel | doc-02 §6.1–6.3 · doc-06 §5 value:bluff-by-size table · **heuristic** for %s |
| Vs-river-bet | doc-02 §6.4, §10.3 · doc-06 §5–§6 · **heuristic + under-bluff exploit reasoning** |

**Live-web sources consulted this pass (corroborate direction/magnitude, not new exact
numbers):**
- [The Mechanics of C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/) — GTOWizard
- [Flop Heuristics: IP C-Betting in Cash Games](https://blog.gtowizard.com/flop-heuristics-ip-c-betting-in-cash-games/) — GTOWizard
- [Defending vs BB Check-Raise on Paired Flops](https://blog.gtowizard.com/defending-vs-bb-check-raise-on-paired-flops/) — GTOWizard
- [The Worst Turn Card](https://blog.gtowizard.com/the-worst-turn-card/) — GTOWizard (brick-turn barrel ≈85% no-draw / merged made)
- [Principles of River Play](https://blog.gtowizard.com/principles-of-river-play/) — GTOWizard
- [MDF & Alpha](https://blog.gtowizard.com/mdf-alpha/) — GTOWizard
- [Multiway Pot Strategy: GTO Ranges for 3+ Players](https://thinkgto.com/blog/understanding-multiway-ranges-with-gto-ranges) — ThinkGTO (3-way c-bet ~35% vs ~70% HU; bluffs drop dramatically)
- [Struggling in Multiway Pots — GTO Wizard AI](https://www.pokernews.com/strategy/struggling-in-multiway-pots-gto-wizard-shows-the-answer-51069.htm) — PokerNews / GTOW AI (value threshold rises, size 33–50%)

Every numeric frequency in §3–§9 is **approximate** and labeled as a heuristic prior; the
web sources set direction/magnitude, not solver-exact combos.

---

## 12. Node families / spots left "no baseline yet" (honest coverage list)

Covered = a spot R5 can chart AND grade from this spec (all seven shipped grader families,
HU + multiway, category-weight resolution). **Left "no baseline yet" — R5 must mark these
NOT-charted AND ungraded on BOTH sides, never fabricated:**

1. **Donk/lead lines** (BB or caller leading into the aggressor) — doc-02 §4.5 says default
   is *don't donk*; no grader node, no content.
2. **Delayed c-bet, probe bet, overbet lines** (doc-07 §3) — advanced, no node.
3. **Hero-as-check-raiser** (defender initiating a check-raise) — only the *facing*-check-
   raise node exists; hero's own flop/turn check-raise decision has no grader.
4. **3-bet-pot and 4-bet-pot postflop** — ranges shift materially vs SRP; SRP is the only
   authored shape. `grade_map` also refuses non-SRP postflop.
5. **Limped-pot postflop**, and any **multiway line the S8 binary bucket can't resolve to a
   defensible category weight** (e.g. 4+-way specific seat dynamics) — binary HU-vs-3+ is
   the honest resolution; finer multiway counts stay "no baseline".
6. **Short-SPR / all-in / jam trees** — `grade_map` gates these out (too shallow for the
   small/big buckets); no baseline.
7. **Blocker-level and kicker-level resolution** — the four categories are the finest the
   spec claims; "which A5 to bluff" is doc-07 material, out of the model.
8. **Post-check-raise 4-bet on paired boards (the raise leg only)** — no solver data;
   the `_merits_vs_check_raise` raise merit deliberately gets no paired bump (code CW-2b).
9. **Turn/river spots generally in `grade_map`** — the S10 mapper only builds preflop +
   HU flop c-bet today; the turn/river GRADERS exist and this spec covers them, but until
   R5 (or a later slice) widens `grade_map`, a live turn/river decision may still be
   "unmappable" → "no baseline yet" at the mapping layer even though the grader logic exists.
   R5 must decide whether to widen the mapper; this spec is ready for it either way.

---

## 13. Hand-off to R5

**What the chart consumes.** For hero's CURRENT postflop spot the chart looks up
`(node_family, texture/turn-class/river-class context, price bucket)` and renders the
**category-weight table** for that context: four rows (`strong`/`weak_made`/`draw`/`air`,
with the friendly labels in §1) × the family's three actions (check/bet-small/bet-big for
aggressor nodes; fold/call/raise for facing nodes), each cell an **approximate frequency**.
Hero's own hand is highlighted in its category row (reuse the preflop chart's "your hand is
here" affordance). The panel carries the same **"≈ approximate, heuristic"** caption the
preflop chart uses. If `is_multiway(spot)`, the chart shows the **post-`_apply_multiway`**
frequencies (§10.1). An unsupported spot (any §12 item, or `grade_map` returns None) shows
**"no chart for this spot yet"** — never a fabricated table.

**How the grader re-points.** The graders already emit exactly this category × action
frequency structure (`per_action` in `EvaluationResult`). R5's Reconciliation rule makes
THIS spec the single source: where the shipped merit constants disagree with a spec number,
R5 re-points the grader by tuning the merit constant (or reading the target frequency from
content) so the graded frequency equals the charted frequency for the same spot. Because the
spec is authored *on* the grader's four-category / three-action / `_frequencies()` pipeline
(§2), re-pointing is a constant-tuning job, not a rewrite — and a spot the spec leaves "no
baseline yet" (§12) stays ungraded AND uncharted on both sides.

**Consistency test R5 must ship (per the roadmap pass/fail):** for every supported spot,
assert the chart's displayed best action / per-category stance == the grader's
`best_action` / `per_action` for the same `Spot` (same HU-vs-multiway branch). If they ever
diverge, the spot is a bug, not a "no baseline" — the two must read the identical numbers.

**Single biggest reconciliation risk (call-out for R5):** the chart and grader deriving
frequencies through **two different paths** — e.g. the chart reading authored target
percentages from content while the grader keeps computing them from merit constants +
`_frequencies()` normalization + `_apply_multiway` + busted-draw demotion + `range_advantage`
street-decay. Those pipelines will silently drift (rounding, negative-merit clipping, the
multiway/demotion order-of-operations) unless R5 makes ONE of them authoritative and derives
the other from it. Recommendation: keep the **merit pipeline authoritative** (it already
encodes texture/turn-class/price/multiway/demotion faithfully) and have the chart render the
grader's own `per_action` output for the current spot, rather than a parallel content table —
that makes chart==grader true by construction and reduces this spec to the *tuning target*
for the merit constants, which is the safest reading of the Reconciliation rule.
