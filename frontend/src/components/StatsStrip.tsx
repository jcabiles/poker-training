import type { LeakStat, StatsSummary } from "../api/types";

export default function StatsStrip({
  summary,
  leaks,
}: {
  summary: StatsSummary | null;
  leaks: LeakStat[];
}) {
  if (!summary) return null;
  return (
    <div className="statstrip">
      <div className="stat">
        <b>{Math.round(summary.accuracy * 100)}%</b>
        <span>accuracy</span>
      </div>
      <div className="stat">
        <b>{summary.streak_days}</b>
        <span>day streak</span>
      </div>
      <div className="stat">
        <b>{summary.due_count}</b>
        <span>due</span>
      </div>
      <div className="stat">
        <b>{summary.total_attempts}</b>
        <span>hands</span>
      </div>
      <div className="leaks">
        <span className="lk-title">Top leaks</span>
        {leaks.length === 0 && <span className="lk muted">none yet</span>}
        {leaks.slice(0, 3).map((l) => (
          <span key={l.category} className="lk">
            {l.name} · {Math.round(l.accuracy * 100)}%
          </span>
        ))}
      </div>
    </div>
  );
}
