# Poker Coach App — Phase 0 Roadmap

> Living planning document. Built from four research streams (see `docs/research/`).
> Status: **Phases 0, 1a, 1b, 1c, 2a, 2b, 2c complete & verified** — 148 backend tests green; `scripts/verify.sh` → `BACKEND VERIFY OK`; migration 0004 head. **2d investigated → deferred to Phase 3** (equity-backed range advantage; see below). Flop c-bet + vs-c-bet spots re-surface in `mode=review` via SM-2. **Next: 2e–2k (turn/river/multiway/full-hand), sequenced by dependency — see the Phase 2 section below and `contracts/postflop-turn-river.md`.**

---

## Direction update — the Learning-Experience mandate (July 2026 review)

> Full analysis + SOTA UX research: `docs/ai-dlc/roadmap-review-and-proposal.md` (+ `best-practices-drafts/`).
> **Decided:** the engine-first street sequencing below **stays**, but is now bound by a hard mandate.

**MUST: become a true *teacher*, not just a grader — across ALL streets.** Today the app tests but barely teaches
(feedback is one tautological sentence; the strategy docs 01–08 are invisible in-app; the UI is a flat pile of
mode-buttons). Deferring this is no longer acceptable. Every postflop epic (2f–2k) now ships **with its teaching layer**
— a concept card + an enriched "why" explanation — and **teaching, IA, and onboarding interleave with the engine build**
rather than waiting until after it.

**What this adds (see capability P below):**
- **Multi-tier feedback that teaches the WHY** — deliver the long-promised tiers (verdict → reasoning → deep-dive). Much
  of this is *surfacing data the code already has* (`Entry.rationale`, `EvaluationResult.rationale_tags`, the SM-2
  due-queue) — cheap, not a rebuild.
- **In-app theory — concept cards now, full lessons library later** (decided scope). Cards surface at point-of-need
  (a missed rep links to its concept); a browsable lessons library from docs 01–08 follows as a later phase.
- **Cohesive IA + onboarding** — split the flat mode-buttons into two labeled axes (spot-selection × situation), a
  home/curriculum hub, a first-run placement diagnostic, a study-vs-test toggle, and reveal-the-chart-after-answer.
- **Accuracy debt paid down** — fold the verified research errata (docs 05/06/08) into the near-term build: preflop
  leaks (UTG KQo, HJ QJo, vs-4bet CO QQ), grader leaks (`Texture.suitedness`/`pairing` computed-but-never-read, the
  ace-high exception), and `hand_rank` pocket-pair undervaluation.

**Immediate next build — the "cheap-wins bundle" (approved):** 2-axis mode split · surface `rationale` in feedback ·
consistent decision-quality tiers · grid-absent-then-reveal + study/test toggle · ARIA/live-region/focus fixes · the
05–08 errata. Highest visible improvement for lowest cost/risk; spec + tickets in `docs/ai-dlc/`.

**Reconcile:** the running app shows **no "Challenge" mode** despite prior "merged" status — verify `main` before
planning around it.

## 1. Player profile (who this is for)

- Plays **live** No-Limit Texas Hold'em **cash** only (not online, not tournaments).
- **Winning** at $1/$2, $400 max buy-in (~200bb). Goal: **move up to $2/$3**.
- **Competent novice**, not a beginner — knows fundamentals, has a winning low-stakes strategy, wants to level up.
- Wants **simplified-but-sound** strategy (modern theory, not perfect GTO memorization).
- Single user, **local** app. No accounts, no monetization, no multiplayer.

## 2. Vision

A local, **desktop-first, live-cash-focused** NLHE trainer built around one tight loop:

> **Surface a leak → drill it with fast reps → instant "why + EV cost" feedback → space it with SM-2 → re-surface until mastered.**

It finds leaks from your own drilling (**no hand-history imports**), grades against a **simplified-GTO baseline**, and layers **exploitative adjustments vs live villain types** on top. Covers **preflop and postflop**, simplified for the $1/$2 → $2/$3 climb. Critically, it must **teach the *why*, not just grade** — every rep links to the concept behind it and theory is surfaced in-app, across all streets — so the loop builds understanding, not just pattern-matching (see the Direction update above).

## 3. Goals · Requirements · Constraints (from the original intent)

**Goals:** learn, practice, drill, train. Texas Hold'em only. Tailored to this player's level and move-up goal.

