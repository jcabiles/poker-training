import type { SeatView, ShowdownSeatView } from "../../api/types";
import { fmtBb } from "./simGrade";
import Card from "../Card";

// Simulate S9 hand-over recap — the settlement slip. Lists the seats that
// reached showdown with their revealed cards and this-hand chip delta, plus the
// "Deal next hand" control. Folded villains are never in `showdown`, so no
// hidden hole cards leak here. When the hand ends without a showdown (everyone
// folded to one seat), `showdown` is empty and we show the fold-out line
// instead. Position labels come from the seat roster.
//
// R1: when the HERO folded and the remaining villains did not reach showdown,
// they stayed face-down. Two buttons let the hero reveal them on demand —
// "Reveal Last-In" (seats still live at hand end) and "Reveal All" (every dealt
// seat). If villains did reach showdown, their compared cards arrive through
// `showdown` and auto-reveal like any other public showdown.

function fmtDelta(delta: number): string {
  const sign = delta > 0 ? "+" : delta < 0 ? "−" : "";
  return `${sign}${fmtBb(Math.abs(delta))}`;
}

export default function SimShowdown({
  showdown,
  seats,
  onNextHand,
  dealing,
  heroFolded,
  revealScope,
  onReveal,
}: {
  showdown: ShowdownSeatView[];
  seats: SeatView[];
  onNextHand: () => void;
  dealing: boolean;
  // R1: true only when the hero folded this hand — the sole case where villains
  // stayed face-down and there is anything to reveal. Otherwise the buttons are
  // hidden (a genuine showdown already auto-revealed).
  heroFolded: boolean;
  // Which reveal scope is currently active (drives the pressed state), or null.
  revealScope: "last-in" | "all" | null;
  onReveal: (scope: "last-in" | "all") => void;
}) {
  const posBySeat = new Map<number, string>(seats.map((s) => [s.seat_index, s.position]));
  const canManualReveal = heroFolded && showdown.length === 0;

  return (
    <section className="sim-showdown panel" aria-label="Hand result">
      <h2 className="sim-showdown-title">Hand complete</h2>
      {showdown.length > 0 ? (
        <ul className="sim-showdown-list">
          {showdown.map((s) => {
            const tone = s.delta_bb > 0 ? "up" : s.delta_bb < 0 ? "down" : "even";
            return (
              <li key={s.seat_index} className="sim-showdown-row">
                <span className="sim-showdown-pos">
                  {posBySeat.get(s.seat_index) ?? `Seat ${s.seat_index}`}
                </span>
                <span className="cards sim-showdown-cards">
                  {s.hole_cards.map((c, j) => (
                    <Card key={j} card={c} />
                  ))}
                </span>
                <span className={"sim-showdown-delta num sim-net-" + tone}>
                  {fmtDelta(s.delta_bb)}bb
                </span>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="sim-showdown-fold">
          {heroFolded
            ? "No showdown — you folded. Reveal the villains below."
            : "The pot was taken down before showdown — no cards revealed."}
        </p>
      )}
      {canManualReveal && (
        <div className="sim-reveal-actions" role="group" aria-label="Reveal villain hands">
          {(["last-in", "all"] as const).map((scope) => (
            <button
              key={scope}
              type="button"
              className={
                "btn sim-reveal-btn" + (revealScope === scope ? " sim-reveal-btn-on" : "")
              }
              onClick={() => onReveal(scope)}
              aria-pressed={revealScope === scope}
            >
              {scope === "last-in" ? "Reveal last-in" : "Reveal all"}
            </button>
          ))}
        </div>
      )}
      <button
        type="button"
        className="btn btn-primary sim-deal-btn"
        onClick={onNextHand}
        disabled={dealing}
      >
        {dealing ? "Dealing…" : "Deal next hand"}
      </button>
    </section>
  );
}
