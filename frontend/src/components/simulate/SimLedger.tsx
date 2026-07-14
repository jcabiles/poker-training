import type { SeatView } from "../../api/types";
import { fmtBb } from "./simGrade";

// Simulate S9 ledger — the club's rail sheet. A ruled P&L book: one row per
// seat (position · persona · running net_bb), figures set in mono tabular
// numerals like a settlement slip. net_bb is stack_bb - buyins_bb, so it
// already folds in auto-rebuys — a busted-and-rebought seat reads its true
// lifetime P&L. Hero is pinned first and marked; villains follow in seat order.
// Color is redundant (a +/- sign + the word class carry the meaning), so the
// tone tint never becomes the only cue.

function fmtNet(net: number): string {
  const sign = net > 0 ? "+" : net < 0 ? "−" : "";
  return `${sign}${fmtBb(Math.abs(net))}`;
}

function personaLabel(persona: string | null): string {
  if (!persona) return "You";
  return persona
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function SimLedger({ seats }: { seats: SeatView[] }) {
  // Hero first, then the rest in seat order — a stable reading order.
  const ordered = [...seats].sort((a, b) => {
    if (a.is_hero !== b.is_hero) return a.is_hero ? -1 : 1;
    return a.seat_index - b.seat_index;
  });

  return (
    <section className="sim-ledger" aria-label="Session ledger">
      <h2 className="sim-ledger-title">Rail sheet</h2>
      <table className="sim-ledger-table">
        <thead>
          <tr>
            <th scope="col" className="sim-led-seat">
              Seat
            </th>
            <th scope="col" className="sim-led-who">
              Player
            </th>
            <th scope="col" className="sim-led-net">
              Net bb
            </th>
          </tr>
        </thead>
        <tbody>
          {ordered.map((seat) => {
            const tone =
              seat.net_bb > 0 ? "up" : seat.net_bb < 0 ? "down" : "even";
            return (
              <tr
                key={seat.seat_index}
                className={"sim-led-row" + (seat.is_hero ? " sim-led-hero" : "")}
              >
                <td className="sim-led-seat">{seat.position}</td>
                <td className="sim-led-who">{personaLabel(seat.persona_type)}</td>
                <td className={"sim-led-net num sim-net-" + tone}>
                  {fmtNet(seat.net_bb)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
