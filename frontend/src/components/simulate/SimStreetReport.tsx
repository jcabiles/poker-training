import { useEffect, useState } from "react";

import { getStreetReport } from "../../api/client";
import type { StreetReportView } from "../../api/types";
import { aggregateRates } from "./simGrade";

// Simulate S10 — the all-time report. A compact numbers-only panel in the side
// column, visible with OR without a live session (it's session-independent —
// an aggregate over every graded sim decision). Fetches on mount and refetches
// whenever a hand completes (parent bumps `refreshKey`).
//
// N1: the per-street table moved to the Dashboard. This panel now shows just
// two headline rates — Good decisions and Optimal — aggregated across all
// streets via `aggregateRates` (Wave-1, simGrade.ts). Rates EXCLUDE
// no-baseline rows (same aggregate rule as the recap) — they carry no
// correctness and would dilute the rate; surfacing the coverage count keeps
// sparse v1 grading honest rather than hidden.

export default function SimStreetReport({ refreshKey }: { refreshKey: number }) {
  const [report, setReport] = useState<StreetReportView | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getStreetReport()
      .then((r) => {
        if (!cancelled) {
          setReport(r);
          setFailed(false);
        }
      })
      .catch(() => {
        // Best-effort like the Practice stats panels: on failure the report
        // hides its own error rather than blocking the headline.
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (failed && !report) return null; // never block on a report miss

  return (
    <section className="sim-report" aria-label="All-time record">
      <h2 className="sim-report-title">Your record</h2>

      {report == null ? (
        // Skeleton matching the headline so nothing jumps on load.
        <div className="sim-report-skel" aria-hidden="true">
          <span className="sim-report-skel-row" />
          <span className="sim-report-skel-row" />
        </div>
      ) : report.total_decisions === 0 ? (
        <p className="sim-report-empty">
          No graded decisions yet. Play a mapped spot — a heads-up preflop or a
          flop c-bet — and your record fills in here.
        </p>
      ) : (
        (() => {
          const agg = aggregateRates(report.rows);
          return (
            <div className="sim-report-headline">
              <div className="sim-report-rate sim-report-rate-primary">
                <span className="sim-report-rate-value">
                  {agg.goodPct == null ? "—" : `${agg.goodPct}%`}
                </span>
                <span className="sim-report-rate-label">Good decisions</span>
              </div>
              <div className="sim-report-rate sim-report-rate-secondary">
                <span className="sim-report-rate-value">
                  {agg.optimalPct == null ? "—" : `${agg.optimalPct}%`}
                </span>
                <span className="sim-report-rate-label">Optimal</span>
              </div>
              <p className="sim-report-headline-count">
                {agg.graded} graded
                {agg.no_baseline > 0 ? ` · ${agg.no_baseline} no baseline` : ""}
              </p>
            </div>
          );
        })()
      )}
    </section>
  );
}
