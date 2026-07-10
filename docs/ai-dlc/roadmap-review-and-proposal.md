# Roadmap Review & Proposed Changes — "Make me a winning player," not "grade more spots"

> Status: **APPROVED (July 2026).** Direction: engine-first sequencing retained, bound by a Learning-Experience mandate
> (true teacher across all streets, interleaved — non-deferrable). In-app theory: concept-cards-now, lessons-later.
> First build: the cheap-wins bundle. `roadmap.md` updated accordingly (see its "Direction update" section).
> Inputs: live app walkthrough (Playwright), full `roadmap.md` read, research docs 01–08, and (folding in) the
> SOTA UX research now running in `best-practices-drafts/`.

## Thesis (the one thing to fix)

The roadmap is **excellent on the grading engine** (swappable provider, freq+EV, content-as-data, street-by-street
coverage) and **thin on the learning experience** (teaching the *why*, a cohesive product, onboarding, a study path).
It optimizes *"grade more spots across more streets."* To actually make you a **winning $2/$3 player**, the app must
**teach + test + organize** — not just grade. The core proposal: add a first-class **Learning Experience** pillar and
**rebalance sequencing** so the product becomes a cohesive teacher *sooner*, interleaved with the turn/river build —
instead of finishing ~53 postflop engine tickets before the human-facing learning gaps get touched.

---

## What the app does WELL today
- **Sound architecture** — swappable `StrategyProvider`, freq+EV results, content-as-data, migrations. Genuinely future-proof.
- **A real drilling loop** — spot → decide (keyboard) → graded **freq + EV** → SM-2 re-surfacing. The engine works.
- **Broad preflop** + flop **c-bet / facing-c-bet / facing-check-raise**, graded by texture + range-advantage.
- **Range grid, stats strip, texture & equity quizzes, light/dark theme.** Leak tracking + spaced repetition exist.

## What it does POORLY
- **Teaching (the headline gap).** Post-answer feedback is **one generated sentence** ("AKo: raise is the play from CO")
  + an EV/freq list. The roadmap's promised **3-tier feedback** (E: flash → "why" → deep dive) is **not built** — there
  is one flat tier, and the "why" is a *tautology*. It says *what*, never *why*.
- **Optimal vs Acceptable vs wrong commentary** — only a colored label + `−EVbb`. No explanation of *why* Acceptable is
  close, or what a mistake concedes *conceptually*. Authored `rationale` isn't surfaced.
- **Cohesion / information architecture** — a flat stack of **3 view-tabs + 7 mode-buttons**, no grouping, hierarchy, or
  ordering. Your "random buttons everywhere" worry is real.
- **EV realism** — proxy EVs are shown as hard numbers (`fold −3.37bb`) with no "approximate" framing; can mislead.
- **Study vs test** — the **169-hand answer chart is visible while you decide**; no "test me blind" vs "study with the
  chart" distinction, so a drill can be passively read off the grid.

## What it does NOT do AT ALL
- **No in-app education.** The rich strategy docs (01–08) are **invisible to the user** — zero lessons, zero theory,
  zero concept explanations. The app can't teach blockers, range advantage, MDF, board texture… even though we now have
  vetted content for all of it.
- **No onboarding / first-run orientation** — you cold-start into a random `vs_limpers` spot with no guidance.
- **No guided curriculum / "what to work on next"** — mastery-gating (H) isn't surfaced; there's no study plan or skill map.
- **No mental-game / bankroll / move-up readiness** (Phase 4 — fine later, but it *is* part of "becoming a winning player").

---

## Fair scorecard — does the roadmap ALREADY plan to fix these?
| Gap | In roadmap? | Reality |
|---|---|---|
| Full street coverage (turn/river/multiway/full-hand) | **Yes** (2f–2k) | Genuinely planned & well-sequenced. Keep. |
| 3-tier "why" feedback | Listed (E, Phase 1) | **Not delivered.** Needs re-prioritizing + a real spec. |
| Mastery / curriculum ladder | Listed (H, Phase 1/2) | Not built, not surfaced in UX. |
| **In-app theory / lessons** | **Absent** | **Biggest omission** — no learning-content pillar at all. |
| Cohesive IA / onboarding | Implied under UX (K) | Not called out as a problem; currently disjointed. |
| Research errata (05–08 fixes) | Not yet | New — fold into near-term tickets. |

---

## Proposed changes to the roadmap

**1. Add a first-class "Learning Experience" pillar (new capability P).** In-app lessons/theory surfaced from docs 01–08
(concept cards linked *from* missed reps), enriched multi-tier explanations, onboarding, and a curriculum/home hub. Pull
the highest-leverage parts **early**, not after all of turn/river.

**2. Actually deliver 3-tier feedback (re-prioritize E, spec it).** Tier 1 verdict+EV (have) → Tier 2 *why* (the concept
at play + strategic reasoning, from `rationale` + research) → Tier 3 deep dive (link to the lesson + range context).

**3. Enrich Optimal/Acceptable/wrong commentary.** Explain *why* Acceptable is defensible and what the mistake concedes
conceptually — not just an EV delta. Surface authored `rationale`. Frame proxy EVs as approximate until Phase 3.

**4. Fix cohesion / IA + onboarding.** Group modes by street/purpose, add a home/curriculum hub, first-run orientation,
a **study-vs-test toggle**, and **reveal-the-chart-after-answer**. *(Specifics fold in from the Thread-B SOTA research —
see section below.)*

