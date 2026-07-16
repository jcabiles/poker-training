# 11 — Postflop Ranges by Node (Category-Weight Frequencies)

**Purpose:** A single `spot → category-frequency` spec covering the seven shipped postflop grader node families (HU + multiway), so an openable postflop call/fold/raise chart and the existing postflop graders can read the **same source of truth**. The spec is expressed as **category weights** (`strong` / `weak_made` / `draw` / `air` → action frequency), not combo strings, because postflop range is board-conditioned. Scope: live $2/$3, ≈100–200bb, HU single-raised pot as the base shape with a multiway (3+) variant per family. **Every frequency and EV below is approximate — heuristic + published-strategy grounded, never solver-exact.**

**Source / full decision doc:** `docs/ai-dlc/research/RES-C-postflop-ranges.md` (RES-C). This entry captures the per-node frequency tables and the taxonomy; the full spike also carries the representation-choice justification, the grader-machinery mapping, the S8-multiway reconciliation notes, and the R5 hand-off. **Consumed by build slice R5** (points the openable postflop chart AND re-points the shipped S6/S7 graders at this spec, per the "Reconciliation rule"). No app code was edited by the research.

---

## 1. Representation: category weights, not combo strings

The spec is a `(node family, board-texture context, hand category) → action-frequency` table. **Why category weights, not combo strings:**
1. **Postflop range is board-conditioned.** The same holding (A♠5♠) is a nut-flush draw on one board, third pair on another, air on a third. A combo-string chart would need one string per board × prior-action node — the solver table the project's no-go bans.
2. **The graders already ARE a category model.** `backend/app/domain/postflop.py::_hand_category()` collapses hero's hole+board into four buckets, scores them through a merit function, and normalizes to per-action frequencies. If the chart speaks the same four categories, the chart renderer and grader read one spec with zero translation layer.
3. **It stays honest about approximation** — category weights read as heuristic priors; combo strings imply a solver-exact frontier the project does not have.

**The taxonomy (frozen to match the code):**

| Category (code) | `_hand_category()` definition | Chart label |
|---|---|---|
| `strong` | made straight, made flush, set, two pair, overpair | **Value / strong made** |
| `weak_made` | top pair (any kicker) or a weaker single pair | **Medium made** |
| `draw` | flush draw **or** OESD, not yet made | **Draw** |
| `air` | none of the above | **Air** |

Frozen rules the spec must honor because the graders do:
- **River busted-draw demotion:** on the river a `draw` has zero outs → both river graders demote it to `air`. The river view must show a busted draw under **Air**, never Draw.
- **`weak_made` = plain top pair, deliberately NOT strong** (a "never fold TPTK vs a big c-bet" bug fix). The chart must not promote top pair into the value bucket.
- **Category granularity is coarse by design** — kicker strength, draw quality, and blockers are unmodeled. A stated approximation, not a bug.

**Action shapes.** Aggressor families (`cbet`, `turn_barrel`, `river_barrel`) emit **check / bet-small / bet-big**. Facing families (`vs_cbet`, `vs_check_raise`, `vs_turn_bet`, `vs_river_bet`) emit **fold / call / raise**. All figures below are approximate live-$2/$3 priors rounded to readable buckets (e.g. "~70%") — they encode direction and magnitude of the swing between textures/categories, the most a heuristic can honestly claim.

---

## 2. Flop C-BET — hero = aggressor, checked to, HU SRP

| Category | Dry/paired high (K72r, QQ6) | Wet two-tone (KJ7ss) | Monotone (QJTmono) |
|---|---|---|---|
| `strong` | bet ~90% (small-lean) / check ~10% | bet ~80% (**big**-lean) / check ~20% | bet ~55% (small) / check ~45% |
| `weak_made` | bet ~60% (small) / check ~40% | check ~65% / bet ~35% small | check ~75% / bet ~25% small |
| `draw` | bet ~65% (small) / check ~35% | bet ~70% (**big** semibluff) / check ~30% | check ~60% / bet ~40% small |
| `air` | bet ~45% (small range-bet) / check ~55% | check ~75% / bet ~25% big-only-if-nut-draw | check ~85% / bet ~15% |

