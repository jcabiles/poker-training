# RES-I — Multiway (3-way BB-defense) mapper funnel: fresh measurement + lever sweep

**Spike, Epic 5 pre-work. Output = measured funnel + lever recommendation for the M1
"funnel levers" slice. NO app code changed.** Created 2026-07-22, AFTER Epic 4
(price-aware defense, size-linked bluffing, aggression cap, paired-board fix) and
PRs #53/#54 (open gates widened to 4.5bb) — all numbers below are post-those-changes.
The old 400-hand "0 fires" probe and the refuter's "persona-mix + open-band are the
dominant chokes" hypothesis are both superseded by this measurement (the hypothesis is
**refuted**: both of those levers measure ~zero effect today; the real chokes are
hero-seat scope, hero BB-defense width, and the postflop line gates).

---

## 1. Method

- **Instrumented the REAL path.** Hands play out through the real engine
  (`deck.deal_hand` → `engine.start_hand` → `engine.apply`) with the real bot policy
  (`play.bot_decision`, per-seat `PersonaPack`s). At every hero decision point the
  pre-decision state is fed to the REAL `grade_map.map_decision_point` and the REAL
  `grade_map_postflop.map_mw_flop_vs_cbet / map_mw_vs_turn_bet / map_mw_vs_river_bet`.
  Fire counts always come from the real mapper return values. Kill-attribution labels
  re-use the real gate helpers (`_mw_srp_preflop`, `_mw_check_bet_responded`,
  `_mw_check_bet_call_call`, `_mw_ranges`, `_is_canonical_bet`) called in the mapper's
  own gate order — no reimplementation of the gates.
- **Hero policy proxy.** The hero seat must act for hands to progress; hero plays a
  persona pack. Two proxies bound real-user behavior: `tag` (disciplined, narrow BB
  defense) and `calling_station` (very wide BB defense). This matters a lot — see §2.
- **Harness details.** Seat 0 = hero; button rotates `hand_no % 9`; stacks reset to
  100bb every hand (removes stack-depth confounds vs the session's carry-over);
  lineup shuffled across seats 1–8 per hand; one seeded `random.Random` per config
  drives deals + all actions (fully reproducible).
- **Sample size.** 10,000 hands per config (18 configs ≈ 180k hands total). Primary
  seed 20260722; key configs replicated at seed 7. Fires are rare events — at 10k hands
  the per-1000 figures carry roughly ±0.5–1.0 noise (seed-7 replicates shown).
- **Lever counterfactuals** via scratch-script monkeypatching (tree untouched):
  - caller-pair content gate off: `gp._mw_ranges` → `_srp_ranges`-only (skip the
    `VS_RFI (caller, opener)` entry requirement);
  - size gate widened: `gp._is_canonical_bet` accepts the whole persona bet grid
    {0.33, 0.5, 0.75, 1.0}×pot on every street (canonical today: flop 0.33/0.75,
    turn 0.5/0.75, river 0.5/1.0);
  - open-band counterfactuals computed from recorded `open_to` distributions (no
    re-run needed).
- Harness: `mw_funnel.py` in the session scratchpad (not committed).

## 2. Fresh funnel decomposition (baseline: current lineup, hero=tag, 10k hands)

Per 1,000 hands, seed 20260722 (seed 7 in parens where it differs):

| Stage | /1000 hands |
|---|---|
| Hands dealt | 1000 |
| Flops seen (any) | 805 |
| Flops with exactly 3 live players | 286 |
| **MW-canonical shape** (real `_mw_srp_preflop` passes at flop start) | **23.8** (23.9) |
| … hero seated in it as **BB** | **0.7** (1.4) |
| … hero seated as opener / cold-caller (unmapped today) | 2.0 / 1.3 |
| … hero folded pre (bot-vs-bot MW pot) | 19.8 |
| Hero-BB decision points inside MW pots (flop/turn/river) | 1.2 / 0.9 / 0.4 |
| **MW mapper fires** | **0.0** (0.1) |

**Stage 3-way-flop → MW-shape (2,859 → 238 flops, what killed 2,621):**

| Kill (real gate) | count | note |
|---|---|---|
| Limped pot (no preflop raise; BB checked option) | 1,110 | fish/station limp chains — structurally excluded (`pre` action-set gate) |
| >2 preflop calls (limp/call chains, 4+ entrants pre) | 890 | `calls=3/4/5` |
| SRP 3-way **without the BB** (two non-blind cold-callers) | 485 | BB folded; shape requires BB in |
| Blind entrant (SB caller / blind open) | 115 | |
| 3-bet pots (`raises=2+`) | 24 | |
| Open-size band | **0** | see §3 L2 |

**Hero-BB conditional (why 0.7, not ~26 = 23.8/9×9):** hero is BB in ~111/1000 hands.
MW-shape formed in 0.63% of hero-BB hands (tag proxy) vs 2.6% of bot-BB hands — the
hero's own preflop defense width is a ~4× damp on top of the 1/9 seat share. With the
station proxy: 3.0% → 3.7/1000 hero-BB MW pots.

**Hero-BB postflop line kills** (station-hero runs for sample size): the opener checks
the flop (no bet → nothing to grade — structural), opener bets a **non-canonical size**
(0.5-pot or 1.0-pot flop bets from the persona grid; flop canon is 0.33/0.75 only),
caller raises (different node — deliberate None), multi-action streets (check-raise
wars), and for turn/river the prior street's bet-call-call breaking (incl. the caller
folding the flop, which kills turn/river continuation by design). Hero-BB's own flop
CHECK decision (`flop:acts=0`) is structurally ungraded — the MW family maps facing
nodes only.

