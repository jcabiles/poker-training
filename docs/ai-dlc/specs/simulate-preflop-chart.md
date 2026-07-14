# Spec — Simulate collapsed preflop range chart (point-of-need)

> NEXT-item slice, roadmap `docs/ai-dlc/roadmap/simulate-table.md`. Gate-1 direction
> locked BY THE USER 2026-07-12: baseline chart + exploit note (persona-adjusted squares
> explicitly rejected → Later bet behind exploit-aware grading). Built autonomously under
> the user's 2026-07-12 "proceed with everything" instruction; solo-inception — refuter
> pass still mandatory before build.
> Runs AFTER S10/S11 waves merge (shares `SimulateView.tsx`/`types.ts`/`app.css`).

## Goal (one line)
A collapsed panel on the Simulate view that, when it's the hero's preflop turn on a
mappable spot, expands to the baseline 13×13 action-mix chart for that exact spot plus a
one-line persona-keyed exploit note — and honestly says "no chart for this spot yet"
otherwise.

## Decisions (Gate-1 locked + inception-resolved)
- **Baseline squares + qualitative exploit note.** Chart squares are the generic
  baseline; the note comes from the exploit content's authored `rationale` line for
  (mapped node, live villain persona). No recomputed squares.
- **Multiway note precedence: MOOT for v1** — `grade_map` maps HU-canonical spots only,
  so a chart implies exactly one live villain; the note keys off that villain. Unmappable
  (incl. multiway) spots show the no-chart message instead.
- **Preflop only.** Panel renders only when `street == preflop` and it is the hero's
  turn; hidden postflop (it is a preflop chart, not a range viewer — that's the separate
  villain-range-reveal slice).
- **Collapsed by default, state persisted** (localStorage key exactly
  `"simChart.collapsed"` — refuter low-1: never reuse Practice's literal
  `"rangeGrid.collapsed"`).
- **Preflop mapping coverage EXTENDED (refuter high-2, autonomous scope decision
  2026-07-12):** grade_map's v1 preflop scope (RFI/vs-RFI) would render "no chart yet"
  on most real preflop spots even though content/preflop has full charts for
  blind_defense, vs_3bet, vs_4bet, vs_limpers. New ticket C0 extends
  `grade_map.map_decision_point` to those four HU-canonical preflop families under the
  SAME full-confidence gate (return None on any ambiguity — never fabricate). This
  widens S10's graded coverage too (a deliberate, flagged supersession of S10's
  "RFI/vs-RFI only" enumeration; the refuter on C0's diff must re-verify the
  no-fabrication gate per family). Anything unmappable still gets the honest no-chart
  message.
- **Stale-response guard (refuter high-1):** the chart fetch never blocks the action
  bar; instead the client stamps each request with the current (session_id, hand_no,
  is_hero_turn) identity and DISCARDS any response arriving after the identity changed
  (hero acted / events landed / hand advanced). No chart for a resolved decision point
  is ever rendered.
- **Villain resolution named (refuter med-1):** the mapped Spot carries
  `villain_type=None`; the service resolves the note's persona by mapping the Spot's
  `facing` position → the matching `sim_seat.persona_type`, then
  `registry.lookup(index, spot, villain_type=persona)`. Unit test asserts the note's
  villain equals the actual live opponent seat (mis-pairing = fabrication).
- **Refetch only while expanded (refuter med-2):** a new hero preflop turn refetches
  ONLY if the panel is currently expanded; collapsed panels cost zero fetches across
  all turns, not just before first expand.
- **Copy-don't-touch idiom:** a new `SimRangeChart.tsx` renders the same markup/CSS
  classes as Practice's `RangeGrid.tsx` (`.gridwrap/.grid/.cell/...`, read-only reuse —
  the SimTable↔PokerTable precedent). `RangeGrid.tsx` itself is NOT edited (Practice
  drill + quiz owner).

## Reuse map (verified in code)
- Spot mapping: `app.domain.table.grade_map.map_decision_point` (S10 T1) — same
  full-confidence gate; chart availability ≡ gradeability.
- Grid: `app.domain.grading.range_grid(lookup(_INDEX, spot))` — exactly how
  `api/v1/drill.py:317` builds Practice's preflop grid.
- Exploit note: content registry exploit entries (`content/preflop/exploit.json` —
  `villain_type` + `rationale` fields; `registry.py` keeps baseline + exploit pairs).

## Files / interfaces to touch
**Backend**
- `backend/app/services/sim_session.py` — small read-only helper: current decision point
  → mapped Spot → grid + exploit-note lookup (live villain persona from `sim_seat`).
- `backend/app/api/v1/simulate.py` — `GET /simulate/{session_id}/preflop-chart` →
  `{available: bool, node_label, grid, exploit_note: {villain_label, rationale} | null}`;
  `available=false` (+ no grid) when not hero's preflop turn or unmappable. Server-side
  state only — no client-supplied spot params.
- `backend/app/schemas/simulate.py` — `PreflopChartView` schema.
**Frontend**
- `frontend/src/api/types.ts` — mirror `PreflopChartView`.
- `frontend/src/components/simulate/SimRangeChart.tsx` — NEW (RangeGrid markup copy,
  sim-owned); fetches on first expand (collapsed default = zero cost per decision);
  refetches per new hero preflop turn; renders the exploit note under the grid with the
  villain label; renders the no-chart message when `available=false`.
- `frontend/src/components/SimulateView.tsx` — mount the panel (main column, under the
  action bar) only when `is_hero_turn && street === "preflop"`.
- `frontend/src/styles/app.css` — `.sim-chart-*` section appended (tokens-only; the grid
  cells reuse existing shared classes read-only).

## Out of scope
Persona-adjusted chart squares (Later bet) · postflop charts · villain range reveal
(separate slice) · any change to Practice's `RangeGrid.tsx`/drill flow · content
authoring beyond what `exploit.json` already has (missing persona/node pairs ⇒ note
omitted, chart still shows) · new migrations (read-only feature).

## Constraints (invariants)
Grading/content via existing seams (`grade_map`, content registry, `range_grid`) — no
duplicated strategy logic · never fabricate a chart for an unmapped spot · "approx."
labeling on the chart header (RangeGrid idiom) · tokens-only CSS, AA both themes,
visible focus on the toggle · hero-only privacy unchanged (chart shows hero strategy,
not villain cards) · FE types hand-maintained.

## Verify-by (end-to-end)
- Hero preflop turn on a mappable spot (e.g. folded-to-hero RFI): expand → grid matches
  the Practice drill grid for the same spot (fixture compare on the endpoint); exploit
  note shows the live villain's rationale when content has the pair.
- Multiway/limped/unmappable preflop turn → `available=false` → panel shows "no chart
  for this spot yet"; postflop → panel absent.
- Collapse state persists across reload; no fetch until first expand (network assert).
- Practice drill RangeGrid pixel-identical (no shared-class edits).
- `./scripts/verify.sh` + `ruff` + FE typecheck/build green; `design-reviewer`
  acceptable both themes; refuter pass on this spec BEFORE build.
