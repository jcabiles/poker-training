# Professional Teacher Rework — Roadmap (updated 2026-07-02)

> Living, pass/fail, resumable. A fresh context should read this and know exactly what's left.
> **Supersedes the sequencing** in `roadmap-review-and-proposal.md`: the Learning-Experience pillar becomes the **Now**
> column; turn/river coverage (2f–2k) moves to **Next/Later**. PRD: `docs/ai-dlc/prd/professional-teacher-rework.md`.
> Contract maps (honest current-state): `docs/ai-dlc/contracts/{feedback-evaluation,persistence-datamodel,frontend-ia-tokens}.md`.
>
> **Gate decisions (2026-07-02):** audience = *"me now, others later"* (seams not machinery) · *teaching + UX first* ·
> *concept-cards now, lessons library later* · appetite = *large/comprehensive*.
>
> **Resume rule:** work the Now column top-down; do the first unchecked slice; verify its pass/fail actually passes
> before marking `[x]` (agents falsely mark work done). Hand ONE slice at a time to `/ai-dlc`.

---

## North-star outcome(s) — the WHY

- **Primary (you):** *become a winning $2/$3 player.*
  Metric: trained-spot **decision accuracy ↑ / EV-loss ↓** across sessions (already computed by `services/stats.py`).
  Baseline: today's accuracy + EV-loss per leak category → Target: sustained upward trend on the pressure spots that gate the move-up.
- **Enabling (others later):** *a cohesive teacher a stranger can pick up.*
  Metric: **cold-start → first-understood-rep** is walkable with zero author explanation.
  Baseline: cold-start dumps you into a random `vs_limpers` spot, no onboarding, tautological "why" → Target: oriented,
  placement-seeded, every rep links to the concept behind it. *Seams, not the multi-user machinery.*

**Why these, and why now:** the engine already grades the most-played spots (all preflop + all flop). ~40 more turn/river
tickets deepen a tool that still doesn't *teach*. Highest leverage now = the human-facing layer. The maps confirm the
teaching data is *partly* free (`chosen_eval` unrendered, 12 authored exploit rationales, `due_items()` already computed)
and *partly* real new work (baseline preflop + all postflop are templated tautologies) — sized honestly per slice below.

---

## NOW — spec-ready vertical slices (work top-down; ICE = Impact·Confidence·Ease, 1–10)

> Each is thin + end-to-end + observable. ICE surfaced as the "why" for order — a lens, not a law; re-order at the gate.

- [x] **N1 — Tiered feedback shape (teaching walking-skeleton).** *(done 2026-07-02: FeedbackTiers via pure domain/feedback.py composer + TieredFeedbackProvider wrapper in the factory — every provider inherits; chosen_eval rendered; deep-dive collapsed; refuter pass)* ICE 9·8·6.
      **Problem:** post-answer "why" is one flat, tautological string (`grading.py:196` "AKo from CO: raise is the play");
      the promised verdict→reasoning→deep-dive was never built, and `chosen_eval` is delivered-but-never-rendered.
      **Outcome-link:** primary (teach the why) + enabling (stranger understands a rep).
      **Solution:** add a **structured tiered field** to `EvaluationResult` (verdict / reasoning / deep-dive as distinct
      fields — NOT parsing the one prose slot), author it via a **shared post-processing wrapper** so a future solver
      provider inherits it (the teaching seam), render the tiers in `FeedbackPanel` incl. the free `chosen_eval`
      (freq/EV of the action you actually picked). Update the FE type surface to match the new shape — **manual `types.ts`
      edit is acceptable** until the Next "FE type-gen CI gate" wires `gen:api`→`schema.d.ts` (that pipeline is unwired
      today; nothing imports `schema.d.ts`). *(Recommended: consider pulling that gate into Now before N1/N5 — both touch
      API shapes and would pay for it twice.)*
      **Pass/fail:** a graded drill renders ≥2 distinct tiers incl. chosen-action freq/EV; postflop+exploit reasoning is
      non-tautological; the new field appears in `types.ts` and typechecks against usage; `./scripts/verify.sh`→
      `BACKEND VERIFY OK` + FE `typecheck && build` clean; locked string-assert tests (`test_grading.py:43,204,225-237`)
      updated deliberately.
      **Appetite:** ~1 epic. **No-gos:** don't author baseline-preflop prose here (that's N3); no DB persistence of rationale.