## 3. Lever sweeps (10k hands each)

### L1 — Lineup mix (verdict: NOT a lever; skip)

The app offers exactly **one** lineup, hardcoded at `backend/app/domain/table/play.py:35`
(`LINEUP`: 2×fish, 2×tag, station, nit, lag, maniac). There is no config surface — any
"lineup lever" is a code change. Swept four mixes with both hero proxies:

| Lineup | MW-shape /1000 | fires /1000 (hero=tag) | fires /1000 (hero=station) |
|---|---|---|---|
| current | 23.8 | 0.0 | 0.1 |
| no_maniac (maniac→station) | 17.6 | 0.0 | 0.0 |
| loose_passive (3 fish, 2 station, nit, 2 tag) | 12.2 | 0.0 | 0.7 |
| all_tag (8 tags) | 7.4 | 0.1 | 0.6 |

Effect on **fires ≈ nil** (within noise). Counter-intuitively, passive mixes LOWER
MW-shape volume: fish/station replace raised pots with **limped** pots (loose_passive:
2,468 limped-3-way-flop kills vs 1,110 current), and limped pots are structurally
excluded. Implementation size if pursued anyway: code. Side-effects: S4 table-texture
calibration drift (see §5) + product feel.

### L2 — Open-size band (verdict: already solved; closed)

Zero band kills in every run. Cap is 4.5 (`_OVERSIZE_OPEN_CAP`, grade_map_preflop.py:58)
and the max persona open is maniac's 4.5 — everything is in-band since #53/#54.
Counterfactual old 3.0 cap: 101/238 = **42% of MW-shaped pots** had `open_to` > 3.0
(distribution: 3.0×137, 3.5×2, 4.0×17, 4.5×82) and would have died. That win is banked;
there is **no further headroom** (no persona opens above 4.5). Implementation size: none.

### L3 — Content gaps: `VS_RFI` cold-caller pairs (verdict: build; content-only)

`_mw_ranges` requires a `VS_RFI (caller, opener)` entry with a CALL range. Audit of the
21 ordered non-blind pairs: **9 exist, 12 missing** — LJ_vs_UTG, LJ_vs_UTG1, HJ_vs_UTG1,
CO_vs_UTG1, BTN_vs_UTG1, LJ_vs_UTG2, HJ_vs_UTG2, CO_vs_UTG2, BTN_vs_UTG2, HJ_vs_LJ,
CO_vs_LJ, BTN_vs_LJ (i.e., almost nothing is authored behind UTG1/UTG2/LJ opens).
`_srp_ranges` itself is NOT a gap — RFI + BB blind-defense entries exist for all seven
non-blind openers. Measured (current lineup, caller-gate patch only):

| Hero proxy | fires /1000 base → patched |
|---|---|
| tag | 0.0 → 0.2 |
| station | 0.1 → 0.6 |

