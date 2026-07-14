// Simulate — "Watch" toggle. A single pill (styled to match one Speed chip)
// that governs what happens when the hero folds: ON (default) plays the
// remaining villains out to showdown at the current Speed so the user can watch
// them play amongst themselves; OFF restores the instant skip straight to the
// next hand. Sits immediately left of the Speed picker.
//
// A real <button> with aria-pressed gives correct toggle semantics + keyboard
// for free. The gilt ON state mirrors a selected Speed chip and is redundant
// with aria-pressed (never colour alone). Own classes — it shares NO markup
// with SimSpeedPicker, so the segmented Speed control stays untouched.

export default function SimWatchToggle({
  watch,
  onChange,
}: {
  watch: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      className="sim-watch"
      aria-pressed={watch}
      title="Play out folded hands to showdown (off = skip to next hand)"
      onClick={() => onChange(!watch)}
    >
      <span className="sim-watch-face">Watch</span>
    </button>
  );
}
