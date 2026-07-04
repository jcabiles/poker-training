# UI Contracts — card-room-polish UX pass (scanned 2026-07-03)

> Fresh read-only scan of `frontend/src/**` by contract-mapper, verified against code (NOT the stale
> `frontend-ia-tokens.md`, which predates N4–N8 — its grid section is now factually wrong).
> Consumed by: `docs/ai-dlc/specs/card-room-polish-ux.md`.

## (a) Token system contract — `frontend/src/styles/tokens.css`

- **Theme mechanism:** `:root` = light defaults (`tokens.css:2-56`); `[data-theme="dark"]` overrides same var names (`:58-83`). Switch = `data-theme` attr on `<html>`. Default theme **dark**, hardcoded in `frontend/index.html:2`. No JS theme detection, no persistence.
- **Theme-independent tokens:** action colors `--act-raise/call/fold/mixed/on` (`tokens.css:103-109`; `--act-mixed` DEAD since N5) and felt scrims `--felt-chip-bg/--felt-line-bg` (`:113-116`).
- **Semantic roles:** `--bg/surface/text/muted/border/primary/primary-text/good/good-bg/bad/bad-bg/warn/warn-bg/felt/felt-text/card-bg/suit-red/suit-black/accent-cell` (`:3-21`, dark `:59-77`).
- **Type scale:** `--text-2xs(9)/xs(11)/sm(12)/md(13)/base(15)/lg(20)/xl(22)` px (`:24-30`). All 7 used — fully load-bearing.
- **Space ramp:** `--space-1(4)/2(8)/3(12)/4(16)/6(24)/8(32)` + legacy alias `--space: var(--space-2)` (`:33-39`). `app.css` mixes named steps with old `calc(var(--space) * N)` idiom (e.g. `app.css:4,11,26,40,64,110,147`) — both coexist.
- **Radius ramp:** `--radius-xs(2)/sm(4)/md(8)/lg(10)/pill(999)` + alias `--radius: var(--radius-lg)` (`:42-47`). **Barely adopted** — most of app.css hardcodes raw `8px/4px/999px/2px/6px` (violations in §b). Biggest tokens-exist-but-unwired gap.
- **Elevation:** `--shadow-felt/panel/card/overlay` per theme + alias `--shadow: var(--shadow-panel)` (`:51-55`, dark `:78-82`). `--shadow-overlay` unused (reserved; no modal exists).
- **Load-bearing tokens** (>5 uses): `--text-md`, `--text-sm`, `--space` (via calc), `--border`, `--surface`, `--muted`, `--radius`, `--primary`.
- **Global focus ring:** `:focus-visible { outline: 3px solid var(--primary); outline-offset: 2px; border-radius: 4px }` (`tokens.css:96-100`) — app-wide universal rule. Don't shadow per-component without AA check both themes.

## (b) CSS architecture + violations — `frontend/src/styles/app.css`

Convention: flat, un-namespaced lowercase classes (`.card`, `.btn`, `.panel`, `.cell`) — no BEM/modules/scoping; collision-avoidance by discipline only.

**Media queries (only two):**
- `@media (max-width: 820px) { .layout { grid-template-columns: 1fr } }` (`app.css:29-33`) — sole responsive breakpoint.
- `@media (prefers-reduced-motion: no-preference) { .gridwrap.reveal { animation ... } }` (`app.css:382-386`, keyframes `:387-396`) — the ONLY animation in the app; sole motion-a11y surface.

**Focus:** global tokens.css rule + one local addition `.input:focus-visible { border-color: var(--primary) }` (`app.css:559-561`).

