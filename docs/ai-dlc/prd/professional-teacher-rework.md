# PRD — Professional Teacher Rework (Learning-Experience-first)

> Status: **DRAFT for roadmap-gate approval (2026-07-02).** Supersedes the sequencing in
> `roadmap-review-and-proposal.md` by making the Learning-Experience pillar the **Now** column
> and pushing turn/river coverage to Next/Later. Discovery decisions locked at the gate:
> **audience = "me now, others later"** (seams not machinery) · **teaching + UX first** ·
> **concept-cards now, lessons library later** · appetite = **large / comprehensive**.

---

## 1. Context & problem

**What exists today (real systems):** a working local NLHE trainer. Backend: FastAPI + a pure
domain core (`backend/app/domain/` — `preflop.py`, `postflop.py`, `srs.py`, `texture.py`,
`equity.py`, `hand_rank.py`, `EvaluationResult`, `Entry`) + SQLite/Alembic (head 0005). Frontend:
React/Vite/TS (`App.tsx`, `RangeGrid.tsx`, `FeedbackPanel.tsx`, plus the cheap-wins additions
`RationaleTags.tsx` / `StudyTestToggle.tsx`). Strategy lives in `content/` packs. Coverage: **all
preflop + all flop** (c-bet, facing c-bet, facing check-raise), graded freq+EV with SM-2 re-surfacing,
leak tracking, and exploit drills.

**The problem:** the app is an excellent **grader** and a poor **teacher**. Post-answer "why" is one
tautological sentence ("AKo: raise is the play from CO") + an EV list. The vetted strategy research
(`docs/research/01–08`) is **invisible in-app** — zero lessons, zero concept explanations. There is
**no onboarding** (cold-start into a random spot), **no home/curriculum**, and the visual layer lacks a
real design system. None of this makes a **winning $2/$3 player**, and none of it makes the app
**attractive to a future user who isn't its author**.

**Why now:** the engine already covers the most-played spots (preflop + flop). Adding ~40 more
turn/river grading tickets deepens a tool that still doesn't teach. The highest-leverage next work is the
**human-facing layer** — and per the gate, the data for much of it (`Entry.rationale`,
`EvaluationResult.rationale_tags`, the SM-2 due-queue) **already exists in code** and is merely unsurfaced.

## 2. Goal & non-goals

**Goal (outcome-shaped):** turn the app from a grader into a **cohesive teacher a competent-novice can
pick up and improve with** — measured by (a) trained-spot accuracy ↑ / EV-loss ↓ over sessions for the
primary user, and (b) a **cold-start-to-first-understood-rep** path a stranger can complete without the
author explaining anything.

**Non-goals (explicit — prevents creep):**
- 🚫 **No auth / accounts / hosting / billing / multiplayer** now. We build **data-model seams** so a
  future multi-user version isn't a rebuild — not the machinery.
- 🚫 **No solver tables** now (Phase 3). Heuristic + a *credible interim EV* only.
- 🚫 **No hand-history imports** — leaks come from drilling (core product decision, unchanged).
- 🚫 **No live-session logger / mental-game** module now (Phase 4).
- 🚫 **No full browsable lessons library** now — concept cards at point-of-need only (library = Later).
- Turn/river/multiway/full-hand grading is **not abandoned** — it moves to **Next/Later**, each street
  shipping **with its lesson** when it lands.

## 3. Affected files / interfaces

*(Refined against the read-only contract maps in `docs/ai-dlc/contracts/` — feedback-evaluation,
persistence-datamodel, frontend-ia-tokens.)*

- **Teaching / feedback:** `EvaluationResult` (+ its API response model), `preflop.py`/`postflop.py`/`srs.py`
  graders (rationale authoring), `FeedbackPanel.tsx`, `RationaleTags.tsx`, generated `openapi.json` types.
- **Concept cards:** NEW content type under `content/` (versioned data + schema, mirror the existing
  content-pack pattern) + a card-render component + rep→card linkage keyed on `rationale_tags` / leak category.
- **Onboarding / curriculum:** NEW top-level views in the FE shell; profile/settings + SRS-seed storage
  (persistence layer + a migration); the SM-2 due-queue surfaced as "today's plan".
- **Design system:** the CSS design-token file(s) — add type/space/radius/shadow scales + elevation model;
  `RangeGrid.tsx` cell rendering (dominant-color → proportional freq bars).
