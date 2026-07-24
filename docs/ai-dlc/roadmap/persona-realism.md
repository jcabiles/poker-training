# Persona Realism — Roadmap (created 2026-07-23)

> Living, pass/fail, resumable. A fresh context reads this + the two source docs and knows exactly what's left.
> **Engine contract map (READ FIRST):** `docs/research/12-persona-engine-and-realism-fixes.md`
> — every lever, merit table, formula, line anchor, and INVARIANT. This roadmap is the *decomposition*.
> **Grounded numbers (magnitudes):** `docs/ai-dlc/research/persona-realism-audit-2026-07-24.md` §10
> (prescriptions P1–P9) — a merit multiplier is a FIT SEED, never a drop-in constant (softmax law).
> **Full-scope backlog (superset, local/uncommitted):** `docs/ai-dlc/research/persona-realism-FULL-BUILDOUT.md`
> — every buildable item (Tracks A–H, Phases 0–9), findings-coverage map, owner forks. This roadmap is the
> *committed subset* of that backlog. Roadmap-structure debate + hardening gates:
> `docs/ai-dlc/research/persona-realism-artifacts/roadmap_debate/DEBATE.md`.
> Parent roadmap: `docs/ai-dlc/roadmap/simulate-table.md`.
>
> **Resume rule:** work waves in order; verify a slice's pass/fail ACTUALLY passes before `[x]`
> (agents falsely mark work done). Hand ONE slice at a time to `/ai-dlc`. Every slice gets a fresh
> `refuter` at fan-in (maker ≠ checker).

---

## Decisions locked (2026-07-23 interview) — what this roadmap commits to

The narrow 2026-07-23 scope lock (stop before position / stack-depth / texture) is **RE-OPENED**. The grounded
research re-promotes those to core. This roadmap now holds the **full grounded program** as NOW/NEXT slices and
the **deferred/architecture tail** as typed Later bets. Specifically:

1. **Scope = full program, tail as Later.** Grounded prescriptions → NOW/NEXT; opener-position, villain-range
   rungs b/c, blockers, exploit-coaching, 5+way multiway → Later bets.
2. **Villain-range rung (a) is COMMITTED to NEXT** — a coarse static preflop-range-by-position *lookup* (data, not
   a solver; stays no-solver-compliant). It unlocks the barrel-more-on-scare-cards pilot and "facing a [type]"
   reads. Rungs (b) persona-conditional prior and (c) full equity-vs-range estimator stay Later.
3. **All four hardening gates adopted:** (D7) a new metric must show the expected direction before its slice can
   close; (D8) a seeded node-trace pack catches "right stat, wrong reasoning"; (D9) a human-realism playtest
   before the final band re-anchor; (F1) every mechanic slice files a coaching seam-row.
4. **Coaching seam-feeds the active teacher-rework** — concept-card candidates + a cleaner GTO grading baseline
   ride on landed mechanics (no new coaching roadmap, no collision). Full exploit-coaching is a Later ticket.

**Defaults applied (veto any at the approval gate):** opener-position-aware defense (needs schema+plumbing) →
Later · WTSD downward re-anchor → accepted, once, at W4 close · out-of-position realization damp → Later · commit-
factor spread → let the elasticity split carry separation first, widen the `D` exponent only if measured too weak ·
reference pool stays **online low-mid 9-max ~100bb** (the whole keystone is calibrated to it).

---

## North-star outcome — the WHY

- **Primary:** *the six villain bots make decisions that match their real-world archetype* — so the
  Simulate table teaches transferable reads instead of training the hero against unhinged, streetless bots.
  **Metric:** each persona's computed facing-a-bet distribution matches its archetype's documented shape —
  polarized rivers, archetype-correct fold-to-size elasticity, no off-archetype open-limps, no literal
  no-pair-no-draw calls, position/street/stack-aware lines.
  **Baseline (measured, doc 12):** maniac raised one pair on the river 38–54% and called busted air 23%;
  station called pure air 78%; fish & station differed only by a uniform stickiness shift (no shape
  difference); every response node was position/size/street-blind. → **Target:** river raises come only from
  `TWO_PAIR_PLUS+` / bluff-cell; air-call ≈0 without a draw; station fold-rate ≈flat across bet sizes while
  fish is fit-or-fold; bots answer a UTG open differently from a BTN open; turn ≠ flop. All six personas.
  **Runnable metric:** a **committed persona-distribution test module** with fixed hole/board/legal/history
  contexts and explicit numeric thresholds + tolerances, asserting per persona: river bucket→action
  distributions, size-response slopes (fold-rate vs bet size), positional/price preflop deltas, and conditional
  barrel/give-up rates. Each slice adds its assertions to it — that suite, not prose like "≈0 / roughly flat",
  is what "matches its archetype" means. Population VPIP/PFR/AF/WTSD stats stay a **secondary** regression check.

## Why this is one initiative, not six persona fixes

