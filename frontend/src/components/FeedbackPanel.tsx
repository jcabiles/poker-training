import type { EvaluationResult } from "../api/types";

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
  return (
    <div className={"panel feedback " + tone + "-bg"}>
      <span className={"badge " + tone}>
        {(result.correctness ?? "").toUpperCase()} · −{result.ev_loss_bb}bb
      </span>
      {result.is_mixed && (
        <p className="mixed">Mixed spot — more than one action is defensible here.</p>
      )}
      <p className="why">{result.explanation}</p>
      <ul className="mix">
        {result.per_action.map((a, i) => (
          <li key={i}>
            <b>{a.action}</b> {Math.round(a.frequency * 100)}% · EV {a.ev_bb}bb
            {a.action === result.best_action.action && <span className="best">best</span>}
          </li>
        ))}
      </ul>
      <button className="btn btn-primary" onClick={onNext}>
        Next <kbd>Space</kbd>
      </button>
    </div>
  );
}