**Raw px violations (token exists but unused, or no token exists):**
- `app.css:2` `max-width:1080px` shell (no content-width token)
- `:25` `360px` fixed sidebar col
- `:55-56` `.card` `border-radius:8px`, `padding:6px 10px`; `:86-87` card `52×72px` (no size tokens)
- `:136-138` `.kbd` radius 4px, padding/margin raw
- `:164` `.badge` `999px` (→ `--radius-pill`)
- `:221,226` `.mix li`/`.best` raw
- `:264,274-275` `.rationale` gap 6px, `999px`, padding raw
- `:295,298` `.gridtoggle` `min-height:36px`, transparent border
- `:317,325` `.grid gap:1px`, `.cell` radius 2px (→ `--radius-xs`)
- `:367-368` `.cell.sample` 14×14
- `:422-423,470,479,517-518` misc 4–10px gaps/margins
- `:485-486` `.lk` pill + padding raw
- `:510-511` `.cell.hero { outline:3px solid var(--text); outline-offset:-3px }` — looks like a focus ring but means "your hand"; a global focus-ring pass could reskin it accidentally
- `:526-527` `.line` radius 6px, padding raw
- `:557` `.input width:120px`
- `:571-572` `.villain` pill + padding raw

No raw hex/rgba in app.css — all color token-referenced (hex lives only in tokens.css, sanctioned).

**Dead CSS/tokens:** `.cell.pair` (`app.css:349-352`, dead since N5), `--act-mixed` (`tokens.css:107`), `--shadow-overlay` (reserved).

## (c) Shell / routing / keyboard contracts — `frontend/src/App.tsx`

- **Shell** (`App.tsx:209-234`, always rendered): `.app` → `.topbar` (h1 + theme `.btn`) → `<StatsStrip>` → `.modes` (VIEWS tab row: Home/Practice/Texture quiz/Equity quiz). Below: `Home` / drill UI / `QuizPanel` conditional (`:236-278`).
- **Hash routing** (`frontend/src/lib/hashRoute.ts`): `#/<view>` or `#/drill/<mode>`. `View = "home"|"drill"|"texture"|"equity"` (`hashRoute.ts:9`). Bad view → `"home"` (`:36`); drill with bad mode → `"random"` (`:37`). `formatHash()` (`:41-43`) appends mode only for drill. **Load-bearing fallback:** `App.tsx:106-115` hashchange handler preserves prior drill mode when switching to non-drill views. Hash write sites: `App.tsx:150,228`; `ConceptCard.tsx:15`; `Home.tsx:51,89,100,122`.
- **Keyboard shortcuts** (`App.tsx:172-197`): global keydown, gated `view === "drill"` (`:173`). Ignores keydown when activeElement is BUTTON/INPUT/SELECT/TEXTAREA/contentEditable (`:176-182`). With result: space/n → loadNext (`:183-188`); else key→`legalDecisions(spot)` match (`:190-193`; keys F/C/R/K/B/V from `lib/decisions.ts:11-17,31`). **Layered under** DecisionBar's roving-tabindex arrow-nav — two separate keyboard systems, do not merge; extra interactive wrappers break the focused-BUTTON guard.
- **Theme toggle** (`App.tsx:199-202`): flips `document.documentElement.dataset.theme` directly — no React state, no localStorage. Reload reverts to index.html's `data-theme="dark"`. Only theme mechanism; preserve the exact write.
- **Grid visibility** (`App.tsx:204-207,262,268-273`): `showGrid = hasGrid && (studyTestMode==="study" || !!result)`; `!showGrid` appends `layout-single` (`app.css:541-543`). Behavioral state class — restyle allowed, class-presence logic frozen.
- **Deep-link fetch-once** (`App.tsx:117-121`): mount fetch uses hash-derived mode (no random-then-correct race). Don't touch effect deps during markup work.

## (d) Per-component contracts