- [x] **N2 — Accuracy debt paydown.** *(done 2026-07-02: CW-3b via embedded equity-vs-random table replacing the proxy — false ties dissolved; CW-2b noted; doc-06 fold-equity EV wired into grade_cbet; EVs labeled ≈ in UI; both refuters pass)* ICE 7·8·6.
      **Problem:** grades we're about to *teach from* have known leaks — teaching amplifies a wrong grade. CW-3b
      (pocket-pair ranks) was **reverted** in the Challenge merge; CW-2b unresolved; EVs shown as hard numbers though proxy.
      **Outcome-link:** primary (trustworthy accuracy metric).
      **Solution:** anchor pocket-pair ranks to computed-equity ordering in `hand_rank.py`, **reconciling
      `test_hand_rank.py` determinism/tie model** (don't just bump a coefficient); CW-2b one-line documented scope note in
      `postflop.py`; wire a **credible interim fold-equity EV** from `equity.py` + doc-06 fold tables; label proxy EVs
      *approximate* in `FeedbackPanel` until Phase 3.
      **Pass/fail:** `pytest` green incl. updated hand-rank expectations; EV labeled approximate in the UI; `verify.sh` +
      FE build clean. **Appetite:** ~1 small epic. **No-gos:** no solver tables; don't touch `spot_signature()` (orphans SRS).

- [x] **N3 — Authored strategic rationale (content path + first tranche).** *(done 2026-07-03: non-exploit preflop + postflop rationale paths wired into authored_rationale; rfi 6/6 + vs_rfi 6/6 + new content/postflop/cbet.json 3/3 authored, doc-grounded; refuter pass)* ICE 9·7·4.
      **Problem:** the bulk teaching gap — every non-exploit preflop pack has **zero** authored `rationale` (~85% of reps),
      and postflop graders **never read `Entry.rationale`** at all. N1's tiers are empty without this.
      **Outcome-link:** primary (teach the why across streets).
      **Solution:** wire a content-pack `rationale` path into the **postflop graders** (they take range strings today, not
      `Entry`), and **author** `rationale` for the first preflop tranche (`rfi` + `vs_rfi`). Remaining packs → Next.
      **Pass/fail:** RFI + vs-RFI + at least one postflop node render non-tautological authored reasoning sourced from
      content (not f-strings); content validates against the pack schema; `verify.sh` + tests green.
      **Appetite:** ~1 epic. **No-gos:** not all packs (tranche only); no new prose-generation model — authored data.

- [x] **N4 — Design-system foundations (tokens · scales · elevation).** *(done 2026-07-02: --text/--space/--radius ramps + felt→panel→card→overlay shadows both themes; all raw px + rgba tokenized; refuter pass)* ICE 6·9·7 (cheap enabler).
      **Problem:** `tokens.css` has solid semantic colors but **no type scale, no space/radius/shadow ramps, no
      felt→panel→card→overlay elevation model**; font sizes are raw px scattered across `app.css`. No visual hierarchy for a hub.
      **Outcome-link:** enabling (professional/attractive) — unblocks N6/N7 visuals.
      **Solution:** add `--text-*` type scale + `--space/--radius/--shadow` ramps + an elevation model to `tokens.css`;
      refactor raw-px/`rgba` usages to tokens; keep AA contrast + visible focus both themes.
      **Pass/fail:** token scales exist and are used (no new ad-hoc px/hues); contrast check passes light+dark; FE build clean.
      **Appetite:** ~1 small epic (pure FE). **No-gos:** no component redesign here (tokens only); don't restyle the grid (N5).
      *(INVEST note: a near-horizontal enabler, kept standalone deliberately — it DOES change observable contrast/focus, is
      cheap, and de-risks N6/N7 by giving them a real visual hierarchy to build on. Fold into N6 if you'd rather not ship it alone.)*

- [x] **N5 — Frequency-mix grid cells (backend contract + FE render).** *(done 2026-07-03: range_grid() returns per-action freqs; stacked-segment cells with mix aria-labels; challenge.py adapter lossless for RFI; orphaned mixed legend dropped; refuter pass)* ICE 6·8·4.
      **Problem:** grid cells show one dominant color; the real per-action mix is computed then **collapsed to a single
      label** in `range_grid()` (`grading.py:241-257`) before the wire — the #1 grid oversimplification. It's a *backend*
      contract, not a FE-only change.
      **Outcome-link:** enabling (truthful, professional data-viz).
      **Solution:** widen `range_grid()` + the API response to return **per-action frequencies**; restructure
      `RangeGrid.tsx` cell markup + CSS into proportional stacked bars; update the FE type surface for the new shape
      (**manual `types.ts` edit acceptable** until the Next CI-gate wires `gen:api`; nothing imports `schema.d.ts` today).
      **Pass/fail:** a mixed-frequency handclass renders proportional segments; API returns per-action freqs; `types.ts`
      matches the new response shape and typechecks; `verify.sh` + typecheck/build green. **Appetite:** ~1 epic.
      **No-gos:** don't change grading logic/thresholds; don't restyle non-grid components.

- [x] **N6 — App-shell + minimal routing (hub walking-skeleton).** *(done 2026-07-03: hand-rolled hash routing #/<view>[/<mode>], reload+deep-link restore, back/forward safe, keyboard guard intact, no router lib; refuter pass)* ICE 5·8·6.
      **Problem:** no router — pure conditional rendering; reload resets to drill/random; no deep-link/resume; `App.tsx`
      owns all state with the topbar/StatsStrip/VIEWS-row unconditional and shortcuts gated on `view==="drill"`. A hub/path
      can't be resumable without this.
      **Outcome-link:** enabling (cohesion; resumable "today's plan").
      **Solution:** introduce minimal (hash-based) routing + a thin shell so views are deep-linkable/resumable **without
      breaking** the drill keyboard-guard, topbar, or StatsStrip assumptions.
      **Pass/fail:** reload restores the current view (not reset); a view is deep-linkable; drill shortcuts still gated
      correctly; FE build green. **Appetite:** ~1 small epic. **No-gos:** no new nav content yet (that's N7); no router lib
      unless justified at spec.

- [x] **N7 — Home / curriculum hub + "today's plan".** *(done 2026-07-03: Home = first tab + default route (absorb); GET /review/plan surfaces due_items() read-only with family+position labels; 9-node ordered path with attempts-weighted mastery (solid ≥80% · 20+ reps); refuter pass. Known limit: 5 preflop nodes map to random mode pending a per-family /drill/next filter — see Next)* ICE 8·7·5 (needs N6, benefits from N4).
      **Problem:** flat tab pile; mastery hidden; no "what to work on next." The SM-2 due-queue (`due_items()`, already
      computed + indexed `ix_srs_item_due_date`) is invisible.
      **Outcome-link:** primary (guided improvement) + enabling (cohesion).
      **Solution:** a home view rendering `due_items()` as **"today's plan"** (pure read-only surfacing — new endpoint/view,
      no new storage) + a **single ordered learning path** with surfaced mastery thresholds; navigating a node loads its drill.
      ⚠️ **Decision (surface at spec):** does the hub **replace / absorb / sit above** the existing `VIEWS` tab row (which is
      the de-facto top-level nav today)? The map flags this as an IA decision, not a silent insert — resolve it before building.
      **Pass/fail:** home lists today's due items from `due_items()`; a single path with mastery labels renders; a path node
      loads its drill; `verify.sh` + build green. **Appetite:** ~1 epic. **No-gos:** no branching skill-tree (single path);
      no new SRS storage; onboarding/placement is N-Next, not here.

- [x] **N8 — Concept cards (point-of-need, ~10–15).** *(done 2026-07-03: 15 doc-grounded cards + leak/tag matcher in services + /cards/match endpoint + FeedbackPanel point-of-need render with hash-route drill-this; refuter pass, live-probed against real grader outputs)* ICE 8·6·4 (benefits from N1/N3).
      **Problem:** research docs 01–08 are **invisible in-app**; a missed rep explains nothing conceptual; no leak→card map
      exists and `leak_category` alone is too coarse to key one (e.g. `VS_RFI=112` = call/3bet/fold together).
      **Outcome-link:** primary (teach the concept) + enabling (stranger learns).
      **Solution:** a NEW versioned card content type under `content/` + schema (mirror `ContentPack`); a card component;
      rep→card linkage keyed on **`leak_category` + disambiguating `rationale_tags`** (map lives in `app/services`, not
      `app/domain`); card → "drill this" round-trip.
      **Pass/fail:** ≥10 cards validate against schema; a wrong answer surfaces the correct card; card→drill round-trips;
      `verify.sh` + build green. **Appetite:** ~1 epic. **No-gos:** no browsable lessons library (Later); cards are
      point-of-need only; no full docs-01–08 port.

- [x] **N9 — Portable-data seam ("others later" insurance).** *(done 2026-07-02: migration 0006, owner_id `''`-sentinel on both tables, srs_item PK = (owner_id, signature), 6 selects scoped; refuter pass)* ICE 4·6·6 (do before N-Next onboarding seeds data).
      **Problem:** persistence has **zero identity/tenancy**; `srs_item.signature` is a content-derived **PK** looked up via
      bare `session.get()` — a 2nd user would *silently overwrite* SM-2 progress. Deferring the PK change gets expensive
      (full-table rebuild once data exists).
      **Outcome-link:** enabling (multi-user isn't a rebuild).
      **Solution:** migration `0006` — nullable `owner_id` on `drill_attempt` + `srs_item` (additive, existing pattern) AND
      **widen `srs_item` PK to `(owner_id, signature)` now while zero data to migrate** (⚠️ the one shape decision — surfaced
      for gate approval; do NOT fold owner into the signature hash); thread `owner_id IS NULL` scoping into the 6 unscoped
      `select()` sites (`services/review.py`, `services/stats.py`).
      **Pass/fail:** migration applies; all existing read/write paths work unchanged (single-user implicit, NULL owner);
      domain-purity + full `pytest` green; `verify.sh` OK. **Appetite:** ~1 small epic.
      **No-gos:** no auth/login/accounts/hosting; no per-tenant DB routing; single SQLite file stays.
      ⚠️ **INVEST exception (acknowledged):** this is a **gate-mandated infrastructure seam** — by design it changes *no*
      observable behavior for today's single user; the value is future-proofing (the gate chose "design the seams now"). It's
      the one Now item not thin-and-vertical; accepted as a scoped exception, not an oversight. Do it before N-Next onboarding
      seeds `srs_item` rows, so those seeds are owner-scoped from birth.

## NEXT — validated problems / opportunities (not yet spec'd)

- **Onboarding + placement diagnostic.** *Evidence:* cold-start into a random spot; competent-novice deserves a seeded
  start; maps show the natural fit = seed `srs_item` rows via `record_attempt()` (no new table) + an "onboarded" flag.
  *Candidate slices:* first-run orientation; a short diagnostic; scoring→SM-2-seed mapping; needs N7 (path to seed into) +
  N9 (owner-scoped seeds). *Open questions:* diagnostic length/shape; how performance maps to initial `ease_factor`/`due_date`.
- **Turn barrel (2f) — with its lesson.** *Evidence:* research §5.1–5.2 (scare-card / picked-up-equity / capped-range);
  `range_advantage()`'s `node_context` param is dead code needing real new scoring. *Candidate slices:* aggressor 2nd-bet
  grader + turn drill mode + leak bucket + **its concept card + tiered feedback** (per the mandate — a street ships *with*
  teaching). *Open questions:* barrel-sizing buckets; multiway deferral.
- **Remaining rationale authoring tranches.** *Evidence:* N3 does the path + RFI/vs-RFI only; `vs_3bet/vs_4bet/vs_limpers/
  blind_defense` + all postflop nodes still templated. *Candidate slices:* author per pack; extend the postflop content path.
- **Engagement: streak-with-forgiveness + consistency heatmap.** *Evidence:* SOTA UX research (`best-practices-drafts/`) —
  Duolingo streak-freeze cut churn 21%. *Candidate slices:* streak model + forgiveness; a calendar-heatmap view over
  `drill_attempt.created_at`. *Open question:* does a single local user value streaks — validate before building.
- **FE type-generation CI gate.** *Evidence:* `types.ts` is hand-maintained + already drifted (missing `solver_node_key`);
  `verify.sh` only checks paths exist, not schema equality. *Candidate slice:* wire `gen:api` + a CI check tying FE types to
  the live backend schema. *(N1/N5 regenerate locally; this makes it enforced.)*

## LATER — bets / outcomes (unexplored · NO hard dates)

- **Bet: full browsable lessons library** (docs 01–08 in-app). *Segment:* self + future learners · confidence: med ·
  assumptions to test: do point-of-need cards (N8) satisfy the need, or is a library wanted? · review-by: after N8 lands + used.
- **Bet: complete turn/river/multiway/full-hand coverage** (2g facing-turn · 2h river value/bluff · 2i facing-river ·
  2j multiway · 2k full-hand). *Confidence:* hi (well-sequenced in old roadmap) · **assumptions to test:** does 2f + its
  teaching move the primary metric (accuracy↑/EV-loss↓) enough to justify continuing the full engine build-out — or does the
  teaching layer alone capture most of the gain? · review-by: after 2f + teaching land.
- **Bet: solver-grade strategy (Phase 3)** — `SolverTableProvider` + `HybridProvider` on the same interface; revisit **2d
  equity-backed range advantage** (deferred — needs solver EV data). *Confidence:* med · review-by: after postflop breadth.
- **Bet: live integration + mental game (Phase 4)** — live session logger, move-up readiness diagnostic, variance framing.
  *Confidence:* lo · review-by: after the trainer proves it moves the primary metric.
- **Bet: real multi-user** (auth / hosting / accounts) — the "others" the N9 seam enables. *Confidence:* lo ·
  assumptions to test: is there demand beyond the primary user? · review-by: after primary-user value is proven.
- **Bet: custom scenario builder + content-pack editor UI (Phase 5).** *Confidence:* lo · review-by: open-ended.

## Out of scope / no-gos (global)

- 🚫 **No auth / accounts / hosting / billing / multiplayer machinery now** — N9 builds the *data seam* only.
- 🚫 **No solver tables now** (Phase 3) — heuristic + credible interim EV only; EVs labeled *approximate*.
- 🚫 **No hand-history imports** — leaks come from drilling (core product decision).
- 🚫 **No live-session logger / mental-game module now** (Phase 4).
- 🚫 **No full browsable lessons library now** — concept cards at point-of-need only.
- ✅ **Invariants held throughout:** domain core free of web/DB imports (test-enforced); results freq+EV never boolean;
  grading behind the one async `StrategyProvider`; strategy as versioned content-data; FE types generated from
  `openapi.json` (stop hand-editing `types.ts`); CSS = design tokens only; AA contrast + visible focus both themes; every
  schema change ships an Alembic migration; `spot_signature()` is frozen (changing it orphans SRS history).
- ⚠️ **Ask-first:** any `StrategyProvider` interface-shape change; any migration that rewrites existing rows (vs additive);
  pulling a Later engine epic (2g–2k) into Now; adding a new top-level dependency.
- **Process:** may `git push` + open PRs on `feat/*`/`fix/*`/`chore/*` autonomously; never push to `main`, force-push, or
  merge a PR without explicit confirmation.
