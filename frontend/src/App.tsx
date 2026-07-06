import { useCallback, useEffect, useState } from "react";

import { getLeaks, getNext, getPlan, getSummary, grade } from "./api/client";
import type {
  ActionType,
  Decision,
  EvaluationResult,
  LeakStat,
  Mode,
  ReviewPlanResponse,
  Spot,
  StatsSummary,
} from "./api/types";
import DecisionBar from "./components/DecisionBar";
import FeedbackPanel from "./components/FeedbackPanel";
import Home from "./components/Home";
import ModeGroup from "./components/ModeGroup";
import PokerTable from "./components/PokerTable";
import QuizPanel from "./components/QuizPanel";
import RangeGrid from "./components/RangeGrid";
import StatsStrip from "./components/StatsStrip";
import StudyTestToggle, { type StudyTestMode } from "./components/StudyTestToggle";
import { legalDecisions } from "./lib/decisions";
import { formatHash, parseHash, type View } from "./lib/hashRoute";

const VIEWS: { id: View; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "drill", label: "Practice" },
  { id: "texture", label: "Texture quiz" },
  { id: "equity", label: "Equity quiz" },
];

// Spot-selection strategy: which spot to serve next, within the current mode.
const PREFLOP_MODES: { id: Mode; label: string }[] = [
  { id: "random", label: "Random" },
  { id: "review", label: "Review (due)" },
  { id: "leak_focus", label: "Leak focus" },
  { id: "exploit", label: "Exploit" },
  { id: "challenge", label: "Challenge" },
];

// Postflop situations: which street/action spot to drill.
const POSTFLOP_MODES: { id: Mode; label: string }[] = [
  { id: "postflop", label: "Postflop (c-bet)" },
  { id: "vs_cbet", label: "Facing c-bet" },
  { id: "vs_check_raise", label: "Facing check-raise" },
];

// CW-6: Study shows the answer grid while deciding (PR #6 behavior); Test
// hides it until the spot is graded, then reveals it.
const STUDY_TEST_KEY = "studyTestMode";

function readStudyTestMode(): StudyTestMode {
  try {
    return window.localStorage.getItem(STUDY_TEST_KEY) === "test" ? "test" : "study";
  } catch {
    return "study";
  }
}

function writeStudyTestMode(mode: StudyTestMode): void {
  try {
    window.localStorage.setItem(STUDY_TEST_KEY, mode);
  } catch {
    /* localStorage unavailable — preference just won't persist */
  }
}

