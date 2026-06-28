const SUIT: Record<string, string> = { c: "♣", d: "♦", h: "♥", s: "♠" };

export default function Card({ card }: { card: string }) {
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
