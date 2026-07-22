# Research Vetting Verdict — Usability Matrix

Adversarial validity/usability review of the 7 research dumps feeding the poker-math calibration
spec and the persona/multiway modeling note. Verdicts: **USE-AS-IS** · **USE-WITH-CAVEAT** ·
**DOWNGRADE-TO-QUALITATIVE** · **DROP**. Target doc: **CALIBRATION SPEC** (solvable/derivable/
well-sourced) or **MODELING NOTE** (persona deltas / multiway / exploit magnitudes — the
"not-solved, estimate" layer).

Reviewer web-spot-checked the most load-bearing/suspicious numbers only (citations inline). Base
explainer reviewed for coherence: `Poker Math — Comprehensive Reference.md`.

---

## SAFE TO USE (hard-codeable into the CALIBRATION SPEC)

These are algebraic identities or numbers verified against a primary/credible source this pass:

- **EV / fold-equity / break-even formulas** (pushfold-shove-ev §1): `EV = F·P + (1−F)·[E·(P+B) − (1−E)·B]`; break-even bluff `F = Risk/(Pot+Risk)`. Pure algebra, corroborated multi-source.
- **EQR definition + formula** (equity-realization §1): `EQR = pot-share / equity`; 70%-pot-share/40%-equity → 175%. **Verified verbatim** at GTO Wizard glossary (gtowizard.com/en/glossary/equity-realization-eqr/).
- **Realized EV = raw equity × EQR × pot** as the industry-standard framing (equity-realization §1). Solved/derivable.
- **Continue rule** `raw_equity × R ≥ pot_odds_required_equity` (equity-realization §4). Direct algebraic consequence of the EQR definition.
- **Risk premium is ICM-only; cash OOP-disadvantage = equity realization, NOT risk premium** (facing-raise-risk-premium, whole doc). RP = ReqEquity(ICM) − ReqEquity(cEV); **verified** — every surveyed source keeps the terms separate. This is a *correction the base explainer must absorb.*
- **MDF splits across multiway defenders as ~n-th root of HU alpha** (cbet-and-multiway §3.3): 1%-pot bet 99%→~44% (9-way); 10%-pot 91%→~26% (8-way); "33% HU folds → ~58% each of two opponents." **Verified** (independent source restates the p² / n-th-root math verbatim). Pure arithmetic.
- **α / MDF / bluff:value-by-size tables** (preflop-3bet §5.1; already in base explainer §2.4/§3.2/§3.3). Closed-form game theory.
- **Blocker combinatorics** (preflop-3bet §4.1): holding one Ace cuts AA 6→3 and AK 12→8 (16→12 incl. suited). Exact combinatorics — USE-AS-IS. (The *ranking* A5s>A2s is qualitative — see below.)
- **Rake mechanism + BB-defense equity shift** (rake §2.2): ~30%→~35% raw-equity-needed under a $5 cap at $1/2; $5 rake = 29.4% of a $17 pot vs 13.5% of a $37 pot. **Verified** at Upswing. Label the 5-point figure "approximate, single-cap example."
- **C-bet-by-texture frequencies/sizings, heads-up SRP** (cbet-and-multiway §1): dry 33%-pot high-freq; wet 75%/125%; monotone straight board (QJT-mono) 33%-pot, checks-back-98%. Direct GTO Wizard solver outputs — USE-AS-IS as illustrative single-spot solver numbers (not universal constants).

---

## DO NOT USE / DOWNGRADE

