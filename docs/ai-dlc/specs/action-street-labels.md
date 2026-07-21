# Spec — Action panel: street-labeled board headers

**Goal:** Group the Simulate "Action" log (`SimEventLog`) by street, each group under a header showing the street name + its cumulative board as compact log chips (Preflop = label only).

Part of the Simulate initiative (`docs/ai-dlc/roadmap/…`); pure frontend polish, no roadmap slice pass/fail affected.

## Direction (chosen)
Mockup **02 — board-card headers** (`scratchpad/action-street-mockups.html`). Header per street: `<Street name>` + cumulative board chips. Compact log-sized card chips (rank + suit glyph, red suits colored), not felt-sized cards.

## Files / interfaces to touch
- `frontend/src/components/simulate/SimEventLog.tsx` — add `board: string[]` prop; group the *shown* prefix by street; render a street header (label + chips) before each group; render a small card-chip element.
- `frontend/src/components/SimulateView.tsx:875` — pass `board={hand.board}`.
- `frontend/src/components/simulate/simPlayback.ts` — `export` `boardCountForStreet` (single source for the per-street count).
- `frontend/src/styles/app.css` — header + card-chip styles (`.sim-log-street`, `.sim-log-card`, etc.), tokens only.

## Behavior
- Render only the shown prefix `shown = events.slice(0, Math.max(0, stagedIndex))` (unchanged).
- **Group by CONTIGUOUS RUN of `street`, not by distinct street value** (refuter #1). Walk `shown` in order; start a new group whenever `street` differs from the previous item's. Never `groupBy(street)` into one bucket per value — that would merge a non-contiguous repeat of a street into one header and reorder chips.
- A group appears only once ≥1 of its events is in `shown` → headers self-gate, no empty "Turn" pop-in.
- Header per group:
  - Label = capitalized street ("Preflop", "Flop", "Turn", "River").
  - **Chips = `board.slice(0, boardCountForStreet(group.street))` — the count derives from THAT group's OWN `street` field, NEVER from the last shown event's street or the batch's terminal street** (refuter #2 — `stagedTableState` uses a terminal-street shortcut that is correct for the single felt but WRONG applied per-group; do not reuse its street/board output here). Cumulative: Flop 3, Turn 4, River 5; Preflop → 0 → no chips.
  - Because each group's count comes from its own already-revealed street, no chip for a street appears before that street's action reveals → spoiler-safe and felt-aligned.
  - Unknown/unexpected `street` string → `boardCountForStreet` returns 0 → header renders with 0 chips (never crash, never guess) (refuter #6).
- Card chip = rank + suit glyph; hearts/diamonds use the red suit color, spades/clubs the ink color. Redundant text (glyph), never color-only.
- **Keying (preserve once-only reveal, refuter #3):** each action `<li>` keeps a key equal to its GLOBAL index within `shown` (a running counter across all groups), NOT a per-group `.map` index that resets to 0 each group. A reset key collides across groups and re-fires `sim-log-reveal` on already-shown lines. Header key = the group's street string.
- **aria-live (refuter #4):** keep exactly ONE `aria-live="polite"` region wrapping the whole grouped list — not one per group. Compute the grouping in a `useMemo` keyed on `(events, stagedIndex)` so a fresh array isn't built every render (avoids AT double-announce). Header street text sits inside the region so the reader gets "Flop" before its actions.
- Empty state unchanged: `events.length === 0` → `null`. `stagedIndex === 0` → `shown` empty → render the panel title only, NO group/header (not even a bare "Preflop") (refuter #5).

## Out of scope
- No backend, `EventView`, or `frontend/src/api/types.ts` change (`street` + `board` already exist).
- `SimActionBar` untouched. Panel title stays "Action". No other panel (SimStreetReport etc.) restyled.
- No new board reveal/animation timing; no felt/table change. No cumulative-vs-new toggle (cumulative fixed).

## Constraints (invariants)
- Spoiler seam: derive headers/chips only from the shown prefix; never key off full `events`/`board` beyond it.
- CSS values from design tokens only; AA contrast + red-suit not the sole cue.
- FE types hand-maintained — no change needed here, but if any, edit `types.ts` manually.
- Grading path, `StrategyProvider`, `spot_signature()` untouched.

## Verify-by (end-to-end)
1. `cd frontend && npm run typecheck && npm run build` — clean.
2. `./scripts/serve.sh start`; open Simulate, play a hand to the turn/river with villain action.
3. Confirm: Action log shows "Preflop / Flop / Turn / River" headers; Flop header shows 3 chips, Turn 4, River 5; Preflop none.
4. During staged playback: a street's header + chips appear only as that street's first action reveals — no empty header, no board card shown before the felt deals it. Earlier-street headers never gain later-street chips.
5. **stagedIndex=0** (batch queued, nothing revealed yet): panel shows title only, no header. **Mid-street-start batch** (first shown event is a flop action, no preflop events in this batch): first header is "Flop" with 3 chips, correct and not a spoiler.
6. Staged reveal animation fires once per line — no re-flash of already-shown lines when a new street's first line appears.
7. Toggle light/dark: chips + headers legible (AA), red suits distinguishable by glyph not just color.
