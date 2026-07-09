# Tickets — Midnight Club redesign (look & feel + momentum features)

Approved reference: `docs/ai-dlc/specs/midnight-club-reference.html` (self-contained mockup; open in a
browser, Night|Day toggle top-right, `?tab=` + `?theme=` deep links). Direction: "private members' club" —
near-black green grounds, spotlit felt stage, champagne-gold foil, art-deco brackets, display serif.
Branch: `feat/midnight-club-redesign`. Sequential unless noted — `app.css` and `tokens.css` are
single-owner hotspots. Design tickets (T1–T7, T9) use the ux-ui-designer → design-reviewer build loop;
T8 is backend, tests-only verification.

**Scope guardrails.** The mockup is a *register* to hit, not a pixel spec: keep the app's existing fonts
(Fraunces display / Source Sans 3 / mono — do NOT introduce Palatino), keep the existing semantic token
names (`--bg/--surface/--text/--primary/…`), and keep the theme-independent `--act-*` range colors with
their documented AA floors (tokens.css:177-194) — restyle the chrome *around* the grid, not the cell
colors. Invariants: CSS values from tokens only · AA + visible focus in both themes · EVs labeled
approximate · no new deps.

## T1 — Token intensification (tokens.css only)
Push both themes toward the reference palette while keeping every token name and documented contrast
floor. Night: grounds deepen toward the mockup's near-black green ramp (`#0a0e0b` page / `#10150f` /
`#151c15` surfaces, hairline `#26301f`); brass stays the one metal voice but gains a bright step and a
glow (reference: gold `#c9a75c`, bright `#e6d29a`, deep `#9a7d3c`, glow `rgba(201,167,92,0.16)`).
Day: warm parchment ramp (`#f6f0e2` page / `#fdfaf1` surface), label gold `#8a6d22` (AA on cream).
New tokens (both themes): `--surface-2` (higher elevation), `--gold-bright`, `--gold-glow`,
`--stage-bg` (dark frame around the felt, both themes), `--page-glow` (radial ambience).
- **AC**: every ratio annotated in tokens.css re-verified and annotations updated; `--act-*` block and
  `--felt-chip/line-bg` scrims untouched; app boots in both themes with no component CSS edits and no
  regressions worse than "colors shifted" (layout/AA intact).
- **Done**: typecheck/build clean; no raw hex outside tokens.css (existing grep gate).
- **Owns**: `frontend/src/styles/tokens.css`.

## T2 — Chrome: masthead, Night|Day toggle (persisted), nav tabs — after T1
Brand lockup (diamond mark + serif wordmark + letterspaced smallcaps tagline); the "Theme" button becomes
a gilded Night|Day switch (`role="switch"`, knob slides under the active label — see reference masthead);
theme choice persists to localStorage (existing try/catch pattern, key `theme`) and restores on boot
(default: dark/night); nav tabs restyle — serif, letterspaced, gold active underline.
- **AC**: toggle operable by keyboard with visible focus in both themes; reload restores last theme; tabs
  keep `aria-current` semantics; StatsStrip/views unaffected below the nav.
- **Done**: design-reviewer pass (1440 + 1024, both themes) + typecheck/build + hex grep clean.
- **Owns**: `frontend/src/App.tsx` (topbar/nav/theme blocks), `frontend/src/styles/app.css` (chrome blocks).

## T3 — Stats strip → club marquee — after T2
Enlarged serif stat numerals, letterspaced smallcaps labels, hairline column dividers, leak chips as
gilded pills with the diamond bullet (reference: stat strip on every tab).
- **AC**: same data, same DOM order for screen readers; AA in both themes; fits without wrap at 1024px.
- **Done**: design-reviewer pass + typecheck/build + hex grep clean.
- **Owns**: `frontend/src/components/StatsStrip.tsx`, `frontend/src/styles/app.css` (stats blocks).

## T4 — Practice stage: spotlit felt + decision bar + mode chips — after T3
The felt becomes a lit stage: `--stage-bg` dark frame, radial glow, rim vignette (reference Practice tab).
Seat pods/action chips recolored to on-felt tokens; decision bar restyled — Raise as the gilded primary,
Fold/Call as dark club buttons, key hints (`F/C/R`, `Space`) in engraved kbd chips; mode chips + Study/Test
toggle restyled to match (gilded active state).
- **AC**: all four drill modes render correctly; quizzes' `.felt` usage stays visually coherent (they
  restage in T7); decision-bar hit targets ≥44px; both themes AA incl. on-felt text; 1024×768 shows felt +
  decision bar without scrolling (existing gate).
- **Done**: design-reviewer pass (all drill modes) + typecheck/build + hex grep clean.
- **Owns**: `frontend/src/components/PokerTable.tsx` (class hooks/markup only), `frontend/src/components/DecisionBar.tsx`,
  `frontend/src/components/ModeGroup.tsx`, `frontend/src/components/StudyTestToggle.tsx`, `frontend/src/styles/app.css` (table/decision/mode blocks).

