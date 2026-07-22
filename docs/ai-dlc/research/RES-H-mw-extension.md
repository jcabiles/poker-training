# RES-H — Multiway coverage extension: 4+-way grading + caller-re-raises-c-bet grader

**Spike, Epic 5 (multiway coverage). Output = decision doc + engine-measured targets. NO app code.**
Created 2026-07-22. This doc becomes LAW for Epic 5 build slices: builders copy the directions/design
below; refuters verify against it. It consumes the binding multiway law (RES-D §6, SYNTHESIS A2) and
the A1 fold-ceiling law (SYNTHESIS A1 / RES-D §5), and it is grounded in **seeded engine sims** — the
N5 lesson (a reasoned closing-seat claim was wrong; verify with the engine) is honored throughout.

**Confidence tags** (RES-D convention):
- **[SOLVED]** — provable arithmetic / a direct engine measurement (reproducible from the seeded sim).
- **[SOURCED]** — cited to a named external source.
- **[DERIVED-ASSUMPTION]** — we computed it (direction-anchored); a design target, not a truth.

**Sim provenance.** All engine numbers below come from `advance`-style all-bot playouts through the
production engine + `play.bot_decision` sampler (`app/domain/table/{engine,play,personas}.py`), the
default 8-bot `LINEUP` on seats 1–8 plus a TAG hero stand-in on seat 0, 100bb stacks, seed
`20260722`, N = 6000 hands (button rotates `i % 9`). Scripts are in the session scratchpad
(`mw_sim.py`, `mw_detail.py`, `aggpos.py`, `dp_rate.py`). Numbers are the seeded run; ±~1pp Monte-Carlo
noise at N = 6000. **Bot caveat (carried everywhere):** the sampler is a heuristic persona model, not
a live population — it raises c-bets more mechanically than the live "raise = value" read implies, so
raise-frequency numbers are treated as an **upper bound** on the live rate, and reachability numbers as
"engine reality," explicitly distinct from live-population frequency.

---

## §1. Engine reality (measured) — [SOLVED, seeded N=6000]

### 1.1 Players-to-flop distribution (default lineup)

| Field at flop | Hands | % of all hands | % of hands that reach a flop |
|---|---:|---:|---:|
| folded pre / no flop shown | 1090 | 18.2% | — |
| **2-way (HU)** | 2522 | 42.0% | 51.4% |
| **3-way** | 1680 | 28.0% | 34.2% |
| **4-way** | 598 | 10.0% | 12.2% |
| 5-way | 98 | 1.6% | 2.0% |
| 6-way | 12 | 0.2% | 0.2% |
| **4+-way (total)** | **708** | **11.8%** | **14.4%** |

**Reading.** 4+-way flops are **11.8% of all hands / 14.4% of flops seen** — not negligible, but ~⅓
the volume of 3-way (28%) and ~⅕ of HU (42%). Within 4+, the mass is almost entirely 4-way (598 of
708); 5-way is rare (1.6%) and 6-way vanishing (0.2%). So "4+-way" is, in practice, **"4-way, plus a
long thin tail."** SRP-with-≥1-cold-caller pots are 43.4% of all hands; of those, 4+-way to the flop
is 95/1000 hands.

### 1.2 Closing seat in multiway pots — verified from ACTION ORDER, not position

The N5 done-note recorded (correctly, at the time) that in the specific 3-way mapped shape "hero = BB
closes." The sim shows this is **shape-dependent, not universal** — the exact finding that makes a
naive positional 4-way extension unsafe.

Last responder to a multiway c-bet (opener bets, who acts LAST before the street resolves), N = 647
multiway c-bets:

| Last responder | share |
|---|---:|
| BB | 17% |
| SB | 14% |
| BTN | 12% |
| CO / UTG2 / HJ / LJ / UTG1 / UTG | 8–11% each |

And, restricting to the **N5-family shape** (SRP, opener c-bets, ≥1 cold-caller, BB in) and asking
"does the BB act *after all cold-callers* vs the c-bet?" — the closing-seat assumption the mapper
depends on:

| | count | share |
|---|---:|---:|
| **BB is last of the callers (N5 shape holds)** | 114 | **53%** |
| **a cold-caller acts AFTER the BB (N5 shape breaks)** | 102 | **47%** |

