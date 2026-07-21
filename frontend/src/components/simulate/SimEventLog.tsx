import { useMemo } from "react";
import type { EventView } from "../../api/types";
import { boardCountForStreet } from "./simPlayback";

// Simulate S11 event log — the pacing seam. The server returns every bot action
// since the hero's last decision as one already-resolved batch; this log is
// where that batch is REPLAYED at a human pace. `stagedIndex` (owned by
// SimulateView, shared with the felt) is how many of the batch's events are
// revealed so far — we render only that prefix, so lines appear one at a time
// as the timer walks the index up. The same index gates the felt's seat state,
// keeping call and table in lockstep. Reads like a dealer's call sheet:
// position, verb, amount — now sheeted by street, each street's board dealt in
// its header. Empty when the hero opens the action.

const SUIT: Record<string, string> = { c: "♣", d: "♦", h: "♥", s: "♠" };

function verb(action: string, amount: number, allIn: boolean): string {
  switch (action) {
    case "fold":
      return "folds";
    case "check":
      return "checks";
    case "call":
      // All-in short-call never reads as a limp — the shove is the point.
      if (allIn) return `calls all-in ${amount}bb`;
      return amount <= 1 ? "limps" : `calls ${amount}bb`;
    case "bet":
      return allIn ? `shoves all-in ${amount}bb` : `bets ${amount}bb`;
    case "raise":
      return allIn ? `raises all-in to ${amount}bb` : `raises to ${amount}bb`;
    case "post":
      return allIn ? `posts all-in ${amount}bb` : `posts ${amount}bb`;
    default:
      return action;
  }
}

function cap(street: string): string {
  return street.charAt(0).toUpperCase() + street.slice(1);
}

// One street's board card, log-sized (a compact chip, not the felt's face card).
// Suit glyph is redundant with color — red is never the only cue.
function SimLogCard({ card }: { card: string }) {
  const rank = card[0] === "T" ? "10" : card[0];
  const suit = card[1];
  const red = suit === "h" || suit === "d";
  return (
    <span className={"sim-log-card" + (red ? " red" : "")}>
      <span className="sim-log-card-r">{rank}</span>
      <span className="sim-log-card-s">{SUIT[suit]}</span>
    </span>
  );
}

interface StreetGroup {
  street: string;
  // Each item keeps its GLOBAL index within the shown prefix — the reveal
  // animation keys off it so an entrance fires once and never re-fires as later
  // groups mount (a per-group index would reset to 0 and collide across groups).
  items: { e: EventView; gi: number }[];
}

export default function SimEventLog({
  events,
  stagedIndex,
  board,
}: {
  events: EventView[];
  stagedIndex: number;
  board: string[];
}) {
  // Group the revealed prefix into CONTIGUOUS runs of street — a new group only
  // when the street changes from the previous line. Not group-by-value: a
  // non-contiguous repeat of a street stays its own header rather than merging.
  const groups = useMemo<StreetGroup[]>(() => {
    const shown = events.slice(0, Math.max(0, stagedIndex));
    const out: StreetGroup[] = [];
    shown.forEach((e, gi) => {
      const last = out[out.length - 1];
      if (last && last.street === e.street) last.items.push({ e, gi });
      else out.push({ street: e.street, items: [{ e, gi }] });
    });
    return out;
  }, [events, stagedIndex]);

  if (events.length === 0) return null;

  // One aria-live region wraps every group so each newly-revealed line (and the
  // street header it arrives under) is announced once, in order.
  return (
    <section className="sim-log" aria-label="Recent action">
      <h2 className="sim-log-title">Action</h2>
      <div className="sim-log-groups" aria-live="polite">
        {groups.map((g) => {
          // Chip count comes from THIS group's own street — never the last shown
          // event's street — so a header never shows a card before that street's
          // action has been revealed (the felt has dealt it by then).
          const cardCount = boardCountForStreet(g.street);
          return (
            <div className="sim-log-group" key={g.items[0].gi}>
              <div className="sim-log-street">
                <span className="sim-log-street-name">{cap(g.street)}</span>
                {cardCount > 0 && (
                  <span className="sim-log-street-cards">
                    {board.slice(0, cardCount).map((c, ci) => (
                      <SimLogCard card={c} key={ci} />
                    ))}
                  </span>
                )}
              </div>
              <ol className="sim-log-list">
                {g.items.map(({ e, gi }) => (
                  <li
                    key={gi}
                    className={"sim-log-item sim-log-reveal sim-log-" + e.action}
                  >
                    <span className="sim-log-pos">{e.position}</span>
                    <span className="sim-log-verb">{verb(e.action, e.amount_bb, e.all_in)}</span>
                  </li>
                ))}
              </ol>
            </div>
          );
        })}
      </div>
    </section>
  );
}