The **same root causes** drive every symptom (doc 12 §5, §9): the postflop engine is **context-blind** — one
shared merit table × 5 scalar levers, with no input for position, board texture, street, stack depth, or villain
range. So the fixes below repair **all six personas at once**; the aggressive three (maniac/LAG/TAG) are just
where the damage is loudest.

---

## Cross-cutting discipline — applies to EVERY opting-in slice

### Softmax law (anti-cosmetic-change) — NON-NEGOTIABLE
The engine normalizes merits into probabilities, so a merit multiplier is **NOT** the observed frequency change.
Every magnitude in §10 / the build-out is a **FIT SEED**: measure the observed stat → adjust the merit → re-measure.
Dropping in "×0.75 / ×0.50" or a fixed fold-reduction as-is ships a **cosmetic** change. No slice closes on
"the constant is in the code"; it closes on "the observed stat hit its target band."

### Metric Definition-of-Done gate (D7 — hardening gate)
A slice that needs a NEW harness metric to prove its effect **cannot close until that metric is live AND showing
the expected direction** (e.g. the IP-vs-OOP c-bet delta must exist and move before the position slice closes).
This converts "directional-until-built" from an open IOU into a per-slice exit criterion.

### Node-trace realism pack (D8 — hardening gate, anti-degeneracy)
A lightweight seeded-replay pack: fixed hands per persona across IP/OOP, overcards, turn barrel, busted draw,
multiway, high-commitment spots — logging bucket, draw class, merits, chosen action, intended prescription. Catches
"**right stat, WRONG node**" (a maniac hitting its aggression number by over-valuing made hands instead of
bluffing). Built in W0; each behavior slice adds its spots. Scope = seeded replay + merit log, NOT a new framework.

### Human-realism playtest checkpoint (D9 — hardening gate)
Blinded seeded replays + short free-play with 2–3 poker-literate reviewers. Acceptance = reviewers distinguish
archetypes above chance AND flag no recurring persona-breaking lines. Runs at **W3.5**, after the context
mechanics and BEFORE the final band re-anchor, so "feels human" feedback informs the fit. Stats-conformant ≠
line-coherent.

### Coaching seam intake (F1 — hardening gate)
> ⚠️ Code collision: this hardening-gate **F1** (seam intake) is NOT the audit's **finding F1** (position ignored
> postflop, which this roadmap fixes in W3-b). Same string, unrelated referents — disambiguate on hand-off.
Every mechanic slice files a structured seam-row (mechanic · concept-card candidate · baseline stat moved ·
example replay seed · source test · owner · status) into the `professional-teacher-rework` **Next** column as
accepted / deferred-with-reason. **A slice isn't done until its seam-row is filed.** Batch handoff at W4 close.

### Range-estimator parity — for any slice that makes the LIVE bot diverge (Codex-Sol HIGH)
`range_estimate.py:278` recovers the villain's action distribution by **replaying the persona policy** with a
capture-rng. "Keep `range_estimate` byte-identical" holds **only for un-opted-in direct callers**. The moment a
slice makes the live bot diverge from the streetless policy, the estimator MUST be threaded the **same** context
and re-tested for **parity with the live policy** — else the villain-range reveal feature silently lies. Each such
slice owns extending the estimator's replay context + a parity test. The action draw stays the FIRST `rng.choices`.

