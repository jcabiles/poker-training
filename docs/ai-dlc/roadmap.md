# Poker Training App — Phase 0 Roadmap

> Living planning document. Built from four research streams (see `docs/research/`).
> Status: **Phases 0, 1a, 1b, 1c, 2a, 2b complete & verified.** **Phase 2c (postflop SRS review) built & verified** — 148 backend tests green; `scripts/verify.sh` → `BACKEND VERIFY OK`; migration 0004 head. Flop c-bet + vs-c-bet spots now re-surface in `mode=review` via SM-2, keyed on their texture/SPR/faced-bet archetype: `srs_item` gains 4 nullable postflop columns, `record_attempt` persists + backfills them, `_rebuild_postflop` reconstructs a due archetype via the 2a/2b builders, and a `Spot.srs_signature` override guarantees the due row graduates even on an approximate reconstruction. Closes the core "surface → drill → re-surface until mastered" loop for postflop. Remaining slices: Phase 2d (turn / river / check-raise-as-aggressor + equity-backed range advantage), squeeze (multiway), mastery-gating.

---

## 1. Player profile (who this is for)

- Plays **live** No-Limit Texas Hold'em **cash** only (not online, not tournaments).
- **Winning** at $1/$2, $400 max buy-in (~200bb). Goal: **move up to $2/$3**.
- **Competent novice**, not a beginner — knows fundamentals, has a winning low-stakes strategy, wants to level up.
- Wants **simplified-but-sound** strategy (modern theory, not perfect GTO memorization).
- Single user, **local** app. No accounts, no monetization, no multiplayer.

## 2. Vision

A local, **desktop-first, live-cash-focused** NLHE trainer built around one tight loop:

> **Surface a leak → drill it with fast reps → instant "why + EV cost" feedback → space it with SM-2 → re-surface until mastered.**

It finds leaks from your own drilling (**no hand-history imports**), grades against a **simplified-GTO baseline**, and layers **exploitative adjustments vs live villain types** on top. Covers **preflop and postflop**, simplified for the $1/$2 → $2/$3 climb.

## 3. Goals · Requirements · Constraints (from the original intent)

**Goals:** learn, practice, drill, train. Texas Hold'em only. Tailored to this player's level and move-up goal.

**Hard requirements**
- Preflop AND postflop coverage (postflop phased after preflop).
- Simplified strategy grounded in modern theory — not perfect GTO.
- Best-in-class learning workflow (deliberate practice + spaced repetition + explanatory feedback).
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
- **2e (next real slice):** turn play (2nd barrel) and/or check-raise as the aggressor's response — stable heuristics, new strategy coverage.
- **2f:** river value/bluff, multiway, simplified math surfaced (rule of 2&4, pot odds, MDF); **full-hand (preflop→river)** drill mode.
- Postflop heuristics: c-bet by texture, barreling, river value/bluff, multiway, simplified math.
- New drill modes: **street**, **full-hand**; drills for line construction, hand-reading, multiway.
- Extend leak taxonomy + analytics + mastery ladder to postflop.

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