## T5 — Feedback panel: verdict headline + EV ledger rows — after T4
Verdict as a serif headline with italic action words ("You chose *raise* — *fold* earns more here."),
correctness stamp chip (MISTAKE/OPTIMAL/…), EV comparison as three ledger rows (YOU/BEST/COST) behind a
gold left rule with mono figures, rationale tags as diamond-bulleted pills, concept card with art-deco
corner brackets, gilded Next button (reference Practice tab, post-decision state).
- **AC**: every EV/frequency figure rendered exactly once; ARIA contract intact (`role=status`,
  `aria-live=polite`, mount-focus on Next, Space/N works); all graded states (optimal/acceptable/
  mistake/blunder + mixed) styled; both themes AA.
- **Done**: design-reviewer pass (graded states × both themes) + typecheck/build + hex grep clean.
- **Owns**: `frontend/src/components/FeedbackPanel.tsx`, `frontend/src/styles/app.css` (feedback blocks).

## T6 — Range grid panel chrome — after T5
Panel gets the club treatment: corner-bracket frame, "SOLVER LINE" style smallcaps header with the spot
label, refined legend (chip swatches + "your hand" outline). Cell colors (`--act-*`) unchanged.
- **AC**: grid data/coloring identical; collapsed-state behavior (localStorage) preserved; hero-cell
  outline ≥3:1 in both themes; Study/Test reveal behavior unchanged.
- **Done**: design-reviewer pass + typecheck/build + hex grep clean.
- **Owns**: `frontend/src/components/RangeGrid.tsx`, `frontend/src/styles/app.css` (grid panel blocks).

## T7 — Quiz staging + grouped villain range — after T6
Texture + equity quizzes get the staged treatment (dark frame + glow around the board, serif question,
club answer buttons). Equity quiz: the comma-list villain range is parsed into grouped chips — pocket
pairs / suited / offsuit, with run collapsing ("22–99", "A2s–A9s") and a combos count header (reference
Equity tab). Pure frontend; parsing lives in a small lib helper with unit-testable input→group cases.
- **AC**: grouping is lossless (chips ∪ = original list; property-checked on the shipped villain ranges);
  quiz grading flows unchanged; keyboard + focus order intact; both themes AA.
- **Done**: design-reviewer pass + typecheck/build + hex grep clean.
- **Owns**: `frontend/src/components/QuizPanel.tsx`, `frontend/src/lib/rangeGroups.ts` (new),
  `frontend/src/styles/app.css` (quiz blocks).

## T8 — Backend: daily EV ledger + practice calendar + last-session recap — parallel-safe after T1 (no shared files with T2–T7)
All derivable from existing `DrillAttempt` rows (`ev_loss_bb`, `created_at`, `correctness`) — **no
migration**. Extend the stats service + API: (a) `summary` gains `ev_given_up_today_bb` (sum of today's
`ev_loss_bb`, local-day via `_local_date`); (b) new `GET /api/v1/stats/calendar?weeks=8` → per-day attempt
counts + accuracy for the heat calendar; (c) new `GET /api/v1/stats/recap` → most recent practice day's
hands, accuracy, bb saved vs given up, and biggest miss (max `ev_loss_bb` attempt with its spot label).
- **AC**: timezone handling matches `_local_date` (naive-UTC round-trip covered by tests); empty-DB and
  single-day edge cases return well-formed zeros/nulls; response models in the API schema layer;
  domain purity test still green (no web/DB imports added to `app/domain/`).
- **Done**: `./scripts/verify.sh` green; `ruff check .` clean.
- **Owns**: `backend/app/services/stats.py`, `backend/app/api/v1/stats.py`, API schema module,
  `backend/tests/test_stats.py` (additions).

## T9 — Home: EV ledger widget, streak heat-calendar, House Recap — after T2 and T8
Masthead gains the EV-ledger widget (today's bb given up + daily leak-budget bar — budget is a FE
constant for now, labeled approximate); Home gains the 8-week heat calendar ("Attendance") and the
"House Recap / Last session" card (hands · accuracy · bb saved · biggest miss), plus the club restyle of
Today's Plan and Learning Path (reference Home tab). New fields/endpoints hand-added to
`frontend/src/api/types.ts` + `client.ts` (schema.d.ts stays unwired).
- **AC**: Home renders gracefully when calendar/recap fetches fail (best-effort like existing stats);
  heat-calendar cells have text alternatives (title/aria); both themes AA; NEW features match reference
  layout at 1440/1024.
- **Done**: design-reviewer pass + typecheck/build + hex grep clean.
- **Owns**: `frontend/src/components/Home.tsx`, `frontend/src/App.tsx` (masthead widget slot — sequential
  after T2), `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/styles/app.css` (home blocks).

## T10 — Whole-app sweep — after T9
Final design-reviewer sweep: all four tabs × both themes × 1440/1024, all drill modes, graded feedback
states, quizzes, Home widgets against the reference file. Fixes route back to owning tickets' files.
- **AC**: reviewer verdict pass, zero blockers/majors; deterministic gates all green.
- **Done**: verify.sh + ruff + typecheck/build + hex grep green; final screenshots delivered.
- **Owns**: no files (review-only).

## DAG

T1 → T2 → T3 → T4 → T5 → T6 → T7 → T9 → T10, with T8 → T9 (T8 may run any time after T1).
No parallel execution on the frontend chain — `app.css` is a single-owner hotspot throughout.

## Explicitly out of scope
Session recap *modal/flow* beyond the Home card · XP/gamification · Blitz/timed modes · focus mode ·
position×module matrix · SRS forecast chart (candidates for a later epic) · any change to grading,
`spot_signature()`, SRS, or content packs.
