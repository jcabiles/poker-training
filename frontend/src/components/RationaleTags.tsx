/**
 * Human-readable chips for `EvaluationResult.rationale_tags` — the reasoning
 * behind a grade (node type, range advantage, hand category, board texture),
 * not just the pass/fail verdict. CW-5.
 *
 * Postflop tags are rich (e.g. ["cbet", "hero", "draw", "wet"]); preflop is
 * currently just ["chart"] pre-decision, or a single mistake-shape tag like
 * ["over_fold"] post-decision — thin by design today (deeper preflop "why"
 * is a later enhancement). This renders whatever tags the backend sends; it
 * doesn't invent reasoning that isn't there.
 */

// Tag -> short human phrase. Grouped by where each tag comes from in
// backend/app/domain/{grading,postflop}.py.
const TAG_PHRASES: Record<string, string> = {
  // Grading basis
  chart: "chart-based",
  exploit: "exploit adjustment",

  // Preflop mistake shape (post-decision; grading.py::_tags)
  correct: "correct line",
  over_fold: "folded too much",
  over_aggressive: "too aggressive",
  under_aggressive: "too passive",
  loose_call: "loose call",
  off_chart: "off chart",

  // Postflop node (postflop.py)
  cbet: "c-bet spot",
  vs_cbet: "facing a c-bet",
  vs_check_raise: "facing a check-raise",

  // Range advantage — aggressor's view (cbet node)
  hero: "you have range advantage",
  villain: "villain has range advantage",
  // Range advantage — defender's view (vs_cbet / vs_check_raise nodes)
  defender: "you have range advantage",
  aggressor: "villain has range advantage",
  neutral: "range advantage is neutral",

  // Hand category
  strong: "strong hand",
  weak_made: "weak made hand",
  draw: "drawing hand",
  air: "no made hand",

  // Board texture
  wet: "wet board",
  dry: "dry board",
  medium: "medium board",
};

/** Falls back to de-slugging an unmapped tag (e.g. a future backend tag)
 * instead of hiding it. */
function describeTag(tag: string): string {
  return TAG_PHRASES[tag] ?? tag.replace(/_/g, " ");
}

export default function RationaleTags({ tags }: { tags: string[] }) {
  if (tags.length === 0) return null;
  return (
    <ul className="rationale">
      {tags.map((tag, i) => (
        <li key={`${tag}-${i}`} className="rationale-chip">
          {describeTag(tag)}
        </li>
      ))}
    </ul>
  );
}