**[SOLVED] finding.** The BB closes the multiway betting only **~53% of the time** in the SRP shape —
specifically when the aggressor is EARLY and the cold-caller sits between the aggressor and the BB. When
the aggressor is IP (CO/BTN opener), the **BB acts first postflop (OOP) and a cold-caller closes** (e.g.
`aggressor=CO callers=[HJ] resp_order=[BB, HJ]`). **This is the N5 lesson re-confirmed at higher field
width: the "BB closes" rule is not general — any 4-way extension MUST gate on the actual closing seat
from the action order, never assume it.** The current N5 mapper already does the right thing implicitly:
it requires the exact `check(BB) → bet(opener) → respond(caller) → hero(BB)` sequence and returns None
otherwise, so it only ever fires in the ~53% of shapes where BB genuinely closes. A 4-way extension of
that mapper inherits the same guard for free **only if it keeps the "hero closes / everyone behind has
acted" invariant explicit** (see §2.4).

### 1.3 Caller-raises-the-c-bet reachability (feeds §3–§4) — [SOLVED]

Whole-hand occurrence (any pot): a preflop cold-caller (non-BB) raises the opener's flop c-bet in
**210 / 6000 hands = 35.0/1000**; of those the c-bet was into a multiway (≥3-to-flop) field in
**122/6000 = 20.3/1000**. A BB check-raise of the c-bet (the *existing* `grade_vs_check_raise` family)
occurs **33/6000 = 5.5/1000** — so the cold-caller raise is **~6× more common than the BB check-raise**
by occurrence.

**Decision-point reachability** (the number that matters for a grader — how often the acting seat is the
opener who c-bet and now faces the raise), any seat as opener:

| Decision-point family | fires / 1000 hands | field at the raise (2 / 3 / 4 / 5-way) |
|---|---:|---|
| **opener faces a COLD-CALLER flop raise (NEW family)** | **16.8** | 73 / 22 / 5 / 1 |
| opener faces a BB check-raise (existing `grade_vs_check_raise`) | 3.3 | — |
| N5 3-way `map_mw_flop_vs_cbet` (hero=BB closes) fires | 1.8 | — |
| HU `map_flop_vs_cbet` (hero=BB faces c-bet) fires | 5.2 | — |
| HU `map_flop_vs_check_raise` fires | 0.17 | — |

By opener position, the cold-caller-raise rate per c-bet spot: **UTG 28.8%, UTG2 21.3%, LJ 18.0%,
UTG1 16.4%, BTN 15.6%, HJ 11.3%, CO 9.4%, SB 8.8%, BB 8.2%** (overall 15.4% of SRP cold-caller c-bets).
Early openers get raised most — consistent with the cold-caller's positional + range edge (§3.2).

**Note on field-at-the-raise:** 73 of 101 cold-caller-raise decision points are effectively **HU by the
time the raise lands** (the other callers folded to the c-bet, leaving dead money) — the same "degrade
to 2-live with dead money in the pot" pattern the N5 mapper already handles. Only 22 are genuinely
3-way-live and 5 four-way at the raise.

---

## §2. 4+-way extension — directions (RES-D style, tagged)

### 2.1 Is there a published 4+-way baseline? — [SOURCED] **No.**

