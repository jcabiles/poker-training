/**
 * Study / Test toggle (CW-6). Purely controlled + presentational — the mode
 * value and its localStorage persistence live in App.tsx, the same way the
 * drill `Mode` is owned by App and handed down to ModeGroup.
 */
export type StudyTestMode = "study" | "test";

export default function StudyTestToggle({
  mode,
  onChange,
}: {
  mode: StudyTestMode;
  onChange: (mode: StudyTestMode) => void;
}) {
  return (
    <div className="studytest">
      <div className="studytest-toggle" role="group" aria-label="Study or test mode">
        <button
          type="button"
          className={"btn" + (mode === "study" ? " btn-primary" : "")}
          aria-pressed={mode === "study"}
          onClick={() => onChange("study")}
        >
          Study
        </button>
        <button
          type="button"
          className={"btn" + (mode === "test" ? " btn-primary" : "")}
          aria-pressed={mode === "test"}
          onClick={() => onChange("test")}
        >
          Test
        </button>
      </div>
      <span className="studytest-hint">
        {mode === "test"
          ? "Test: the range chart is hidden until you're graded."
          : "Study: the range chart is visible while you decide."}
      </span>
    </div>
  );
}