| Component | Classnames | ARIA / a11y | State classes | Inline styles |
|---|---|---|---|---|
| `Card.tsx` | `.card`, `.card.red`, `.r`, `.s` | none | `red` for h/d suits (`:6,8`) | none |
| `StatsStrip.tsx` | `.statstrip .stat .leaks .lk-title .lk .lk.muted` | renders `null` when summary null (`:10`) — element not always in DOM | `.lk.muted` no-leaks (`:31`) | none |
| `PokerTable.tsx` | `.felt .ctx .line .villain .seats .seat .pos .stack .board .pot .hero .cards .herometa` | `aria-label="community cards"` on `.board` (`:54`) | `.line`/`.villain` conditional render (`:41-44`) | none |
| `DecisionBar.tsx` | `.decisionbar .btn .btn-primary` | `role="toolbar" aria-label aria-orientation` (`:53-55`); roving tabIndex per button (`:67`); per-button aria-label incl. shortcut (`:68`) | `btn-primary` when `d.primary` (`:65`) | none — `btnRefs` array needs one flat `<button>` per option, stable order |
| `FeedbackPanel.tsx` | `.panel.feedback {tone}-bg`, `.badge {tone}`, `.mixed .tier-verdict .chosen-eval .tier-reasoning .tier-deepdive .deepdive-text .mix .best .studytest-hint`(reused), `.btn.btn-primary` | `role="status" aria-live="polite" aria-atomic` root (`:59-61`); imperative focus → Next button on mount (`:23,30-32`) | `tone` from `correctness` via TONE map (`:8-13,22`) drives `.badge` + `-bg` classes | none. `.feedback` class has NO css rule — free styling hook |
| `ConceptCard.tsx` | `.concept-card{-title,-summary,-body}`, `.btn` | native `<details>/<summary>`; drill-btn aria-label (`:33`) | none | none |
| `RationaleTags.tsx` | `.rationale .rationale-chip` | `<ul>/<li>`; null when empty (`:60`) | none | none |
| `StudyTestToggle.tsx` | `.studytest .studytest-toggle .studytest-hint`, `.btn.btn-primary` | `role="group" aria-label` (`:17`); `aria-pressed` both buttons (`:21,29`) | `btn-primary` active mode | none |
| `RangeGrid.tsx` | `.gridwrap(.reveal) .gridtoggle .gridchevron .gridtitle .grid .gridrow .cell(.hero) .cell-segments .cell-segment.action-* .cell-label .gridlegend .lgi .cell.sample.action-*` | `aria-expanded/controls` toggle (`:67-68`); ARIA table `role=table/row/cell` + `aria-labelledby` (`:87-89,105`); per-cell title+aria-label with mix (`:107-108`) | `hero` on handClass match (`:98,106`); `reveal` one-shot animation (`:63`) | **LOAD-BEARING:** `style={{ flex: \`${s.freq} 0 0%\` }}` per segment (`:115`) = backend frequency data, never remove/hardcode |
| `Home.tsx` | `.home`, `.panel.home-section`, `.home-section-title .home-due-count`, `.mix.home-due-list`, `.studytest-hint`(reused), `.btn.btn-primary`, `.home-path .home-path-node`, `.badge {tone}` | semantic h2/ul/ol only | mastery badge tone via MASTERY_TONE (`:45-49,125`) | none. `.home-section` has NO css rule |
| `QuizPanel.tsx` | `.quizpanel .felt .ctx .cards .board .herometa .prompt .decisionbar .btn(.btn-primary) .input`, `.panel {good/bad}-bg`, `.badge {good/bad}`, `.why` | native form semantics | `good/bad` off `res.correct` — quiz-only boolean, distinct from EvaluationResult (invariant governs drill grading, not quiz) | `style={{ marginTop: "var(--space)" }}` (`:73`) — token-referenced inline; migrate to class |
| `ModeGroup.tsx` | `.mode-group .mode-group-label .modes`, `.btn.btn-primary` | `role="group" aria-labelledby` slugified from label (`:19-21`) | `btn-primary` active | none |

