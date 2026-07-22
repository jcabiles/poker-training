# Poker-Math 3-Doc Set — Final Adversarial Review

Final integration review of the three Obsidian docs (Explainer, Calibration Spec, Modeling Note)
against the source-of-truth `docs/research/_vetting-verdict.md`. All math re-derived from scratch;
every DROP/DOWNGRADE item hunted for leakage. Skeptical pass.

**Bottom line: PASS on 4 of 5 checks. One real defect (a mislabeled multiway figure) — a
labeling/wording error, not a fabrication or an arithmetic error.**

---

## Ranked problems

### 1. [MODERATE — labeling + internal consistency] Multiway "~58%" is a FOLD frequency, but the spec calls it a "continue requirement"

**Where:** Calibration Spec §9 (line 121):
> "the **per-player continue requirement** scales roughly as the **n-th root** of the heads-up
> defense: e.g. '33% HU folds → ~58% each of two opponents.' **[SOLVED — verified arithmetic]**"

**The problem.** The arithmetic is fine (√0.33 = 57.4% ≈ 58%), but the *quantity* is mislabeled.
Tracing to the source dump (`cbet-and-multiway.md` line 73) and the verdict (line 23), the 58% is a
per-opponent **FOLD** frequency in the *bluffing* context: a bluff that needs a combined 33% fold
heads-up needs each of two opponents to **fold** ~58% (0.58² ≈ 0.33). The per-player **continue /
defend** figure is the complement, **~42%**. So calling 58% a "continue requirement" is wrong by
~16 points.

**Made worse by a second conflation in the same sentence.** The other worked numbers from the same
n-th-root family (dump lines 87–89: "1%-pot 99%→**44%** 9-way; 10%-pot 91%→**26%** 8-way") are
per-player **DEFENSE** figures (verified: 1 − (1/101)^(1/8) = 43.8% ≈ 44%). So §9 as written mixes
two opposite quantities under one label: 44%/26% are *defense*, 58% is a *fold*. And "n-th root of
the heads-up **defense**" is imprecise — the root is taken of the heads-up **alpha/fold** (0.33),
not the heads-up defense (0.67); √0.67 = 0.82, not 0.58.

**The same slip is echoed in the Modeling Note** §3 (line 61): "the per-player **continue**
requirement scales ~as the **n-th root** of the HU defense" — inherits the identical wrong framing.

**Fix (spec §9 + modeling §3).** Either:
- (a) keep 58% but relabel it correctly: "a bluff needing 33% combined fold heads-up needs each of
  two opponents to **fold ~58%** (√0.33); equivalently each must **continue ~42%**"; and change
  "n-th root of the heads-up defense" → "n-th root of the heads-up **alpha (fold share)**"; OR
- (b) to keep the "continue requirement" framing, use the 44%/26% examples (which ARE per-player
  defense) and drop or restate the 58% as its complement (42%).

The `[SOLVED — verified arithmetic]` tag is defensible for the *number*, but the surrounding prose
is not internally consistent, so this is a genuine failure of Check 5 (and partially Check 3).

---

## Everything that PASSED (verified, not assumed)

