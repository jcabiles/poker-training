import type { ActionType, Spot } from "../api/types";
import { legalDecisions } from "../lib/decisions";

export default function DecisionBar({
  spot,
  disabled,
  onDecide,
}: {
  spot: Spot;
  disabled: boolean;
  onDecide: (action: ActionType, sizeBb?: number | null) => void;
}) {
  const options = legalDecisions(spot);
  return (
    <div className="decisionbar">
      {options.map((d, i) => (
        <button
          key={i}
          className={"btn" + (d.primary ? " btn-primary" : "")}
          disabled={disabled}
          onClick={() => onDecide(d.action, d.size_bb)}
        >
          {d.label} <kbd>{d.key}</kbd>
        </button>
      ))}
    </div>
  );
}
