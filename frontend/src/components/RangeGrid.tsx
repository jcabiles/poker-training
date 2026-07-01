import { useState } from "react";

import type { Spot } from "../api/types";
import { RANK_ORDER, handClass } from "../lib/poker";

const LEGEND: [string, string][] = [
  ["action-raise", "raise"],
  ["action-call", "call"],
  ["action-mixed", "mixed"],
  ["action-fold", "fold"],
];

const COLLAPSED_KEY = "rangeGrid.collapsed";
const TITLE_ID = "range-grid-title";

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(COLLAPSED_KEY) === "true";
  } catch {
    return false;
  }
}

function writeCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(COLLAPSED_KEY, collapsed ? "true" : "false");
  } catch {
    /* localStorage unavailable — collapse state just won't persist */
  }
}

export default function RangeGrid({
  spot,
  grid,
  revealed = false,
}: {
  spot: Spot;
  grid: Record<string, string>;
  /** CW-6: true only for the Test-mode post-grade reveal. That mount always
   * starts expanded (ignoring the persisted collapse preference — Study mode
   * may have left it collapsed) and plays a one-shot reveal animation. The
   * user can still collapse it afterward via the existing toggle, same as
   * Study mode. */
  revealed?: boolean;
}) {
  const [collapsed, setCollapsed] = useState(() => (revealed ? false : readCollapsed()));
  const hero = handClass(spot.hero.hole_cards[0], spot.hero.hole_cards[1]);
  const node = spot.node_context.join(", ") + (spot.facing ? ` vs ${spot.facing}` : "");

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      writeCollapsed(next);
      return next;
    });
  };

  return (
    <div className={"gridwrap" + (revealed ? " reveal" : "")}>
      <button
        type="button"
        className="gridtoggle"
        aria-expanded={!collapsed}
        aria-controls="range-grid-body"
        onClick={toggleCollapsed}
      >
        <span>Range</span>
        <span className="gridchevron" aria-hidden="true">
          {collapsed ? "▸" : "▾"}
        </span>
      </button>
      <div id="range-grid-body" hidden={collapsed}>
        <div className="gridtitle" id={TITLE_ID}>
          {node} range
        </div>
        {/* APG "table" semantics (CW-7), not "grid" — these cells are static,
            read-only lookups (no click/selection), so the interactive
            grid pattern (roving tabindex, arrow-key cell navigation) does
            not apply; APG itself says to use table for read-only data. Each
            row is a real role="row" element kept out of the box tree via
            `display: contents` so it doesn't disturb the existing 13-column
            CSS Grid placement on `.grid`. */}
        <div className="grid" role="table" aria-labelledby={TITLE_ID}>
          {RANK_ORDER.map((r1, i) => (
            <div className="gridrow" role="row" key={`row-${i}`}>
              {RANK_ORDER.map((r2, j) => {
                const cls =
                  i === j ? r1 + r2 : i < j ? r1 + r2 + "s" : RANK_ORDER[j] + RANK_ORDER[i] + "o";
                const action = grid[cls] ?? "fold";
                const isHero = cls === hero;
                return (
                  <div
                    key={`${i}-${j}`}
                    role="cell"
                    className={`cell action-${action}${isHero ? " hero" : ""}`}
                    title={`${cls}: ${action}`}
                    aria-label={`${cls}: ${action}${isHero ? ", your hand" : ""}`}
                  >
                    {cls}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div className="gridlegend">
          {LEGEND.map(([c, label]) => (
            <span key={c} className="lgi">
              <span className={`cell sample ${c}`} /> {label}
            </span>
          ))}
        </div>
        <div className="gridlegend">your hand: {hero}</div>
      </div>
    </div>
  );
}
