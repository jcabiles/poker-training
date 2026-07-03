import type { LeakStat, Mode, ReviewPlanResponse } from "../api/types";
import { formatHash } from "../lib/hashRoute";

// N7 — mastery thresholds. Named constants (not silent magic numbers) and
// surfaced verbatim in the "Learning path" key below.
export const MASTERY_ACCURACY_THRESHOLD = 0.8; // "solid" needs >= this accuracy...
export const MASTERY_ATTEMPTS_THRESHOLD = 20; // ...and >= this many attempts.

type Mastery = "new" | "learning" | "solid";

interface PathNode {
  title: string;
  mode: Mode;
  leakCategories: number[]; // app/domain/leaks.py LeakCategory ints this node exercises
}

// N7 — single ordered learning path (no branching skill tree; see roadmap
// §N7 no-gos). Several preflop nodes share the "random" drill mode because
// `/drill/next` has no per-node-context filter for preflop families — that's
// a backend-filtering change out of scope here (this slice is read-only path
// surfacing over the existing 8 drill modes).
const LEARNING_PATH: PathNode[] = [
  { title: "RFI", mode: "random", leakCategories: [100, 101, 102, 103, 104] },
  { title: "vs RFI", mode: "random", leakCategories: [112] },
  { title: "Blind defense", mode: "random", leakCategories: [110] },
  { title: "vs Limpers", mode: "random", leakCategories: [150] },
  { title: "vs 3-bet", mode: "random", leakCategories: [120, 121] },
  { title: "C-bet", mode: "postflop", leakCategories: [200] },
  { title: "Facing c-bet", mode: "vs_cbet", leakCategories: [201] },
  { title: "Facing check-raise", mode: "vs_check_raise", leakCategories: [202] },
  { title: "Exploits", mode: "exploit", leakCategories: [300, 301, 302, 303] },
];

// Mastery is computed from the EXISTING /stats/leaks response (attempts +
// accuracy per leak_category bucket) — no new stats surface.
function masteryFor(leakCategories: number[], leaks: LeakStat[]): Mastery {
  const matching = leaks.filter((l) => leakCategories.includes(l.category));
  const attempts = matching.reduce((sum, l) => sum + l.attempts, 0);
  if (attempts === 0) return "new";
  const accuracy = matching.reduce((sum, l) => sum + l.attempts * l.accuracy, 0) / attempts;
  return accuracy >= MASTERY_ACCURACY_THRESHOLD && attempts >= MASTERY_ATTEMPTS_THRESHOLD
    ? "solid"
    : "learning";
}

const MASTERY_TONE: Record<Mastery, string> = {
  new: "neutral",
  learning: "warn",
  solid: "good",
};

function goTo(hash: string) {
  window.location.hash = hash;
}

// N7 — home/curriculum hub: "today's plan" (the due SM-2 queue) + a single
// ordered learning path. `plan` is null when the fetch hasn't resolved or
// failed (fire-and-forget, tolerated the same way stats already are) — the
// due section then falls back to the same empty-state copy as a genuinely
// empty queue, so the view never blocks on it.
export default function Home({
  plan,
  leaks,
}: {
  plan: ReviewPlanResponse | null;
  leaks: LeakStat[];
}) {
  const dueItems = plan?.items ?? [];
  const dueCount = plan?.due_count ?? 0;

  return (
    <div className="home">
      <section className="panel home-section">
        <h2 className="home-section-title">Today&apos;s plan</h2>
        {dueCount > 0 ? (
          <>
            <p className="home-due-count">
              <b>{dueCount}</b> due for review
            </p>
            <ul className="mix home-due-list">
              {dueItems.map((item) => (
                <li key={item.signature}>
                  {item.label} <span className="studytest-hint">due {item.due_date}</span>
                </li>
              ))}
            </ul>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => goTo(formatHash("drill", "review"))}
            >
              Start reviews
            </button>
          </>
        ) : (
          <p>
            Nothing due —{" "}
            <button
              type="button"
              className="btn"
              onClick={() => goTo(formatHash("drill", "random"))}
            >
              drill something new
            </button>
          </p>
        )}
      </section>

      <section className="panel home-section">
        <h2 className="home-section-title">Learning path</h2>
        <p className="studytest-hint">
          solid ≥{Math.round(MASTERY_ACCURACY_THRESHOLD * 100)}% · {MASTERY_ATTEMPTS_THRESHOLD}+
          reps
        </p>
        <ol className="home-path">
          {LEARNING_PATH.map((node) => {
            const mastery = masteryFor(node.leakCategories, leaks);
            return (
              <li key={node.title}>
                <button
                  type="button"
                  className="btn home-path-node"
                  onClick={() => goTo(formatHash("drill", node.mode))}
                >
                  <span>{node.title}</span>
                  <span className={`badge ${MASTERY_TONE[mastery]}`}>{mastery}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}