Small absolute win but it multiplies the base ~3–6×, and in the baseline run **both**
decisions that survived every line gate died exactly here. Implementation: content-only
(12 authored entries, RES-A discipline). Co-benefit (not measured here): those same
missing pairs make the HERO's own preflop cold-call/3-bet decisions from those seats
unmappable in `map_preflop` — authoring them widens preflop coverage too.

### L4 — Canonical-size gate vs the persona bet grid (verdict: build, with grading care)

Personas bet from the grid {0.33, 0.5, 0.75, 1.0}×pot (`sizing_by_node`, e.g. tag
cbet_dry puts 30% on 0.5-pot, cbet_wet 30% on 1.0-pot), but the flop line gate accepts
only 0.33/0.75. Patch: accept the whole grid per street.

| Config (current lineup) | fires /1000 |
|---|---|
| base (tag / station) | 0.0 / 0.1 |
| size gate only | 0.1 / 0.5 |
| caller gate only (L3) | 0.2 / 0.6 |
| **L3 + L4 together** | **0.3 / 1.5** (station seed 7: **3.2**) |
| L3+L4, all_tag lineup, station | 1.9 |
| L3+L4, loose_passive, station | 1.5 |

L3+L4 together are super-additive (~×5–15 on the base) because the funnel is a chain of
ANDs. Implementation: code (the `_is_canonical_bet` fraction sets in
`grade_map_postflop`/`sizing.POSTFLOP_BET_FRACS` recognition — NOT the hero's offered
sizes) **plus** grading treatment of the newly recognized faced sizes — see §5.

### L5 — Hero-seat scope widening (verdict: ceiling measured; DO NOT build in M1)

Currently-unmapped hero decision points inside MW-shaped pots with hero as **opener or
cold-caller** (the ceiling of widening the family beyond BB):

| Hero proxy | ceiling /1000 hands | composition |
|---|---|---|
| tag | 6.2 (seed 7: 11.3) | mostly hero-as-opener c-bet/barrel nodes |
| station | 8.5 | mostly hero-as-caller facing nodes |

This is the ONLY lever with ≥5/1000 headroom. It is also the biggest build: new mappers
(MW aggressor c-bet/barrel, MW cold-caller closing/non-closing) and a grading model for
betting INTO two live players. Reported as ceiling only, per the spike scope.

### Hero-policy sensitivity (not an app lever — flagged)

Every conditional stage hinges on how wide the USER defends the BB: hero-BB MW pots
0.7/1000 (tag proxy) vs 3.7/1000 (station proxy); fires with L3+L4 0.3 vs 1.5–3.2.
The product cannot pull this lever (coaching/UX nudges aside); all M1 projections
should quote the tag–station range, not a point estimate.

## 4. Recommended minimal lever set + threshold

**Threshold: ≥5 graded MW decisions per 1,000 hands** (tag–station average). Rationale:
a substantial Simulate session is ~150–250 hands, so 5/1000 ≈ one graded MW rep per
session on average — enough for the coach/recap to surface multiway play as a real,
recurring topic — and it is the level at which a committed user (~2–3k hands) can
accumulate an N7-rankable leak group (`_LEAK_MIN_SAMPLE = 5` graded per
(node, position)). The brief's example of ≥10/1000 is measurably unreachable: even with
EVERY in-scope gate relaxed and a maximally loose hero, BB-only fires cap at ~1.5–3.2/1000.

**Ordered lever set (cost/benefit):**

1. **L3 — author the 12 missing `VS_RFI` pairs** (content-only, zero bot-behavior
   change, preflop-coverage co-benefit). Cheapest per unit of win; removes the gate that
   killed 100% of the baseline's fully-canonical arrivals.
2. **L4 — widen line-gate size recognition to the persona grid** (small code change +
   RES-E grading extension, §5). Largest per-line effect; with L3 it moves fires from
   ~0 to 0.3–3.2/1000.
3. **L5 — hero-seat widening** (opener + caller MW mappers): the only path to the
   ≥5/1000 threshold (ceiling 6–11/1000 on top of L3+L4). Big build — recommend M1
   ships L3+L4 with a 30k-hand re-measure gate, and L5 is a separate go/no-go slice
   decided on that measurement.