- **4+-way postflop is not solved and not published.** GTO Wizard ships HU and **3-way** postflop
  solving; **multiway ≥4-way postflop is explicitly on the roadmap, not released** — "multiway postflop
  expansion to scale up to 9 players is planned … only after 3-way one-size postflop solutions."
  ([GTO Wizard — 3-Way Solving launch](https://blog.gtowizard.com/now_live_3_way_solving_nodelocking_2_0_and_50k_icm_ft_sims/);
  [GTO Wizard AI Custom Multiway Solving](https://blog.gtowizard.com/gto-wizard-ai-custom-multiway-solving/))
- **Why:** adding one player multiplies game-tree size ~1000× and there is **no unique equilibrium** in
  >2-player games (SYNTHESIS "ONE real disagreement" resolution: equilibria exist but are non-unique and
  carry no minimax guarantee). ([GTO Wizard — Quirks of Nash Equilibrium in Multiway]; Brown & Sandholm,
  *Science* 2019 — see `cbet-and-multiway.md` §3.4).
- The only aggregate multiway number in the literature is the directional **"c-bet frequency roughly
  halves HU→3-way (~70%→~35%)"**, and even that is **[SOURCED/HEURISTIC]**, not a solver dump — the
  exact 70→35 pairing "too weak to be a calibration target" (SYNTHESIS A3; `cbet-and-multiway.md` §3.1,
  §6). No source states a 4-way c-bet %, MDF, or defense frequency.

**Conclusion [SOURCED]:** there is **no defensible published 4+-way baseline** to grade against. Any
4-way grade is an extrapolation of a 3-way heuristic, which is itself an extrapolation of HU solves.

### 2.2 The binding law this extension must obey — [SOLVED from RES-D §6 / SYNTHESIS A2]

Multiway adjustments are **DIRECTION-only**: *bluff less + value-lean + tighter bluff-catch per added
opponent.* **Never** a per-opponent MDF constant, an n-th-root defense frequency, or a second multiway
model. The n-th-root fold relation (√α per opponent) is a symmetric-independent idealization that never
holds at a real table; it is arithmetic, not a defense target. This is non-negotiable and it is exactly
what makes a principled 4-way extension *possible*: we are not asserting a 4-way frequency, only pushing
the existing HU merits further in the already-established direction.

### 2.3 Extend the 3-way structure — do NOT build a new one. **[DERIVED-ASSUMPTION]**

**Recommendation: extend the existing F4-style multiplier, do not add a 4-way structure.** The current
`_apply_multiway` (in `postflop.py`) is a **binary** bucket — it fires identically for 3-way and 8-way
(`is_multiway(spot)` is `≥3`). It applies fixed scalars: `_MW_BLUFF_DAMPEN=0.6`, `_MW_VALUE_LEAN=1.15`,
`_MW_THIN_VALUE_DAMPEN=0.7`, `_MW_CATCH_TIGHTEN=1.3`. The F4 precedent for the *bot* side already made
this opponent-count-aware: `_MW_CATCH_TIGHTEN = 1.15 ** max(opp - 1, 0)` — a **per-opponent geometric
push in the sanctioned direction, applied facing-path-only to weak catcher categories.**

The clean, law-compliant 4-way extension is to make the grader's `_apply_multiway` scalars **opponent-
count-scaled the same way**, e.g. replace the flat constants with `base ** max(opp - 1, 0)` forms so
4-way pushes strictly harder than 3-way but along the identical axis:

- bluff dampen: `0.6 ** max(opp-1, 0)` on aggressive merits for air/draw (compounds: 4-way damps more
  than 3-way — matches the multiplicative fold-equity collapse `P1×P2×…`, `cbet-and-multiway.md` §3.1).
- value-lean and thin-value dampen: geometric in `opp-1` likewise (value threshold rises with each live
  hand — `cbet-and-multiway.md` §3.2, the A♣T♣2♠ two-pair-falls-behind example).
- catch-tighten on the facing side: reuse the F4 shape `1.15 ** max(opp-1, 0)` verbatim.

**Why extend, not rebuild:** (a) a new 4-way structure would need 4-way targets that **do not exist**
(§2.1) — it would be inventing numbers, the cardinal no-go; (b) the direction-only law says the *only*
legitimate multiway signal is "more of the same per opponent," which is precisely a geometric multiplier;
(c) it keeps ONE multiway model (RES-D §6: "no second multiway model"); (d) HU output stays byte-
identical (`opp-1 = 0 ⇒ exponent 0 ⇒ scalar 1.0`), and 3-way changes only if we re-fit the base to keep
`base**1` equal to today's flat constant (recommended: keep 3-way byte-identical, let 4-way diverge).

The multiplier **magnitudes** for 4-way are **[DERIVED-ASSUMPTION]** (direction-anchored, no solver
truth); the **invariants** are the hard contract:
1. **Monotone in opponents:** for a fixed hand/texture, bluff/thin-value aggressive merit is
   non-increasing and catch-fold merit non-decreasing as `opp` rises (3-way ≤ HU aggression, 4-way ≤
   3-way aggression).
2. **Direction-only:** the adjustment never introduces an MDF/defense frequency or per-opponent
   pot-odds constant — it only *scales existing merits*.
3. **HU byte-identical** (`opp=1`), **3-way byte-identical to today** (pin the base so `base**1` equals
   the current flat scalar), 4-way is the only new behavior.

### 2.4 The reachability + closing-seat gate — the honest boundary

§1.2 proved the closing seat is not BB in ~47% of multiway shapes, and §1.1 showed 4+-way is 11.8% of
hands but 5/6-way is a thin tail. Two consequences for the mapper (grade_map), separate from the merit
math above:

- **Only grade a 4-way spot when hero CLOSES the action** (everyone behind hero has already acted vs the
  faced bet). This is the same invariant the N5 mapper enforces; a 4-way mapper must keep it explicit and
  return **None** ("no baseline yet") for any spot with a live player still to act behind hero — the
  grader cannot see that player's range and must not fabricate a read. This is not a limitation to
  apologize for; it is the correct honest boundary.
- **Cap the extension at 4-way; keep 5+-way as `_apply_multiway`'s existing binary bucket** (or "no
  baseline yet" if unmapped). 5-way is 1.6% and 6-way 0.2% of hands — building/validating a distinct
  5-way path is effort against a vanishing denominator. The geometric multiplier will *numerically*
  handle 5+ if `opp` is passed through, but do not claim 5-way accuracy: label anything past 4-way as
  the same directional bucket, not a calibrated tier.

### 2.5 Where "no baseline yet" beats grading — the confidence boundary **[stated as law]**

Show **"no baseline yet"** rather than a grade when:
- hero does **not** close the multiway action (a live player is still behind) — §2.4;
- the field is **5+-way** and the spot is not one the binary bucket already covers safely;
- the line is **off the SRP continuation shape** the mappers verify street-by-street (limped MW, donk
  leads, delayed c-bets, caller-raises — the N5 still-None list, unchanged);
- the **cold-caller's range is unmodeled** for that (caller, opener) pair (the `_mw_ranges` content
  gate) — no fabricated third range.

The 4-way merit direction (§2.3) is a **defensible push**, not a truth. Grading a 4-way spot where hero
closes and the shape is SRP-canonical is honest (freq+EV, approximate, direction-only); grading anything
outside that is inventing a number. **When in doubt, "no baseline yet" is the correct and valued answer.**

---

## §3. Caller-re-raises-c-bet grader design

**The spot:** hero opened, c-bet the flop, and a **preflop cold-caller (not the BB)** raises the c-bet.
Hero must respond (fold / call / re-raise). This is distinct from a BB check-raise both in *range* (§3.2)
and in *who acts* (a caller who called preflop IN POSITION, then raised).

### 3.1 Closest existing family — `grade_vs_check_raise`, and what transfers

`grade_vs_check_raise` (`postflop.py`) is the right parent: hero is the ORIGINAL aggressor facing a
raise of his c-bet, exactly as here. What transfers **as-is**:
- The **AGGRESSOR-view** `range_advantage()` call (hero is still the preflop+flop aggressor), passing the
  raiser's position as the counterpart (the refuter-caught "don't pass hero's position twice" rule).
- The **fold/call/raise merit shape** and the elevated fold baseline: `_merits_vs_check_raise` uses
  `fold = 1.6` (vs `_merits_vs_cbet`'s 0.6) because "a raise-after-my-bet is fresh strength news, a
  stronger prior than the static board read" (research §10.3). This prior is **even stronger** for a cold-
  caller (§3.2) — the new grader's fold baseline should be **≥ 1.6**, arguably higher.
- The texture-conditioned `bluffy` modulation (bluffs plausible on low/connected/wet, rare on dry).
- The `_raise_sizing_verdict` overlay (dry→small, wet→big) and the whole `EvaluationResult` freq+EV shape.
- `_apply_multiway` composes on top when the raise lands in a still-multiway pot (§2.3).

What must **change** (the range asymmetry, §3.2): the fold baseline is higher and the "raise is a bluff"
term is smaller — a cold-caller raise is more value-weighted than a BB check-raise, so marginal made
hands and bluff-catchers should fold *more* and hero's own light 4-bet-bluff merit should be *lower*.

### 3.2 The range asymmetry — cold-caller raises are heavily sets / two-pair — [SOURCED]

Cold-caller ranges are **capped and nut-heavy**: a good cold-caller flats a tight range dominated by
medium/small pocket pairs and suited broadways, having **3-bet the premiums (AA/KK/QQ/AK) preflop** — so
those top hands are *removed* from the flat. The consequence on the flop:
- "That range contains a surprisingly high percentage of strong hands like sets and overpairs … a huge
  nut advantage, which incentivizes raising with a ton of [value] hands." ([GTO Wizard — Barreling as IP
  Cold-Caller](https://blog.gtowizard.com/barreling-as-ip-cold-caller/); [GTO Wizard — OOP C-betting vs
  Loose Cold-callers](https://blog.gtowizard.com/oop-c-betting-vs-loose-cold-callers/))
- At **live low stakes specifically**, the read is even sharper: recreationals "check-raise/raise only
  6–8%, which is too infrequent … against players who raise below ~5%, fold everything except the top of
  your range because they almost always have two pair or better."
  ([Upswing — Golden Rule for Low Stakes](https://upswingpoker.com/golden-rule-for-low-stakes-cash/);
  [Upswing — Spots You Should Almost Never C-Bet](https://upswingpoker.com/spots-to-rarely-c-bet/))
- Set-mining math corroborates: a caller who flatted 22–JJ to set-mine flops a set ~11.8% per pair, and
  a raise from that capped range concentrates on **sets + two-pair + the occasional strong draw** — the
  "raise = value" read. This is the same nut-advantage logic `cbet-and-multiway.md` §3.2 cites for value
  tightening multiway.

**Design consequence [DERIVED-ASSUMPTION, exploit-anchored]:** the grader's prior is "**a cold-caller's
flop raise is value until proven otherwise**." Concretely vs `_merits_vs_check_raise`: (a) raise the fold
baseline further above 1.6; (b) shrink the `bluffy` credit that lets marginal hands continue; (c) give
hero's own re-raise-as-bluff merit a *lower* ceiling than the check-raise node (you are re-raising into a
capped nut-heavy range — thin value and bluffs both lose); (d) keep top-of-range value re-raises and
strong draws as the primary continue. **This is a direction, not a solver frequency** — no MDF, no
per-combo number.

### 3.3 Minimal grader design

**Inputs** (all already available on the mapped `Spot` — mirror `grade_vs_check_raise`):
- hero hole cards + flop board → `_hand_category` (strong / weak_made / draw / air);
- `range_advantage()` aggressor-view (hero pos, raiser pos, flop texture);
- `price = faced_raise / pot` (pot already includes the raise) — used for the *pot-odds* terms only, NOT
  as an α ceiling (§3.4);
- the raiser's identity = a preflop cold-caller (the mapper guarantees this — a new
  `map_flop_vs_caller_raise` gating on: SRP opener = hero, hero c-bet canonical, a **non-BB preflop
  caller** raised, hero closes / faces it); the caller's range comes from the same `VS_RFI` call content
  entry the `_mw_ranges` gate already resolves.

**Verdict shape** (unchanged from the family): per-action **frequency + approximate EV** over
{fold, call, raise}, `is_mixed`, `sizing_correctness` via `_raise_sizing_verdict`, `correctness` via the
existing EV-loss ladder (`POST_ACCEPTABLE_MAX / POST_MISTAKE_MAX / POST_MIX`). Never a boolean.

**Merit function** `_merits_vs_caller_raise(value, adv, price, texture, cat)` — a sibling of
`_merits_vs_check_raise` with the §3.2 asymmetry baked in: higher fold baseline, smaller `bluffy` credit,
lower raise-bluff ceiling. Composes with `_apply_multiway` when still multiway (§2.3).

### 3.4 α does NOT apply here — [SOLVED from RES-D §5 / SYNTHESIS A1] — **explicit**

The A1 fold-ceiling calibration (`_calibrate_catcher_fold`, the `price = B/(P+B) = α` clamp) is scoped in
the code and in RES-D to **flat-call defense nodes only — flop `grade_vs_cbet` and turn
`grade_vs_turn_bet`.** It **must NOT be applied when responding to a raise**, for the reason RES-D states
verbatim:

> "NOT the check-raise node — **α is the flat-call form and 'doesn't work with a raise'** (RES-D §1c, GTO
> Wizard); its fold-heavy live-exploit prior stays." (`postflop.py` F5 block comment; RES-D §5 scope;
> SYNTHESIS A1: "`P/(P+B)` is the flat-**call** indifference form … GTO Wizard explicitly warns it
> doesn't work with a raise.")

Why, mechanically: α = `B/(P+B)` is the bettor's **bluff-indifference** point — it answers "how often may
I fold to a *bet* facing a balanced bettor." When hero faces a **raise**, hero is not the bettor choosing
a fold-ceiling against his own bet's price; hero is a **caller getting a price on a re-raise from a range
that is not balanced but capped and value-heavy** (§3.2). The correct threshold is **pot-odds vs the
raiser's *actual* value:bluff ratio**, which here skews hard to value — so the honest read is often *fold
more than α would suggest*, the exact opposite of α acting as a floor. Using α here would (a) apply a
formula outside its derivation and (b) systematically *under-fold* into a nut-heavy range — a real EV
leak. The pot-odds `price` term still lives inside the merit function (cheap raises get called wider);
what is forbidden is the α **ceiling/floor clamp** `_calibrate_catcher_fold`. **The new grader must not
call `_calibrate_catcher_fold`.** (Same rule the check-raise grader already follows.)

---

## §4. Reachability — honest report

| Spot | occurrence /1000 | decision-point /1000 | verdict |
|---|---:|---:|---|
| **cold-caller raises c-bet (NEW family)** | 35.0 (any) / 20.3 (mw) | **16.8** | **worth building** |
| BB check-raise (existing `grade_vs_check_raise`) | 5.5 | 3.3 | already covered |
| N5 3-way BB-closes `map_mw_flop_vs_cbet` | — | 1.8 | already shipped |
| 4+-way flops (any) | — | 11.8% of hands | worth extending §2 |

**The caller-re-raise family is NOT rare — it is the single most reachable un-covered postflop node
found.** At **16.8 decision points / 1000 hands** it fires **~5× more than the existing BB-check-raise
mapper (3.3)** and **~9× the N5 3-way mapper (1.8)**. Contrast the explicit "<1/1000 ⇒ maybe not worth
it" bar in the brief: this clears it by an order of magnitude. It does **not** need a bot-behavior lever
to become reachable — it is already the highest-frequency gap.

**Honesty caveats (do not drop):**
- The 16.8/1000 is an **engine (bot) rate**, and the persona sampler raises c-bets more mechanically than
  live players do — the live cold-caller-raise rate is **lower** (the "raise = value, and value is rare"
  read of §3.2/§3.4 is *exactly why* it is rarer live). Treat 16.8 as an **upper bound**; the family is
  worth building even at, say, ⅓ that live rate (~5/1000, still > the BB check-raise family).
- **73 of 101** cold-caller-raise decision points are effectively **HU by the time the raise lands**
  (other callers folded to the c-bet), so most instances grade on the plain HU aggressor-facing model
  with dead money correctly in the pot — the same degrade-to-2-live pattern N5 already handles. Only
  ~27% are genuinely 3+-way-live at the raise; those compose `_apply_multiway` on top.
- 4+-way *field* coverage (§2) is a smaller marginal win than the caller-raise grader: 4-way is 10% of
  hands but the *gradeable* subset (hero closes, SRP-canonical shape) is a fraction of that (§1.2's 53%
  closing-seat rate × the canonical-shape gate). Real but thinner than the caller-raise family.

---

## §5. Recommended slice cut — with pass/fail

**Two slices, in this order.** They are cleanly separable (different graders, different mappers, no shared
function bodies) and have very different confidence footings — slice 1 rests on a real reachability
number and a sourced range read; slice 2 rests on a direction-only extrapolation with no baseline. Ship
the high-confidence, high-reach one first.

### Slice H1 (FIRST) — Caller-re-raises-c-bet grader (hero response) — **high confidence, high reach**

Build `_merits_vs_caller_raise` + `grade_vs_caller_raise` (sibling of `grade_vs_check_raise`, §3.1/§3.3),
the §3.2 value-skewed prior, and a `map_flop_vs_caller_raise` mapper (SRP, hero = opener, hero c-bet
canonical, a **non-BB** preflop caller raised, hero faces/closes; caller range via the existing `VS_RFI`
content gate; degrade-to-2-live when other callers folded). **α clamp `_calibrate_catcher_fold` is NOT
called** (§3.4).

**Pass/fail:**
1. The mapper **fires** in a seeded bot belt-test at a rate consistent with §1.3 (≥ ~5/1000 decision
   points; the sim shows 16.8) — assert non-zero and in-band, not an exact count.
2. `grade_vs_caller_raise` returns freq+EV over {fold,call,raise} with `sizing_correctness`; **never a
   boolean**; `is_mixed` correct.
3. **Range-asymmetry direction test:** for a fixed marginal `weak_made` hand + texture + faced size, the
   caller-raise grader's FOLD frequency is **strictly ≥** `grade_vs_check_raise`'s (a cold-caller raise
   is more value-weighted → fold more). A `strong` hand still favors continue in both.
4. **α-not-applied test:** the grader does not import/call `_calibrate_catcher_fold`; a direct assertion
   (grep-level or a unit test that the fold share is *not* clamped to the α band) — a marginal hand vs a
   raise may fold **above** the α ceiling for the faced size, which the flat-call grader could not.
5. `_apply_multiway` composes when the mapped spot is still multiway (facing-side path).
6. HU/3-way existing grader outputs **byte-identical** (hash-pin unchanged); `TAXONOMY_VERSION` bumped
   only if the node taxonomy gains the family; `verify.sh` + FE build green; refuter-on-diff PASS.
7. Every off-shape line (donk-raise, limped pot, delayed c-bet, hero-not-opener) returns **None**.

### Slice H2 (SECOND) — 4-way merit extension (opponent-count-scaled `_apply_multiway`) — **lower confidence, thinner reach**

Make `_apply_multiway`'s scalars **opponent-count-aware** via geometric `base ** max(opp-1, 0)` forms
(§2.3), reusing the F4 `1.15 ** max(opp-1,0)` catch-tighten shape; thread `opp` (live-opponent count)
into the call. Extend the 4-way mappers (`map_mw_*`) to fire when hero closes a **4-way** SRP shape,
keeping the explicit "hero closes / all behind have acted" gate (§2.4); cap at 4-way, 5+ stays the binary
bucket or "no baseline yet."

**Pass/fail:**
1. **HU byte-identical** (`opp=1` ⇒ exponent 0 ⇒ scalar 1.0; hash-pin unchanged) **and 3-way byte-
   identical to today** (base pinned so `base**1` equals the current flat constant) — assert both.
2. **Monotone-in-opponents test:** for a fixed air/draw hand + texture, aggressive (bluff) merit is
   non-increasing HU→3-way→4-way; for a fixed weak_made catcher, facing FOLD merit is non-decreasing
   across the same. (The §2.3 invariant, the hard contract — not the magnitudes.)
3. **Direction-only test:** no MDF/per-opponent pot-odds constant is introduced; the change is purely a
   scalar multiplier on existing merits (code-review assertion + a test that removing the multiplier
   recovers the HU merits exactly).
4. A 4-way SRP spot **where hero closes** maps and grades; a 4-way spot **with a live player behind hero**
   returns **None** ("no baseline yet") — assert both, from an engine-driven state (§1.2 shows both occur).
5. 5+-way is not claimed as a calibrated tier (label = binary bucket); `verify.sh` + build green;
   refuter-on-diff PASS.

**Why this order:** H1 is grounded in a measured 16.8/1000 reachability and a sourced range read — real,
buildable, high-value, high-confidence. H2 is a direction-only extrapolation with **no published 4-way
baseline** (§2.1) and a **thinner gradeable denominator** (§1.2/§4); it is legitimate as a *directional
push* but must never present a 4-way *frequency*, and its honest default outside the closing-seat SRP
shape is "no baseline yet." Doing H1 first delivers the biggest coverage win on the firmest footing;
H2 extends the frontier where the evidence is weakest, exactly where "no baseline yet" must stay a
first-class answer.
