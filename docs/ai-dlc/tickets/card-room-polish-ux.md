# Tickets — card-room-polish (UX/UI pass)

> Spec: `docs/ai-dlc/specs/card-room-polish-ux.md` · Contracts: `docs/ai-dlc/contracts/card-room-polish-ux.md`
> **DAG: strictly sequential T1→T8.** Every ticket touches `app.css` (and most touch `tokens.css`) — both are
> single-owner hotspots, so no parallelization. Build loop per ticket: ux-ui-designer → boot → design-reviewer →
> iterate (max 3) → deterministic gates.
> Done-condition shorthand `GATES` = `cd frontend && npm run typecheck && npm run build` clean **and**
> hex-gate `grep -nE '#[0-9a-fA-F]{3,8}|rgba?\(' frontend/src/styles/app.css frontend/src/components/*.tsx frontend/src/App.tsx` → 0 hits.

## T1 — Typography foundation (fonts + type tokens)

Self-host the two committed families (one display serif for headings, one text family for UI/body; numerics/data may use system mono), wire `--font-display`/`--font-body`(/`--font-mono`) tokens, apply the hierarchy.
**Owned files:** `frontend/public/fonts/` (new), `frontend/index.html`, `frontend/src/styles/tokens.css`, `frontend/src/styles/app.css`.
**AC:** woff2 files committed + licensed for self-hosting; `@font-face` with `font-display: swap` + preload links; family names referenced ONLY via `--font-*` tokens; headings render display serif, body renders text family; serif never used below `--text-base` (small sizes stay on the text family for legibility); no CDN font requests.
**Done:** GATES; dev-server network panel shows fonts load 200 (no 404 fallback); no FOIT; license/attribution file committed alongside the font binaries in `frontend/public/fonts/` (prefer OFL-licensed families) — a 200 proves the file exists, not that it's shippable (refuter R6).

## T2 — Card-room palette (tokens, both themes)