**Hard requirements**
- Preflop AND postflop coverage (postflop phased after preflop).
- Simplified strategy grounded in modern theory — not perfect GTO.
- Best-in-class learning workflow (deliberate practice + spaced repetition + explanatory feedback).
- **A true teacher, not just a grader** — in-app explanation of the WHY + surfaced theory (concept cards now, lessons library later), delivered across **all streets**; cohesive, onboarded, teaching-forward UX. Interleaves with the engine build — non-deferrable.
- Emulate what the best products do well; avoid their documented pitfalls.

**Constraints**
- Local-only; runs on this machine. Sandbox: Python pip installs allowed, writes restricted to project dir.
- Simplified content must be *correct* within its simplification — verifiable against fixtures.
- CSS = design tokens only; AA contrast + visible focus in both themes (carryover house rule).

## 4. Guiding architecture principles (future-proofing)

These are non-negotiable so the app scales from preflop-MVP to a solver-grade, postflop-complete trainer **without a rebuild**.

1. **Content as versioned data, not code.** Strategy lives in validated content packs (JSON/YAML) with a schema. Engine is content-agnostic.
2. **Swappable `StrategyProvider`.** Grading is one interface (heuristic → solver → hybrid). Downstream consumers never know the source.
3. **Solver-ready Spot schema from day 1.** Store full granular game state even when heuristics ignore fields. No migration to add a solver later.
4. **Frequency + EV evaluation results, never boolean.** Every grade is an action mix with EVs + rationale tags. Feedback/leaks/analytics all consume this richer shape.
5. **Clean layering.** Pure domain core (spot, eval, content) is framework- and DB-agnostic. API layer is thin. Front-end talks to a **versioned API contract** (OpenAPI). Domain logic never leaks into UI or DB.
6. **Stable leak-category taxonomy.** A versioned enumeration both preflop and postflop map into, so analytics survive content growth.
7. **Deterministic, testable grader.** Golden scenario fixtures + range-sanity tests. Swapping providers is verified against fixtures.
8. **Persistence migrations from the start** (SQLite + migration tool).
9. **Design tokens + accessibility** baked in from the first screen.
10. **Modular drill modes.** Drill engine orchestrates pluggable modes (spot, street, full-hand, leak-focus, free); adding a mode never touches the loop core.

## 5. Capability map (the full universe)

| # | Capability | Phase |
|---|-----------|-------|
| A | Strategy/content layer (ranges, postflop heuristics, math, exploit adjustments) — versioned packs | 0/1/2 |
| B | Spot model + game engine (state, legal actions, cards/board, equity utils) | 0/1/2 |
| C | `StrategyProvider` grading interface (heuristic → solver → hybrid) | 0/1/3 |
| D | Drill engine + modes (spot, street, full-hand, leak-focus, free) | 1/2 |
| E | 3-tier feedback (flash+EV → mistake "why" → deep dive) + replay | 1 |
| F | Spaced repetition (SM-2) scheduler | 1 |
| G | Leak tracking + analytics (accuracy & EV-loss by category, leak ranking) | 1/2 |
| H | Mastery-gated progression / curriculum ladder | 1/2 |
| I | Exploit/archetype layer (villain types, IF/THEN deviations, EV-of-exploit) | 1/2 |
| J | Player profile + persistence (progress, settings, stakes) | 0/1 |
| K | UX/UI (range grid, table display, decision input, keyboard, dashboards, theming) | 1/2 |
| L | Live session logger (quick hand entry, post-session review) | 4 |
| M | Move-up readiness diagnostic + mental-game / variance framing | 4 |
| N | Content authoring + validation tooling | 0/ongoing |
| O | Test/quality infra (golden scenarios, range sanity) | 0/ongoing |
| P | **Learning Experience** — in-app concept cards/lessons, multi-tier "why" feedback, onboarding, curriculum/home hub, cohesive IA | 1/2 (interleaved) |

## 6. Phased roadmap

### Phase 0 — Foundations & architecture *(do first)*
The skeleton that makes everything else plug in. Mostly contracts, no game features yet.
- Lock the core schemas: **Spot** (solver-ready), **Action/Decision**, **EvaluationResult** (freq+EV+rationale), **ContentPack**, **SRS item**, **Leak-category taxonomy**.
- Define module boundaries + the `StrategyProvider` interface.
- Scaffolding: Python API skeleton, JS front-end skeleton, SQLite schema + migrations, dev scripts, test harness, CSS design tokens, OpenAPI contract.
- A golden-fixture test harness for the grader.