- **Accuracy debt:** `hand_rank.py` (CW-3b pocket-pair anchoring), `postflop.py` (CW-2b note), `equity.py`
  + fold tables (credible interim EV).
- **Portability seam:** the SQLModel tables + one Alembic migration (nullable owner/scope seam).

## 4. Requirements (atomic, testable)

Each maps to a Now/Next slice in the roadmap; acceptance criteria are the slice's pass/fail check.

- **R1 — Multi-tier "why".** As a learner, after I answer I can see verdict → reasoning → deep-dive, where
  tier-2 surfaces the concept + strategic reason (not a tautology). *AC:* a graded response renders ≥2
  distinct tiers with non-tautological reasoning text sourced from `rationale`/`rationale_tags`;
  typecheck+build clean.
- **R2 — Concept cards at point-of-need.** A missed rep links to a concept card explaining the idea, which
  links back into a drill. *AC:* ≥10 versioned cards validate against a schema; a wrong answer surfaces the
  correct card via its tag/leak key; card → "drill this" round-trips.
- **R3 — Onboarding + placement diagnostic.** First run orients the user and runs a short diagnostic that
  seeds the SRS/mastery instead of a cold random spot. *AC:* a fresh profile completes a diagnostic that
  writes seeded SRS/mastery rows (migration applied); no cold-start into a raw `vs_limpers` spot.
- **R4 — Home / curriculum hub + learning path + "today's plan".** A single visible path + a due-queue view,
  not a flat tab pile. *AC:* a home view renders the SM-2 due-queue as "today's plan" and a single ordered
  path with surfaced mastery thresholds.
- **R5 — Design system + grid truthfulness.** Tokens have scales + an elevation model; grid cells show
  proportional frequency mixes, not one dominant color; AA contrast + visible focus in both themes.
  *AC:* token scales exist and are used (no ad-hoc colors); a mixed-frequency cell renders proportional
  bars; axe/contrast check passes both themes.
- **R6 — Accuracy debt paid.** CW-3b pocket-pair ranks anchored to computed-equity ordering (reconciled
  with `test_hand_rank.py` determinism); CW-2b documented; a credible interim fold-equity EV wired from
  `equity.py` + doc-06 fold tables. *AC:* pytest green incl. updated hand-rank expectations; EV shown as
  *approximate* until Phase 3.
- **R7 — Portable-data seam.** The persistence layer carries a nullable owner/scope so a future multi-user
  version needs data, not a rebuild. *AC:* a migration adds the seam; all existing rows/read paths work
  unchanged (single-user still implicit); domain-purity test green.

## 5. Constraints (hard boundaries — 3-tier)

- ✅ **Always:** keep domain core (`backend/app/domain/`) free of web/DB imports (test-enforced); results
  freq+EV never boolean; grading behind the one async `StrategyProvider` interface; strategy as versioned
  content-data; FE types generated from `openapi.json`; CSS = design tokens only; AA contrast + visible
  focus both themes; every schema change ships an Alembic migration; run `./scripts/verify.sh` +
  `ruff check .` + FE `typecheck && build` before a slice is "done".
- ⚠️ **Ask-first:** any change to the `StrategyProvider` interface shape; any migration that rewrites
  existing rows (vs additive nullable); pulling a Later engine epic (2f–2k) into Now; adding a new
  top-level dependency.
- 🚫 **Never:** auth/accounts/hosting/billing/multiplayer machinery now; solver tables now; hand-history
  imports; push to `main` / force-push / merge a PR without explicit confirmation; commit secrets;
  disable the sandbox (widen the allowlist instead).

## 6. Task / milestone plan

Milestones = the Now column in `docs/ai-dlc/roadmap/professional-teacher-rework.md`. Each Now-slice maps to
one requirement, is a thin end-to-end vertical slice, and carries its own runnable pass/fail check. One slice
at a time is handed to `/ai-dlc`; between slices, re-read the roadmap's pass/fail state before advancing.

## 7. Verification (end-to-end)

A slice is **done** only when: its acceptance criteria pass **AND** `./scripts/verify.sh` → `BACKEND VERIFY OK`
+ `ruff check .` clean + FE `npm run typecheck && npm run build` clean **AND** nothing outside the slice's
declared scope changed. The initiative is done when every Now-slice is `[x]` and the cold-start-to-first-
understood-rep path is walkable end-to-end.
