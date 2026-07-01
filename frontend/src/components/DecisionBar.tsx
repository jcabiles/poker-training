import { useRef, useState } from "react";
import type { KeyboardEvent } from "react";

import type { ActionType, Spot } from "../api/types";
import { legalDecisions } from "../lib/decisions";

// APG Toolbar pattern (CW-7): exactly one button is a tab stop at a time
// (roving tabindex); Left/Right/Home/End move it. This is layered underneath
// — and independent of — App.tsx's global single-letter shortcuts
// (F/C/R/K/B/V), which keep working unchanged via their own activeElement
// guard: those fire regardless of focus, this only governs Tab/Arrow travel
// once the user has tabbed into the bar.
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
  const [activeIndex, setActiveIndex] = useState(0);
  const btnRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const activeSafe = Math.min(activeIndex, options.length - 1);

  const focusAt = (i: number) => {
    if (options.length === 0) return;
    const next = (i + options.length) % options.length;
    setActiveIndex(next);
    btnRefs.current[next]?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      focusAt(activeSafe + 1);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      focusAt(activeSafe - 1);
    } else if (e.key === "Home") {
      e.preventDefault();
      focusAt(0);
    } else if (e.key === "End") {
      e.preventDefault();
      focusAt(options.length - 1);
    }
  };

  return (
    <div
      className="decisionbar"
      role="toolbar"
      aria-label="Your decision"
      aria-orientation="horizontal"
      onKeyDown={onKeyDown}
    >
      {options.map((d, i) => (
        <button
          key={i}
          ref={(el) => {
            btnRefs.current[i] = el;
          }}
          type="button"
          className={"btn" + (d.primary ? " btn-primary" : "")}
          disabled={disabled}
          tabIndex={i === activeSafe ? 0 : -1}
          aria-label={`${d.label} (shortcut ${d.key})`}
          onFocus={() => setActiveIndex(i)}
          onClick={() => onDecide(d.action, d.size_bb)}
        >
          {d.label} <kbd aria-hidden="true">{d.key}</kbd>
        </button>
      ))}
    </div>
  );
}
