import type { Spot } from "../api/types";
import { RANK_ORDER, handClass } from "../lib/poker";

const LEGEND: [string, string][] = [
  ["action-raise", "raise"],
  ["action-call", "call"],
  ["action-mixed", "mixed"],
  ["action-fold", "fold"],
];

export default function RangeGrid({
  spot,
  grid,
}: {
  spot: Spot;
  grid: Record<string, string>;
}) {
  const hero = handClass(spot.hero.hole_cards[0], spot.hero.hole_cards[1]);
  const node = spot.node_context.join(", ") + (spot.facing ? ` vs ${spot.facing}` : "");
  return (
    <div className="gridwrap">
      <div className="gridtitle">{node} range</div>
      <div className="grid">
        {RANK_ORDER.map((r1, i) =>
          RANK_ORDER.map((r2, j) => {
            const cls =
              i === j ? r1 + r2 : i < j ? r1 + r2 + "s" : RANK_ORDER[j] + RANK_ORDER[i] + "o";
            const action = grid[cls] ?? "fold";
            const isHero = cls === hero;
            return (
              <div
                key={`${i}-${j}`}
                className={`cell action-${action}${isHero ? " hero" : ""}`}
                title={`${cls}: ${action}`}
              >
                {cls}
              </div>
            );
          }),
        )}
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
  );
}
