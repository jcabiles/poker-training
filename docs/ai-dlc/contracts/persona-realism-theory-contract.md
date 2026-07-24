# Persona-Realism Theory Contract

**Status:** Committed engineering artifact. The single authoritative "theory contract" for the persona-realism rework (the Simulate bot decision engine — `backend/app/domain/personas_postflop.py` + `personas.py`, driven by `table/play.py`).

**Precedence:** where the source docs disagree, `persona-realism-artifacts/RECONCILE.md` (the lead's correction ledger) WINS, and the build spec `persona-realism-audit-2026-07-24.md` §10 applies its corrections. This contract encodes the reconciled result. Every magnitude below traces to a source doc + section; anything I could not confirm is tagged `[UNVERIFIED]`.

---

## 1. Purpose & how to use

This doc is **dual-use**:
- **Worker brief (front-load):** injected into an implementer's brief before a persona-realism slice. Tells them the grounded math, the exact gate/boundary of their mechanic, the target stat, and the HARD-vs-directional status of their acceptance criterion.
- **Reviewer rubric (fan-in):** the theory-reviewer applies §11 to a slice's output to render a pass/fail on adherence to the grounded math/theory/framework.

It is a **rubric, not a re-derivation.** It points to the source docs for depth and does NOT replace them. For any magnitude's derivation open §10.1's cited block; for *why* a correction was made open RECONCILE. Do NOT re-run the research or re-derive numbers — both are DONE and captured (FULL-BUILDOUT §7).

**Reference pool (governs the WHOLE stat table):** online low-mid 9-max ~100bb; idealized-distinct caricatures; baseline + villain-behavior only (audit §9.2 / RECONCILE line 7). The entire keystone stat table is pool-specific — see §10.

---

## 2. The softmax law (NON-NEGOTIABLE — the anti-cosmetic-change rule)

The engine clamps each candidate merit ≥0, **normalizes by the sum**, then draws via `rng.choices`. **A merit multiplier is therefore NOT the observed frequency change.** (audit §10.0 "How to read EVERY number"; RECONCILE cross-package note 1; roadmap "Softmax law").

Concrete re-derivation (RECONCILE RP1-S1 / audit §10.0): a 1.2×/0.75× IP/OOP merit on a TAG mid-pair (base P(bet) ≈ 0.507) yields an **observed** split of only **~1.27×**, NOT the "1.5–1.8×" a naive odds-space read expects. A ×0.50 overcard-damp merit on a TAG mid-pair yields **~34%** observed bet-rate, not 25%; on TOP_PAIR (base 74.6%) → **~59.5%**, barely −15pts (RECONCILE RP2-S2 / audit §10.1-P2c).

Two binding consequences:
1. **Every magnitude is a FIT SEED, tuned to a target measured stat — never a drop-in constant.** State the target as an observed closed-loop stat (a CBet split, an AF, a WTSD), then fit the multiplier to hit it. A quoted factor is a *starting shape/direction*, not the answer.
2. **Strong/saturated buckets barely move.** Normalization means a big multiplier on an already-dominant candidate (top-pair P(bet) ≈ 0.95) shifts the observed rate a few points at most. **The effect lives in the marginal / air / draw region.**

**Failure mode (a reviewer MUST reject this):** dropping `×0.75 / ×0.50` (P2) or a flat `×0.25` fold reduction (P6) into the code *as-is* and closing the slice ships a **cosmetic** change — the observed stat has not been fit. No slice closes on "the constant is in the code"; it closes on "the observed stat hit its target band" (roadmap D7 metric-DoD gate).

---

## 3. Semi-bluff EV identities (`[SOLVED]` — confirmed by independent re-derivation, RECONCILE RP3 / audit §10.1-P3a)

Jam `B` into pot `P`, where **P = pot BEFORE the jam** (see §7 denominator unification), equity-when-called `E`.

- **T1 — value-commit threshold** (zero fold-equity is OK; jam is committable):
  `E ≥ B / (P + 2B)`
- **T2 — required realized fold equity** (when below T1):
  `F* = (B − E·(P+2B)) / (P + B − E·(P+2B))`, collapsing to the classic `B/(P+B)` at `E=0`.
- **T3 — pure-call break-even:** `E ≥ B / (P+B)`. Note **T1 < T3 always** (a jam is committable at lower equity than a call).

**Corrected 3×-pot threshold (RECONCILE RP3 "T1 3×-POT EXAMPLE ARITHMETIC — WRONG" / audit §10.1-P3c):**
B = 3P ⇒ `3P/(P+6P) = 3/7 = ` **42.9%**, NOT 60%. The 60% figure is the α / fold-ceiling for a 1.5× bet, not T1 for a 3× jam. **RECONCILE corrected this — 42.9% is authoritative; never write 60% for the 3×-pot T1.** The F5/F6 illustration survives: a flush draw at E ≈ 0.35 < 0.429 fails T1 ⇒ keeps fold mass — but the number reads 42.9%.

**Bettor bluff-share formula (RECONCILE RP5-S5 — lead OVERRULED Sol / audit §10.1-P5c):** the bettor's optimal bluff share of a value bet is
`s / (1 + 2s)` (where `s` = bet-as-fraction-of-pot).
This gives ½=25%, ⅔=28.6%, pot=33%, 2×=40%. **RECONCILE explicitly overruled Sol's accusation that RP5 used the defender form `s/(1+s)`** (which would give 33/40/50/66.7%). RP5's theory is CORRECT — do NOT "fix" it to the defender form. The only wording correction: the engine's `_BUCKET_BLUFF_SHARE` is 4 coarse representatives (SMALL=.20, MED=.27, LARGE=.32, OVERBET=.375), "directionally consistent with `s/(1+2s)`, coarsened to 4 representatives" — NOT "exact match at every size." No engine table change.

---

## 4. Lever → finding map with boundaries

Each row: the mechanic, the finding(s) it fixes, its EXACT gate/boundary, and HARD-vs-DIRECTIONAL status (per §5/§10.3 measurability). Source: audit §10.1 + FULL-BUILDOUT §2. **Boundaries are load-bearing — a reviewer checks the mechanic's gate against this column.**

| Mechanic (P#) | Fixes | EXACT gate / boundary | Tag |
|---|---|---|---|
| **P1 position** IP/OOP factor | F1, F17 | Applies to the **WHOLE aggressive candidate** = `bluff_mass` + `_AGG_BASE` + `_DRAW_AGG_BONUS` (NOT `_AGG_BASE` alone). `in_position` = "no NOT-folded, NOT-all-in opponent acts after me this street"; exclude FOLDED/ALLIN seats; **BB is IP vs SB**. Distinct from `is_aggressor`. Aggressor-side c-bet/barrel ONLY (OOP continue-realization deferred). | direction HARD, magnitude DIRECTIONAL (`LOW`-conf; IP/OOP split needs metric #5) |
| **P2 vulnerability brake** overcard-count damp | F3 (overcard side), part of F16 | Gates **MIDDLE_PAIR / TOP_PAIR ONLY** — do NOT damp `OVERPAIR_TPTK` (bucket bundles overpairs+TPTK; AA-on-K must not damp). Damp `_AGG_BASE` by count of board ranks strictly above pair rank. Fit-seeds 0→×1.00, 1→×0.75, 2+→×0.50 are DIRECTIONAL, non-linear-in-reality. | DIRECTIONAL (per-overcard bet-rate unmeasured); AF HARD must survive |
| **P2 texture-class damp** | F20 | Made pairs only; monotone-in-wetness ORDERING asserted (dry ×1.00 … monotone ×0.55); magnitudes harness-fit. Combined P2 damps floor **≥0.25** (value never vanishes). | DIRECTIONAL |
| **P3 commit brake** `_commit_factor(c)` | F2, tightens F7 | `c = to_call/stack`. Scope to **facing-fold merit ONLY**. Only *raises* fold merit (a direction, never an asserted floor). No-op where `c ≤ c0` (c0 ≈ 0.25–0.35). Uses **pot-before-bet** as P. `test_clamp_and_jam_edge` is the named non-byte-identical exception. | AF/FtC HARD survive; SPR band edges DIRECTIONAL (continuous `c`) |
| **P4 street schedule** `street_agg_mult` | F4, F8, F19 | On the **bluff/semi-bluff side ONLY** (`bluff_mass`/`bluff_cell`, `_DRAW_AGG_BONUS`); made `_AGG_BASE` does NOT decline. Flop ×1.00 (byte-identical invariant), turn ~0.55–0.70×, river ~0.33× (levels harness-fit). Busted-draw river bluff gated `was_draw_on_turn AND bet_prev_street`, straight>flush provenance. `_DRAW_AGG_BONUS[WEAK]` street-scaled (F19). | turn-barrel% DIRECTIONAL (needs metric #6) |
| **P5 river bet floor** `_RIVER_BET_FLOOR` | F6 | New `_RIVER_BET_FLOOR = (MIDDLE_PAIR,)` — **MIDDLE_PAIR only**, distinct from `_RIVER_RAISE_FLOOR` (3 buckets). Unopened BET + `street is RIVER` + bucket is MIDDLE_PAIR ⇒ `agg_merit = 0.0`. TOP_PAIR/OVERPAIR_TPTK un-floored. Archetype-uniform mechanic. | WTSD/AF re-anchor HARD-today (single Wave-4 re-measure) |
| **P6 draw-jam fold** T1/T2-aware | F5 | Zero fold ONLY inside T1 (`E ≥ B/(P+2B)`); below T1 target normalized fold prob ≈ F* (T2), NOT a flat ×0.25. Made hands (rung ≥ OVERPAIR_TPTK) keep low-SPR commit unchanged. | AF/WTSD HARD survive; if F*-targeting too big, downgrade to DIRECTIONAL explicitly |
| **P6/F7 draw-bonus equity gate** | F7 | A **SEPARATE lever** from the fold-side brake — gate `_DRAW_CALL_BONUS` itself by commitment/equity/nutness at high `c`. The fold brake alone does NOT fix F7 (`_DRAW_CALL_BONUS[WEAK]=0.20` is 2.5× the AIR base 0.08). | DIRECTIONAL |
| **P7 faced_frac fix** | F9 | Denominator = `pot_bb − (latest aggressor's raise increment)`, not full `current_bet_to`. Fresh-aggressor tests are a no-op (increment == current_bet_to); the bug is the **self-re-raise** path only. Comment: over-states → over-folds. | DIRECTIONAL + doc-correctness; additive, no test inverts |
| **P8 elasticity split** `stickiness → call_looseness + size_elasticity` | F10 | station = high `call_looseness` / LOW `size_elasticity` (inelastic); fish = moderate `call_looseness` / HIGH `size_elasticity` (fit-or-fold). | AF HARD; size-bucket FtC HARD-pending (metric #4) |
| **P8-JSON preflop** | F11 | JSON-only: delete maniac/LAG open-limps; replace `vs_rfi` `"*"` catch-all `{call:0.55,fold:0.45}` with 3bet-or-fold. Keep pinned maniac spots green. | VPIP/PFR/gap HARD-pending (metric #3) |
| **P9 multiway made-value tighten** `_MW_VALUE_TIGHTEN` | F13 | ~0.8 on `_AGG_BASE` for MIDDLE_PAIR/TOP_PAIR, `** max(opp−1,0)`. HU byte-identical (exponent 0); recommend base so **3-way stays byte-identical, only 4-way diverges**. Cap at labeled 4-way tier. Bluff collapses faster than value tightens. Monotone in opponents. | DIRECTIONAL-only (never gates a build) |

**Deferred (NOT fixes this pass — do NOT claim built):** F18 opener-position defense (needs schema+plumbing, NOT JSON — §9); the range-favorability "barrel-MORE on scare cards" side of F3 (needs F16 villain-range); blocker-based river/bluff selection (audit §10.5).

---

## 5. Per-archetype target-stat table (the keystone, RP6 — audit §10.3)

The idealized-distinct stat signatures. **HARD-vs-directional is critical — a reviewer that demands a strict numeric match on a directional-only target FAILS good work.**

**Only THREE stats are HARD-gatable today** (the harness measures only these — audit §10.3 harness-measurability caveat): **AF, Fold-to-C-bet aggregate, WTSD.** Everything else is HARD-pending (intended gate, DIRECTIONAL until its harness metric is built) or DIRECTIONAL-only.

**Preflop (VPIP / PFR / gap) — HARD-pending #3 (maniac `MED*` gate-with-headroom; 3-bet & fold-to-3bet extremes DIRECTIONAL):**

| | nit | TAG | LAG | maniac | station | fish |
|---|---|---|---|---|---|---|
| VPIP | 13–16 | 19–23 | 26–31 | 45–58 | 42–55 | 36–48 |
| PFR | 10–13 | 16–19 | 21–26 | 38–48 | 8–14 | 10–16 |
| gap | 1–4 | 2–5 | 3–6 | ≤10 | ≥30 | ≥24 |

**Postflop:**

| Stat [tag] | nit | TAG | LAG | maniac | station | fish |
|---|---|---|---|---|---|---|
| C-bet flop overall [HARD-pending #1] | 40–55 | 55–70 | 60–75 | 80–95 | 25–40 | 35–50 |
| Fold-to-C-bet aggregate [**HARD-today**] | 60–75 | 50–60 | 40–50 | 20–35 | **<30** | 35–50 |
| Turn barrel [DIR, #6] | 30–45 | 45–60 | 55–70 | 70–90 | 15–30 | 20–40 |
| WTSD [**HARD-today**, †re-anchor] | 20–28 | 27–31 | 28–33 | 30–40 | 38–48 | 33–42 |
| W$SD [HARD-pending #2] | 55–62 | 52–56 | 48–52 | 40–46 | 40–46 | 44–50 |
| AF [**HARD-today**] | 2–3 | 2.5–3.5 | 3–4 | 4–6 | **<1.5** | 1.5–2.5 |

Also: **C-bet IP/OOP** [DIR, needs #5] · **WWSF** [DIR] · **Check-raise%** [DIR].

**Size-bucket Fold-to-C-bet slope [HARD-pending #4 — the F10 elasticity test]** (SMALL→OVERBET): station **INELASTIC/flat** 3–15→18–40; fish **ELASTIC/steep** 20–38→60–80; nit high-all-sizes; maniac low-all-sizes. Station AND maniac both low aggregate FtC but for OPPOSITE reasons — separate by AF and raise-vs-call share, never FtC alone.

**† WTSD downward re-anchor (C6 — DELIBERATE, NOT silent — audit §10.3 C6):** RP6 WTSD targets sit **BELOW** the current P2a-pinned engine bands at `test_personas_postflop.py:1482`. This is an intentional downward re-anchor at re-fit, not a silent pick:

| Persona | RP6 target | Current pinned BAND | Action |
|---|---|---|---|
| calling_station | 38–48 | (0.51, 0.64) | downward re-anchor |
| passive_fish | 33–42 | (0.53, 0.68) | downward re-anchor |
| nit | 20–28 | (0.37, 0.80) | downward re-anchor (below floor) |
| tag | 27–31 | (0.41, 0.65) | downward re-anchor |
| lag | 28–33 | (0.37, 0.59) | narrow re-anchor (partial overlap) |
| maniac | 30–40 | (0.34, 0.50) | tighten (mostly overlaps) |

The population is inflated vs RP6 (price-blind defense keeps too many pots to showdown); WTSD should FALL once P3/P8 land. AF and Fold-to-C-bet bands mostly already overlap RP6; only WTSD needs the explicit downward re-anchor. **No RP6 number is written into a test as a gate until this reconcile happens** at the single Wave-4 re-measure.

---

## 6. Harness metrics (the metric-DoD rule)

**Rule (roadmap D7):** a metric must be **live AND showing the expected direction** before the slice that needs it can close. Until a metric exists, its gate is DIRECTIONAL, not HARD (audit §10.3).

Metrics to BUILD (Wave 0) and which mechanic each gates:

| # | Metric | Measures | Gates |
|---|---|---|---|
| 1 | **CBet-flop-overall** rate per persona | aggressor-side c-bet rate (only fold-to-*first*-cbet exists today) | P1, P2 |
| 2 | **W$SD** | won-money-at-showdown | (keystone W$SD row) |
| 3 | **VPIP / PFR / gap** aggregates | preflop tightness/aggression | P8-JSON |
| 4 | **Size-bucketed Fold-to-C-bet** | SMALL/MED/LARGE/OVERBET slope (elasticity) | P8 (F10 elasticity test) |
| 5 | **CBet IP vs OOP** split | per-decision IP/OOP (needs `in_position` logged) | P1 |
| 6 | **Turn-barrel%** by persona | per-street aggressor continuation | P4 |

Already live (the three HARD-today gates): **AF, fold-to-first-cbet, WTSD** (`test_persona_postflop_bands` ~:1546–1612).

---

## 7. Invariants & calibration discipline

Verified against FULL-BUILDOUT §5, roadmap "NO-GOS" + "Cross-cutting discipline", and CLAUDE.md.

- **Domain purity:** `backend/app/domain/` (incl. `personas.py`, `personas_postflop.py`) has NO web/DB imports (test-enforced).
- **StrategyProvider:** grading flows through the ONE async `StrategyProvider` (keep swappable). This rework is **bot-side only** — do NOT edit graders (`grade_map*.py`/`postflop.py`).
- **Results = freq + EV, never boolean.** EVs labeled *approximate* (no solver tables).
- **Strategy lives in versioned `content/` data**, not code (mechanics in code, per-persona identity in JSON).
- **Every schema change ships an Alembic migration.** (Relevant only if F18 is ever built.)
- **`spot_signature()` is FROZEN** (+ `TAXONOMY_VERSION`) — grader's, not the bots'; changing it orphans SRS history.
- **NO solver tables** — heuristic + interim EV only. Villain-range rung (a) static lookup stays inside the line; rung (c) equity-vs-range is the no-go-adjacent one.
- **Action draw stays the FIRST `rng.choices`** — `range_estimate.py:278` replays it via a capture-rng; any new randomness comes *after* the action draw (two-stage bluff-sizing is the template).
- **Default-off byte-identity:** new args default to today's behavior (mirror `is_aggressor=False`/`street`) so `range_estimate` + the population harness stay byte-identical until the live loop deliberately opts in.
- **Estimator parity (Codex-Sol HIGH):** the moment a slice makes the LIVE bot diverge from the streetless policy, `range_estimate.py` MUST be threaded the **same** context and re-tested for **parity with the live policy** — else the villain-range reveal silently lies. Each such slice owns extending the estimator's replay context + a parity test.
- **Stacked-multiplier joint calibration (audit §10.2 note 2):** position × texture+overcard × street × sizing × multiway can over-suppress marginal value/bluffs. Apply to the WHOLE aggressive candidate in this order — base merit → made-value damps (P2, `_AGG_BASE` only, floor ≥0.25) → street mult (P4, bluff side only) → position mult (P1, whole candidate) → multiway (P9, geometric). Calibrate the *combined* product to RP6 targets, not each factor independently. P2 (made cells) and P4 (bluff cells) act on **disjoint** cells; position + multiway are the ones to jointly cap.
- **Denominator unification (audit §10.2 note 3):** P3's commit gate P, the F9 faced_frac fix, and P7's aggressor-increment share ONE definition: **"pot before the current aggression."** Using live `pot_bb` (which already includes the current bet) silently lowers thresholds. Do them together.
- **SINGLE band re-anchor at the CLUSTER END, NOT mid-spine (audit §10.2 note 4 / roadmap W4):** the WTSD+AF bands are moved by P5, P3, P6, AND P8 — re-anchor ONCE after the whole P3/P5/P6/P8 cluster lands (Wave 4). Re-anchor levers-first (tune pack levers before widening test bands). The ONLY early-wave test edit is P5's unit-assertion split (a byte-level assertion, not a band). **Do NOT re-fit bands mid-spine.**
- **Immutable coverage baseline + cumulative delta (anti-laundering):** an immutable initiative-start snapshot (`coverage_baseline.persona-realism-start.json`) exists; each slice re-records the operational fixture for CI green AND reports the CUMULATIVE graded-coverage delta vs the immutable snapshot. Any cumulative loss needs explicit adjudication.
- **Anti-sizing-tell:** value hands must not become size-readable (`test_sizing_spread_no_deterministic_strength_to_size`). This is F14, an INTENTIONAL-LEAVE (§8).
- **Bluff-ordering pin:** `test_bluff_ordering_across_personas_at_fixed_size` pins `station < nit < fish < tag < lag < maniac` — any bluff-path change re-anchors it deliberately.

---

## 8. Intentional-leaves (do NOT "fix")

These findings are correct design — a reviewer who sees a slice "fixing" one should FAIL it (FULL-BUILDOUT §2/§5; roadmap NO-GOS).

- **F12** — the aggression cap (5.6) compresses maniac/lag on *strong* hands. This is a **deliberate RES-D saturation fix**, not a leak. Do NOT "fix."
- **F14** — no strength-correlated sizing (value size ≈ bluff size per persona). This is the **anti-sizing-tell invariant** — sizing is decoupled from hand strength ON PURPOSE. Do NOT "fix." (Sizing overrides are permitted only in the deferred N6 slice, and only *respecting* this no-go.)

---

## 9. Correction ledger (do NOT re-introduce these refuted claims)

Pulled from RECONCILE + the §10 capstone corrections. Any worker or reviewer re-introducing these is WRONG.

1. **60% → 42.9%** — the 3×-pot T1 threshold is **42.9%** (`3/7`), NOT 60%. 60% is the α ceiling for a 1.5× bet. (RECONCILE RP3; §3 above.)
2. **The weak-draw fix needs its OWN gate** — the fold-side commit brake ALONE does NOT fix F7. `_DRAW_CALL_BONUS[WEAK]=0.20` is 2.5× the AIR base (0.08); a ~1.5× fold-merit boost barely dents the inflated call merit. F7 requires a **separate** equity/commitment gate on `_DRAW_CALL_BONUS` itself. (RECONCILE RP3 "F7 AUTO-FIX NOT EARNED".)
3. **faced_frac tests cover fresh-raisers only** — `test_faced_frac_raise_over_bet_lands_medium_not_small` (563) and `test_faced_frac_check_raise_lands_large` (577) use a FRESH aggressor (zero prior street chips), so `increment == current_bet_to` and the increment fix is a **no-op** there — they stay GREEN. The bug is the **self-re-raise** path, which no current test covers ⇒ a NEW self-re-raise test is required. (RECONCILE RP7 correction to BOTH reviewers; the earlier `pot−to_call` fix WOULD have broken 563 — the increment fix does not.)
4. **Delete the "~80% of the benefit" river claim** — this number was unsupported; delete it. Rank-only still misses blocker thin value, blocker bluffs, kicker effects, range caps, texture, line history. No fake precision. (RECONCILE RP5-S6.)
5. **Opener-position defense (F18) is NOT a JSON-only fix** — `sample_preflop_action` receives only the ACTOR's seat + a bare `facing` string; there is NO opener-position discriminator. Defending differently vs a UTG-open vs a BTN-open needs **sampler plumbing + a schema change** (`content/models.py:98–101` new `vs_rfi` opener axis) + re-authoring every pack + new tests. It CANNOT sit in the Wave-1 JSON bucket; it is deferred (owner decision). The F11 maniac-limp / `"*"`-catch-all fix stays JSON and stays in Wave 1 — the two are separate. (RECONCILE capstone #1; audit §10.1-P8 F18 reclassification.)
6. **P2's `×0.75 / ×0.50` are fit-SEEDS, not earned constants** — mark DIRECTIONAL; equity drops are non-linear (mild on 1 overcard, steeper on 2+). Under softmax ×0.50 yields ~34% observed, not 25%. (RECONCILE capstone #6 / RP2-S2.)
7. **P2 overcard damp gates MIDDLE_PAIR / TOP_PAIR ONLY — never OVERPAIR_TPTK** — the bucket bundles overpairs + TPTK; AA-on-K-high must NOT damp. (RECONCILE RP2-S4.)
8. **The made-hand vulnerability brake is NOT a "range-favorability proxy"** — RELABEL it a vulnerability (NPOT) brake, validated by equity-monotonicity (the correct validation for THAT purpose). The range-favorability "barrel-MORE on scare cards" side is UNBUILT / DEFERRED (needs F16 villain-range). Do not claim the equity check earns it. (RECONCILE RP2-S5, "most important call in the research".)
9. **RP5's bluff-share formula is CORRECT — the lead OVERRULED Sol** — RP5 used `s/(1+2s)` (the bettor form), NOT `s/(1+s)` (the defender form Sol accused it of). Do NOT "fix" RP5 to the defender form. Only "exact match at every size" wording is wrong (the code table is 4 coarse representatives). (RECONCILE RP5-S5.)
10. **P6 "toward T2" must be REAL, not slogan-EV** — a fixed `r∈[0.2,0.5]` fold reduction presented as if it targets T2 is cosmetic under softmax (TAG fold 50%→20%, station 36%→12% still force bad low-fold stack-offs). Either target the normalized post-softmax fold prob ≈ F*, or **downgrade P6 to DIRECTIONAL explicitly** — do not fake T2-awareness. (RECONCILE capstone #5 / RP3-P6.)
11. **`is_aggressor` ≠ `in_position`** — `is_aggressor` is the WHOLE-HAND last aggressor; P1's `in_position` is a per-street boolean. Do not conflate. **BB is IP vs SB** (postflop SB acts first — the audit's "BB OOP to SB" was backwards). Exclude ALL-IN/FOLDED seats from "acts after me." (RECONCILE RP1-S3.)
12. **The commit gate's P is pot-BEFORE-bet, not live `pot_bb`** — using live pot silently lowers the threshold. `c = to_call/stack` is an SPR-INTERACTION term (`c = faced_frac · P/stack`), NOT orthogonal to pot price. (RECONCILE RP3.)
13. **The "never semi-bluff-jam a station / value-jam only" line is a HERO exploit, NOT a bot mechanic** — it requires villain-range knowledge the sampler does not have (F16, range-blind). Deferred to the coaching layer. (RECONCILE RP3; audit §10.5.)

---

## 10. Reference pool

Everything is calibrated to **online low-mid 9-max ~100bb** (audit §9.2 / RECONCILE line 7). The whole §5 stat table is pool-specific. If the target audience/pool differs, the entire keystone needs recalibration (FULL-BUILDOUT §6 #7). Anchors were mostly derived from 6-max solver outputs and transferred to 9-max — so the exact IP/OOP *gap* magnitude is `LOW`-conf (9-max changes opening ranges / caller composition / multiway incidence), while the *direction* (IP>OOP) is `HIGH`-conf (RECONCILE RP1-S6).

---

## 11. Reviewer checklist (apply to a slice's output — each item is pass/fail)

The most important section. For a persona-realism slice under review:

1. **[Softmax law]** Are ALL new magnitudes justified by a MEASURED (observed closed-loop) stat hitting its target, or are any dropped-in constants closing the slice on "the constant is in the code"? Any un-fit constant → **FAIL**.
2. **[Metric-DoD]** If the slice needs a NEW harness metric to prove its effect, is that metric live AND showing the expected direction? If not, the slice cannot close on a HARD gate → **FAIL** (unless correctly self-labeled DIRECTIONAL).
3. **[Gate boundary — §4]** Does the mechanic's gate exactly match §4? Specifically: P2 damp gates MIDDLE_PAIR/TOP_PAIR only (NOT OVERPAIR_TPTK)? P5 floor is MIDDLE_PAIR only? P1 factor hits the WHOLE aggressive candidate (`bluff_mass`+`_AGG_BASE`+`_DRAW_AGG_BONUS`)? P4 street mult on the bluff side only (made `_AGG_BASE` does NOT decline)? P3 commit brake scoped to facing-fold merit only? Any boundary mismatch → **FAIL**.
4. **[EV numbers — §3]** If the slice cites a threshold: is the 3×-pot T1 read as **42.9%** (not 60%)? Are T1/T2/T3 the exact forms? Is the bettor bluff share `s/(1+2s)` (not `s/(1+s)`)? Any wrong number → **FAIL**.
5. **[Correction ledger — §9]** Does the slice re-introduce any refuted claim in §9 (F7 auto-fix without a separate gate; F18 as JSON-only; "~80% benefit"; range-favorability claimed as earned; P6 flat-r faked as T2-aware; `is_aggressor` used as `in_position`; live `pot_bb` as the gate denominator)? Any → **FAIL**.
6. **[HARD-vs-directional — §5]** Does the slice's acceptance criterion demand a strict numeric match on a DIRECTIONAL-only target (e.g. per-overcard bet-rate, IP/OOP split, turn-barrel%, multiway value)? Demanding a hard match on a directional target FAILS good work → **FAIL the criterion**. Conversely, are the three HARD-today gates (AF, Fold-to-C-bet, WTSD) actually checked where applicable?
7. **[Band re-anchor — §7]** Was any band re-anchored **mid-spine**? The only legitimate band re-anchor is the SINGLE Wave-4 cluster re-measure; the only early-wave test edit is P5's unit-assertion split. Any mid-spine band widening (outside the P5 assertion split) → **FAIL**.
8. **[Intentional-leave — §8]** Did the slice "fix" F12 (aggression-cap compression) or F14 (no strength-correlated sizing)? Either → **FAIL**.
9. **[Estimator parity — §7]** Does the slice make the LIVE bot diverge from the streetless policy? If so, did it thread `range_estimate.py` the SAME context and add a parity test? Divergence without parity → **FAIL**.
10. **[Default-off byte-identity]** Do new args default to today's behavior so `range_estimate` + the population harness stay byte-identical for un-opted-in callers? Is the action draw still the FIRST `rng.choices` (new randomness only after)? If not → **FAIL**.
11. **[Denominator unification — §7]** If the slice touches faced_frac / commit-gate / T1, does it use ONE "pot before current aggression" denominator (not live `pot_bb`)? If not → **FAIL**.
12. **[Stacked-multiplier order — §7]** If the slice adds a multiplier, is it applied to the whole aggressive candidate in the §10.2 order, and is the *combined* product calibrated (not each factor independently)? If not → **FAIL**.
13. **[Domain purity + scope]** Does the slice keep `personas*.py` pure (no web/DB), leave the grader / `spot_signature()` untouched, and stay inside the files its ticket names? Any breach → **FAIL**.
14. **[Coverage delta]** Did the slice report the cumulative graded-coverage delta vs the immutable snapshot, and is any loss adjudicated? Silent loss → **FAIL**.

---

## 12. Source pointers

- **Grounded magnitudes / engine mapping / acceptance criteria (P1–P9):** `docs/ai-dlc/research/persona-realism-audit-2026-07-24.md` §10.1 (per-P blocks), §10.2 (cross-package interactions), §10.2a (context-plumbing contract), §10.3 (keystone stat table + C6 re-anchor), §10.4 (sequencing/waves), §10.5 (deferred gaps), §10.6 (owner decisions).
- **Corrections / what was refuted (AUTHORITATIVE):** `docs/ai-dlc/research/persona-realism-artifacts/RECONCILE.md` — per-package (RP1–RP8) verdicts + the capstone 8 corrections.
- **Lever→finding map, invariants §5, findings coverage F1–F20 §2, glossary §8:** `docs/ai-dlc/research/persona-realism-FULL-BUILDOUT.md`.
- **Wave plan, cross-cutting discipline (softmax/D7/D8/D9/parity/baseline), no-gos:** `docs/ai-dlc/roadmap/persona-realism.md`.
- **Findings F1–F20 (root cause, evidence, class):** audit §3, §6b.
- **Depth on any single package:** `persona-realism-artifacts/RP1_findings.md … RP8_findings.md` + `RP*_sol.md` (adversarial reviews).
