// Simulate — "Grading" toggle. A single pill (styled to match the Watch
// toggle) that governs whether in-hand grading renders: Coach (pressed) shows
// the live hero verdict badge + the end-of-hand recap; Real play (unpressed,
// default) withholds both so the table can be rehearsed "for real." Grading
// is still computed + recorded in both modes — this toggle only gates what
// renders (see SimulateView's two gate sites). Sits in the topbar controls
// alongside SimWatchToggle/SimSpeedPicker.
//
// A real <button> with aria-pressed gives correct toggle semantics + keyboard
// for free. The gilt "on" state mirrors a selected Speed chip / pressed Watch
// toggle and is redundant with aria-pressed (never colour alone). Reuses the
// existing .sim-watch classes — this control is shaped identically (pill,
// same face/pressed/focus treatment), just a different setting.

export default function SimGradingToggle({
  coachMode,
  onChange,
}: {
  coachMode: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      className="sim-watch"
      aria-pressed={coachMode}
      aria-label={
        coachMode ? "Grading feedback: coach mode" : "Grading feedback: real-play mode"
      }
      title="Coach mode shows live grading; Real play hides it (grading is still recorded)"
      onClick={() => onChange(!coachMode)}
    >
      <span className="sim-watch-face">Grading: {coachMode ? "Coach" : "Real play"}</span>
    </button>
  );
}
