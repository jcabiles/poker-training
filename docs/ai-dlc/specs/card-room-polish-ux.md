# Delta spec — card-room-polish (UX/UI-only pass)

**Goal (one line):** make the whole app look professionally designed under a committed "refined card-room" aesthetic — visual/CSS/markup polish only, zero behavior change.

Contracts: `docs/ai-dlc/contracts/card-room-polish-ux.md` (fresh 2026-07-03 scan — read it before touching anything).
Tickets: `docs/ai-dlc/tickets/card-room-polish-ux.md`. Profile: `docs/ai-dlc/profile.md`.
Roadmap relation: sits on top of the completed Now column (N4 tokens, N5 grid, N6 routing, N7 hub, N8 cards) of `docs/ai-dlc/roadmap/professional-teacher-rework.md`; inherits its global no-gos.

## Design commitment (Gate 1, locked 2026-07-03)

- **Purpose & audience:** local NLHE trainer; primary user is the author ($1/$2 → $2/$3 live). Screen jobs: Home hub = "what do I work on today" · Drill = "make this decision fast" · Feedback = "understand why" · Grid = "see the real frequency mix".
- **Named aesthetic: Refined card-room.** Mood anchor: upscale private card room / high-end casino lounge. Deep felt-green surfaces on the existing felt→panel→card→overlay elevation model, warm brass/cream accents, tactile card materiality, serif display type for headings, disciplined text/mono type for data.
- **Scope:** whole-app polish — shell/topbar/nav, Home hub, drill view (PokerTable, DecisionBar, Card), FeedbackPanel + ConceptCard + RationaleTags, RangeGrid, QuizPanel, StatsStrip, StudyTestToggle, ModeGroup.
- **Theming:** dark primary (designed first, hardest-optimized); light stays fully AA.
- **Motion:** subtle only — 100–200ms micro-transitions (hover/focus, panel reveals, feedback-tier expand); every animation/transition behind `prefers-reduced-motion` guards.
- **A11y target:** WCAG 2.2 AA — 4.5:1 text / 3:1 UI contrast, 24px targets, visible focus, both themes.
- **Breakpoints:** 1440 and 1024 (design-reviewer grades both). 375 out of scope.
- **Anti-goals:** standard slop bans (no indigo/violet gradient default, no Inter-only, no uniform card grids, no centered two-button hero, no gradient blobs) **plus**: no skeuomorphic casino kitsch (no 3D chips, wood grain, playing-card ornaments); no density loss on drill/grid views (EV data stays above the fold at 1440); max 2 self-hosted font families (one display serif + one text family; monospace may come from the system stack).

## Files / surfaces to touch

- `frontend/src/styles/tokens.css` — palette refinement (felt greens, brass/cream accents), `--font-*` family tokens, any new size tokens (content width, card dims, sidebar width), both themes. **Single-owner hotspot — tickets touching it are sequenced.**
- `frontend/src/styles/app.css` — all component styling; token-adoption sweep of the raw-px sites listed in contracts §b; new component styles. **Single-owner hotspot.**
- `frontend/index.html` — `@font-face` preload links only (title/meta may be polished).
- `frontend/public/fonts/` (new) — self-hosted font files (woff2, licensed for self-hosting).
- `frontend/src/components/*.tsx` + `frontend/src/App.tsx` — classname/markup adjustments ONLY where a visual treatment needs a hook; every change must respect the hazards list (contracts §Redesign hazards).

## Out of scope (explicit)

No behavior/logic changes · no new features/views/routes · no backend/API/types.ts changes · no data-shape changes · no 375px mobile work · no router/keyboard-system changes · no theme-persistence fix (existing inconsistency, noted, not ours) · no test-suite introduction · no dependency additions beyond font files (no CSS framework, no icon lib without gate approval).

## Constraints (from profile invariants + contract hazards)

