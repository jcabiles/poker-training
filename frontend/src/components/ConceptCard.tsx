import type { ConceptCard as ConceptCardData } from "../api/types";
import { formatHash } from "../lib/hashRoute";

/**
 * Point-of-need teaching card (N8) — surfaced below the feedback tiers for a
 * MISTAKE/BLUNDER result. Collapsed by default: title + summary are always
 * visible, the full body is behind the existing <details> convention (see
 * FeedbackPanel's "Deep dive"). "Drill this" round-trips to the concept's
 * drill mode via hash routing — no App.tsx involvement needed.
 */
export default function ConceptCard({ card }: { card: ConceptCardData }) {
  const bodyParagraphs = card.body.split(/\n\n+/);

  const drillThis = () => {
    window.location.hash = formatHash("drill", card.drill_mode);
  };

  return (
    <div className="concept-card">
      <p className="concept-card-title">{card.title}</p>
      <p className="concept-card-summary">{card.summary}</p>
      <details>
        <summary>Learn more</summary>
        {bodyParagraphs.map((p, i) => (
          <p key={i} className="concept-card-body">
            {p}
          </p>
        ))}
        <button
          type="button"
          className="btn"
          onClick={drillThis}
          aria-label={`Drill this concept (${card.drill_mode} mode)`}
        >
          Drill this
        </button>
      </details>
    </div>
  );
}
