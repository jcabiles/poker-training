# Sol + Opus synthesis — poker-math docs adversarial review

**Date:** 2026-07-21. Two fresh-context adversarial reviewers, independent tooling:
- **Sol** (Codex / GPT-5-class, `codex exec`) — inline-content prompt, independent re-derivation + own poker-theory knowledge. Findings: `sol-findings-raw.md`.
- **Opus** (Claude, live WebSearch/WebFetch) — recomputed every formula in Python, checked each number against authoritative sources. Findings: `opus-findings.md`.

## Headline: they converge

- **Zero arithmetic errors, both reviewers, independently.** Every core formula — MDF `P/(P+B)`, alpha `B/(P+B)`, break-even-to-call `B/(P+2B)`, pure-bluff break-even `B/(P+B)`, polar river bluff fraction `f/(1+2f)` with value:bluff `(1+f):f`, the multiway n-th-root, 3-bet combinatorics, rake pot-fractions, both EV forms — recomputes exact to the decimal.
- **Both explicitly conclude the docs give the RIGHT targets for the Epic-4 fix.** The size-dependent direction the two confirmed bugs need ("defense and bluffing both scale with bet size; a flat rate is broken") is stated correctly.
- **The `[SOLVED]/[SOURCED]/[DERIVED-ASSUMPTION]` labeling discipline is honest** (both).

## Where they AGREE on a problem (these are the real signal)

| # | Issue | Sol | Opus | Actionable |
|---|---|---|---|---|
| **A1** | **MDF over-labeled as a defense "floor" / "defend (call+raise) ≥ X%".** `P/(P+B)` is the flat-**call** indifference form; GTO Wizard explicitly warns it "doesn't work with a raise." It's a maximally-exploitative fold-*ceiling*, not equilibrium defense. Real solver ranges sit **below** raw MDF pre-river (bluffs carry equity). | CRITICAL #1 | MODERATE M1+M2 | **Highest priority for Epic-4.** Use the **alpha column as a fold-ceiling sanity check** — that correctly catches the confirmed *price-blind-defense* bug. Do **NOT** hard-assert "fold ≈ MDF" on flop/turn or vs polar/capped bettors, or the grader marks a correct bot wrong. |
| **A2** | **Multiway n-th-root defense assumes symmetric + independent opponents.** Arithmetic is right (√0.33→42% each); the idealization never holds at a real table (correlated, asymmetric, sequential, can raise). | CRITICAL #3 | MODERATE M3 | Direction only ("each defends less than HU; fold equity collapses"). **Never a per-opponent grading constant.** |
| **A3** | **"~70%→~35% c-bet halving" too weak to be a calibration target.** | MODERATE #6 | could-not-break (real pattern, illustrative) | Keep as a *principle* ("multiway c-bet drops substantially"), not a validation number. |
| **A4** | **EQR examples (79%/118%/~2%) are single-spot extremes, not bands.** | MODERATE #9 | MODERATE M6 | Keep "never a global constant" adjacent to every instance; don't hard-code `raw×R`. |
| **A5** | **Rake bb/100 (35–60) is table-level, not per-hero.** | MODERATE #8 | MINOR N5 | Label allocation method; keep "self-derived, uncited" loud. |

## The ONE real disagreement

**"Multiway has no unique equilibrium."**
- **Sol** calls this **overstated (CRITICAL #2)**: finite multiplayer games *do* have Nash equilibria; phrasing like "provably no unique optimal strategy / no game-theoretic solution" risks implying non-existence.
- **Opus** treats the docs' wording as **correct and well-sourced** (cites Brown & Sandholm approvingly), not a finding at all.

**Resolution — they're compatible.** Both agree on the underlying fact: multiplayer equilibria **exist but are non-unique and lose the two-player-zero-sum minimax (unexploitability) guarantee.** Sol is objecting to loose phrasing; Opus read the literal "no *unique* equilibrium" as fine. Fix = tighten the wording to "equilibria exist but are non-unique and carry no minimax guarantee" everywhere the docs currently say "no solution / provably no unique optimal strategy." Low-effort, both would accept.

**Severity gap (not a contradiction):** Sol labels 3 items CRITICAL; Opus labels 0 CRITICAL. On *substance* they agree — every Sol "CRITICAL" is an *applicability/labeling* issue, not wrong math, which is exactly Opus's MODERATE framing. Neither found a number the bot/grader would compute wrong.

## Net for Epic-4 (bot-math-fix)

1. **The docs are trustworthy as the yardstick.** Ground-truth numbers are exact; fix slices can cite them.
2. **Bake in the A1 guardrail:** alpha = fold-ceiling sanity check (catches price-blind defense); pot-odds-vs-actual-value:bluff for river bluff-catches; **no blanket "fold≈MDF" assertion on flop/turn.** This is the single most important cross-reviewer takeaway and must shape the hero-grading slice.
3. **A2–A5 → "directional, not a constant"** guarantees for multiway, c-bet, EQR, rake — none become hard grading targets.
4. **Doc tightening (optional, low-effort):** unify EV notation across docs 01/02; soften the multiway-equilibrium phrasing; keep single-spot EQR extremes labeled.
