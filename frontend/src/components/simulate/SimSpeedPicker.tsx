// Simulate S11 — table-speed control. A native radio group (normal / fast /
// instant) that sets how fast the client replays each bot-action batch. It is
// pure chrome inside the Simulate view (never the global App nav) and writes
// straight through to the caller, which persists the choice to localStorage.
//
// Real <input type="radio"> gives correct keyboard travel (arrows move + select
// within the group, one tab stop) and screen-reader semantics for free — the
// segmented look is CSS over a visually-hidden control. Under
// prefers-reduced-motion the pacing collapses to instant regardless of the
// selected value; the control still reflects the stored intent.

export type SimSpeed = "normal" | "fast" | "instant";

const OPTIONS: { value: SimSpeed; label: string; hint: string }[] = [
  { value: "normal", label: "Normal", hint: "lifelike bot timing" },
  { value: "fast", label: "Fast", hint: "quicker replay" },
  { value: "instant", label: "Instant", hint: "no animation" },
];

export default function SimSpeedPicker({
  speed,
  onChange,
}: {
  speed: SimSpeed;
  onChange: (next: SimSpeed) => void;
}) {
  return (
    <fieldset className="sim-speed">
      <legend className="sim-speed-label">Speed</legend>
      <div className="sim-speed-opts">
        {OPTIONS.map((o) => (
          <label key={o.value} className="sim-speed-opt" title={o.hint}>
            <input
              type="radio"
              name="sim-speed"
              className="sim-speed-input"
              value={o.value}
              checked={o.value === speed}
              onChange={() => onChange(o.value)}
            />
            <span className="sim-speed-face">{o.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
