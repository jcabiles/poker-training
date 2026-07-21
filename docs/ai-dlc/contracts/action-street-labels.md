# Contracts — Action panel street labels

Area: Simulate Action log (`SimEventLog`). Read-only scan for the street-label change.

## Components & data flow
- `frontend/src/components/simulate/SimEventLog.tsx` — the "Action" panel. Props `{ events: EventView[]; stagedIndex: number }`. Renders the shown prefix `events.slice(0, stagedIndex)` as a flat `<ol.sim-log-list>`; each `<li>` = `.sim-log-pos` + `.sim-log-verb`. Returns `null` when `events.length === 0`.
- `frontend/src/components/SimulateView.tsx:875` — mounts `<SimEventLog events={hand.events} stagedIndex={stagedIndex} />`. `hand.board: string[]` is the full final board (already in scope; passed to `stagedTableState({ finalBoard: hand.board })` at :573).
- `frontend/src/components/simulate/simPlayback.ts` — `STREET_BOARD_COUNT { preflop:0, flop:3, turn:4, river:5 }` and internal `boardCountForStreet(street)`. `stagedTableState` slices `finalBoard.slice(0, boardCountForStreet(street))` for the felt.

## Invisible contracts (must not break)
1. **Staged reveal is the spoiler seam.** Only the revealed prefix (`slice(0, stagedIndex)`) may render. Anything keyed off the *full* `events`/`board` beyond that prefix leaks the outcome ahead of the replay (see `contracts/simulate-playback-spoiler.md`, commit c29fb23). Street headers must derive only from shown events; board chips for a street may show only cards for streets present in the shown prefix.
2. **`EventView` shape is fixed** — `{ position, action, amount_bb, street, all_in, seat_index }`. `street ∈ {preflop,flop,turn,river}` already present. No backend / type change.
3. **Reveal animation** — `.sim-log-reveal` fires once per staged line via the `key={i}`/`sim-log-in` keyframe. New header elements must not disrupt per-line entrance (headers are not list items).
4. **aria-live="polite"** on the list announces each newly-revealed line. Grouping must keep newly-revealed actions inside a live region.
5. **Design-token-only CSS** — new header/chip styles use existing tokens (`--primary`, `--gold-bright`, `--act-raise`, `--space-*`, `--radius-sm`, suit colors). No raw values.
6. **Card ordering** — `hand.board` is dealt order (flop[0..2], turn[3], river[4]); cumulative slice per street must preserve it.

## Integration points
- Board source: `hand.board` (SimulateView) → new `board` prop on SimEventLog.
- Per-street count: reuse `simPlayback` by exporting `boardCountForStreet` (avoid a second copy of `STREET_BOARD_COUNT`).
- No other consumer imports SimEventLog. SimActionBar, backend, `types.ts` untouched.
