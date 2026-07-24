// Simulate — "Reveal" debug toggle. A single pill (mirrors the Watch toggle)
// that governs whether the on-demand villain-card reveal buttons are offered on
// the hand-over panel. OFF (default) = normal play, villains stay face-down and
// the face-down range-reading drill is preserved. ON = the "Reveal all" /
// "Reveal last-in" buttons appear after EVERY hand so the hero can inspect what
// the bots were actually holding (range debugging). Client-only, localStorage.
//
// A real <button> with aria-pressed gives correct toggle semantics + keyboard
// for free. The gilt ON state mirrors a selected control and is redundant with
// aria-pressed (never colour alone). Own classes — shares NO markup with the
// Speed control.

export default function SimDebugToggle({
  debugReveal,
  onChange,
}: {
  debugReveal: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      className="sim-watch"
      aria-pressed={debugReveal}
      title="Debug: offer Reveal-all / Reveal-last-in buttons after every hand"
      onClick={() => onChange(!debugReveal)}
    >
      <span className="sim-watch-face">Reveal</span>
    </button>
  );
}