- **DROP — base explainer's "IP worth ~5–10% realized equity vs OOP"** (Poker Math Reference §1.4, line 100). False precision; the one clean solver flop shows ~79% OOP / ~118% IP = **~39-point gap**, and illustrative extremes run to ~100 points. Replace with range-and-caveat framing (see equity-realization verdict below).
- **DROP — "60% average realization" behind the K9o/UTG example** as a *calibration constant* (equity-realization §2b). Untraceable to a primary solver run; usable only as a directional illustration.
- **DOWNGRADE — 10bb/15bb push/fold combo tables** (pushfold §2): single secondary source (deepfold.co). Keep the *shape* (widen as stacks shorten; SB ~50% at 10bb is directionally confirmed); do NOT hard-code exact combos without an HRC/ICMIZER pull. Also out-of-scope (app is 100bb cash).
- **DOWNGRADE — 5-bet range "QQ+/AK at 100bb"** (preflop-3bet §3): no disclosed-methodology source; forum/anecdote only. Keep as qualitative "value-heavy, shove-dominant."
- **DROP as sourced fact — 4-bet sizing multiplier "2.2–2.5× the 3-bet"** (preflop-3bet §2.3): the dump explicitly could NOT source it; base explainer §4.3/§4.5 states it as fact. Either derive/label as a convention or drop the precision.
- **DOWNGRADE — all exploit *magnitudes*** (player-types §4): no numeric "call X% wider" exists in any source. MODELING NOTE, qualitative-only, each paired with "approximate, not solved."
- **USE-WITH-CAVEAT — "no-flop-no-drop is universal"**: false. Some CA rooms rake every hand / use flat drop (one primary CA filing confirms). State as "most rooms, not universal."
- **GAP — live $2/$3 bb/100 rake cost**: no direct source exists. Derive analytically and label an assumption; do not present as sourced.

---

## Per-dump matrices

### 1. equity-realization.md — MOSTLY USABLE (concept solid, one base-doc correction forced)

| Claim | Verdict | Target | Caveat / citation |
|---|---|---|---|
| EQR = pot-share/equity; 175% worked example | USE-AS-IS | SPEC | Verified verbatim, GTO Wizard glossary |
| realized EV = raw × EQR × pot (industry standard) | USE-AS-IS | SPEC | Algebraic identity, 4 sources agree |
| Continue iff raw_equity × R ≥ pot-odds threshold | USE-AS-IS | SPEC | Direct consequence of EQR def |
| Drivers of R (position, initiative, playability, draws-over-realize, SPR) | USE-WITH-CAVEAT | SPEC | Directional consensus; magnitudes spot-specific, not constants |
| Single-spot solver examples (79% OOP/118% IP; 62%; A2s ~2%; K85dd draw 5.81 vs TPWK 5.36) | USE-WITH-CAVEAT | SPEC | Label each as illustrative single-flop, not aggregate |
| **"~5–10% IP/OOP edge" (base doc)** | **DROP** | SPEC | False precision; real single-flop gaps ~39pts+. **Replace** with: "IP realizes more; gap highly spot-dependent — single-digit-to-~15pts in shallow/high-playability spots, 20–40+pts when OOP range is capped/low-playability." Anchor on the 79%/118% example, labeled single-spot. |
| "60% avg realization" (K9o/UTG) | DROP as constant / keep directional | SPEC | Untraceable to primary solver; illustrative only |
| "solvers defend 5–15pts tighter than MDF" (BB) | DOWNGRADE-TO-QUALITATIVE | SPEC | Secondary summary, no primary study located |
| Acevedo/Janda heatmaps exist but figures not accessed | DROP (contents) | — | Existence sourced, numbers not — do not cite figures |

**Adjudication of self-flag:** The base doc's "~5–10%" IS too-narrow/false-precision. Correct replacement = the range-and-caveat framing above; if one anchor number is needed, use ~79% OOP / ~118% IP labeled as one illustrative flop, never a global constant.

### 2. rake-and-adjustments.md — MIXED (mechanism solid; the live $2/$3 bb/100 number is a genuine gap)