Anchors: dry/paired → range-bet small (~33% pot), high frequency (KK5r ≈96% c-bet). Wet two-tone → bet big / polarize (KJ7 75–125% pot), fewer bluffs. Monotone → check most, small when betting (QJTmono ≈50%). **Ace-high discount:** ace-high boards c-bet a notch less (BB over-continues any ace) — already in `range_advantage()`.

**Multiway (3+):** shift toward **check**, value-only, bluffs largely cut — `air`/`draw` bet frequencies roughly **halve**, `strong` leans more toward betting, sizes come down a tier. Solver corroboration: 3-way c-bet ~35% vs ~70% HU. Matches `_apply_multiway(facing_side=False)` (dampen air/draw ×0.6, lift strong ×1.15).

---

## 3. Flop VS-C-BET — hero = defender facing the c-bet, HU SRP

| Category | Small c-bet (≤~40% pot) | Big c-bet (≥~66% pot) |
|---|---|---|
| `strong` | raise ~45% / call ~50% / fold ~5% | raise ~35% / call ~60% / fold ~5% |
| `draw` | call ~55% / raise ~30% (semibluff) / fold ~15% | call ~45% / raise ~25% / fold ~30% |
| `weak_made` | call ~70% / fold ~25% / raise ~5% | call ~45% / fold ~50% / raise ~5% |
| `air` | fold ~80% / call ~10% / raise ~10% (low-connected-wet only) | fold ~90% / call ~5% / raise ~5% |

Anchors: MDF is a floor sanity-check (vs 33% pot ≈75%, vs pot ≈50%), not a per-hand rule; live $2/$3 defenders fold slightly more than MDF (field under-bluffs). Semibluff-raise draws on wet boards; do NOT check-raise weak made or pure air except low-connected-wet. **Paired-board raise bump:** paired boards check-raised ~2.5–5× more (24% on QQ6 vs 5–9% elsewhere) — already wired.

**Multiway (3+):** defense **tightens sharply** — fold more, raise-bluff almost never, continue only with nut-potential draws + strong made. Matches `_apply_multiway(facing_side=True)`.

---

## 4. Flop VS-CHECK-RAISE — hero = the c-bettor facing a raise, HU SRP

| Category | vs check-raise (any normal size) |
|---|---|
| `strong` | raise/4-bet ~40% (value) / call ~55% / fold ~5% |
| `draw` | call ~60% / fold ~25% / raise ~15% (low-connected-wet semibluff only) |
| `weak_made` | fold ~65% / call ~35% / raise ~0% |
| `air` | fold ~90% / call ~5% / raise ~5% (low-connected-wet only) |

Live-exploit anchor: at $2/$3 a check-raise is **fresh strength news** — default to folding anything short of a strong made hand or real draw. Encoded as `fold = 1.6` baseline (vs 0.6 facing a plain c-bet). **This is a deliberate deviation BELOW solver-optimal continuing frequency** (solver bettor folds ≈40% = MDF; we fold more) — justified by live read, labeled approximate. The raise leg intentionally gets **no paired-board bump** (no solver data — a "no baseline" inheritance).

**Multiway (3+):** even more fold-weighted; a raise into two is more polarized to value.

---

## 5. Turn BARREL — hero = flop c-bettor deciding the 2nd barrel, HU SRP

Turn-card class drives the barrel (`over` | `pairing` | `straight` | `flush` | `blank`):

| Category | Scare turn (`over`, `pairing`) | Draw-completing (`flush`, `straight`) | Brick (`blank`) |
|---|---|---|---|
| `strong` | bet ~85% (big-lean) / check ~15% | bet ~70% / check ~30% | bet ~75% / check ~25% |
| `draw` | bet ~70% (big semibluff) / check ~30% | check ~55% / bet ~45% | check ~55% / bet ~45% small |
| `weak_made` | check ~65% / bet ~35% small | check ~75% / bet ~25% | check ~70% / bet ~30% (pot-control) |
| `air` | bet ~40% (best bluffs, big) / check ~60% | check ~80% / bet ~20% | check ~85% / bet ~15% (give-up) |

Anchors: fire scare cards that weaken the caller's continue range, give up bricks with air, check medium showdown value for pot control, give up more OOP. Barrel ~⅔ pot on scare turns with value + best draws. Magnitude notes: brick turns → barrel range ≈85% no-draw / merged made (air barrels collapse); deeper stacks barrel *less* (an SPR effect the fixed-size model does not vary on depth — **approximate**).

