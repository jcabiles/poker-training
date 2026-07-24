import type { SeatView, ShowdownSeatView } from "../../api/types";
import { fmtBb } from "./simGrade";
import Card from "../Card";

// Simulate S9 hand-over recap — the settlement slip. Lists the seats that
// reached showdown with their revealed cards and this-hand chip delta. Dealing
// the next hand now lives on the topbar "Next hand →" control (SimulateView),
// which sits above the fold; this panel no longer carries its own deal button.
// Folded villains are never in `showdown`, so no
// hidden hole cards leak here. When the hand ends without a showdown (everyone
// folded to one seat), `showdown` is empty and we show the fold-out line
// instead. Position labels come from the seat roster.
//
// R1: two buttons let the hero reveal the just-played villain cards on demand —
// "Reveal Last-In" (seats still live at hand end) and "Reveal All" (every dealt
// seat). Cards that reached a genuine showdown also arrive through `showdown`
// and auto-reveal. The buttons are gated on the `debugReveal` toggle (default
// off) — a range-inspection aid — and, when on, appear after EVERY hand,
// including hands the hero played to showdown.

function fmtDelta(delta: number): string {
  const sign = delta > 0 ? "+" : delta < 0 ? "−" : "";
  return `${sign}${fmtBb(Math.abs(delta))}`;
}

export default function SimShowdown({
  showdown,
  seats,
  heroFolded,
  debugReveal,
  revealScope,
  onReveal,
}: {
  showdown: ShowdownSeatView[];
  seats: SeatView[];
  // True when the hero folded this hand — drives only the empty-showdown copy.
  heroFolded: boolean;
  // Debug range-inspection toggle. When on, the reveal buttons are offered after
  // every hand regardless of hero fold / showdown; when off (default) they are
  // hidden and the face-down range-reading drill is preserved.
  debugReveal: boolean;
  // Which reveal scope is currently active (drives the pressed state), or null.
  revealScope: "last-in" | "all" | null;
  onReveal: (scope: "last-in" | "all") => void;
}) {
  const posBySeat = new Map<number, string>(seats.map((s) => [s.seat_index, s.position]));
  const canManualReveal = debugReveal;

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
            ? debugReveal
              ? "No showdown — you folded. Reveal the villains below."
              : "No showdown — you folded."
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
    </section>
  );
}