1. CSS values from design tokens only — no new raw hex anywhere outside `tokens.css`; migrate existing raw-px radius/space sites to ramps while passing through (contracts §b list).
2. AA contrast + visible focus in both themes — the global `:focus-visible` ring (tokens.css:96-100) stays app-wide; re-check its contrast against any new surface colors.
3. Never break the silent-break hazards: RangeGrid `flex: freq` inline style (data) · ARIA table nesting `.grid > .gridrow > .cell` · DecisionBar flat button list + roving tabindex · FeedbackPanel `role="status"` + imperative Next-focus · `layout-single` state class logic · theme toggle `dataset.theme` write · hash-route call sites · `.cell.hero` outline is a semantic marker, not a focus ring.
4. Shared-class bleed (`.btn .panel .mix .studytest-hint .badge .felt`) — restyling shared classes is allowed but must be checked in EVERY consuming component; splitting a shared class into per-context classes is the safer move when treatments diverge.
5. Fonts self-hosted only (sandbox/CSP: no Google Fonts CDN at runtime); family names routed through new `--font-display` / `--font-body` tokens.
6. Zero FE tests exist — `tsc --noEmit` + build + design-reviewer are the only gates; be conservative with markup edits.
7. Dead code (`--act-mixed`, `.cell.pair`, `--shadow-overlay`) may be deleted or repurposed deliberately — note which in the ticket.

## Verify-by (end-to-end)

1. `cd frontend && npm run typecheck && npm run build` — clean.
2. `./scripts/verify.sh` → `BACKEND VERIFY OK` (proves no accidental backend touch).
3. No-raw-hex gate: `grep -nE '#[0-9a-fA-F]{3,8}|rgba?\(' frontend/src/styles/app.css frontend/src/components/*.tsx frontend/src/App.tsx` → zero hits (hex/rgba live only in tokens.css).
4. Boot `./scripts/serve.sh start`; **design-reviewer** pass on `http://localhost:5173` covering `#/home`, `#/drill/random` (pre-answer, post-answer correct, post-answer wrong, study + test modes), `#/drill/postflop` (the no-grid `layout-single` + community-card `.board` state — range grid is preflop-only per `backend/app/api/v1/drill.py:228`), `#/drill/exploit` (the only mode rendering `.villain` + `.line`, `PokerTable.tsx:41-44`), `#/texture`, `#/equity` — at 1440 and 1024, dark AND light themes — graded against the design commitment above + AA numbers. Verdict must be `pass`.
   Density check is mechanical, not vibes: at 1440×900, PokerTable + DecisionBar + grid-toggle header fit within the 900px viewport height (no scroll to reach the decision buttons or grid toggle).
5. Reduced-motion spot-check: with `prefers-reduced-motion: reduce` emulated, no transition/animation runs.
6. Keyboard spot-check: F/C/R/K/B/V + space/N still work in drill; arrow-nav in DecisionBar; visible focus ring on tab.

## Refuter findings (real pass, verdict `fail` → all folded 2026-07-03)

- **R1 high (→ T2 AC):** `.cell-label` renders 9px `--act-on` (white) text directly on `--act-raise/call/fold` segments (`app.css:345-347,503-508`) — needs **4.5:1** (normal text), not the 3:1 UI ratio; brass/cream repaints are exactly the colors that fail white-on-light. Named explicitly in T2, not left to the blanket clause.
- **R2 high (→ Verify-by 4, T5/T7 Done):** original route list never opened any postflop mode (grid is preflop-only, `drill.py:228`) nor `#/drill/exploit` (sole `.villain`/`.line` renderer) — `layout-single`-via-no-grid-data was never screenshotted. Routes added.
- **R3 med (→ T6/T7 AC):** commitment promises "disciplined text/mono for data" but no AC named which fields get it — now pinned: EV bb values, frequency %, quiz deltas get `--font-mono` + `tabular-nums`.
- **R4 med (→ Verify-by 4, T5/T7 AC):** "no density loss" vs 24px targets had no tie-breaker — now mechanical: PokerTable + DecisionBar + grid-toggle header fit within 900px height at 1440×900.
- **R5 low (→ this section):** the previous draft of this section was a placeholder written before the refuter ran; replaced with the real findings (meta-finding: never pre-claim folds).
- **R6 low (→ T1 Done):** runtime 200-check proves the font file exists, not that it's shippable — license/attribution file must be committed alongside the binaries (prefer OFL families).
