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
      <RationaleTags tags={result.rationale_tags} />
      <p className="why">{result.explanation}</p>
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
