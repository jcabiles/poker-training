import { useEffect, useRef } from "react";

import type { EvaluationResult } from "../api/types";
import RationaleTags from "./RationaleTags";

const TONE: Record<string, string> = {
  optimal: "good",
  acceptable: "good",
  mistake: "warn",
  blunder: "bad",
};

export default function FeedbackPanel({
  result,
  onNext,
}: {
  result: EvaluationResult;
  onNext: () => void;
}) {
  const tone = TONE[result.correctness ?? "optimal"] ?? "warn";
  const nextRef = useRef<HTMLButtonElement>(null);

  // CW-7: the decision button the user just clicked is now disabled, which
  // would otherwise strand keyboard focus on <body>. This panel only ever
  // mounts fresh (App.tsx renders it only while `result` is set, and grading
  // can't re-fire while a result exists), so a mount-only effect is enough.
  useEffect(() => {
    nextRef.current?.focus();
  }, []);

  return (
    <div
      className={"panel feedback " + tone + "-bg"}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <span className={"badge " + tone}>
        {(result.correctness ?? "").toUpperCase()} · ≈−{result.ev_loss_bb}bb
      </span>
      {result.is_mixed && (
        <p className="mixed">Mixed spot — more than one action is defensible here.</p>
      )}
      {/* N1 tier 1 — verdict: what happened (falls back to the flat explanation
          for any result graded outside the tiered wrapper). */}
      <p className="tier-verdict">{result.tiers?.verdict ?? result.explanation}</p>
      {result.chosen_eval && (
        <p className="chosen-eval">
          Your action: played {Math.round(result.chosen_eval.frequency * 100)}% here · EV ≈
          {result.chosen_eval.ev_bb}bb
        </p>
      )}
      {/* N1 tier 2 — reasoning: why, composed from tags + authored rationale. */}
      <RationaleTags tags={result.rationale_tags} />
      {result.tiers && <p className="tier-reasoning">{result.tiers.reasoning}</p>}
      {/* N1 tier 3 — deep dive: the full numbers, collapsed by default. */}
      <details className="tier-deepdive">
        <summary>Deep dive — full action mix</summary>
        {result.tiers && <p className="deepdive-text">{result.tiers.deep_dive}</p>}
        <ul className="mix">
          {result.per_action.map((a, i) => (
            <li key={i}>
              <b>
                {a.action}
                {a.size_bb ? ` ${a.size_bb}bb` : ""}
              </b>{" "}
              {Math.round(a.frequency * 100)}% · EV ≈{a.ev_bb}bb
              {a.action === result.best_action.action &&
                a.size_bb === result.best_action.size_bb && <span className="best"> best</span>}
            </li>
          ))}
        </ul>
        {/* N2/CW-2b: EVs are a heuristic proxy, not solver-exact -- the "≈"
            prefixes above plus this note keep that honest until Phase 3. */}
        <p className="studytest-hint">EV values are approximate (proxy, not solver-exact).</p>
      </details>
      <button
        ref={nextRef}
        type="button"
        className="btn btn-primary"
        onClick={onNext}
        aria-label="Next spot (shortcut Space)"
      >
        Next <kbd aria-hidden="true">Space</kbd>
      </button>
    </div>
  );
}
