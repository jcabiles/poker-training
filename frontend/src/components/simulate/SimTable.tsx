import type { CSSProperties } from "react";

import type { SeatView, ShowdownSeatView, SimulateHandView } from "../../api/types";
import Card from "../Card";

// Simulate S9 table. A purpose-built felt for the persistent session: it reuses
// PokerTable's felt/ring/rail CSS classes and elliptical geometry verbatim (so
// it reads as the same room), but renders the richer per-seat data S9 owns and
// PokerTable does not carry — persona badge, chips-in-front, live status, and
// showdown reveals. PokerTable.tsx itself stays untouched (Practice/Quiz still
// use it). Privacy: a non-hero seat's hole cards are rendered ONLY when that
// seat is in `showdown` — folded/live villains stay face-down.

// Canonical 9-max seating order (clockwise) — same ring PokerTable uses.
const RING = ["UTG", "UTG1", "UTG2", "LJ", "HJ", "CO", "BTN", "SB", "BB"];

// Seat-pod coordinates on the elliptical rail (identical math to PokerTable's
// slotStyle — geometry DATA, not styling). Slot 0 (hero) sits bottom-center.
function slotStyle(i: number, n: number): CSSProperties {
  const theta = Math.PI / 2 + (i * 2 * Math.PI) / n;
  const x = 50 + 43 * Math.cos(theta);
  const y = 50 + 38 * Math.sin(theta);
  return { left: `${x}%`, top: `${y}%` };
}

// Persona archetypes arrive as SCREAMING_SNAKE VillainType values; render them
// as short Title Case labels for the seat badge.
function personaLabel(persona: string): string {
  return persona
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function SimTable({ hand }: { hand: SimulateHandView }) {
  const { seats, board, pot_bb, hero, to_act_seat, button_seat } = hand;
  const showdownBySeat = new Map<number, ShowdownSeatView>(
    hand.showdown.map((s) => [s.seat_index, s]),
  );

  // Rotate the ring so the hero pod is always bottom-center, exactly like
  // PokerTable. Seats arrive indexed 0..8; position tells us where each sits on
  // the felt. Order the felt slots by the RING, anchored on the hero.
  const byPos = new Map<string, SeatView>(seats.map((s) => [s.position, s]));
  const ring = RING.filter((pos) => byPos.has(pos));
  const heroIdx = Math.max(ring.indexOf(hero.position), 0);
  const ordered = ring.map((_, i) => byPos.get(ring[(heroIdx + i) % ring.length])!);

  return (
    <div className="stage">
      <div className="felt felt-staged">
        <div className="ctx">
          Simulate · 0.5/1 · 9-max · hand{" "}
          <span className="sim-ctx-no">{hand.hand_no}</span> · {hand.street}
        </div>
        <div className="tablering" role="group" aria-label="table seats">
          <div className="rail" aria-hidden="true" />
          <div className="table-center">
            {board.length > 0 && (
              <div className="board" aria-label="community cards">
                {board.map((c, i) => (
                  <Card key={i} card={c} />
                ))}
              </div>
            )}
            <div className="pot">Pot {pot_bb}bb</div>
          </div>

          {ordered.map((seat, i) => {
            const isButton = seat.seat_index === button_seat;
            const folded = seat.status === "folded";
            const allin = seat.status === "allin";
            const isToAct = to_act_seat != null && seat.seat_index === to_act_seat;
            const reveal = showdownBySeat.get(seat.seat_index);
            const style = slotStyle(i, ordered.length);

            // Chips-in-front: this street's commitment, shown as a small puck in
            // front of the seat. Suppressed for folded seats (nothing to show).
            const chips =
              seat.invested_street_bb > 0 && !folded ? (
                <span className="sim-chips" title="chips in front">
                  {seat.invested_street_bb}bb
                </span>
              ) : null;

            if (seat.is_hero) {
              return (
                <div
                  className={
                    "tseat heroseat sim-seat" + (isToAct ? " sim-seat-act" : "")
                  }
                  key={seat.seat_index}
                  style={style}
                >
                  {chips}
                  <div className={"hero-ring" + (isToAct ? " sim-ring-live" : "")}>
                    <div className="cards">
                      {hero.hole_cards.map((c, j) => (
                        <Card key={j} card={c} />
                      ))}
                    </div>
                  </div>
                  <div className="herometa">
                    {hero.position}
                    {isButton && (
                      <span className="dealer" aria-label="dealer button">
                        D
                      </span>
                    )}{" "}
                    · <span className="sim-stack num">{hero.stack_bb}bb</span>
                    {isToAct && (
                      <>
                        {" "}
                        · <span className="toact">your turn</span>
                      </>
                    )}
                  </div>
                </div>
              );
            }

            return (
              <div
                className={
                  "tseat sim-seat" +
                  (folded ? " tseat-folded" : "") +
                  (isToAct ? " sim-seat-act" : "")
                }
                key={seat.seat_index}
                style={style}
              >
                {chips}
                {reveal ? (
                  <span className="cards sim-reveal" aria-label={`${seat.position} shows`}>
                    {reveal.hole_cards.map((c, j) => (
                      <Card key={j} card={c} />
                    ))}
                  </span>
                ) : (
                  !folded && (
                    <span className="tseat-cards">
                      <Card faceDown />
                      <Card faceDown />
                    </span>
                  )
                )}
                <span className="pos">
                  {seat.position}
                  {isButton && (
                    <span className="dealer" aria-label="dealer button">
                      D
                    </span>
                  )}
                </span>
                {seat.persona_type && (
                  <span className="sim-persona" title={personaLabel(seat.persona_type)}>
                    {personaLabel(seat.persona_type)}
                  </span>
                )}
                <span className="stack num">
                  {seat.stack_bb}bb
                  {allin && <span className="sim-allin"> all-in</span>}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
