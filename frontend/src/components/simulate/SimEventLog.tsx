import type { EventView } from "../../api/types";

// Simulate S9 event log — a static list of the bot actions taken since the
// hero's last decision (S9 has no pacing; S11 owns any animation). Reads like a
// dealer's call sheet: position, verb, amount. Empty when the hero opens the
// action (nothing has happened yet), so callers gate on `events.length`.

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

export default function SimEventLog({ events }: { events: EventView[] }) {
  if (events.length === 0) return null;
  return (
    <section className="sim-log" aria-label="Recent action">
      <h2 className="sim-log-title">Action</h2>
      <ol className="sim-log-list">
        {events.map((e, i) => (
          <li key={i} className={"sim-log-item sim-log-" + e.action}>
            <span className="sim-log-pos">{e.position}</span>
            <span className="sim-log-verb">{verb(e.action, e.amount_bb)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