**Explicitly rejected:** lineup changes (no measured effect on fires; S4 calibration +
product-feel risk) and open-band changes (already solved; zero kills, zero headroom).
Honest bottom line for the PRD: L3+L4 alone leave graded-MW rare (~0.3–3/1000,
hero-dependent). If Epic 5 needs the threshold met, L5 must be in scope.

## 5. Risks / side-effects flagged for the build slice (flags, not decisions)

- **L4 grading correctness (HIGH).** Recognizing a 0.5-pot or 1.0-pot flop bet is only
  half the lever — the graders bucket faced sizes small/big (RES-E) and F2 made bot bet
  size information-bearing (size-linked polar bluff share). A newly recognized 0.5-pot
  flop bet must map to a defined faced-size bucket / price, not silently collapse into
  the 0.33 bucket, or EV baselines mis-price exactly the spots this lever adds. RES-E
  is live law — the slice must extend it, not bypass it.
- **L4 blast radius.** `_is_canonical_bet` is shared by the HU turn/river mappers and
  `sim_session`'s display==grade gates (`_is_turn_barrel_node`, `_facing_raise_spot`).
  Widening recognition changes HU coverage too (that's a feature — same choke — but the
  S10/S11 display==grade invariant must be re-verified, and hero's OFFERED sizes
  (`POSTFLOP_BET_FRACS`) should stay 2-button).
- **L3 range quality.** The 12 new `VS_RFI` entries are grading baselines and Practice
  content; they need RES-A-grade review, not filler ranges. No bot-behavior effect
  (bots play from persona packs, not content ranges).
- **S4 band stats.** L3 (content) and L4 (recognition) change ZERO bot behavior — the
  S4 per-persona calibration bands and table-texture suite are untouched by the
  recommended set. Lineup levers WOULD drift the S4 table-texture calibration (the
  players-to-flop floor 2.4 was derived for the maniac-bearing lineup) — one more
  reason they're rejected.
- **Measurement noise.** Fires are rare events; 10k-hand estimates carry ±~1/1000
  (seed replicates: 1.5 vs 3.2). The M1 acceptance gate should re-measure at ≥30k hands
  with this harness before declaring the threshold met/missed.
- **Hero-policy dependence.** All funnel projections are bounded by the tag/station
  proxies; a real user sits somewhere between. Any M1 pass/fail number must state which
  proxy it assumes.
- **Structural non-decisions.** Hero-BB's own check decision in an MW pot and
  opener-checks-flop hands produce no gradeable facing node by design; funnel
  accounting should not count them as recoverable losses.

## 6. M1 re-measure (post-build, 2026-07-22 — the M7 go/no-go input)

M1 shipped L3 (all 12 `VS_RFI` caller pairs authored, `vs_rfi.json` v2) and L4
(`_is_canonical_bet` recognition widened to `RECOGNIZED_BET_FRACS` =
{0.33, 0.5, 0.75, 1.0, **1.5**}×pot, every street — one step past the §1
counterfactual grid: the maniac's 1.5-pot overbet is also recognized, since it
maps to the defined RES-E OVERBET bucket and the graders price the live
pot-fraction). Hero OFFERED sizes stayed 2-button; zero bot-behavior change
(coverage-baseline hand stream total 1233 unchanged; graded 242 → 267).

**30,000 hands per config, §1 method** (real engine + real bot policy, hero
seat 0 plays the stated persona proxy, button rotates, stacks reset 100bb,
lineup shuffled per hand, one seeded Random; fires = non-None real
`map_mw_*` returns at hero pre-decision states; harness `mw_remeasure.py`,
scratchpad, not committed):

| Hero proxy | seed 20260722 | seed 7 |
|---|---|---|
| tag | **0.27**/1000 (8 fires: 8 flop) | **0.23**/1000 (7: 7 flop) |
| calling_station | **1.93**/1000 (58: 51 flop / 7 turn) | **2.73**/1000 (82: 70 flop / 12 turn) |

Squarely inside the §3 L3+L4 projection (tag ~0.3, station 1.5–3.2; river
fires remain ~0 — the 3-street bet-call-call line rarely survives intact).
**Verdict for M7: graded-MW is far below the ≥5/1000 threshold (§4) under
BOTH proxies — the go/no-go should be GO on L5 hero-seat widening** (measured
ceiling 6–11/1000 on top of these numbers) if Epic 5 still wants the
threshold met.