### Baseline & calibration discipline (anti-laundering)
Re-recording `coverage_baseline.json` every slice replaces the comparator, so small repeated losses can vanish.
Rule: an **immutable initiative-start snapshot** (`coverage_baseline.persona-realism-start.json`) exists; each
slice re-records the operational fixture for CI green **and** reports the CUMULATIVE graded-coverage delta vs the
immutable snapshot; any cumulative loss needs explicit adjudication. The **W4 pass** does the ONE authoritative
combined population-band re-anchor after the whole spine converges (don't chase bands across waves).

---

## NOW — the grounded program, as spec-ready vertical slices

### Wave plan (dependency order from the build-out §4)
**W0 foundation** (denominator + measurement + anti-degeneracy infra — unblocks honest gating for all of NOW)
→ **W1 low-risk wins** → **W2 identity + EV** → **W3 context** (plumbing → position/street/texture)
→ **W3.5 human-realism checkpoint** → **W4 commitment brake LAST + single band re-anchor + seam batch**.
All postflop-mechanic slices own `personas_postflop.py` ⇒ they run **serially** on that spine. The commitment
brake is sequenced LAST (highest regression risk; it must layer on the stabilized price/fold equation, not force
re-tuning). Every slice: default-off byte-identity for un-opted-in direct callers until the live loop opts in.

---

### ✅ DONE

- [x] **P1 — Correctness patch (fold-aces, open-limps, oversized 3bet, air-calls, dead-mix guard).** ✅ 2026-07-23
      Branch `feat/persona-realism-p1` (#83). Station no longer folds AA/KK/AKs unopened; maniac/LAG non-SB
      open-limps deleted; maniac `threebet_mult`→~3.3; maniac vs_4bet re-jams lighter/trappier than LAG;
      `_CALL_BASE[AIR]` 0.25→0.08 (street-neutral base drop); dead-mix validator + CI guard. Suite green,
      coverage 28.3→29.4%. (`tanh`-saturation `aggression` re-author deferred → NEXT.)

- [x] **P2a — Street-aware refactor + river polarization (keystone).** ✅ 2026-07-23
      Branch `feat/persona-realism-p2a` (#85). Added the `street` kwarg (default byte-identical); floored river
      RAISE for {MIDDLE_PAIR, TOP_PAIR, OVERPAIR_TPTK} + air-CALL to 0; `play.py` + `range_estimate.py` opt in
      (estimator-parity test green). Bands re-anchored (WTSD/AF). **Note the residue for W1:** P2a floored the
      river *raise*; the unopened river one-pair **BET** floor (MIDDLE_PAIR only) is still open → slice W1-a below.

---

### W0 — foundation (measurement + shared inputs + anti-degeneracy)

- [ ] **W0-a — Shared pot-before-aggression denominator (A1).** *ICE 7·9·8 — small, shared.*
      **Problem:** the commitment gate (W2), the semi-bluff EV math (W2), and the faced_frac fix (W1) all need
      "the pot before the current bet/raise" + the latest aggressor's increment; a wrong denominator silently
      corrupts every EV threshold downstream.
      **Solution:** one domain-pure helper reconstructing pot-before + latest-aggressor increment from
      `state.action_history` (already at the `play.py` call site). No DB, no new state.
      **Pass/fail:** a self-re-raise unit test returns the correct pre-aggression pot; every existing suite stays
      byte-identical (pure add, no consumers yet). **No-gos:** domain purity; don't rewire the action draw.
      **Appetite:** ~1 small slice.

- [ ] **W0-b — Harness metric scaffolding + Definition-of-Done gate (D1–D7).** *ICE 8·8·5 — infra, walking skeleton.*
      **Problem:** the harness measures only 3 stats today (AF, fold-to-cbet, WTSD). Six grounded mechanics can't
      be *honestly* gated without new metrics — so their acceptance would be prose, not a test.
      **Solution:** add the metric framework + six metrics: CBet-flop overall (D1), W$SD (D2), VPIP/PFR/gap joint
      (D3), size-bucket Fold-to-C-bet curve (D4 — the elasticity test), IP-vs-OOP C-bet split (D5), turn-barrel%
      (D6). Wire the **metric-DoD rule (D7)**: a downstream slice may not close until its metric is live + directional.
      **Pass/fail:** each metric computes on the existing fixture and emits a value; the DoD rule is documented in
      this file and referenced by the slices that depend on it. **No-gos:** measurement only, no behavior change;
      don't re-anchor any band here. **Appetite:** ~1 large slice (can sub-split per metric at `/ai-dlc`).

- [ ] **W0-c — Node-trace realism pack (D8) + harness-fit loop doc (D11).** *ICE 7·8·6 — infra, anti-degeneracy.*
      **Problem:** stat-conformant bots can still play incoherent lines ("right stat, wrong node"); and the softmax
      law means every magnitude is a fit loop that must be repeatable.
      **Solution:** the seeded-replay + merit-log pack (D8) with an initial spot set; a short documented fit loop
      (measure → adjust seed → re-measure) + the single-end-of-cluster re-anchor rule (D11).
      **Pass/fail:** the pack runs and logs bucket/draw/merits/action/prescription for the seed set; the fit-loop
      doc exists and is linked from each mechanic slice. **No-gos:** lightweight (no new framework). **Appetite:** ~1 slice.

### W1 — low-risk wins (small, contained, some infra already present)

- [x] **W1-a — River one-pair BET floor, MIDDLE_PAIR only (B8, fixes F6).** ✅ 2026-07-24 (feat/persona-realism-w1).
      `_RIVER_BET_FLOOR=(MIDDLE_PAIR,)`; the named byte-identity test split (theory H1); slice-authorized
      seeded-fixture re-records (golden AF/WTSD, coverage 30.4%, limper belt) — tolerance BANDS stay frozen to W4-b.
      *ICE 7·8·7 — small; re-anchors bands.*
      **Problem:** P2a floored the river *raise* but the unopened river **BET** for a middle pair (a bluff-catcher,
      never a value bet) is still not floored.
      **Solution:** `_RIVER_BET_FLOOR = (MIDDLE_PAIR,)` — floor the unopened river BET for MIDDLE_PAIR ONLY; strictly
      narrower than the existing raise-floor (which also covers top pair). Reframe as a conservative HU/balanced-villain
      DEFAULT (middle pair CAN value-bet vs capped/station ranges — a rank approximation, not a theorem).
      **Pass/fail:** middle-pair river unopened BET → 0 (committed unit assertion); top-pair/overpair BET untouched
      (assertion split). **The population WTSD/AF band re-anchor is DEFERRED to W4-b** (§10.4: P5 ships behind the
      unit-assertion split ONLY — re-anchoring here would re-fit bands that W2/W3 then move again). **No-gos:** don't
      touch the raise-floor P2a set; MIDDLE_PAIR only; no band edits pre-W4. **Appetite:** ~1 small slice.

- [x] **W1-b — faced_frac increment fix + backwards comment (B9, fixes F9).** ✅ 2026-07-24 (feat/persona-realism-w1).
      ENGINE-ONLY (Codex #1: the estimator builds CALL min_bb=None → numerator 0 → the denominator fix is inert
      there, so NO `_Ctx`/estimator change was needed). play.py threads the W0-a increment; comment direction fixed
      (OVERSTATES); self-re-raise + back-raise + fresh-identity + wiring tests. **Follow-up spun out → Later:
      the estimator is faced-price-BLIND (numerator 0) — a pre-existing approximation; giving it a real to_call is a
      separate, higher-blast-radius slice.** *ICE 7·9·8 — small, genuinely low-risk.*
      **Problem:** on same-street re-raises the faced-price denominator uses the whole bet-to instead of the latest
      aggressor's increment → over-states price → over-folds; the in-code comment documents this backwards.
      **Solution:** use the A1 latest-aggressor increment as the same-street re-raise denominator; fix the comment.
      **Depends-on:** W0-a. **Pass/fail:** existing faced_frac tests 563/577 stay green (they cover fresh raisers
      only); a NEW self-re-raise test proves bots over-fold slightly less to 3-bet wars. **No-gos:** don't change
      fresh-raiser behavior. **Appetite:** ~1 small slice.

- [x] **W1-c — Multiway made-value tightening (B10, fixes F13).** ✅ 2026-07-24 (feat/persona-realism-w1).
      `_MW_VALUE_DAMP=0.8` (unfit directional seed) on TOP_PAIR/MIDDLE_PAIR unopened BET only, capped at the 4-way
      tier; HU byte-identical; monotone+plateau test via exact captured weights. *ICE 6·7·8 — small, directional.*
      **Problem:** value-betting is opponent-count-blind — made hands barely tighten as more players see the flop.
      **Solution:** a geometric damp `~0.8**(opp−1)` (FIT SEED) on made-value aggression as opponent count rises;
      HU byte-identical; cap at a **labeled 4-way tier** (5+way magnitudes are unresearched — Later).
      **Pass/fail:** made-value aggression non-increasing in opponents (monotone test); HU byte-identical.
      **No-gos:** don't extend past the 4-way label; directional-only until a multiway metric exists. **Appetite:** ~1 small slice.

### W2 — persona identity + EV correctness

- [x] **W2-a — Elasticity split: `stickiness` → `call_looseness` + `size_elasticity` (C1, fixes F10).** ✅ 2026-07-24 (PR pending) — *ICE 8·7·5 — the keystone identity fix.* Two optional levers, default-off byte-identical; opt-in `size_elasticity` uses a DIRECT exponent (0 = size-blind, fixing the `0**-DAMP` crash + direction reversal a naive rename caused — fan-in catch). Station `size_elasticity 0.0` (flat fold-curve), fish `1.3` (steep). Fixtures re-recorded (shared-table); bands frozen.
      **Problem:** one dial controls **both** how loose a persona calls **and** how much bet size scares it, so you
      can't make the **station inelastic-but-loose** (calls any size) while the **fish is elastic-but-scared**
      (fit-or-fold) — the one axis that *defines* their difference is welded shut.
      **Solution:** two optional levers — `call_looseness` (the flat CALL multiplier) + `size_elasticity` (drives the
      price_factor exponent, decoupled from looseness); default = today's `stickiness`. Prefer a **continuous** faced-
      size function over the 4 abrupt α buckets. Station `size_elasticity ≈ 0` + high looseness; fish high elasticity +
      moderate looseness. Update the monotonicity pins to the new levers.
      **Depends-on:** W0-b (D4 size-bucket FtC curve — the elasticity test) must be live + directional before close.
      **Pass/fail:** station fold-rate roughly flat across SMALL→OVERBET; fish fold-rate rises steeply with size;
      `call_looseness↑` never lowers call freq; α-ceiling + monotonicity pins re-anchored deliberately (these are
      lever-identity assertions, NOT the population bands). **Population WTSD/AF band re-anchor DEFERRED to W4-b** —
      do not re-fit bands mid-spine. **No-gos:** keep default-off byte-identity for un-split packs; no band edits
      pre-W4. **Appetite:** ~1 large slice.

- [x] **W2-b — Semi-bluff draw-jam gate + weak-draw equity gate (B5 + B5b, fixes F5 + F7).** ✅ 2026-07-24 (PR pending) — *ICE 7·8·5 — coupled pair.* EV-gated commit shift: made hands value-jam byte-identical; a facing draw commits only when rule-of-4-and-2 equity clears the T1 threshold `f/(1+2f)` (STRONG folds to a 3×-pot overbet, jams pot-committed); naked WEAK draw stops stacking off (B5b damp). **Deviation (owner-approved, both reviewers):** the roadmap's "fold merit ≈ F\*" conflated the opponent's required-fold with the bot's own fold prob — replaced by a directional own-action policy (existing price-aware fold stands below T1). Rigorous F\* → Later. **maniac WTSD band assertion deferred to W4-b** (sits on the frozen 0.50 ceiling; throughput-n sampling noise, pre-existing).
      **Problem:** the SPR-commit path zeros fold merit and fires for naked air+draw (forced no-fold jam, F5); and the
      `_DRAW_CALL_BONUS` (0.20, ~2.5× the air base) makes bots chase weak draws too far (F7) — a fold-side brake alone
      can't overpower it.
      **Solution (one slice, two coupled levers):** (B5) zero fold ONLY inside the value-commit zone T1 (equity ≥
      B/(P+2B)); below T1 set fold merit so the *normalized* fold prob ≈ F* (the T2 required-fold identity), NOT a fixed
      multiplier; multiway preserves more fold mass. (B5b) a SEPARATE gate damping the draw call/raise BONUS by
      commitment/equity at high c. Sequence B5b→B5 finalize (B5's F* fold-merit is set LAST against the boosted denominator).
      **Depends-on:** W0-a. EV identities re-derivation-CONFIRMED (T1/T2; the 3×-pot threshold is **42.9%**, not 60%).
      **Pass/fail:** a flush draw pot-committed still jams; the same draw vs a 3×-pot overbet now folds; a naked weak
      draw stops stacking off at high commitment. **No-gos:** no equity SOLVE (heuristic rule-of-4-and-2 proxy; its
      calibration is Later/H7). **Appetite:** ~1 large slice.

### W3 — context (plumbing → position / street / texture)

- [x] **W3-a — Just-ahead plumbing: `in_position` + `bet_prev_street` + `busted_draw` (A2/A3/A4).** *ICE 7·8·6 — plumbing, walking-skeleton.* ✅ 2026-07-24 (PR pending) — new pure `table/postflop_context.py` (derivations + `PostflopContext`), threaded through `sample_postflop_decision` unread (defaults = today); 18 derivation unit tests; every golden/coverage/limper fixture byte-identical with NO re-record (walking skeleton = zero rng displacement). First of the 2-PR W3 packaging (plumbing seam).
      **Problem:** the postflop sampler receives almost no situational context; the position/street/busted mechanics
      below each need one boolean the sampler doesn't get.
      **Solution:** thread three derived inputs (default = today's behavior): **A2** `in_position` (true iff no
      not-folded, not-all-in opponent acts after me this street — exclude FOLDED + ALL-IN seats; **BB IS in position vs
      SB** postflop; 3+-handed = last live seat); **A3** `bet_prev_street` (per-street aggressor memory — fixes the
      whole-hand `is_aggressor` mislabel F17, which ALSO corrupts sizing-node selection); **A4** `busted_draw` provenance
      (preserve "was a draw that missed" past the river).
      **Pass/fail:** derivation unit tests for multiway / BvB / all-in (A2), delayed-stab vs barrel + sizing-node
      selection (A3), busted-draw survives the river reset (A4); all existing suites byte-identical (no consumers yet).
      **No-gos:** thread just-ahead of consumers, not big-bang; domain purity. **Appetite:** ~1 slice.

- [ ] **W3-b — Position mechanic IP/OOP (B1, fixes F1).** *ICE 7·6·5 — GROUNDED direction, DIRECTIONAL magnitude.*
      **Problem:** bots play IP and OOP identically.
      **Solution:** an IP/OOP multiplier on the WHOLE aggressive candidate (bluff_mass + `_AGG_BASE` + draw-agg bonus,
      not just `_AGG_BASE`) + an optional per-persona `position_sensitivity` lever (station/fish ≈ 0 = stay
      position-blind as an intended leak; TAG/nit = full). FIT SEEDS, per-type LOW-confidence.
      **Depends-on:** W3-a (A2); W0-b D5 (IP/OOP c-bet split) live + directional before close (D7 gate). Coordinate the
      bet-band re-level with W3-c.
      **Pass/fail:** a CBet_IP > CBet_OOP gap appears for disciplined types (D5 metric); aggression-factor stays in band.
      **No-gos:** aggressor-side c-bet/barrel frequency ONLY (the OOP continue-realization damp is Later — don't smuggle
      it in). **Appetite:** ~1 large slice.

- [ ] **W3-c — Street-conditional aggression schedule + busted-draw river bluff (B6 + B7, fixes F4/F19/F8).** *ICE 7·7·4 — GROUNDED shape, turn LEVEL fit.*
      **Problem:** aggression is street-neutral (turn == flop byte-identical); `bluff_mass` doesn't decay; busted draws
      lose their identity at the river and can't tell a coherent story.
      **Solution:** a `street_agg_mult` on the BLUFF/semi-bluff merit ONLY (value unchanged): flop 1.0 (byte-identical
      invariant) → turn ~0.5–0.7× → river ~0.33× at pot (FIT SEEDS); polarization tightens flop 2:1 → turn 1:1 → river
      1:2. Street-scale the weak-draw agg bonus (full flop → cut turn → ~0 river) to fix F19. Add river bluff mass when
      the hand was a draw that bet the prior street (B7, via A4); prefer busted STRAIGHT draws over busted FLUSH draws
      (a provenance PROXY — validate via the LBR harness before treating as HARD). Optional `street_polarization` lever
      (maniac ≈ flat decline, nit steep).
      **Depends-on:** W3-a (A3/A4); W0-b D6 (turn-barrel%) live + directional before close (D7 gate).
      **Pass/fail:** the turn decision is no longer byte-identical to flop; `bluff_mass(river) < bluff_mass(flop)` for a
      fixed persona/bucket; a give-up line exists (checks back / folds air it would have barrelled); turn-barrel bands
      land in archetype ranges (D6). **No-gos:** heuristic only (no equity solve). **Appetite:** ~1 large slice.

- [ ] **W3-d — Made-hand vulnerability + texture brakes (B2 + B3, fixes F3-overcard-side + F20).** *ICE 7·6·4 — GROUNDED direction, magnitudes fit.*
      **Problem:** a vulnerable made hand doesn't slow down when overcards fall (F3); board texture affects only SIZING,
      never whether-to-bet (F20).
      **Solution:** (B2) on MIDDLE_PAIR / TOP_PAIR ONLY (NOT OVERPAIR_TPTK — it bundles overpairs), damp the bet merit by
      the count of overcards on board (0→×1.00, 1→×0.75, 2+→×0.50 FIT SEEDS; non-linear). (B3) multiply the whether-to-bet
      merit for one-pair by board wetness class (dry ×1.00 → high-two-tone ×0.85 → low-connected ×0.70 → monotone ×0.55
      FIT SEEDS; ordering asserted, magnitudes fit; a set still bets). Compose JOINTLY with B1 + multiway so multipliers
      don't stack into over-suppression. (The "barrel-MORE on scare cards" range side is DEFERRED to the villain-range
      pilot — NEXT.)
      **Depends-on:** W3-b (joint composition); D8 node-trace coverage.
      **Pass/fail:** made-pair bet-rate falls by overcard count for TAG/nit (by-overcard metric); one-pair bet-rate falls
      with wetness (ordering test); OVERPAIR_TPTK untouched. **No-gos:** gate strictly to the named buckets. **Appetite:** ~1 large slice.

### W3.5 — checkpoint (gates before the final re-anchor)

- [ ] **W3.5 — Human-realism playtest (D9).** Blinded seeded replays + short free-play, 2–3 poker-literate reviewers.
      **Pass/fail:** reviewers distinguish archetypes above chance AND flag no recurring persona-breaking lines; any
      flagged line feeds a fix before W4. Runs after W3, before the W4 re-anchor.

### W4 — highest regression risk, LAST

- [ ] **W4-a — Stack-depth commitment brake (B4, fixes F2).** *ICE 7·6·4 — HIGHEST regression risk → sequenced LAST.*
      **Problem:** pricing is pot-fraction only, no stack-depth term — a scared fish never folds an overpair below SPR 2.
      **Solution:** a multiplicative brake on FOLD merit keyed on commitment fraction `c = to_call/stack`, with a
      dead-zone `c₀≈0.25–0.35` (no-op when shallow-cost → byte-identical on deep-stack tests). It's an SPR-interaction
      term (NOT orthogonal to pot price) — compose with, don't replace, the fitted MDF/α price math (RES-D).
      **Depends-on:** the stabilized W2/W3 price/fold equation; **W3.5 (D9 playtest) — any flagged persona-breaking
      line fixed before this slice starts.** Core term `c=to_call/stack` is stack-based (no A1 needed); A1 only if it
      also uses a pot-before/SPR-safety component.
      **Pass/fail:** a TAG folds ~80%-stack King-high while still stacking off a set; aggression-factor/fold-to-cbet
      survive; `test_clamp_and_jam_edge` green. **No-gos:** scope to facing-fold merit only. **Appetite:** ~1 large slice.
      *(Commit-factor archetype spread: let W2-a's `call_looseness` carry nit-vs-station separation first; widen the `D`
      exponent only if the spread measures too weak.)*

- [ ] **W4-b — Single combined band re-anchor (D11) + coaching seam batch handoff (F1).** *ICE 8·8·6 — the ONE authoritative re-anchor.*
      **Problem:** mid-spine re-anchors aren't final (population coupling); coaching seams must be handed off coherently.
      **Solution:** the ONE authoritative combined WTSD/AF population-band re-anchor + coverage re-record after the whole
      spine converges; report the cumulative graded-coverage delta vs the immutable start snapshot; batch-file all
      accumulated seam-rows into `professional-teacher-rework` Next.
      **Pass/fail:** all six personas' bands hold with in-file justification; cumulative coverage delta adjudicated (not
      silently accepted); every mechanic slice has a filed seam-row. **No-gos:** no NEW behavior here — calibration +
      handoff only. **Appetite:** ~1 slice.

---

## NEXT — validated problems / committed items, not yet spec'd (ship a slice each)

> Direction is *indicated* (these are triaged, grounded problems) but NOT locked — the mechanic, magnitudes, and
> pass/fail belong to `/ai-dlc` slice planning when each is promoted to NOW. Treat the solution sketches as leads.

- **Villain-range rung (a) — coarse static preflop-range-by-position lookup (G1-a) — COMMITTED.** Give the engine a
  cheap, static, per-position preflop range *lookup* (data, not a solver — stays no-solver-compliant). Unlocks the
  **barrel-MORE-on-scare-cards** side of F3/B2 (currently deferred) and "you're facing a [type]" reads. Ships with its
  validation: **the LBR-style exploiter harness (D10)** + an offline Spearman equity-correlation check (the only
  non-circular way to validate a range/texture proxy without a solver) + a focused **range-proxy research pass (H1)**
  and **draw-equity proxy validation (H7)**. Source: build-out Track G1 rung (a), Track D10, Track H1/H7.
- **Preflop price/stack-aware responses (non-schema part).** Pass raise-size + effective stack + all-in state into the
  preflop sampler (new kwargs, default = today's behavior); author price-elastic response nodes. A min-raise vs a shove
  must produce different continue frequencies at the same `facing`. *(The opener-position axis needs a schema change →
  Later.)* Population coupling: re-anchor deferred to a combined pass, as in W4.
- **Coaching concept cards per landed mechanic (F2) → feed teacher-rework.** Point-of-need cards for: position/equity-
  realization, SPR/commitment, river polarity (bluff-catch vs thin value), board texture/overcards, barreling & give-up,
  persona elasticity. Each rides on a landed mechanic; concept cards only (no browsable library); EVs labeled approximate;
  grading behind the async `StrategyProvider`. Owned by `professional-teacher-rework`.
- **Cleaner GTO-baseline for grading (F3).** Feed the grounded GTO-baseline layer (the "A" layer of the two-layer frame)
  into the `StrategyProvider` so grading reflects sounder baselines.
- **`tanh` soft-saturation aggression (M1, code + deferred content half).** Replace the hard 5.6 cap so a higher lever
  still strictly orders maniac above LAG at every merit; calibrate to observable AF, not lever magnitude. The maniac
  `aggression` re-author deferred from P1 lands here.
- **Split `aggression` into value/bluff × bucket × street (M4/F6).** One scalar multiplies every non-bluff bucket's raise
  merit uniformly; separate `value_agg` (made ≥ TOP_PAIR) from the bluff term.
- **Graded SPR-commit curve (M6/F8).** Smooth commitment over (spr_commit − live SPR) × equity × draw × street, per-persona
  commit strength; keep TPTK able to fold rivers. *(Partly complemented by W4-a's fold-side brake — spec the boost-side here.)*
- **Value/bluff/street/texture sizing overrides (N6).** Permit sizing overrides **respecting the anti-sizing-tell no-go**.
- **Bucket/kicker granularity (N4).** Kicker strength, relative-nut class, board vulnerability. *(Blocker/combinatorics is Later.)*
- **Same-street 3bet+ under-folds (N2-claude).** Fix the acknowledged `:468-474` path if the memory rework touches it.

## LATER — bets (problem · confidence · assumption to test) — the deferred / architecture tail

- **Villain-range rungs (b) + (c) (G1-b/c).** (b) persona-conditional range prior updated by the betting line — medium;
  (c) full equity-vs-range estimator — the only NO-GO-ADJACENT rung vs "no solver tables". **Confidence: med/low.** Assumption:
  whether rung (a) realism is enough, or the barrel-more/exploit payoff justifies climbing. Decide the rung at promotion.
- **Exploit-coaching in-program ("you're facing a [type], here's how to adjust") (F4).** *High-level placeholder — the owner
  wants this eventually.* Teach the hero to adjust vs each archetype (vs a station value-bet thinner / never bluff; vs a nit
  fold to aggression). **Depends on:** villain-range rung (a) exposed to the grader **+ a new research pass for adjustment
  magnitudes (H2)** — the grounding research explicitly deferred exploit-coaching. **Context/source docs:**
  `persona-realism-FULL-BUILDOUT.md` Track F4 + Track G1; audit `§10.5` + `§9.2` (coaching-scope = baseline+behavior only
  this pass); studies RP1/RP8. **Confidence: med.** Assumption: the coaching payoff justifies the villain-range + research cost.
- **Blocker / combinatorics awareness on the river (G2).** A hand representation richer than the 7-rung strength ladder so
  river value/bluff selection can use blockers/removal (the dominant modern river factor). **Confidence: low.** Assumption: a
  rank-only engine's river ceiling is unacceptable. (No "% of benefit" figure — that unsupported claim was struck.)
- **Multiway theory beyond a 4-way tier (G3).** Calibrated 5+way adjustments. **Confidence: low** (solver support for 3+way is
  thin; 5-way ≈ 1.6% of hands). Direction-only until researched (H5).
- **Out-of-position equity-realization damp (B11).** An OOP facing-continue / bluff-catch realization damp (the R-factor's
  effect on CALLING, not just betting). **Confidence: med.** Deferred — risks colliding with the W4 commitment brake +
  faced-price defense; revisit after the position/street bands settle. Do NOT claim W3-b already represents it.
- **Delayed c-bet / probe / stab frequencies (B12).** Checked-prior-street stab lines. **Confidence: low** — solver-sanctioned
  but published only qualitatively; needs a research pass (H4) for numbers. Reuses A2 + A3 machinery once those land.
- **Opener-position-aware preflop defense (E1) + limper-count ranges (E3).** BB defends ~3–3.5× as wide vs a BTN open as vs a
  UTG open. **Confidence: med.** Deferred — needs a `content/models.py` schema change (opener-position axis on `vs_rfi`) +
  sampler plumbing (A5/A6) + an Alembic-style data-shape migration + new tests. Owner gate.
- **Persona sub-types (multiple packs per archetype) (F5).** `VillainType` is enum-locked. **Confidence: med.** *Direct enabler
  for Hidden-persona mode, not for realism per se* — sequence it WITH that mode, not here.
- **Reference-pool recalibration (H6).** If the target pool ever changes from "online low-mid 9-max ~100bb," the whole keystone
  (archetype stat table) needs recalibration. **Confidence: n/a** — a conditional trigger, not a planned build.
- **Solver-boundary revisit for kicker/equity precision (N4/N5 ceiling).** **Confidence: low.** Assumption: whether
  "simplified-but-winning" heuristics suffice, or this is the trigger to revisit the no-solver line. EVs stay *approximate* either way.
- **Rigorous semi-bluff F\* fold target (from W2-b).** W2-b shipped a *directional* below-T1 fold policy (existing price-
  aware fold merit stands) after both reviewers flagged the roadmap's "fold merit ≈ F\*" as conflating the OPPONENT's
  required-fold frequency with the BOT's own fold probability. A principled version would define the bot's own below-T1
  fold target q from a justified model and set fold merit last as `q/(1-q)·Σ(nonfold merits)` (the closed form both
  reviewers derived). **Confidence: low.** Assumption: whether the directional policy is realistic enough, or a
  defensible q model is worth the machinery. Pairs with the draw-equity proxy calibration (H7).

---

## Global out-of-scope / NO-GOS (inherited invariants — doc 12 §6.3)

- **No solver tables** — heuristic + interim EV only; EVs labeled *approximate*. *(Villain-range rung (a) is a static data
  lookup, NOT a solver — it stays inside this line; rung (c) is the no-go-adjacent one.)*
- **Grader untouched** — do NOT edit `grade_map*.py` / `postflop.py` graders; `spot_signature()` + `TAXONOMY_VERSION` stay
  **frozen** (they're the grader's, not the bots'). Blast radius = bot side only.
- **Domain purity** — `personas.py` / `personas_postflop.py` stay pure domain (no web/DB imports).
- **Action draw stays the FIRST `rng.choices`** — `range_estimate.py:278` replays it via a capture-rng; any new randomness
  comes *after* the action draw (F2 two-stage bluff-sizing is the template).
- **New args default to today's behavior** (mirror `is_aggressor=False`) so `range_estimate` + the population harness stay
  byte-identical until the live loop deliberately opts in.
- **Softmax law** — every magnitude is fit-to-observed-stat, not a drop-in constant (no cosmetic changes).
- **Re-anchor bands levers-first, ONCE per cluster** — tune pack levers before widening test bands; the ONE authoritative
  combined re-anchor is W4; widen only with in-file justification.
- **Re-record `coverage_baseline.json` deliberately** with each play-changing slice + report cumulative delta vs the
  immutable snapshot; any cumulative loss needs explicit adjudication.
- **Anti-sizing-tell** — value hands must not become size-readable (`test_sizing_spread_no_deterministic_strength_to_size`);
  F14 is an INTENTIONAL-LEAVE, do not "fix" it.
- **INTENTIONAL-LEAVE** — F12 (aggression cap compresses strong hands — a deliberate RES-D saturation fix) + F14 (sizing
  decoupled from strength on purpose). Do NOT "fix" these.
- **`test_bluff_ordering_across_personas_at_fixed_size`** pins `station < nit < fish < tag < lag < maniac` — any bluff-path
  change re-anchors it deliberately.
- **The architectural line** — range-blindness (F16) is currently by design. The barrel-more range side, exploit-coaching,
  and villain-range rungs (b)/(c) push against "no solver tables"; building them past rung (a) is an owner-gated architecture
  decision, not a bug-fix.

---
*Handoff: on approval, the top unchecked NOW slice (W0-a) goes to `/ai-dlc` for per-feature planning. One slice at a time;
re-read pass/fail state between slices (agents falsely mark work done); fresh `refuter` at each fan-in.*
