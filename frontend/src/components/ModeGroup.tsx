import type { Mode } from "../api/types";

/**
 * A labeled group of mode-selection buttons (e.g. "Preflop practice",
 * "Postflop spots"). Purely presentational — selection logic and the
 * `Mode` values themselves live in the caller.
 */
export default function ModeGroup({
  label,
  modes,
  activeMode,
  onSelect,
}: {
  label: string;
  modes: { id: Mode; label: string }[];
  activeMode: Mode;
  onSelect: (mode: Mode) => void;
}) {
  const headingId = `mode-group-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return (
    <div className="mode-group" role="group" aria-labelledby={headingId}>
      <h2 className="mode-group-label" id={headingId}>
        {label}
      </h2>
      <div className="modes">
        {modes.map((m) => (
          <button
            key={m.id}
            className={"btn mode-chip" + (m.id === activeMode ? " btn-primary" : "")}
            onClick={() => onSelect(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>
    </div>
  );
}