**5. Fold research errata (05–08) into near-term fix tickets** *(cheap, high-trust, independently verified):*
   - Preflop leaks: UTG opens KQo, HJ opens QJo, vs-4bet CO calls QQ too light (doc 05).
   - Postflop grader leaks: `Texture.suitedness` & `Texture.pairing` **computed but never read**; `range_advantage()`
     ignores the ace-high exception (doc 06, grep-confirmed).
   - `hand_rank` **undervalues pocket pairs** (55/66/77) — regrade ordering from computed equity (doc 08, reproducible).
   - **Credible interim EV**: wire `equity.py` + doc-06 fold tables for a real fold-equity EV — a cheap upgrade *before*
     the Phase 3 solver (doc 08).

**6. Surface curriculum / mastery + a study plan (re-prioritize H).** "What to work on next," a skill map, session shape
(~10–20 min), interleaving — per learning-science doc 03.

**7. Re-sequence: interleave learning-experience work with the engine build.** Each new street (2f–2i) ships **with its
lesson + enriched feedback**, not just a grader. Rebalance so the app teaches sooner.

**8. Reconcile a discrepancy:** the running app has **no "Challenge" mode** despite prior "merged" status — verify what's
actually on `main` before planning around it.

---

## Proposed re-sequencing (high level, for discussion)
- **Near-term (next 1–3 epics):** (a) 05–08 errata fixes [cheap, high-trust]; (b) **real multi-tier explanations +
  surface rationale/theory** [closes the teaching gap]; (c) **IA / onboarding cleanup** [cohesion].
- **Mid:** continue turn/river (2f→2i) — but each street lands *with* its lesson + enriched feedback.
- **Keep as-is:** multiway (2j), full-hand (2k), solver swap (Phase 3), live/mental-game (Phase 4).

---

## SOTA UX specifics — FOLDED IN (Thread-B research, complete)
Three example-rich docs now in `best-practices-drafts/` (learning-pedagogy · poker-coach & data-viz · IA/visual).
**Biggest cross-cutting insight: the highest-leverage fixes are cheap** — much of the "teaching" upgrade is *surfacing
data the code already has* (`Entry.rationale`, `EvaluationResult.rationale_tags`, the SM-2 due-queue in `srs.py`), and
the top IA win is a front-end-only reshuffle. This is not a rebuild.

**Feeds proposal #2/#3 (teaching + verdict tiers):**
- **Tiered "why"** — verdict → reasoning → deep-dive (GTO Wizard, Duolingo). Tier-2 is mostly *surfacing the existing
  `rationale` / `rationale_tags`*, not new content.
- **Named 5-tier decision quality**, not binary — reuse ONE scale (Best→Blunder, à la chess.com 8-tier / GTO Wizard
  5-tier) identically across feedback, hand-history, and analytics.
- **Error-personalized explanations** (Duolingo Smart Tips) + **progressive hint ladders** (chess.com). Avoid DTO's
  **"black box"** pitfall — numbers without a one-line *why*.

**Feeds proposal #4 (IA / study-vs-test / grid):**
- **Split the 7 buttons into two labeled axes** — *spot-selection* (Random/Review/Leak-focus/Exploit) × *situation*
  (Preflop/Postflop/vs-c-bet/vs-check-raise). Front-end-only; biggest IA win for least cost.
- **Study/Test = two-layer control** — named mode **plus** a per-panel reveal toggle + pause-after-mistake.
- **Render the answer grid ABSENT pre-decision, not blurred** (blur leaks color blobs). **Reveal after answer.**
- **Grid cells are frequency mixes → proportional bars/stacks, not one dominant color** (the #1 grid oversimplification).
- **ARIA is missing entirely** on RangeGrid + DecisionBar — apply W3C APG grid + toolbar patterns; announce feedback via
  a live region; fix focus stranding on disabled buttons post-grade.
- **Design tokens need scales** (type scale, `--space`/`--radius`/`--shadow` ramps, a felt→panel→card→overlay elevation model).

**Feeds proposal #6 (onboarding / curriculum / engagement):**
- **A single visible learning PATH**, not a branching tree (Duolingo's own pivot) + **legible named mastery thresholds**.
- **A placement diagnostic** on first run (you're a competent novice, not a zero-start) to seed the path + SRS.
- **Surface the SM-2 due-queue as "today's plan"** (already computed — pure surfacing) + calendar-heatmap consistency +
  **streak with forgiveness** (Duolingo's streak-freeze cut churn 21%).
- **"Concept card" content model** — bidirectionally linked, reusable; link a missed rep → its concept card → the drill.

### Prioritization — cheap wins vs bigger bets
| Tier | Move | Cost |
|---|---|---|
| **Cheap wins (do first)** | 2-axis mode split · surface `rationale` in feedback · 5-tier verdict scale · grid-absent-then-reveal · study/test toggle · ARIA + live-region + focus fix · 05–08 errata fixes | Mostly front-end / surfacing |
| **Mid bets** | Multi-tier "why" + hint ladder · "today's plan" queue view · analytics bucketing + dual-unit EV loss · token scales/elevation · credible interim EV (equity.py + fold tables) | New UI + light backend |
| **Bigger bets** | Concept-card lesson system + learn↔drill interleaving · placement diagnostic + curriculum path · mastery ladder surfaced | New content model + pillar |

---

## Decisions for you (at the gate)
1. **How aggressively to pull the Learning Experience forward** vs finish the postflop engine first.
2. **Scope of in-app theory** — full lessons vs lightweight concept-cards linked from feedback.
3. **Whether to do the 05–08 errata fixes now** as a quick first build (they're cheap and verified).
