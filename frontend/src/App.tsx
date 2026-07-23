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
import HistoryView from "./components/HistoryView";
import Home from "./components/Home";
import ModeGroup from "./components/ModeGroup";
import PokerTable from "./components/PokerTable";
import QuizPanel from "./components/QuizPanel";
import RangeGrid from "./components/RangeGrid";
import SimulateView from "./components/SimulateView";
import SimDashboard from "./components/simulate/SimDashboard";
import StatsStrip from "./components/StatsStrip";
import StudyTestToggle, { type StudyTestMode } from "./components/StudyTestToggle";
import { legalDecisions } from "./lib/decisions";
import { formatHash, parseHash, type View } from "./lib/hashRoute";

// N7: Simulate is the app home (first + default view); the old curriculum hub
// stays reachable, relabeled "Learn". Nav order leads with the play surface,
// then the dashboard that measures it, then Practice + quizzes + Learn.
const VIEWS: { id: View; label: string }[] = [
  { id: "simulate", label: "Simulate" },
  { id: "history", label: "History" },
  { id: "dashboard", label: "Dashboard" },
  { id: "drill", label: "Practice" },
  { id: "texture", label: "Texture quiz" },
  { id: "equity", label: "Equity quiz" },
  { id: "home", label: "Learn" },
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

// T9 — the masthead EV ledger's "daily leak budget". A frontend constant for
// now (no solver-backed budget exists yet), so the bar + its label are marked
// approximate. The bar fills toward this ceiling and clamps at 100%.
const DAILY_LEAK_BUDGET_BB = 12;

// T2: Night|Day room. Default dark ("night"); the chosen theme persists so
// the room stays the way you left it across reloads.
const THEME_KEY = "theme";
type Theme = "dark" | "light";

function readTheme(): Theme {
  try {
    return window.localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

function writeTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(THEME_KEY, theme);
  } catch {
    /* localStorage unavailable — preference just won't persist */
  }
}

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

// T9 — the running EV tab at the club bar. `givenUpBb` is today's summed
// ev_loss_bb (approximate, 2dp); a value > 0 means EV was given up and reads in
// the loss tone. The meter fills toward DAILY_LEAK_BUDGET_BB and clamps at 100%
// (an over-budget day is still capped visually, but the mono figure tells the
// full story). The whole widget is decorative-of-a-stat; the figure + label
// carry the meaning for AT, so the bar itself is aria-hidden.
function EvLedger({ givenUpBb }: { givenUpBb: number }) {
  const lost = givenUpBb > 0;
  const pct = Math.min(100, Math.round((Math.max(0, givenUpBb) / DAILY_LEAK_BUDGET_BB) * 100));
  // Loss tone only when EV was actually given up; a clean day (0) stays neutral.
  const figure = lost ? `−${givenUpBb.toFixed(1)}` : givenUpBb.toFixed(1);
  return (
    <div className="ev-ledger-widget">
      <span className="new-tag" aria-hidden="true">
        New
      </span>
      <div className="elw-body">
        <span className="elw-eyebrow">EV Ledger · Today</span>
        <span className="elw-figures">
          <span className={"elw-figure" + (lost ? " loss" : "")}>{figure}</span>
          <span className="elw-unit">bb given up</span>
        </span>
      </div>
      <div className="elw-meter">
        <span className="elw-bar" aria-hidden="true">
          <span className={"elw-fill" + (lost ? " loss" : "")} style={{ width: `${pct}%` }} />
        </span>
        <span className="elw-budget">{pct}% of daily leak budget · approx.</span>
      </div>
    </div>
  );
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
  // The inline snippet in index.html sets data-theme before first paint; mirror
  // it into state so the Night|Day switch renders the correct side.
  const [theme, setTheme] = useState<Theme>(() => {
    const attr = document.documentElement.dataset.theme;
    return attr === "light" ? "light" : attr === "dark" ? "dark" : readTheme();
  });
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
    setTheme((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      writeTheme(next);
      return next;
    });
  };

  const hasGrid = Object.keys(grid).length > 0;
  // CW-6: Study shows the grid as soon as it exists (#6 behavior, unchanged);
  // Test withholds it until the spot is graded, then it reveals.
  const showGrid = hasGrid && (studyTestMode === "study" || !!result);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-crest" aria-hidden="true">
            <svg viewBox="0 0 46 46" fill="none">
              <rect x="1" y="1" width="44" height="44" rx="4" className="crest-frame" strokeWidth="1" />
              <rect x="5" y="5" width="36" height="36" rx="2" className="crest-inner" strokeWidth="0.6" />
              <path d="M23 12 L31 23 L23 34 L15 23 Z" className="crest-mark" />
              <path d="M23 17 L27.5 23 L23 29 L18.5 23 Z" className="crest-eye" />
            </svg>
          </span>
          <div className="brand-lockup">
            <h1 className="brand-name">
              Poker <span className="brand-amp">·</span> Trainer
            </h1>
            <span className="tag">preflop + flop · heuristic</span>
          </div>
        </div>
        <div className="masthead-right">
          <button
            type="button"
            className="theme-toggle"
            role="switch"
            aria-checked={theme === "light"}
            aria-label="Switch between Night and Day rooms"
            onClick={toggleTheme}
          >
            <span className="tt-track" aria-hidden="true">
              <span className="tt-opt tt-night">Night</span>
              <span className="tt-opt tt-day">Day</span>
              <span className="tt-knob" />
            </span>
          </button>

          {/* T9 — EV ledger widget: today's running bb given up + a daily
              leak-budget bar. Renders from the summary the app already fetches
              (best-effort — hidden until summary resolves). The budget is a FE
              constant; the figure and label are approximate. */}
          {summary && <EvLedger givenUpBb={summary.ev_given_up_today_bb} />}
        </div>
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

      {/* Practice-scoped strip (accuracy/streak/due/hands/leaks are all drill
          data). Hidden on the Simulate cluster (simulate/history/dashboard) so
          its "accuracy" never sits beside the differently-scoped "Your record"
          Good/Optimal rates and read as the same scale. */}
      {view !== "simulate" && view !== "history" && view !== "dashboard" && (
        <StatsStrip summary={summary} leaks={leaks} />
      )}

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
      ) : view === "simulate" ? (
        <SimulateView />
      ) : view === "history" ? (
        <HistoryView />
      ) : view === "dashboard" ? (
        <SimDashboard />
      ) : (
        <QuizPanel kind={view} />
      )}
    </div>
  );
}
