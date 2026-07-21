# Tickets — Action panel street-labeled board headers

Spec: `docs/ai-dlc/specs/action-street-labels.md`. Small FE-only change; ~1 dev, sequential. Owner file per ticket in **bold**.

## T1 — Export `boardCountForStreet`
- **`frontend/src/components/simulate/simPlayback.ts`**
- Change `function boardCountForStreet` → `export function boardCountForStreet`. Nothing else.
- **Done:** `import { boardCountForStreet } from "./simPlayback"` resolves; `npm run typecheck` clean; existing `simPlayback.test.ts` still green.

## T2 — Group SimEventLog by street + render headers
- **`frontend/src/components/simulate/SimEventLog.tsx`**
- Add prop `board: string[]`.
- In a `useMemo` on `(events, stagedIndex)`, build `shown = events.slice(0, Math.max(0, stagedIndex))` and split into groups by **contiguous run of `street`** (new group when street changes from prev item) — NOT `groupBy(street)`. Each group item keeps its **global index in `shown`** for keying.
- Per group render a header: capitalized street label + a chip per card in `board.slice(0, boardCountForStreet(group.street))` — count from the **group's own street**, never the terminal/last-shown street (spoiler guard). Preflop → 0 chips. Unknown street → 0 chips, header still renders.
- Then the group's `<li>` action lines (existing markup). `<li key={globalIndex}>` (running counter across groups) so `sim-log-reveal` fires exactly once and never re-fires on shown lines. Header key = street string.
- Keep exactly ONE `aria-live="polite"` region wrapping the whole grouped list (not one per group); header text inside it.
- Empty state unchanged (`events.length === 0` → `null`); `stagedIndex === 0` → title only, no header.
- Card chip: rank + suit glyph; class marks red suits (♥♦) vs black (♠♣) for the CSS in T4.
- **Done:** `npm run typecheck && npm run build` clean; component renders grouped list with headers (verified in T5).
- **Depends:** T1.

## T3 — Pass board from SimulateView
- **`frontend/src/components/SimulateView.tsx`** (line ~875)
- `<SimEventLog events={hand.events} stagedIndex={stagedIndex} board={hand.board} />`.
- **Done:** typecheck clean; log shows chips at runtime.
- **Depends:** T2.

## T4 — Header + card-chip styles
- **`frontend/src/styles/app.css`** (near `.sim-log*`, ~2826)
- Add `.sim-log-street` (label, gilt rule/underline per mockup 02), `.sim-log-street-cards`, `.sim-log-card` (+ `.red` variant). Tokens only (`--primary`, `--gold-bright`, `--border`, `--space-*`, `--radius-sm`, suit/ink colors). AA in both themes.
- **Done:** headers + chips match mockup 02; light/dark legible.
- **Depends:** T2 (needs the class names).

## T5 — Verify end-to-end
- No file owned; runs the spec's Verify-by.
- `npm run typecheck && npm run build`; `./scripts/serve.sh start`; play a hand to river with villain action; confirm headers, cumulative chip counts (3/4/5), preflop label-only, staged-reveal gating (no empty header, no card before the felt deals it, no earlier header gaining later chips), stagedIndex=0 shows title-only, animation fires once, both themes.
- **Done:** all Verify-by steps pass.
- **Depends:** T2, T3, T4.

Parallelizable: none meaningfully (T2 is the spine). T4 can start once T2's class names are fixed.