export default function App() {
  // N6: view + drill mode live in the URL hash (deep-link/reload restore).
  const [route, setRoute] = useState(() => parseHash(window.location.hash));
  const { view, mode } = route;
  const [spot, setSpot] = useState<Spot | null>(null);
  const [grid, setGrid] = useState<Record<string, Record<string, number>>>({});
  const [result, setResult] = useState<EvaluationResult | null>(null);
  // The graded decision, kept alongside `result` so FeedbackPanel can name
  // the chosen action (EvaluationResult.chosen_eval carries only freq + EV).
  const [chosen, setChosen] = useState<Decision | null>(null);
  const [studyTestMode, setStudyTestMode] = useState<StudyTestMode>(() => readStudyTestMode());
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [leaks, setLeaks] = useState<LeakStat[]>([]);
  const [plan, setPlan] = useState<ReviewPlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshStats = useCallback(async () => {
    try {
      const [s, l] = await Promise.all([getSummary(), getLeaks()]);
      setSummary(s);
      setLeaks(l);
    } catch {
      /* stats are best-effort */
    }
  }, []);

  const loadNext = useCallback(async (m: Mode) => {
    setError(null);
    setResult(null);
    setChosen(null);
    try {
      const r = await getNext(m);
      setSpot(r.spot);
      setGrid(r.grid);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  // Hash is the source of truth: hashchange (tabs, mode buttons, back/forward,
  // manual edits) syncs state. Non-drill hashes carry no mode segment, so keep
  // the previous drill mode while on a quiz view.
  useEffect(() => {
    const onHashChange = () => {
      setRoute((prev) => {
        const next = parseHash(window.location.hash);
        return next.view === "drill" ? next : { view: next.view, mode: prev.mode };
      });
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // Fetches on mount with the deep-linked mode (single fetch, no random-then-
  // deep-linked race) and again whenever the mode changes via the hash.
  useEffect(() => {
    loadNext(mode);
  }, [mode, loadNext]);

  useEffect(() => {
    refreshStats();
  }, [refreshStats]);

  // N7 — today's plan is fetched only while home is active; fire-and-forget
  // (best-effort like stats) so home still renders with a graceful
  // placeholder (Home treats `plan === null` as an empty due queue) if this fails.
  useEffect(() => {
    if (view !== "home") return;
    let cancelled = false;
    getPlan()
      .then((p) => {
        if (!cancelled) setPlan(p);
      })
      .catch(() => {
        if (!cancelled) setPlan(null);
      });
    return () => {
      cancelled = true;
    };
  }, [view]);

  const selectMode = (m: Mode) => {
    if (m === mode) {
      loadNext(m); // re-clicking the active mode still deals a fresh spot
      return;
    }
    window.location.hash = formatHash("drill", m);
  };

  const selectStudyTestMode = (m: StudyTestMode) => {
    setStudyTestMode(m);
    writeStudyTestMode(m);
  };

  const decide = useCallback(
    async (action: ActionType, sizeBb?: number | null) => {
      if (!spot || result) return;
      try {
        const decision: Decision = { action, size_bb: sizeBb ?? undefined };
        const r = await grade(spot, decision);
        setResult(r);
        setChosen(decision);
        refreshStats();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    },
    [spot, result, refreshStats],
  );

  useEffect(() => {
    if (view !== "drill") return;
    const handler = (e: KeyboardEvent) => {
      const target = document.activeElement;
      const interactiveTags = ["BUTTON", "INPUT", "SELECT", "TEXTAREA"];
      if (
        target instanceof HTMLElement &&
        (interactiveTags.includes(target.tagName) || target.isContentEditable)
      ) {
        return;
      }
      if (result) {
        if (e.key === " " || e.key.toLowerCase() === "n") {
          e.preventDefault();
          loadNext(mode);
        }
        return;
      }
      if (!spot) return;
      const key = e.key.toUpperCase();
      const opt = legalDecisions(spot).find((d) => d.key === key);
      if (opt) decide(opt.action, opt.size_bb);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [view, spot, result, mode, decide, loadNext]);

  const toggleTheme = () => {
    const h = document.documentElement;
    h.dataset.theme = h.dataset.theme === "dark" ? "light" : "dark";
  };

  const hasGrid = Object.keys(grid).length > 0;
  // CW-6: Study shows the grid as soon as it exists (#6 behavior, unchanged);
  // Test withholds it until the spot is graded, then it reveals.
  const showGrid = hasGrid && (studyTestMode === "study" || !!result);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <h1>Poker Trainer</h1>
          <span className="tag">preflop + flop · heuristic</span>
        </div>
        <button className="btn" onClick={toggleTheme}>
          Theme
        </button>
      </header>

      <nav className="nav-tabs" aria-label="Sections">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            className={"nav-tab" + (v.id === view ? " active" : "")}
            aria-current={v.id === view ? "page" : undefined}
            onClick={() => {
              window.location.hash = formatHash(v.id, mode);
            }}
          >
            {v.label}
          </button>
        ))}
      </nav>

      <StatsStrip summary={summary} leaks={leaks} />

      {view === "home" ? (
        <Home plan={plan} leaks={leaks} />
      ) : view === "drill" ? (
        <>
          <div className="mode-groups">
            <ModeGroup
              label="Preflop practice"
              modes={PREFLOP_MODES}
              activeMode={mode}
              onSelect={selectMode}
            />
            <ModeGroup
              label="Postflop spots"
              modes={POSTFLOP_MODES}
              activeMode={mode}
              onSelect={selectMode}
            />
          </div>

          <StudyTestToggle mode={studyTestMode} onChange={selectStudyTestMode} />

          {error && (
            <div className="panel bad-bg">Error: {error}. Is the backend running on :8008?</div>
          )}

          {spot && (
            <main className={"layout" + (showGrid ? "" : " layout-single")}>
              <section>
                <PokerTable spot={spot} />
                <DecisionBar spot={spot} disabled={!!result} onDecide={decide} />
                {result && (
                  <FeedbackPanel result={result} chosen={chosen} onNext={() => loadNext(mode)} />
                )}
              </section>
              {showGrid && (
                <aside>
                  <RangeGrid spot={spot} grid={grid} revealed={studyTestMode === "test"} />
                </aside>
              )}
            </main>
          )}
        </>
      ) : (
        <QuizPanel kind={view} />
      )}
    </div>
  );
}
