# Persona Realism — Roadmap (created 2026-07-23)

> Living, pass/fail, resumable. A fresh context reads this + doc 12 and knows exactly what's left.
> **Engine contract map (READ FIRST):** `docs/research/12-persona-engine-and-realism-fixes.md`
> — every lever, merit table, formula, line anchor, and INVARIANT. This roadmap is the *decomposition*;
> doc 12 is the *reference*. Review record: `docs/ai-dlc/research/RES-J-persona-realism.md`.
> Parent roadmap: `docs/ai-dlc/roadmap/simulate-table.md` (its NEXT "Persona realism" bullet points here).
>
> **Scope (locked 2026-07-23 interview):** **Core realism fix** — correctness patches + the
> street-aware refactor + the stickiness split + position/size-aware preflop responses. We STOP
> before the deep-judgment tier (kicker granularity, price-vs-equity, sub-types) — those are Next/Later.
>
> **Resume rule:** work waves in order; verify a slice's pass/fail ACTUALLY passes before `[x]`
> (agents falsely mark work done). Hand ONE slice at a time to `/ai-dlc`. Every slice gets a fresh
> `refuter` at fan-in (maker ≠ checker).

---

## North-star outcome — the WHY

- **Primary:** *the six villain bots make decisions that match their real-world archetype* — so the
  Simulate table teaches transferable reads instead of training the hero against unhinged, streetless bots.
  **Metric:** each persona's computed facing-a-bet distribution (the doc-12 §4/§9.2 regeneration) matches
  its archetype's documented shape — polarized rivers, archetype-correct fold-to-size elasticity, no
  off-archetype open-limps, no literal no-pair-no-draw calls.
  **Baseline (measured, doc 12):** maniac raises one pair on the river 38–54% and calls busted air 23%;
  station calls pure air 78%; fish & station differ only by a uniform stickiness shift (no shape
  difference); every response node is position/size-blind. → **Target:** river raises come only from
  `TWO_PAIR_PLUS+` / bluff-cell; air-call ≈0 without a draw; station fold-rate ≈flat across bet sizes while
  fish is fit-or-fold; bots answer a UTG open differently from a BTN open. All six personas.
  **Runnable metric (Codex-Sol F2 — "regenerate the tables" is not yet a real gate):** the north-star's
  actual acceptance test is a **committed persona-distribution test module** with fixed hole/board/legal/
  history contexts and explicit numeric thresholds + tolerances, asserting per persona: river bucket→action
  distributions, size-response slopes (fold-rate vs bet size), positional/price preflop deltas, and
  conditional barrel/give-up rates. Each slice below adds its assertions to it — that suite, not prose like
  "≈0 / roughly flat", is what "matches its archetype" means. Population VPIP/PFR/AF/WTSD stats stay a
  **secondary** regression check, never the north-star substitute.

## Why this is one initiative, not six persona fixes

The **same two root causes** drive every symptom (doc 12 §5, §9): (1) the postflop engine is
**street-blind / memoryless** — flop = turn = river given the same bucket; (2) single scalars
(`stickiness`, `aggression`) each do **two jobs**. So the fixes below repair **all six personas at
once**; the aggressive three (maniac/LAG/TAG) are just where the river damage is loudest.

---

## NOW — spec-ready vertical slices (ICE = Impact·Confidence·Ease, 1–10)