| Claim | Verdict | Target | Caveat / citation |
|---|---|---|---|
| Rake tightens ranges (mechanism); marginal/speculative hands cut first | USE-AS-IS | SPEC | Solved math, Upswing |
| BB-defense equity-needed ~30%→~35% under $5 cap; 29.4%/13.5% pot-fraction | USE-WITH-CAVEAT | SPEC | **Verified** at Upswing; label 5-pt figure "approx, single-cap example." Note conflicting 30%→50% secondary summary exists — use order-of-magnitude only |
| Rank order of what-moves-most (SB limp > cold-calls > BB defense > RFI; RFI changes shape) | USE-WITH-CAVEAT | SPEC | Consistent across sources; directional |
| "88 folds to 2x on BTN" | USE-WITH-CAVEAT | SPEC | Explicitly a *harsh* 10%-cap-2bb stress test, NOT live $2/3 — label as such |
| Live $2/$3 = ~5–10% pot, cap ~$4–6 (+$1 promo) | USE-WITH-CAVEAT | SPEC | Representative range, venue-specific, not a constant |
| No-flop-no-drop universal | USE-WITH-CAVEAT | SPEC | FALSE — "most rooms; some CA rooms rake every hand / flat drop" (1 primary CA filing) |
| **Live $2/$3 bb/100 rake cost** | **GAP — derive & label** | SPEC | No direct source exists. Derive analytically (pot × rake% × flop-seen freq, capped); label an assumption, not sourced |
| Online bb/100 anchors (~8–10 @2NL, ~4–5 @100–200NL) | USE-WITH-CAVEAT | SPEC | Online-only anchor; do not present as the live number |
| CardPlayer SB-limp claims | USE-WITH-CAVEAT | SPEC | 403-blocked, search-summarized — lower confidence |

**Adjudication of self-flag:** No direct live $2/$3 bb/100 figure exists → **derive-and-label**, do not downgrade the whole rake treatment to qualitative. The equity-shift and mechanism ARE well-sourced; only the bb/100 scalar is a gap.

### 3. pushfold-shove-ev.md — MIXED (formulas solid; combo tables weak + out-of-scope)

| Claim | Verdict | Target | Caveat / citation |
|---|---|---|---|
| Shove-EV formula + break-even fold freq | USE-AS-IS | SPEC | Algebra, multi-source |
| 15–20bb outer boundary / <10bb pure push-fold | USE-WITH-CAVEAT | SPEC | Consensus across Upswing/HRC/deepfold |
| Nash push/fold = equilibrium of simplified game tree | USE-AS-IS | SPEC | Solved/derivable |
| **10bb/15bb combo tables (UTG 12%, BTN 40%, SB 50%…)** | **DOWNGRADE-TO-QUALITATIVE** | MODELING NOTE | Single secondary source (deepfold.co). SB ~50% @10bb directionally confirmed; exact combos NOT — require HRC/ICMIZER pull. Also out-of-scope (100bb cash) |
| ICM tightens 10–25% on bubble | DROP (for this app) | — | Tournament-only; app is cash. Keep only as scope note |
| cEV is the correct cash short-stack framework (not ICM) | USE-AS-IS | SPEC | Correct; but short-stack cash is out of current scope |

**Adjudication of self-flag (deepfold combo tables):** DOWNGRADE — keep direction (ranges widen as stacks shorten; SB is the natural shover ~50% at 10bb), drop the exact combos as ground-truth. Note the whole regime is <20bb and thus out of the 100bb scope anyway.

### 4. preflop-3bet-4bet-5bet.md — MIXED-TO-WEAK on the upper tree (3-bet solid, 4/5-bet thin)

