import type { EventView } from "../../api/types";

// Simulate S11 event log — the pacing seam. The server returns every bot action
// since the hero's last decision as one already-resolved batch; this log is
// where that batch is REPLAYED at a human pace. `stagedIndex` (owned by
// SimulateView, shared with the felt) is how many of the batch's events are
// revealed so far — we render only that prefix, so lines appear one at a time
// as the timer walks the index up. The same index gates the felt's seat state,
// keeping call and table in lockstep. Reads like a dealer's call sheet:
// position, verb, amount. Empty when the hero opens the action.

function verb(action: string, amount: number): string {
  switch (action) {
    case "fold":
      return "folds";
    case "check":
      return "checks";
    case "call":
      return amount <= 1 ? "limps" : `calls ${amount}bb`;
    case "bet":
      return `bets ${amount}bb`;
    case "raise":
      return `raises to ${amount}bb`;
    case "post":
      return `posts ${amount}bb`;
    default:
      return action;
  }
}

export default function SimEventLog({
  events,
  stagedIndex,
}: {
  events: EventView[];
  stagedIndex: number;
}) {
  if (events.length === 0) return null;
  // Only the narrated prefix is visible; the rest of the batch is withheld until
  // the timer reveals it. aria-live=polite so each newly-revealed line is
  // announced as the action plays out.
  const shown = events.slice(0, Math.max(0, stagedIndex));
  return (
    <section className="sim-log" aria-label="Recent action">
      <h2 className="sim-log-title">Action</h2>
      <ol className="sim-log-list" aria-live="polite">
        {shown.map((e, i) => (
          <li
            // key includes the reveal index so each staged line mounts fresh and
            // its entrance animation fires exactly once.
            key={i}
            className={"sim-log-item sim-log-reveal sim-log-" + e.action}
          >
            <span className="sim-log-pos">{e.position}</span>
            <span className="sim-log-verb">{verb(e.action, e.amount_bb)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