### Phase 1 — Preflop MVP vertical slice *(this is v1 — shippable & genuinely useful)*
The complete learning loop, preflop content only.
- Preflop content packs: RFI by position, vs-3bet, vs-4bet, blind defense, squeeze, vs-limpers, sizing — simplified tiers from research.
- `HeuristicStrategyProvider` (preflop): chart lookup → freq + approx-EV + rationale.
- Preflop scenario generator/sampler over the Spot model.
- Drill engine: **spot mode**, **leak-focus mode**, **free explore**.
- 3-tier feedback + instant replay.
- **SM-2 spaced repetition** integrated into the queue.
- **Auto leak tracking** + analytics dashboard (accuracy + EV-loss by preflop category, top-3 leaks).
- **Exploit/archetype drills (preflop):** villain types + IF/THEN preflop deviations on the baseline.
- UI: 13×13 range grid, position/stack/hand display, fast keyboard input, feedback panels, dashboard.
- Player profile + persistence; mastery-gating across preflop modules.

### Phase 2 — Postflop expansion
- **2a (DONE):** flop c-bet (HU SRP) graded by texture + positional range-advantage; pure-Python equity engine; board-texture classifier; `CompositeProvider` route-by-street; flop-c-bet drill mode; foundational quizzes (texture classification, equity estimation); postflop leak buckets (200/210/211); texture/SPR-bucketed postflop signature.
- **2b (DONE):** facing a flop c-bet (HU SRP defense) — fold/call/raise graded by texture + defender-perspective range advantage + pot-odds/MDF + bet-size; `vs_cbet` drill mode; faced-bet bucket in the postflop signature; leak `VS_CBET=201`.
- **2c (DONE):** postflop SRS review — flop c-bet + vs-c-bet spots re-surface in `mode=review` via SM-2 (4 nullable `srs_item` columns, migration 0004, archetype reconstruction, `srs_signature` graduation override). First migration since 1c.
- **2d (INVESTIGATED → DEFERRED to Phase 3):** equity-backed range advantage. Bounded Monte-Carlo over the heuristic ranges does not recover a stable signal (mean equity flat ~0.5; strong-share width-biased; top-of-range noisy/counterintuitive). Real range advantage is a solver/EV property → revisit with Phase 3 solver tables. Positional+texture heuristic retained. See `tickets/phase-2d-equity-backed.md`.
- **2e–2k (planned; sequenced by dependency, one epic per session — see `contracts/postflop-turn-river.md`):** turn/river coverage + multiway + full-hand mode. There is currently NO street-level dispatch past preflop (flop/turn/river all hit the same provider), and 5 call sites silently truncate any board to its first 3 cards — this must be fixed before turn/river grading is safe, not worked around per-feature.
  - **2e-0 — Foundational fixes** *(DONE & verified — 163 tests green, `BACKEND VERIFY OK`)*: raise-aware `srs.faced_bet_bucket()` rewrite (reads current `CALL.min_bb` + subtracts hero's prior street investment, not a history max-scan); `postflop._hand_category()` fix (added made-straight/made-flush detection AND demoted plain top pair from `strong` to `weak_made` — a live bug already in shipped 2b, caught by the refuter pass); street-gated `PostflopHeuristicProvider.supports()` (turn/river now → `NOT_FOUND`, no longer silently graded as a flop); all 5 `texture.classify()` call sites now slice `board[:3]` explicitly.
  - **2e-1 — Facing a flop check-raise** *(DONE & verified — 183 tests green, `BACKEND VERIFY OK`)*: hero c-bet, defender check-raised, hero responds fold/call/raise (sized 4-bet). New `grade_vs_check_raise` grader encodes the "$1/$2 check-raises are rarely bluffs" prior as a genuinely stronger fold baseline (1.6 vs vs-cbet's 0.6 — verified: a weak_made hand folds ~0.69 here vs ~0.55 vs a plain c-bet); `build_check_raise_spot` builder with the incremental-`CALL` sizing the refuter caught (`raise_to − cbet`, not the raw total); `vs_check_raise` drill mode + SRS-review reconstruction; leak `VS_CHECK_RAISE=202`; frontend "Facing check-raise" mode + a street-scoped betting-line verb fix (a flop check-raise no longer mislabels as "3-bets"). Closes the flop c-bet loop.
  - **2f — Turn barrel** *(needs 2e-0)*: aggressor's 2nd-bet decision — scare-card / picked-up-equity / capped-range logic per `docs/research/02-postflop-strategy.md` §5.1–5.2. `range_advantage()`'s `node_context` param is currently dead code — this needs real new scoring, not just a new tag. ~7 tickets.
  - **2g — Facing a turn bet** *(needs 2e-0, 2f)*: defender fold/call/raise vs the barrel. ~6 tickets.
  - **2h — River value/bluff** *(needs 2e-0 — `_hand_category` fix is a hard prereq)*: value betting + blocker-aware bluff selection per §6.1–6.3. Genuinely new domain code (blocker logic touches hole-card/board suit-rank overlap, not just merit scoring). ~7-8 tickets.
  - **2i — Facing a river bet** *(needs 2h)*: bluff-catching per §6.4 (blockers + range-capping reads). ~6-7 tickets.
  - **2j — Multiway adjustments** *(needs 2e-1 through 2i)*: cross-cutting sizing/frequency modifier (research §9) touching every grader above — sequenced last-but-one because it changes a moving target if done earlier. ~6-8 tickets.
  - **2k — Full-hand (preflop→river) drill mode** *(needs everything above)*: pure drill-engine/UI orchestration routing hero through the existing graders across one continuous hand — mechanically last, not a judgment call. ~5-6 tickets.
  - ~53 tickets total across 8 epics — larger than 2a+2b+2c combined; each epic ships as its own spec → tickets → build → verify cycle, matching how every phase 0–2c was actually built (never batched).
- Extend leak taxonomy (postflop 200–299, 96 numbers free) + analytics + mastery ladder as each epic lands.

### Phase 3 — Solver-grade strategy (swap-in)
- `SolverTableProvider` implementing the same interface: precomputed solver tables, board isomorphism + bet-size bucketing, spot keying.
- `HybridProvider` (solver where available, heuristic fallback).
- "**GTO baseline + exploit deviation in one view**" fully realized.
- Enabled — not blocked — by Phase 0/1 schema choices.

### Phase 4 — Live integration & mental game
- Live session logger: quick hand entry, game context, results, post-session review feeding the leak system.
- Move-up readiness diagnostic ($2/$3 checklist: bankroll, accuracy on pressure spots, mental-game self-assessment).
- Variance/mental-game framing; pre/post-session rituals.

### Phase 5 — Polish & advanced *(ongoing/optional)*
- Custom scenario builder, content-pack editor UI, broader analytics, export/backup, refinements.

## 7. Tech stack

- **Front-end:** JS framework + TypeScript + Vite. (Framework pick — React vs Svelte — is an open decision below.)
- **Back-end:** Python **FastAPI** + **Pydantic** (Pydantic models *are* our schemas) → auto-generated **OpenAPI** contract.
- **Persistence:** **SQLite** via SQLModel/SQLAlchemy + **Alembic** migrations.
- **Domain core:** pure Python package, no web/DB imports — independently testable.
- **Tests:** pytest with golden fixtures for the grader.

## 8. The grading-swappability guarantee (your key question)

Start with **simplified charts + heuristics**. Because of principles 2–4 (provider interface, solver-ready Spot schema, freq+EV results), upgrading to **bundled solver tables** later is: *add a new provider class + add data files.* The drill loop, feedback, SRS, leak tracking, and UI are untouched. **Not a rebuild.**

## 9. Open decisions (to resolve at the roadmap gate)

- Front-end framework: **React** vs **Svelte**.
- Sequencing: spec **Phase 0 first** (foundations), then Phase 1 — vs combine Phase 0+1 into one v1 spec.
- Confirm desktop-first; confirm ~10–20 min session shape.

## 10. v1 (Phase 0 + Phase 1) — explicit scope

**In:** preflop drilling loop, 3-tier feedback, SM-2, leak tracking, exploit/archetype drills (preflop), range-grid UI, persistence, mastery-gating.
**Out (deferred):** postflop, solver tables, live session logger, readiness diagnostic, custom scenario builder.