**Math re-derivations (Check 2) — all exact:**
- MDF 100/175 = **57.1%**; break-even 75/250 = **30%**. ✓
- By-size table: ⅓ 75/25/20 · ½ 67/33/25 · ⅔ 60/40/28.6 · ¾ 57/43/30 · pot 50/50/33.3 · 2× 33/67/40. ✓
- EQR 0.70/0.40 = **175%**. ✓
- Polar-river bluff fraction f/(1+2f): 20/25/28.6/33.3/40%; value:bluff 4:1…1.5:1. ✓
- Multiway √: √0.33 = **57.4% ≈ 58%** (arithmetic correct — only the *label* is wrong, see #1).
- Rake bb/100: 30–40 raked × $3.5–4.5 / $3 = **35–60 bb/100** (corners: 30×3.5/3=35, 40×4.5/3=60). ✓
- Rake pot-fraction: 5/17 = **29.4%**, 5/37 = **13.5%**. ✓
- K9o realization: 0.35 × 0.60 = **21%** realized. ✓
- Rule-of-2&4 corrections: 9 outs one card 9/47 = 19.1% (×2 says 18); flush by river 35.0% (×4 says
  36); 15 outs two cards = 54.1% (×4 says 60, overstates). ✓ All correct.
- 3-bet combinatorics: KK+ 0.9%, QQ+/AK 2.6%, TT+/AQ+ 4.7% (of 1326). ✓ (pure combinatorics — the
  `[SOLVED]` tag is right despite SplitSuit attribution.)

**Check 1 — Fidelity to the verdict (PASS).** No DROP/DOWNGRADE item reappears as a hard/solved fact:
- "~5–10% IP/OOP edge" — DROPPED and explicitly corrected (Explainer §1.4 line 105; Spec §2 lines
  47/55). Replaced with the spot-dependent range + the 79%/118% single-flop anchor, labeled illustrative.
- 4-bet "2.2–2.5×" — labeled `[CONVENTION]`, "NOT solver-sourced" (Spec §4 line 74; Explainer lines
  296/317). Never stated as solved.
- 5-bet "QQ+/AK" — `[DOWNGRADED — qualitative]`, "forum-level, not solver-sourced" (Spec line 75;
  Explainer line 297).
- Deepfold push/fold combos — `[DIRECTIONAL — single secondary source; out of 100bb scope]` (Spec §7
  line 104; Modeling §4 line 69). Exact combos never hard-coded.
- "Risk premium" for cash — correctly quarantined as ICM-only; cash renamed "equity-realization
  discount" (Spec §8). ✓
- "No-flop-no-drop universal" — corrected to "common but NOT universal" (Spec §6 line 93). ✓
- Position-pair 3bet %s (BTN vs MP 0.9/2.11/3.01, DOWNGRADE) — correctly ABSENT from both math docs. ✓
- Conflicting rake 30→50% figure — flagged "order-of-magnitude only." ✓

**Check 3 — Labeling (PASS, one exception).** SOLVED/SOURCED/DERIVED-ASSUMPTION/QUALITATIVE/HEURISTIC
tags are applied appropriately throughout. The live $2/$3 bb/100 is correctly the sole
`[DERIVED-ASSUMPTION]`. Nothing estimate-y is tagged `[SOLVED]` — **except** the multiway §9 case in
#1, where the number is solved but the labeled *meaning* is wrong. Persona magnitudes and multiway
implementation are correctly `[SOURCED estimate]`/`[HEURISTIC — not solved]` in the modeling note.

**Check 4 — Explainer corrections landed (PASS, all present):**
- §1.4 R range not "5–10%" — line 105, revised to spot-dependent range. ✓
- RFI "9-max seat frame" + map-by-seats-behind — line 283. ✓
- 4-bet/5-bet relabeled as convention/forum-level — lines 296–297, 317. ✓
- §5.7 multiway "~70→35 approx" rule-of-thumb, "see the Modeling note" — line 406. ✓
- §6.2 AFq formula (bets+raises)/(all actions)×100, distinct from AF ratio — line 446. ✓
- Rule-of-2&4 correction (×2 understates, ×4 overstates >8 outs) — line 81. ✓
- Companion-docs callout — lines 15–18. ✓

**Check 5 — Cross-links + internal consistency (FAIL, due to #1 only):**
- All 5 `[[wikilinks]]` resolve to the correct doc titles (explainer ↔ spec ↔ modeling note). ✓
- Solvable-vs-estimate separation held: persona magnitudes + multiway *implementation* live in the
  modeling note; the math docs assert only the arithmetic. ✓
- **Contradiction:** the multiway "continue requirement = 58%" framing (Spec §9 + Modeling §3)
  contradicts the underlying fold/defense semantics and mixes two opposite quantities — see #1.

---

## PASS / FAIL summary

| Check | Verdict |
|---|---|
| 1. Fidelity to the verdict (no DROP/DOWNGRADE as hard fact) | **PASS** |
| 2. Math (all new worked examples re-derived) | **PASS** (every number exact) |
| 3. Labeling (nothing estimate-y tagged solved) | **PASS** (one meaning-mislabel — see #1) |
| 4. Explainer corrections landed | **PASS** (all 7 present) |
| 5. Cross-links + internal consistency | **FAIL** — multiway continue/fold mislabel (#1) |

**One real defect total, severity MODERATE:** the multiway §9/§3 "58% = continue requirement"
mislabel. It is a wording/consistency error (the arithmetic is correct); fixing the two sentences
noted in #1 clears it. No arithmetic errors, no fabricated sources, and every DROP/DOWNGRADE item
stayed out as a hard fact.