**Multiway (3+):** barrel far tighter, value-lean, bluffs cut; air/draw bet frequencies roughly halve.

---

## 6. VS-TURN-BET — hero = flop caller facing the barrel, HU SRP

| Category | Brick turn (`blank`) | Scare turn (`over`/`flush`/`straight`) |
|---|---|---|
| `strong` | raise ~35% / call ~60% / fold ~5% | raise ~30% / call ~65% / fold ~5% |
| `draw` | call ~65% (priced-in) / fold ~30% / raise ~5% | call ~55% / fold ~40% / raise ~5% |
| `weak_made` | call ~55% / fold ~40% / raise ~5% | fold ~65% / call ~35% |
| `air` | fold ~90% / call ~10% | fold ~92% / call ~8% |

Anchors: a 2nd barrel is **stronger news than a lone c-bet, weaker than a check-raise** (fold base 0.8, between vs_cbet's 0.6 and vs_check_raise's 1.6). Price first: cheap barrel → continue wider. On **brick** turns nothing changed → keep disciplined bluff-catches; on **scare** turns the story is credible → fold marginal hands. Draws continue if priced-in on one card to come.

**Multiway (3+):** tighter continue; fold more marginal made, raise almost never.

---

## 7. River BARREL — hero = flop+turn aggressor, value/bluff, HU SRP

Note: `draw` arrives already **demoted to air**.

| Category | Scare river (`over`, `pairing`) | Draw-completing (`flush`, `straight`) | Brick (`blank`) |
|---|---|---|---|
| `strong` | bet ~85% (big/polar) / check ~15% | bet ~70% / check ~30% | bet ~80% (big) / check ~20% |
| `weak_made` | check ~80% / bet ~20% thin | check ~85% / bet ~15% | check ~75% / bet ~25% thin value |
| `air` (incl. busted draw) | bet ~30% (bluff, story-credible) / check ~70% | check ~85% / bet ~15% | check ~85% / bet ~15% (give up) |

Anchors: river is the last bet — strong hands size up and polarize, marginal made hands **check for a free showdown** (a third bet folds out worse, gets called by better), busted draws bluff only where a scare river keeps the story credible. Value:bluff by size (33% pot ≈ 4:1 / pot ≈ 2:1). **Live under-bluff reality:** at $2/$3 you can skip most river bluffs and still print — hence the low `air` bet frequencies.

**Multiway (3+):** value only; `air` bet frequency → near zero.

---

## 8. VS-RIVER-BET — hero = flop+turn caller facing a river bet, HU SRP

Note: busted draws demoted to air.

| Category | Brick river (`blank`) | Scare river (`over`/`flush`/`straight`) |
|---|---|---|
| `strong` | raise ~30% / call ~65% / fold ~5% | raise ~25% / call ~70% / fold ~5% |
| `weak_made` | call ~55% / fold ~45% | fold ~75% / call ~25% |
| `air` (incl. busted draw) | fold ~95% / call ~5% | fold ~97% / call ~3% |

Anchors: **pot odds set the bar**, not the feeling of being bluffed. On **brick** rivers → disciplined bluff-catch with marginal pairs; on **scare** rivers → fold bluff-catchers at a bad price. A busted draw of your own has zero showdown value → never a call (demoted to air). **Live under-bluff exploit:** the population under-bluffs the third barrel badly, especially from tight seats — pot odds must be exceptional before a pure bluff-catcher continues. Fold base 1.0 > turn's 0.8 (a third barrel is the strongest bet-signal short of a check-raise).

**Multiway (3+):** call even less; the extra opponent makes any river bet more value-weighted.

---

## 9. Reconciliation notes (for R5)

