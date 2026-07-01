import { useCallback, useEffect, useState } from "react";

import { getLeaks, getNext, getSummary, grade } from "./api/client";
import type {
  ActionType,
  EvaluationResult,
  LeakStat,
  Mode,
  Spot,
  StatsSummary,
} from "./api/types";
import DecisionBar from "./components/DecisionBar";
import FeedbackPanel from "./components/FeedbackPanel";
import PokerTable from "./components/PokerTable";
import QuizPanel from "./components/QuizPanel";
import RangeGrid from "./components/RangeGrid";
import StatsStrip from "./components/StatsStrip";
import { legalDecisions } from "./lib/decisions";

type View = "drill" | "texture" | "equity";

const VIEWS: { id: View; label: string }[] = [
  { id: "drill", label: "Practice" },
  { id: "texture", label: "Texture quiz" },
  { id: "equity", label: "Equity quiz" },
];

const MODES: { id: Mode; label: string }[] = [
  { id: "random", label: "Random" },
  { id: "review", label: "Review (due)" },
  { id: "leak_focus", label: "Leak focus" },
  { id: "exploit", label: "Exploit" },
  { id: "challenge", label: "Challenge" },
  { id: "postflop", label: "Postflop (c-bet)" },
  { id: "vs_cbet", label: "Facing c-bet" },
  { id: "vs_check_raise", label: "Facing check-raise" },
];

export default function App() {
  const [view, setView] = useState<View>("drill");
  const [spot, setSpot] = useState<Spot | null>(null);
  const [grid, setGrid] = useState<Record<string, string>>({});
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [mode, setMode] = useState<Mode>("random");
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [leaks, setLeaks] = useState<LeakStat[]>([]);
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
    try {
      const r = await getNext(m);
      setSpot(r.spot);
      setGrid(r.grid);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    loadNext("random");
    refreshStats();
  }, [loadNext, refreshStats]);

  const selectMode = (m: Mode) => {
    setMode(m);
    loadNext(m);
  };

  const decide = useCallback(
    async (action: ActionType, sizeBb?: number | null) => {
      if (!spot || result) return;
      try {
        const r = await grade(spot, { action, size_bb: sizeBb ?? undefined });
        setResult(r);
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

  const showGrid = Object.keys(grid).length > 0;

  return (
    <div className="app">
      <header className="topbar">
        <h1>
          Poker Training <span className="tag">preflop + flop · heuristic</span>
        </h1>
        <button className="btn" onClick={toggleTheme}>
          Theme
        </button>
      </header>

      <StatsStrip summary={summary} leaks={leaks} />

      <div className="modes">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            className={"btn" + (v.id === view ? " btn-primary" : "")}
            onClick={() => setView(v.id)}
          >
            {v.label}
          </button>
        ))}
      </div>

      {view === "drill" ? (
        <>
          <div className="modes">
            {MODES.map((m) => (
              <button
                key={m.id}
                className={"btn" + (m.id === mode ? " btn-primary" : "")}
                onClick={() => selectMode(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>

          {error && (
            <div className="panel bad-bg">Error: {error}. Is the backend running on :8008?</div>
          )}

          {spot && (
            <main className={"layout" + (showGrid ? "" : " layout-single")}>
              <section>
                <PokerTable spot={spot} />
                <DecisionBar spot={spot} disabled={!!result} onDecide={decide} />
                {result && <FeedbackPanel result={result} onNext={() => loadNext(mode)} />}
              </section>
              {showGrid && (
                <aside>
                  <RangeGrid spot={spot} grid={grid} />
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
