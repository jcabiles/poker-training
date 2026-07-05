import type { CSSProperties } from "react";

import type { HistoryAction, Spot } from "../api/types";
import Card from "./Card";

const RAISE_VERB = ["opens", "3-bets", "4-bets", "5-bets", "jams"];

// Canonical 9-max seating order (clockwise). Seats are rotated so the hero
// pod always sits bottom-center; action then reads clockwise around the rim,
// exactly like a live table.
const RING = ["UTG", "UTG1", "UTG2", "LJ", "HJ", "CO", "BTN", "SB", "BB"];

type SeatAction = { label: string; kind: "raise" | "call" | "fold" };

// Latest non-post action per seat. The opens/3-bets/4-bets escalation ladder
// is preflop-only (a flop check-raise renders "raises to", never inheriting a
// "3-bets" from an earlier preflop open) — same rule as the retired
// betting-line text.
function latestActions(history: HistoryAction[]): Record<string, SeatAction> {
  let preflopRaises = 0;
  const latest: Record<string, SeatAction> = {};
  for (const h of history) {
    if (h.action === "post") continue;
    if (h.action === "raise") {
      if (h.street === "preflop") {
        const verb = RAISE_VERB[Math.min(preflopRaises, RAISE_VERB.length - 1)];
        latest[h.position] = { label: `${verb} ${h.amount_bb}`, kind: "raise" };
        preflopRaises += 1;
      } else {
        latest[h.position] = { label: `raises to ${h.amount_bb}`, kind: "raise" };
      }
    } else if (h.action === "call") {
      const limp = h.street === "preflop" && h.amount_bb <= 1;
      latest[h.position] = { label: limp ? "limps" : "calls", kind: "call" };
    } else if (h.action === "bet") {
      latest[h.position] = { label: `bets ${h.amount_bb}`, kind: "raise" };
    } else if (h.action === "fold") {
      latest[h.position] = { label: "fold", kind: "fold" };
    }
  }
  return latest;
}

// Seat-pod coordinates on the elliptical rail — geometry data, not styling
// (same idiom as RangeGrid's proportional flex values). Slot 0 (hero) is
// bottom-center (θ=90° in screen coords); slots proceed clockwise.
function slotStyle(i: number, n: number): CSSProperties {
  const theta = Math.PI / 2 + (i * 2 * Math.PI) / n;
  const x = 50 + 43 * Math.cos(theta);
  const y = 50 + 38 * Math.sin(theta);
  return { left: `${x}%`, top: `${y}%` };
}

export default function PokerTable({ spot }: { spot: Spot }) {
  const actions = latestActions(spot.action_history);
  const byPos = new Map(spot.players.map((p) => [p.position, p]));
  // Enriched spots carry all 9 seats; older payloads only the dealt-in actors
  // — filtering RING by presence degrades gracefully either way.
  const ring = RING.filter((pos) => byPos.has(pos));
  const heroIdx = Math.max(ring.indexOf(spot.hero.position), 0);
  const seats = ring.map((_, i) => byPos.get(ring[(heroIdx + i) % ring.length])!);

  return (
    <div className="felt">
      <div className="ctx">
        {spot.node_context.join(", ")} · {spot.game.stakes.sb}/{spot.game.stakes.bb} ·{" "}
        {spot.game.table_size}-max · {spot.effective_stack_bb}bb deep
      </div>
      {spot.villain_type && (
        <div className="villain">Villain: {spot.villain_type.replace(/_/g, " ")}</div>
      )}
      <div className="tablering" role="group" aria-label="table seats">
        <div className="rail" aria-hidden="true" />
        <div className="table-center">
          {spot.board.length > 0 && (
            <div className="board" aria-label="community cards">
              {spot.board.map((c, i) => (
                <Card key={i} card={c} />
              ))}
            </div>
          )}
          <div className="pot">
            Pot {spot.pot_bb}bb{spot.spr != null ? ` · SPR ${spot.spr}` : ""}
          </div>
        </div>
        {seats.map((p, i) => {
          const act = actions[p.position];
          const folded = p.status === "folded";
          if (p.is_hero) {
            return (
              <div className="tseat heroseat" key={p.position} style={slotStyle(i, seats.length)}>
                {act && <span className={"actchip act-" + act.kind}>{act.label}</span>}
                <div className="cards">
                  {spot.hero.hole_cards.map((c, j) => (
                    <Card key={j} card={c} />
                  ))}
                </div>
                <div className="herometa">
                  {spot.hero.position}
                  {spot.hero.position === "BTN" && (
                    <span className="dealer" aria-label="dealer button">
                      D
                    </span>
                  )}{" "}
                  · {spot.hero.stack_bb}bb · you are to act
                </div>
              </div>
            );
          }
          return (
            <div
              className={"tseat" + (folded ? " tseat-folded" : "")}
              key={p.position}
              style={slotStyle(i, seats.length)}
            >
              {act && <span className={"actchip act-" + act.kind}>{act.label}</span>}
              {!folded && (
                <span className="tseat-cards">
                  <Card faceDown />
                  <Card faceDown />
                </span>
              )}
              <span className="pos">
                {p.position}
                {p.position === "BTN" && (
                  <span className="dealer" aria-label="dealer button">
                    D
                  </span>
                )}
              </span>
              <span className="stack">{p.stack_bb}bb</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