The spec is authored **onto the existing grader machinery**, so re-pointing introduces no contradiction. Key points R5 must preserve:
1. **S8 multiway is a binary bucket applied last** — `is_multiway(spot)` = 3+ live players; `_apply_multiway()` runs after base merits, before normalization, HU output byte-identical. Every "multiway" row above is the *direction* S8 already moves (`_MW_BLUFF_DAMPEN`=0.6, `_MW_VALUE_LEAN`=1.15, `_MW_CATCH_TIGHTEN`=1.3). **Do not add a second multiway model in content that fights S8.**
2. **Scaling only touches positive merits** — the spec never promises a multiway frequency *increase* for a category whose base merit is already negative (air raises stay ~0 both HU and MW).
3. **River busted-draw demotion happens upstream of everything** — classify a river draw as air before looking up the spec row.
4. **`range_advantage` decays by street** (flop 1.0 → turn 0.5 → river 0.0) — the per-street tightening of the aggressor's value threshold is this same decay; do not re-encode it as a separate content dial.
5. **Single biggest reconciliation risk:** the chart and grader deriving frequencies through two different paths (chart reads authored content %s while grader computes from merits + normalization + multiway + demotion + street-decay) — they will silently drift. **Recommendation: keep the merit pipeline authoritative and have the chart render the grader's own `per_action` output**, making chart==grader true by construction. The spec then reduces to the *tuning target* for the merit constants.

---

## 10. Spots left "no baseline yet" (honest coverage list)

R5 must mark these NOT-charted AND ungraded on both sides, never fabricated:
1. Donk/lead lines (default is don't donk; no grader node).
2. Delayed c-bet, probe bet, overbet lines (no node).
3. Hero-as-check-raiser (only the *facing*-check-raise node exists).
4. 3-bet-pot / 4-bet-pot postflop (SRP is the only authored shape; `grade_map` refuses non-SRP).
5. Limped-pot postflop, and any multiway line the S8 binary bucket can't resolve to a defensible category weight.
6. Short-SPR / all-in / jam trees (`grade_map` gates these out).
7. Blocker-level and kicker-level resolution (four categories are the finest the spec claims).
8. Post-check-raise 4-bet on paired boards (the raise leg only — no solver data).
9. Turn/river spots the S10 `grade_map` can't yet build (the graders exist and this spec covers them, but the mapper only builds preflop + HU flop c-bet today; R5 decides whether to widen it).

---

## 11. Sources

Per node family, primary grounding is `docs/research/06-postflop-reference-tables.md` (doc-06) + `docs/research/02-postflop-strategy.md` (doc-02), with the exact per-category %s labeled **heuristic**:

| Node family | Grounding |
|---|---|
| Flop c-bet | doc-06 §2 · doc-02 §3 · heuristic %s |
| Vs-c-bet | doc-06 §2 defender splits, §4 paired bump · doc-02 §4, §8 MDF · heuristic %s |
| Vs-check-raise | doc-02 §4.4, §10.3 · doc-06 §4 (fold-heavy prior = labeled deviation below MDF) · heuristic + live-exploit |
| Turn barrel | doc-02 §5.1–5.2 · doc-06 §3 · GTOW "The Worst Turn Card" (brick barrel ≈85% no-draw) · heuristic %s |
| Vs-turn-bet | doc-02 §5.4, §8 · heuristic + pot-odds |
| River barrel | doc-02 §6.1–6.3 · doc-06 §5 value:bluff-by-size · heuristic %s |
| Vs-river-bet | doc-02 §6.4, §10.3 · doc-06 §5–§6 · heuristic + under-bluff exploit |

**Web sources (corroborate direction/magnitude, not exact combos):** GTO Wizard — [C-Bet Sizing](https://blog.gtowizard.com/the-mechanics-of-c-bet-sizing/), [IP C-Betting in Cash Games](https://blog.gtowizard.com/flop-heuristics-ip-c-betting-in-cash-games/), [Defending vs BB Check-Raise on Paired Flops](https://blog.gtowizard.com/defending-vs-bb-check-raise-on-paired-flops/), [The Worst Turn Card](https://blog.gtowizard.com/the-worst-turn-card/), [Principles of River Play](https://blog.gtowizard.com/principles-of-river-play/), [MDF & Alpha](https://blog.gtowizard.com/mdf-alpha/); ThinkGTO — [Multiway Ranges](https://thinkgto.com/blog/understanding-multiway-ranges-with-gto-ranges) (3-way c-bet ~35% vs ~70% HU); PokerNews / GTOW AI — [Struggling in Multiway Pots](https://www.pokernews.com/strategy/struggling-in-multiway-pots-gto-wizard-shows-the-answer-51069.htm).

**Full decision doc:** `docs/ai-dlc/research/RES-C-postflop-ranges.md`.
