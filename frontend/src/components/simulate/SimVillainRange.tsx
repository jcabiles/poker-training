import type { CSSProperties } from "react";

import type { VillainRangeView } from "../../api/types";
import { RANK_ORDER } from "../../lib/poker";

// Simulate villain-range (V2) — a weighted 13×13 HEAT chart of one live
// villain's estimated hand-range. This is a NEW sim-owned cell renderer, NOT
// RangeGrid's action-segment cells: each cell is a single champagne-ink wash
// whose opacity tracks the class weight (one metal voice, matching the room),
// so the eye reads "how likely is this class" at a glance. All styles scope
// under `.sim-vrange-*` — no shared grid/RangeGrid classes are touched.
//
// Honesty rails (spec):
//  • Heat must not rely on color alone: nonzero cells carry a min-opacity floor
//    and the class label is always full-contrast, so weight is legible without
//    reading intensity. Zero-weight classes recede to bare ground (empty).
//  • Preflop is EXACT; postflop is an ≈-estimate — an "estimated" tag shows
//    whenever `exact=false`.
//
// Open/close and fetch/refetch/stale-guard all live in SimulateView; this is a
// pure presentational panel driven by the resolved `range` (or a loading/empty
// state while SimulateView is mid-fetch).

const TITLE_ID = "sim-vrange-title";
const GRID_ID = "sim-vrange-grid";

// The 169 hand classes in RANK_ORDER row/col order — pairs on the diagonal,
// suited above it (i<j), offsuit below (i>j). Same construction RangeGrid uses,
// re-derived here (read-only) so no shared code is imported.
function classAt(i: number, j: number): string {
  const r1 = RANK_ORDER[i];
  const r2 = RANK_ORDER[j];
  if (i === j) return r1 + r2;
  if (i < j) return r1 + r2 + "s";
  return RANK_ORDER[j] + RANK_ORDER[i] + "o";
}

export default function SimVillainRange({
  position,
  range,
  loading,
  errored,
  onClose,
}: {
  /** Seat position label (e.g. "CO") for the header + aria copy. */
  position: string;
  /** Resolved estimate, or null while the first fetch is in flight. */
  range: VillainRangeView | null;
  loading: boolean;
  errored: boolean;
  onClose: () => void;
}) {
  const available = range?.available === true && range.weights != null;
  const weights = range?.weights ?? null;
  const persona = range?.persona_label ?? null;
  const estimated = range != null && range.available && !range.exact;

  // Peak weight normalizes the heat so the hottest class reads as fully inked
  // regardless of the raw scale (weights are relative, not probabilities that
  // sum to 1). Nonzero cells then floor at MIN_OPACITY so a faint class is
  // still visibly present (weight is never conveyed by opacity alone anyway —
  // the label stays full-contrast — but the floor keeps the heat honest).
  const peak = weights ? Math.max(0, ...Object.values(weights)) : 0;
  const MIN_OPACITY = 0.16;

  return (
    <section
      className="sim-vrange"
      aria-labelledby={TITLE_ID}
      onKeyDown={(e) => {
        // Esc closes the panel when focus is inside it (design-review low-3;
        // non-modal, so this is a convenience, not a focus trap).
        if (e.key === "Escape") onClose();
      }}
    >
      <header className="sim-vrange-head">
        <div className="sim-vrange-title" id={TITLE_ID}>
          <span className="sim-vrange-pos num">{position}</span>
          {persona && <span className="sim-vrange-persona">{persona}</span>}
          <span className="sim-vrange-kicker">
            {/* "estimated" only when the math actually is (postflop) — a
                preflop-exact range saying "estimated" contradicted the absent
                amber tag (design-review low-2). */}
            {estimated ? "estimated range" : "range"}
          </span>
        </div>
        <div className="sim-vrange-head-aside">
          {estimated && (
            <span
              className="sim-vrange-approx"
              title="Postflop conditioning is approximate"
            >
              estimated
            </span>
          )}
          <button
            type="button"
            className="sim-vrange-close"
            onClick={onClose}
            aria-label={`Close estimated range for ${position}`}
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>
      </header>

      {loading && !range ? (
        <p className="sim-vrange-status" role="status">
          Reading the range…
        </p>
      ) : errored ? (
        <p className="sim-vrange-status sim-vrange-status-quiet" role="status">
          Range unavailable right now.
        </p>
      ) : available && weights ? (
        <div className="sim-vrange-grid" role="table" aria-labelledby={TITLE_ID} id={GRID_ID}>
          {RANK_ORDER.map((_, i) => (
            <div className="sim-vrange-row" role="row" key={`r${i}`}>
              {RANK_ORDER.map((__, j) => {
                const cls = classAt(i, j);
                const w = weights[cls] ?? 0;
                const on = w > 0;
                // Normalize to peak, then floor nonzero cells so a faint class
                // is still perceptibly inked. Zero cells stay bare ground.
                const intensity = on && peak > 0 ? MIN_OPACITY + (1 - MIN_OPACITY) * (w / peak) : 0;
                const style = { "--w": intensity } as CSSProperties;
                const pct = peak > 0 ? Math.round((w / peak) * 100) : 0;
                return (
                  <div
                    key={`c${i}-${j}`}
                    role="cell"
                    className={"sim-vrange-cell" + (on ? " sim-vrange-cell-on" : "")}
                    style={style}
                    aria-label={
                      on ? `${cls}: ${pct}% of peak weight` : `${cls}: not in range`
                    }
                    title={on ? `${cls} · ${pct}%` : `${cls} · —`}
                  >
                    <span className="sim-vrange-fill" aria-hidden="true" />
                    <span className="sim-vrange-label">{cls}</span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      ) : (
        <p className="sim-vrange-status sim-vrange-status-quiet" role="status">
          No range for this seat right now.
        </p>
      )}
    </section>
  );
}