**Cross-component class reuse (restyle bleeds):**
- `.btn/.btn-primary` — every component.
- `.panel` — FeedbackPanel, Home ×2, QuizPanel result, error banners (`App.tsx:258`, `QuizPanel.tsx:57`).
- `.felt/.ctx/.board/.cards/.herometa` — PokerTable AND QuizPanel identically.
- `.mix` — FeedbackPanel per-action list AND Home due-list (`Home.tsx:79`).
- `.studytest-hint` — StudyTestToggle + Home + FeedbackPanel (generic muted-small-text utility across 3 unrelated components).
- `.badge {good/bad/warn/neutral}` — FeedbackPanel, Home, QuizPanel.

## (e) Fonts

No web fonts. `body { font: var(--text-base)/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif }` (`tokens.css:93`). No `@font-face`, no font `<link>` in index.html (grep-confirmed). Custom webfonts = greenfield; family should route through a `--font-*` token (body stack currently a hardcoded literal — pre-existing gap).

## (f) Data-shape integration points (visual pass must not shape-shift)

- `frontend/src/api/types.ts` hand-maintained; no `schema.d.ts` exists. All components import it directly.
- `EvaluationResult` (`types.ts:56-70`) rendered fields: `correctness, ev_loss_bb, is_mixed, tiers.{verdict,reasoning,deep_dive}, explanation, chosen_eval.{frequency,ev_bb}, rationale_tags, per_action[].{action,size_bb,frequency,ev_bb}, best_action.{action,size_bb}, leak_category` — consumed `FeedbackPanel.tsx:22,64,66,71-96`, `RationaleTags.tsx`. `correctness` = 4-value string enum (no boolean — invariant holds).
- `NextDrillResponse.grid: Record<string, Record<string, number>>` (`types.ts:74`) → `RangeGrid.tsx:93-97` → the flex inline style. (Old contract doc's grid section describes pre-N5 collapsed labels — wrong now.)
- Card string format `"Ah"` 2-char positional contract shared by `Card.tsx:4-6` + `lib/poker.ts:9-12` (`handClass()`).
- `localStorage`: `"studyTestMode"` (`App.tsx:50`), `"rangeGrid.collapsed"` (`RangeGrid.tsx:16`); both try/catch-wrapped. No theme key.
- `ReviewPlanResponse/DuePlanItem` (`types.ts:167-177`), `LeakStat` (`:82-88`) → `Home.tsx:35-43` mastery derivation (client-side only).

## Redesign hazards (silent-break list)

1. `RangeGrid.tsx:115` — `flex: freq` inline style is DATA. Never replace with fixed classes.
2. `App.tsx:262,268-273` — `layout-single` presence is state logic, not breakpoint CSS.
3. `RangeGrid.tsx:87-89,105` — ARIA table depends on exact `.grid > .gridrow(display:contents) > .cell` nesting; extra wrapper divs break the a11y tree.
4. `DecisionBar.tsx` — roving-tabindex ref array needs flat stable `<button>` list; wrappers also break App.tsx's focused-BUTTON keydown guard.
5. `FeedbackPanel.tsx:30-32` — imperative focus to Next button + `role="status" aria-live` root; no test catches removal.
6. Shared classes (`.btn .panel .mix .studytest-hint .badge .felt/.ctx/.board/.herometa`) — one restyle bleeds into 2–4 components.
7. `app.css:510-511` `.cell.hero` outline ≠ focus ring — semantic "your hand" marker.
8. Theme toggle: only mechanism is the `dataset.theme` write (`App.tsx:199-202`); no persistence exists.
9. Hash-route fallbacks + drill-mode preservation (`hashRoute.ts:34-39`, `App.tsx:106-115`) — keep formatHash/parseHash call sites intact when touching nav markup.
10. Token adoption partial — verify each raw-px site before changing token VALUES; some literals have no token yet (card 52×72, sidebar 360, shell 1080).
11. **Zero frontend tests** (glob-confirmed) — only guards are `tsc --strict` + manual QA + design-reviewer.
12. Dead: `--act-mixed`, `.cell.pair`, `--shadow-overlay` — safe to delete/repurpose.
