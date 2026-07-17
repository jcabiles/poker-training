import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";

import type { ActionType, LegalAction, Spot } from "../../api/types";
import { legalDecisions } from "../../lib/decisions";

// Simulate S9 hero action bar. Reuses Practice's predetermined-sizing pattern:
// `legalDecisions` resolves the engine's `legal_actions` into labelled,
// keyboard-mapped fold/check/call/bet/raise options at ENGINE-provided sizes —
// there is no free-form bet input (S9 invariant). It only reads
// `spot.legal_actions`, so we pass a minimal spot-shaped view of the hand's
// legal actions (the assertion is safe: no other Spot field is dereferenced).
// The roving-tabindex toolbar wiring mirrors DecisionBar so keyboard travel and
// focus states match the rest of the app.
export default function SimActionBar({
  legalActions,
  disabled,
  onDecide,
}: {
  legalActions: LegalAction[];
  disabled: boolean;
  onDecide: (action: ActionType, sizeBb?: number | null) => void;
}) {
  const options = legalDecisions({ legal_actions: legalActions } as Spot);
  const [activeIndex, setActiveIndex] = useState(0);
  const btnRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const activeSafe = Math.min(activeIndex, options.length - 1);

  // Global single-letter shortcuts (F/C/R/K/B/V/E — E = the bigger of two
  // preflop raise sizes, N3) — the same keyboard affordance
  // Practice powers from App.tsx (whose handler is gated to the drill view, so
  // it never fires on Simulate). Local here so the kbd hints on the buttons are
  // truthful. Ignore keys when a form control is focused (roving-tabindex
  // Enter/Space already activates a focused button) — mirrors App.tsx's guard.
  useEffect(() => {
    if (disabled) return;
    const handler = (e: globalThis.KeyboardEvent) => {
      const target = document.activeElement;
      const interactiveTags = ["BUTTON", "INPUT", "SELECT", "TEXTAREA"];
      if (
        target instanceof HTMLElement &&
        (interactiveTags.includes(target.tagName) || target.isContentEditable)
      ) {
        return;
      }
      const opt = options.find((d) => d.key === e.key.toUpperCase());
      if (opt) {
        e.preventDefault();
        onDecide(opt.action, opt.size_bb);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [options, disabled, onDecide]);

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
      className="decisionbar sim-actionbar"
      role="toolbar"
      aria-label="Your action"
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
          className={"btn decision-btn" + (d.primary ? " btn-primary" : "")}
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
