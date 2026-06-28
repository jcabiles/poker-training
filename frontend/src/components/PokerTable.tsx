import type { HistoryAction, Spot } from "../api/types";
import Card from "./Card";

const RAISE_VERB = ["opens", "3-bets", "4-bets", "5-bets", "jams"];

function bettingLine(history: HistoryAction[]): string {
  let raises = 0;
  const parts: string[] = [];
  for (const h of history) {
    if (h.action === "post") continue;
    if (h.action === "raise") {
      const verb = RAISE_VERB[Math.min(raises, RAISE_VERB.length - 1)];
      parts.push(`${h.position} ${verb} ${h.amount_bb}`);
      raises += 1;
    } else if (h.action === "call") {
      parts.push(`${h.position} ${h.amount_bb <= 1 ? "limps" : "calls"}`);
    }
  }
  return parts.join(" · ");
}

export default function PokerTable({ spot }: { spot: Spot }) {
  const villains = spot.players.filter((p) => !p.is_hero);
  const line = bettingLine(spot.action_history);
  return (
    <div className="felt">
      <div className="ctx">
        {spot.node_context.join(", ")} · {spot.game.stakes.sb}/{spot.game.stakes.bb} ·{" "}
        {spot.game.table_size}-max · {spot.effective_stack_bb}bb deep
      </div>
      {line && <div className="line">{line}</div>}
      {spot.villain_type && (
        <div className="villain">🎯 Villain: {spot.villain_type.replace(/_/g, " ")}</div>
      )}
      <div className="seats">
        {villains.map((p, i) => (
          <div className="seat" key={i}>
            <div className="pos">{p.position}</div>
            <div className="stack">{p.stack_bb}bb</div>
          </div>
        ))}
      </div>
      {spot.board.length > 0 && (
        <div className="board" aria-label="community cards">
          {spot.board.map((c, i) => (
            <Card key={i} card={c} />
          ))}
        </div>
      )}
      <div className="pot">Pot {spot.pot_bb}bb{spot.spr != null ? ` · SPR ${spot.spr}` : ""}</div>
      <div className="hero">
        <div className="cards">
          {spot.hero.hole_cards.map((c, i) => (
            <Card key={i} card={c} />
          ))}
        </div>
        <div className="herometa">
          {spot.hero.position} · {spot.hero.stack_bb}bb · you are to act
        </div>
      </div>
    </div>
  );
}