| Claim | Verdict | Target | Caveat / citation |
|---|---|---|---|
| 3-bet value/bluff split math (KK+ 0.9%, QQ+/AK 2.6%, TT+/AQ+ 4.7%) | USE-AS-IS | SPEC | Exact combinatorics, SplitSuit |
| Linear-IP / polarized-OOP construction | USE-AS-IS | SPEC | Near-universal consensus |
| 3-bet sizing ~3× IP / ~4× OOP | USE-WITH-CAVEAT | SPEC | Multi-source agreement on shape; exact multiple approximate |
| Position-pair 3-bet %s (BTN vs MP 0.9/2.11/3.01) | DOWNGRADE-TO-QUALITATIVE | SPEC | Weak page-level provenance; re-verify vs primary chart before hard-coding |
| 4-bet value core (QQ+/AK, JJ mixed) | USE-WITH-CAVEAT | SPEC | Consensus shape; single Medium solve for the 46-combo/JJ-37% figure — illustrative |
| A5s blocker mechanism (blocks calls, unblocks folds) | USE-AS-IS | SPEC | Exact combinatorics + GTO Wizard/GipsyTeam |
| A5s>A2s ranking | DOWNGRADE-TO-QUALITATIVE | SPEC | Qualitative ("classic choice"); no frequency-by-frequency solver table |
| **4-bet sizing multiplier "2.2–2.5× the 3-bet"** | **DROP as sourced fact** | SPEC | Dump explicitly could NOT source it. Base explainer states it as fact — relabel as a *convention* or drop precision |
| **5-bet range "QQ+/AK at 100bb"** | **DOWNGRADE-TO-QUALITATIVE** | SPEC | No disclosed-methodology source; forum/anecdote only. Keep "value-heavy, shove-dominant" |
| Preflop bluff-freq-by-size table | DROP (not found) | SPEC | Derivable from α/MDF but no source did it preflop — derive & label, don't fabricate |

**Adjudication of self-flags:** 5-bet 100bb table → DOWNGRADE (qualitative only). 4-bet multiplier → DROP as sourced (may keep as a stated convention). Both weakly sourced; neither safe as a "solved" number.

### 5. player-types-and-exploits.md — MOSTLY QUALITATIVE (correct destination = MODELING NOTE)

| Claim | Verdict | Target | Caveat / citation |
|---|---|---|---|
| VPIP/PFR/AF/3-bet population bands by type | USE-WITH-CAVEAT | MODELING NOTE | HUD-vendor bands; sample/era-dependent, boundaries fuzzy (Whale 55 vs 32 across two samples) |
| PokerTracker two-sample reference table | USE-WITH-CAVEAT | MODELING NOTE | Reproduces sources; disagreements shown = honest |
| WTSD/W$SD/fold-to-cbet/cbet% "good" bands | USE-WITH-CAVEAT | MODELING NOTE | Cross-source disagreement explicit; use "high-20s to low-30s" not a cutoff |
| **Exploit magnitudes** (cut bluffs, widen value, size up, call wider) | **DOWNGRADE-TO-QUALITATIVE** | MODELING NOTE | **Confirmed: qualitative-only.** No numeric "call X% wider" in any source. Pair each with "approximate, not solved" |
| "bluff to zero vs 20%-fold station" | USE-WITH-CAVEAT | MODELING NOTE | Direction sourced; the 20% is illustrative |
| GTO Wizard K44/J75r nodelock exploit | USE-WITH-CAVEAT | MODELING NOTE | Single solved board — does NOT generalize |
| No-unique-solution caveat | USE-AS-IS | MODELING NOTE | Directly sourced (GTO Wizard); the governing frame for this doc |