### Wave plan
**W1** P1 → **W2** P2a ‖ P4 → **W3** P3 → **W4** P2b → **W5** final calibration pass.
P2a/P3/P2b all own `personas_postflop.py` ⇒ they run **serially** on the postflop-engine spine.
**Order is deliberate (Codex-Sol challenge):** P2a first (the headline river fix) → **P3 before P2b** so
the `_price_factor`/facing-fold equation is stabilized *before* P2b layers a scare-card multiplier on it
(P2b-then-P3 would force re-tuning P2b's scare weights).
**P4 owns `personas.py` (preflop) — engine side runs parallel** to the postflop spine; but P4 edits the
`preflop` array in the six packs (different JSON keys than P2b/P3's `postflop` lever block, so low merge
risk) AND **shifts which ranges reach postflop** ⇒ the AF/WTSD/fold-to-cbet population calibration is NOT
final until P4 lands. **W5 is a single combined re-anchor + coverage re-record** after both the postflop
spine and P4 converge (see "Baseline & calibration discipline" below) — do NOT treat any mid-spine
re-anchor as final.
P1 lands the shared `_CALL_BASE` edit (A1) + all content, so it precedes everything.

### Range-estimator parity — a NON-NEGOTIABLE for every opting-in slice (Codex-Sol HIGH)
`range_estimate.py:278` recovers the villain's action distribution by **replaying the persona policy** with
a capture-rng. Doc 12 §6.3's "keep `range_estimate` byte-identical" is correct **only for un-opted-in direct
callers**. The moment P2a/P2b (street/history) or P4 (price/stack/position) make the **live** bot diverge
from the streetless policy, the estimator MUST be threaded the **same** context and re-tested for **parity
with the live policy** — otherwise the villain-range reveal feature (R1) infers polarized river actions
through the stale streetless model and silently lies. **Each of P2a/P2b/P4 owns extending `range_estimate`'s
replay context + a parity test** (live-policy `choices` distribution == estimator's recovered distribution).
The action draw stays the FIRST `rng.choices` regardless (§6.3).

### Baseline & calibration discipline (Codex-Sol MED — anti-laundering)
Re-recording `coverage_baseline.json` every slice replaces the comparator, so a small graded-coverage loss
repeated across slices can vanish even if the initiative regresses net. Rule: **snapshot an immutable
initiative-start baseline** (`coverage_baseline.persona-realism-start.json`) before P1; each slice still
re-records the operational fixture for CI green, but **also reports the CUMULATIVE graded-coverage delta vs
the immutable snapshot**, and any cumulative loss needs explicit adjudication (not silent acceptance). The
W5 pass does the ONE authoritative combined population-band re-anchor after P4 + the spine converge.

---

- [ ] **P1 — Correctness patch: fold-aces, open-limps, oversized 3bet, air-calls, overlap guard.**
      ICE 8·9·8. *(bundled quick wins — ships in days; one deliberate re-baseline)*
      **Problem:** several outright bugs make bots visibly "unhinged" independent of the deep engine
      flaws — the station folds AA/KK/AKs 40% unopened (B1), maniac & LAG open-limp every seat (M3),
      maniac 3-bets 24.75bb (**N4/N5** — doc 12 §9.3; NOT §5's unrelated bucket-collapse "N4", which is
      deferred to this roadmap's NEXT), every persona calls literal no-pair-no-draw (A1), maniac's
      4bet/5bet is *tighter* than LAG's (N3), and authored mixes are silently shadowed (N2).
      **Outcome-link:** removes the loudest off-archetype behavior before the structural work.
      **Solution (content + one shared-table edit + a validator):**
      - **B1** `calling_station.json` — change the premium `unopened` `{raise .6, fold .4}` to
        `raise`/`limp`/`call` (station never folds premiums first-to-act).
      - **M3** delete the **non-SB open-limp** mixes for `maniac.json` + `lag.json` (raise-or-fold archetype).
      - **N4/N5** drop maniac `threebet_mult` 5.5 → ~3.0–3.5 (24.75bb → ~13–16bb).
      - **N3** rebuild maniac `vs_3bet`/`vs_4bet`: wider 4bet value+bluff split + light 5bet-shove bluffs
        (Axs/small-pair), so maniac re-jams *lighter* than LAG, plus a few KK/AA flats for traps.
      - **M1 (content half)** re-author maniac `aggression` 15.0 → a meaningful value **at/below** the
        5.6 cap. *(Framing, per Codex-Sol F4: this is **representation cleanup** — documenting that the 15.0
        is dead above the cap — NOT a behavioral-correctness fix; if the effective value stays ~5.6 the
        played behavior is unchanged. Kept in P1 as a low-risk cleanup. The soft-saturation `tanh` variant
        that actually changes behavior is Next.)*
      - **A1 (shared table)** in `personas_postflop.py` lower `_CALL_BASE[AIR]` ~0.25 → ~0.05–0.10 and
        gate any air-continue behind a real draw (`_DRAW_CALL_BONUS`). **Ownership boundary (Codex-Sol F4):
        A1 is STREET-NEUTRAL** — it drops the *base* air-call merit on every street. The **river-specific**
        "air-call ≈0" gate is **P2a's** (street-aware), not P1's — P1 must not encode river logic. So P1's
        pass/fail asserts the *base* air-call drop (air folds far more to a bet on a no-draw board);
        P2a asserts the additional river-zero gate.
      - **N2** add a content validator rejecting **overlapping combos across mixes in a node**
        (first-match-wins makes later overlaps unreachable — pairs with the B1 premium-fold check).
        **Ordering:** run the validator AFTER N3's maniac rebuild so it self-checks the new mixes for
        introduced overlaps.
      **Pass/fail:** station never folds AA/KK/AKs unopened (test); no persona has a non-SB open-limp mix
      (validator test); maniac `threebet_mult ≤ 3.5`; maniac 5bet-shove range ⊋ LAG's (wider, test); a
      no-pair-no-draw river spot folds air ≥ ~0.9 to a medium bet (regenerate §4 dist); overlap validator
      rejects a synthetic overlapping-combo pack; population bands re-anchored **with in-file justification**
      + `coverage_baseline.json` re-recorded (§6.3); `verify.sh` + `ruff` green.
      **Appetite:** ~1 small epic. **No-gos:** no engine-signature change here (that's P2/P4); no solver
      ranges; no grader/`spot_signature()` touch; keep the anti-sizing-tell overlap.

- [ ] **P2a — Street-aware refactor: thread `street` + polarize the river.** *(THE keystone)*
      ICE 9·7·5. *(fixes M2 + M7 — the user's #1 complaint "maniac over-calls the river / weird choices")*
      **Problem:** the postflop engine takes **no street argument** — flop = turn = river given the same
      bucket (doc 12 §2.4, `:381`). So the maniac raises one pair on the river for "value" (MP 38% / TP 54%),
      LAG/TAG raise one pair 40%/32%, and busted air still calls — rivers should be **polarized** (nuts or
      bluff, never a medium made hand).
      **Outcome-link:** the single change that makes rivers realistic for **all six** personas.
      **Solution:** add a `street` kwarg to `sample_postflop_decision` (derive from `len(board)` at the
      live loop) with a **default that reproduces today's behavior** (mirror `is_aggressor=False`, §6.2).
      On the **river**: floor `_RAISE_BASE[MIDDLE_PAIR]` and `[TOP_PAIR]` to ≈0 (medium hands
      bet/check/call, never raise) and hold air calls near zero.
      **⚠️ Boundary decision (Codex-Sol F7 — internal inconsistency to resolve at `/ai-dlc`):** the stated
      "river raises only from `TWO_PAIR_PLUS+` / bluff-cell" is NOT achieved by flooring MP/TP alone —
      `OVERPAIR_TPTK` keeps a positive shared raise merit (`_RAISE_BASE=0.25 × agg`, and the maniac raises it
      at 5.6×). Decide explicitly whether an overpair/TPTK is "river medium-strength" (thin value → floor it
      too) or a legitimate river value-raise (keep it) — and make the mechanic match the stated boundary.
      Do NOT pull M4/kicker-split into NOW to resolve this; it's a coarse policy gate.
      The live loop (`sim_session.py` / `table/play.py`) opts in; then re-baseline.
      **Estimator parity (Codex-Sol F1 — P2a OWNS this):** when the live loop passes `street=`,
      `range_estimate.py` must ALSO pass it (extend its replay context with street) + a parity test proving
      the estimator's recovered river distribution matches the live polarized policy. "Byte-identical"
      applies only to un-opted-in direct callers, NOT to the reveal feature.
      **Pass/fail:** (a) **default-off (direct callers, no `street=` kwarg)** ⇒ `test_personas_postflop.py`
      byte-identical (verified no `street=` call sites there); (b) **street-on (via `table/play.py` AND
      `range_estimate.py`)** ⇒ maniac river MIDDLE_PAIR raise ≈0 (was 38%), TOP_PAIR raise ≈0 (was 54%),
      LAG/TAG one-pair river raise ≈0, river raises only from the class the boundary-decision permits
      (regenerate §9.2 dist); **estimator-parity test green** (recovered dist == live dist on a river spot);
      `coverage_baseline.json` re-recorded + cumulative-delta reported vs the immutable snapshot; action draw
      still the FIRST `rng.choices` (§6.3); `verify.sh` green.
      **Appetite:** ~1 large epic. **No-gos:** no scare-card term yet (P2b); no bluff-decay yet (P2b); don't
      insert a new `rng` draw before the action `choices` (breaks `range_estimate` — §6.3).

- [ ] **P2b — Memory term: scare-card fold + per-street bluff decay + give-up.**
      ICE 7·7·4. *(**W4 — after P2a AND P3**: needs P2a's `street` arg + P3's stabilized facing-fold
      equation, so scare weights are tuned against the final `_price_factor`, not re-tuned later)*
      *(fixes F3/N3 + the M5 remainder)*
      **May split at `/ai-dlc` (Codex-Sol F5):** scare-card **folding** (a facing-fold-merit multiplier) and
      bluff **decay/give-up** (initiative/history-conditioned *betting*) have different inputs, paths, and
      failure modes — treat as two sub-slices (P2b-i scare-fold, P2b-ii barrel-decay/give-up) if the
      contract scan says so.
      **Problem:** even with street threaded, the engine has no **fear response** and no **give-up** model:
      `bluff_mass` is identical flop = turn = river (doc 12 §5 F3/M5), so the nit can't "run scared when an
      overcard hits the turn" and the maniac barrels air at the same rate on every street.
      **Outcome-link:** the documented nit "one-and-done barrel fold" + realistic declining bluff frequency.
      **Solution:** thread prior-street bucket + **prior aggression** into the facing-fold term; add a
      **scare-card multiplier** (new overcard / flush- or straight-completing card / paired board) on the
      fold merit for pair-class buckets, with **persona-specific sensitivity** (strong for nit/fish,
      near-zero for the inelastic station); **decay `bluff_mass` per street** + explicit give-up /
      continuation logic keyed to prior aggression + runout. **Define "prior aggression" up front
      (Codex-Sol F5):** it means *this bot's own prior-street action + whether it holds initiative* (NOT the
      opponent's aggression) — pin the exact history projection before coding.
      **Estimator parity (Codex-Sol F1):** history-conditioned live behavior means `range_estimate` must be
      threaded the same prior-street/initiative context + a parity test (same as P2a).
      **Pass/fail:** nit folds top pair more on a turn overcard than on a blank turn (direction test);
      station scare-sensitivity ≈0 (near-flat, test); for a fixed persona/bucket `bluff_mass(river) <
      bluff_mass(flop)` (test); a give-up line exists (bot checks back / folds air it would have barrelled);
      estimator-parity test green on a history-conditioned spot; bands re-anchored with justification;
      coverage baseline re-recorded + cumulative-delta reported; `verify.sh` green.
      **Appetite:** ~1 large epic. **No-gos:** heuristic scare term only (no equity solve — that's Next N5);
      keep the default-off byte-identity for un-updated direct callers until the live loop opts in.

- [ ] **P3 — Split `stickiness` → `call_looseness` + `size_elasticity`.**
      ICE 8·7·5. *(**W3 — after P2a, BEFORE P2b**: stabilize the `_price_factor`/facing-fold equation first
      so P2b's scare multiplier is layered on the final equation, not re-tuned — Codex-Sol F5. Street-neutral,
      so it does not depend on P2a's street logic, only on the shared `personas_postflop.py` spine order.)*
      *(fixes F1/M8 — the defining fish/station flaw)*
      **Problem:** one dial controls **both** how loose a persona calls **and** how much bet size scares it
      (doc 12 §5 F1: flat CALL multiplier `:484` **and** the price-fold exponent `:377`). So you can't make
      the **station inelastic-but-loose** (calls regardless of size) while the **fish is elastic-but-scared**
      (fit-or-fold) — the one axis that *defines* the difference is welded shut. Both currently swing
      fold-rate ~4.7× SMALL→OVERBET.
      **Outcome-link:** fish and station finally differ in **shape**, not just a uniform stickiness shift.
      **Solution:** add two optional levers — `call_looseness` (the flat CALL multiplier) and
      `size_elasticity` (drives the `price_factor` exponent, decoupled from looseness); default = today's
      `stickiness` behavior for unauthored packs. Prefer a **continuous** faced-size function over the 4
      abrupt α buckets. Set station `size_elasticity ≈ 0` (near-flat) + high looseness; fish high elasticity
      + moderate looseness. **Update the monotonicity pins to the new levers** while keeping the directional
      guarantees.
      **Pass/fail:** station fold-rate roughly **flat** across SMALL→OVERBET (elasticity≈0, test); fish
      fold-rate rises steeply with size; `call_looseness↑` never lowers call freq; fold monotone in faced
      size + respects the α ceiling (updated pins); persona-ordering test re-anchored **deliberately**; bands
      re-anchored + baseline re-recorded; `verify.sh` green.
      **Appetite:** ~1 large epic. **No-gos:** don't break the monotonicity/α-ceiling invariants (§6.3);
      keep default-off byte-identity for the un-split packs until re-baselined.

- [ ] **P4 — Position/size/stack-aware preflop responses.**
      ICE 7·6·4. *(owns `personas.py` — runs PARALLEL to the P2/P3 postflop spine on the ENGINE side)*
      *(fixes N1/N2-pf)*
      **⚠️ Content dependency on P1:** P4 position-splits the SAME `vs_3bet`/`vs_4bet` pack nodes that
      P1's N3 rebuilds for maniac/lag. The wave plan already serializes P1 (W1) before P4 (W2), so there's
      no concurrency conflict — but a P4 implementer must **build on P1's rebuilt value/bluff mixes, not
      re-litigate N3**. `PersonaNode.positions` already exists in the schema (verified) ⇒ P4 is a
      content-authoring exercise, NOT a content-model change; the "default = today's behavior" claim scopes
      only to `sample_preflop_action`'s function signature.
      **Problem:** `sample_preflop_action` sees only categorical `facing` (doc 12 §5 N2-pf / §9.3 N1,
      `personas.py:61`): a TAG answers a UTG open exactly like a BTN open, and a min-raise exactly like an
      all-in. Real continue frequency is **position-, price-, and stack-sensitive** — this is the
      "not playing within their range realistically" feel.
      **Outcome-link:** preflop responses that respect position and price, on a separate engine from the
      postflop keystone.
      **Solution:** pass **raise size + position + effective stack + all-in state** into the preflop sampler
      (new kwargs, default = today's behavior so existing callers stay byte-identical); author
      **position-split** + **price-elastic** response nodes for `vs_rfi` / `vs_3bet` / `vs_4bet` across the
      six packs. The live loop (`sim_session.py`) opts in.
      **⚠️ NOT cleanly parallel — population coupling (Codex-Sol F3):** P4 changes *which ranges and pot
      types reach the flop*, so the postflop AF/WTSD/fold-to-cbet calibration done in the P2/P3 spine is
      **not final** until P4 lands. P4's pack edits are the `preflop` array (different JSON keys than the
      spine's `postflop` block → low merge risk), but the **population re-anchor + coverage re-record is
      deferred to the W5 combined pass** after BOTH P4 and the spine converge — do not re-anchor bands
      "final" mid-spine.
      **Estimator parity (Codex-Sol F1):** when the live loop passes price/stack/position, `range_estimate`'s
      preflop path must be threaded the same context + a parity test — else the preflop range read diverges
      from the price/stack-aware live policy.
      **Pass/fail:** a TAG facing a UTG open continues **tighter** than vs a BTN open (direction test); a
      min-raise vs a shove produce **different** continue frequencies at the same `facing` (test);
      default-off ⇒ existing preflop tests byte-identical; preflop estimator-parity test green; VPIP/PFR
      bands still hold for all six personas (checked in the W5 combined pass); **coverage baseline re-recorded
      — P4 DOES change the played stream** (Codex-Sol F6 — it was missing this); `spot_signature()` untouched
      (grader's, not the bots'); `verify.sh` green.
      **Appetite:** ~1 large epic. **No-gos:** no solver ranges; no signature-dim renumbering; keep the
      first-match-wins semantics (author non-overlapping nodes — P1's validator guards this).

---

## NEXT — validated problems, not yet spec'd (deeper realism; ship a slice each when core lands)

- **M4 / F6 — Split `aggression` into value/bluff × bucket (× street).** One scalar multiplies every
  non-bluff bucket's raise merit uniformly (5.6× hits weak made hands the same as monsters); also shrinks
  nit MONSTER value-betting. → `value_agg` (made ≥ TOP_PAIR) separate from the bluff term; or scale
  `_RAISE_BASE` by rung.
- **M6 / F8 — Graded SPR-commit curve.** Binary cliff + identical 3.0 boost for all personas; a scared fish
  never folds an overpair below SPR 2. → smooth commitment over (spr_commit − live SPR) × equity × draw ×
  street, per-persona commit strength; keep TPTK able to fold rivers.
- **M1 (code half) — Soft-saturation (`tanh`) aggression** so a higher lever still strictly orders maniac
  above LAG at every merit (replaces the hard 5.6 cap; calibrate to observable AF, not lever magnitude).
- **N6 — Value/bluff/street/texture sizing overrides.** Fish & station share identical own-sizing. →
  permit sizing overrides **respecting the anti-sizing-tell no-go** (F2 two-stage factorization is the template).
- **N5 — Faced price meets hand equity / draw odds.** Bet size scales `_FOLD_BASE` alone; a gutshot and a
  flush draw defend through the same generic mechanism. → coarse pot-odds-vs-outs, then persona deviations.
- **N4 — Bucket/kicker granularity.** All top pairs share TOP_PAIR; every set/straight/flush is one MONSTER
  blob; king-high lumps into ACE_HIGH. → kicker strength, relative-nut class, board vulnerability, blockers.
- **N2-claude — Same-street 3bet+ under-folds.** Acknowledged in-code (`:468-474`); fix if the memory rework
  touches that path.

## LATER — bets (problem · confidence · assumption to test)

- **F5 — Persona sub-types (multiple packs per archetype).** `VillainType` is enum-locked (one
  `passive_fish`/`calling_station` slot; loader raises on duplicates). Separate a stable `profile_id` from a
  broad `archetype`. **Confidence: med.** *This is the direct enabler for **Hidden-persona mode**, not for
  realism per se* — assumption to test: sub-types are wanted **before** Hidden-persona ships. Sequence it
  **with** that mode, not here. (Review-by: when Hidden-persona mode is scoped.)
- **Solver-boundary revisit for N4/N5.** Heuristics hit a ceiling on kicker/equity precision.
  **Confidence: low.** Assumption to test: whether "simplified-but-winning" heuristics are enough, or this is
  the trigger to revisit the solver-baseline no-go. EVs stay labeled *approximate* either way. (No hard date.)

---

## Global out-of-scope / NO-GOS (inherited invariants — doc 12 §6.3)

- **No solver tables** — heuristic + interim EV only; EVs labeled *approximate*.
- **Grader untouched** — do NOT edit `grade_map*.py` / `postflop.py` graders; `spot_signature()` +
  `TAXONOMY_VERSION` stay **frozen** (they're the grader's, not the bots'). Blast radius = bot side only.
- **Domain purity** — `personas.py` / `personas_postflop.py` stay pure domain (no web/DB imports).
- **Action draw stays the FIRST `rng.choices`** — `range_estimate.py:278` replays it via a capture-rng; any
  new randomness comes *after* the action draw (F2 two-stage bluff-sizing is the template).
- **New args default to today's behavior** (mirror `is_aggressor=False`) so `range_estimate` + the population
  harness stay byte-identical until the live loop deliberately opts in.
- **Re-anchor bands levers-first** — tune pack levers before widening test bands; widen only with in-file
  justification (RES-D §4 is the precedent).
- **Re-record `coverage_baseline.json` deliberately** with each play-changing slice; verify graded coverage
  did not regress.
- **Anti-sizing-tell** — value hands must not become size-readable
  (`test_sizing_spread_no_deterministic_strength_to_size`).
- **`test_bluff_ordering_across_personas_at_fixed_size`** pins `station < nit < fish < tag < lag < maniac` —
  any bluff-path change must re-anchor it deliberately.
- **F5 sub-types are Later**, coupled to Hidden-persona mode — not this initiative.

---
*Handoff: on approval, the top NOW slice (P1) goes to `/ai-dlc` for per-feature planning. One slice at a time.*