Refine `tokens.css` color values to the committed aesthetic: deep felt greens, warm brass/cream accents, tactile card surface colors — dark theme designed first, light theme kept coherent. Semantic token NAMES frozen; only values change.
**Owned files:** `frontend/src/styles/tokens.css`.
**AC:** all existing semantic tokens keep their names; AA verified for every text/bg and UI/bg pair in BOTH themes (4.5:1 / 3:1); `--act-raise/call/fold` remain distinguishable from each other and ≥3:1 against cell backgrounds; **`.cell-label` text (`--act-on`) ≥4.5:1 against each of `--act-raise/call/fold` AND `--accent-cell`, at its 9px size, both themes** (normal-text ratio — it's 9px white-on-segment today, `app.css:345-347,503-508`; brass/cream repaints are the exact failure mode — refuter R1); `.cell.hero` outline color ≥3:1 against segment colors; global focus ring ≥3:1 against every new surface; no indigo/violet gradients.
**Done:** GATES; contrast spot-check table (token pair → ratio → pass) pasted into review notes for both themes.

## T3 — Token adoption sweep + cleanup

Migrate every raw-px site listed in contracts §b to the `--radius-*`/`--space-*` ramps; add missing size tokens (`--content-width` 1080, `--card-w/h` 52/72, `--sidebar-w` 360 — values unchanged, just tokenized); move `QuizPanel.tsx:73` inline style to a class; delete dead `--act-mixed` + `.cell.pair`; keep `--shadow-overlay` (reserved).
**Owned files:** `frontend/src/styles/tokens.css`, `frontend/src/styles/app.css`, `frontend/src/components/QuizPanel.tsx`.
**AC:** zero raw px radius values in app.css (grep `border-radius: *[0-9]` → 0); spacing raw-px sites from the contracts list migrated or explicitly justified in a comment; visual output pixel-identical (this ticket changes plumbing, not looks); hazards untouched (RangeGrid flex style, ARIA nesting).
**Done:** GATES; `git diff` shows no component markup changes beyond the one QuizPanel inline-style removal.

## T4 — Shell, topbar, nav, Home hub

Restyle `.app/.topbar/.modes` shell + `Home.tsx` surfaces (`.home-path`, due-list, mastery badges) to the card-room look: clear hierarchy (display serif h1/section titles), refined tab row, hub that answers "what do I work on today" at a glance.
**Owned files:** `frontend/src/styles/app.css`, `frontend/src/App.tsx` (markup hooks only), `frontend/src/components/Home.tsx`, `frontend/src/components/ModeGroup.tsx`, `frontend/src/components/StatsStrip.tsx`.
**AC:** hash-route call sites + VIEWS logic untouched (hazard 9); theme-toggle `dataset.theme` write preserved (hazard 8); StatsStrip null-render contract intact; `.badge` restyle checked in FeedbackPanel + QuizPanel too (shared class); active tab clearly distinguished ≥3:1; 24px min targets.
**Done:** GATES; design-reviewer pass on `#/home` at 1440+1024, dark+light.

## T5 — Drill surface (table, cards, decisions)

PokerTable felt materiality (subtle vignette/texture via CSS only — no image kitsch), refined Card faces (tactile, suit-colored, no ornament), DecisionBar as the fast-decision focal point.
**Owned files:** `frontend/src/styles/app.css`, `frontend/src/components/PokerTable.tsx`, `frontend/src/components/Card.tsx`, `frontend/src/components/DecisionBar.tsx`.
**AC:** DecisionBar stays a flat stable `<button>` list (hazard 4 — roving tabindex + keydown guard); `.felt/.ctx/.board/.herometa` restyle re-checked in QuizPanel (shared classes, hazard 6); `.btn/.btn-primary` treatment coherent app-wide; keyboard hints (`.kbd`) legible; density is mechanical (refuter R4): **at 1440×900, PokerTable + DecisionBar + grid-toggle header fit within the 900px viewport height** (24px targets must fit inside that budget, not excuse breaking it); no skeuomorphic chips/wood.
**Done:** GATES; design-reviewer pass on `#/drill/random` pre-answer, **`#/drill/postflop`** (no-grid `layout-single` + `.board` state — refuter R2), and **`#/drill/exploit`** (only `.villain`/`.line` renderer), dark+light, 1440+1024; F/C/R/K/B/V + arrows still work.

## T6 — Teaching surfaces (feedback, concept cards, tags)

FeedbackPanel tier hierarchy (verdict → chosen-eval → reasoning → deep-dive) with clear tone treatment; ConceptCard as a refined study card; RationaleTags chips; StudyTestToggle.
**Owned files:** `frontend/src/styles/app.css`, `frontend/src/components/FeedbackPanel.tsx`, `frontend/src/components/ConceptCard.tsx`, `frontend/src/components/RationaleTags.tsx`, `frontend/src/components/StudyTestToggle.tsx`.
**AC:** `role="status"` + imperative Next-focus preserved (hazard 5); every EvaluationResult field still rendered (contracts §f list); EV-approximate disclaimer survives; **EV bb values, frequencies (%), and `ev_loss_bb` render in `--font-mono` with `font-variant-numeric: tabular-nums`** (the committed "disciplined mono for data" — refuter R3; aligns the `.mix` per-action columns); `.studytest-hint` change re-checked in Home + StudyTestToggle (triple reuse — split the class if treatments diverge); `.mix` change re-checked in Home due-list; tone `-bg`/badge classes keep semantics.
**Done:** GATES; design-reviewer pass on drill post-answer (correct AND wrong, study AND test) incl. `layout-single` no-grid state, dark+light.

## T7 — Data surfaces (range grid, quizzes, stats)

RangeGrid as truthful pro data-viz (segment colors from T2 action tokens, legible labels, refined legend); QuizPanel (texture + equity) brought to the same standard; StatsStrip leak chips.
**Owned files:** `frontend/src/styles/app.css`, `frontend/src/components/RangeGrid.tsx`, `frontend/src/components/QuizPanel.tsx`, `frontend/src/components/StatsStrip.tsx`.
**AC:** `flex: freq` inline style untouched (hazard 1); ARIA table nesting untouched (hazard 3); `.cell.hero` reads as "your hand", distinct from focus ring (hazard 7); cell labels ≥4.5:1 at 9px (T2's token-level guarantee holds at the rendered surface) or aria-only; **quiz numeric answers/deltas in `--font-mono` + `tabular-nums`** (refuter R3); grid density preserved — 13×13 fits without scroll at 1440×900 (refuter R4); quiz result panels use the shared tone system.
**Done:** GATES; design-reviewer pass on grid (expanded + collapsed + reveal animation), **`#/drill/postflop` no-grid state** (refuter R2), `#/texture`, `#/equity` incl. result states, dark+light.

## T8 — Motion, states, final sweep

Subtle micro-transitions (hover/focus/active on buttons/tabs/cells, panel reveals, tier expand — 100–200ms, all inside `prefers-reduced-motion: no-preference`); disabled/loading/error-banner states; light-theme coherence pass; final whole-app review.
**Owned files:** `frontend/src/styles/app.css`, `frontend/src/styles/tokens.css` (motion tokens if needed).
**AC:** zero motion under reduced-motion emulation; error banners (`App.tsx:258`, `QuizPanel.tsx:57`) + StatsStrip-absent + empty due-list states styled; every interactive element has visible hover + focus + active + disabled treatments both themes; existing `gridReveal` guard pattern reused.
**Done:** GATES; `./scripts/verify.sh` → BACKEND VERIFY OK; full design-reviewer sweep per spec Verify-by 4–6 → verdict `pass`; final screenshots (home, drill pre/post, grid, both quizzes × dark/light × 1440/1024) captured for the completion report.