**Adjudication of self-flag:** Confirmed — exploit magnitudes go to the MODELING NOTE as qualitative-only, every number paired with "approximate, not solved" (matches the project's existing EV-labeling convention).

### 6. cbet-and-multiway.md — MOSTLY USABLE (with one number upgraded past the dump's own worry)

| Claim | Verdict | Target | Caveat / citation |
|---|---|---|---|
| Texture c-bet freqs/sizings (dry 33%, wet 75/125, mono-straight 33%/check-98%) | USE-AS-IS | SPEC | GTO Wizard solver outputs; label as illustrative single-spot |
| Wetness-parabola shape | USE-AS-IS | SPEC | Consistent GTO Wizard + Upswing |
| OOP c-bet ~⅓ aggregate | USE-WITH-CAVEAT | SPEC | Sourced from an MTT-context article; approximate for cash |
| Turn/river worked examples (~40% barrel; overbet vs half-pot) | USE-WITH-CAVEAT | SPEC | Run-out-specific; no universal turn-barrel % — label illustrative |
| Multiway fold-math (p²; ~58% each of two) + MDF n-th-root | USE-AS-IS | MODELING NOTE (math) | **Verified** independently. Arithmetic solid; how ranges implement it is heuristic |
| **"70% HU → 35% 3-way c-bet halving"** | **USE-WITH-CAVEAT** (upgraded from the dump's DOWNGRADE) | MODELING NOTE | Dump self-flagged as untraceable. Reviewer **found an independent source (ThinkGTO) attributing 70%→35% to "GTO Ranges+" solver output.** Still a secondary aggregator, not GTO Wizard primary — so: USABLE with "approximate solver aggregate, ~halving" label, NOT "solved." Do not cite as verbatim GTO Wizard output |
| No-unique-equilibrium-multiway (infinitely many; Pluribus) | USE-AS-IS | MODELING NOTE | Primary academic source (Brown & Sandholm, Science 2019) |

**Adjudication of self-flag (70%→35%):** Do NOT fully downgrade. The mechanism is verified AND the exact pairing now traces to a solver-aggregator secondary source. Keep it as USE-WITH-CAVEAT ("~halving, approximate solver aggregate"), not qualitative-only and not "solved."

### 7. facing-raise-risk-premium.md — USE-AS-IS (this doc is a correction, and it is right)

| Claim | Verdict | Target | Caveat / citation |
|---|---|---|---|
| Risk premium = ICM-only; RP = ReqEquity(ICM) − ReqEquity(cEV) | USE-AS-IS | SPEC | **Verified** — GTO Wizard glossary / O'Kearney / PokerCoaching |
| Cash chips linear → risk premium N/A in cash | USE-AS-IS | SPEC | Verified; directly sourced |
| Cash OOP disadvantage = equity realization, NOT risk premium | USE-AS-IS | SPEC | **The core correction.** GTO Wizard cash 3-bet-pot article frames it entirely via EQR |
| Correct pricing = pot odds tempered by EQR, MDF as floor | USE-AS-IS | SPEC | Derivable; consistent 4 sources |
| Spot-specific OOP numbers (33.9% vs 19.7% check freq; <2% EQR example; 97o folds >20%) | USE-WITH-CAVEAT | SPEC | Illustrative single spots, not general coefficients |
| No general "defend X% tighter OOP" constant | USE-AS-IS (as a *non-claim*) | SPEC | Correctly refuses to fabricate one |
| BB-3bet-vs-UTG 54.4%/45.6% equity | DROP until re-fetched | — | Search-snippet only, not full-text verified |

**Adjudication of self-flag:** CONFIRMED. "Risk premium" is ICM-only; the cash OOP/range-disadvantage effect is equity realization. **This forces a correction on the base explainer**, whose Appendix and §5.8 gesture at OOP disadvantage without ever naming risk premium — good — but any spec text that reaches for "risk premium" in a cash context must be renamed "equity-realization discount."

---

## Cross-cutting corrections the research forces on the base explainer

1. **§1.4 "IP worth ~5–10% realized equity vs OOP" → DROP.** Replace with spot-dependent range framing (single-digit-to-~15pts typical, 20–40+pts when OOP range capped). This is the single most important base-doc fix.
2. **Never use "risk premium" for cash-game OOP pricing.** It is ICM-only. Cash = equity-realization discount + MDF floor. (Base doc mostly avoids the trap; enforce it in spec text.)
3. **§4.3/§4.5 4-bet "~2.2–2.5× the 3-bet" and 5-bet "QQ+/AK"** are conventions/heuristics, not sourced solver numbers — relabel or drop the precision.
4. **§5.7 "c-bet roughly halves HU→3-way"** — keep, label "approximate solver aggregate (~70%→35%)," MODELING NOTE, not "solved."
5. **Rake:** no-flop-no-drop is NOT universal; live $2/$3 bb/100 cost must be derived-and-labeled, not sourced.
6. **Push/fold combo tables** are secondary-sourced and out-of-scope (100bb) — do not hard-code.
