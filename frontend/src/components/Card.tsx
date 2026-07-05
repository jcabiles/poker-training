const SUIT: Record<string, string> = { c: "♣", d: "♦", h: "♥", s: "♠" };

// `faceDown` renders a card back (no rank/suit) — used for villains' unseen
// hole cards on the table. `card` stays required for face-up rendering; the
// union keeps callers honest (a face-up card without a value can't typecheck).
type CardProps = { card: string; faceDown?: false } | { card?: undefined; faceDown: true };

export default function Card(props: CardProps) {
  if (props.faceDown) {
    return <span className="card back" aria-hidden="true" />;
  }
  const { card } = props;
  const rank = card[0] === "T" ? "10" : card[0];
  const suit = card[1];
  const red = suit === "h" || suit === "d";
  return (
    <span className={"card" + (red ? " red" : "")}>
      <span className="r">{rank}</span>
      <span className="s">{SUIT[suit]}</span>
    </span>
  );
}
