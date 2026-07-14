import { useEffect, useState } from "react";

import { getStreetReport } from "../../api/client";
import type { StreetReportRow, StreetReportView } from "../../api/types";
import { fmtEvLoss, streetLabel } from "./simGrade";

// Simulate S10 — the all-time per-street report. A compact numbers-only panel in
// the side column, visible with OR without a live session (it's session
// -independent — an aggregate over every graded sim decision). Fetches on mount
// and refetches whenever a hand completes (parent bumps `refreshKey`).
//
// Per street: graded count, tier mix (best / ok / mistake / blunder), ≈EV-loss
// sum, and the no-baseline count as its OWN figure. ACCURACY EXCLUDES
// no-baseline rows (same aggregate rule as the recap) — they carry no
// correctness and would dilute the rate; surfacing the coverage count keeps
// sparse v1 grading honest rather than hidden.

function accuracyPct(row: StreetReportRow): number | null {
  if (row.graded === 0) return null;
  return Math.round(((row.optimal + row.acceptable) / row.graded) * 100);
}

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
        // hides its own error rather than blocking the table.
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (failed && !report) return null; // never block the table on a report miss

  return (
    <section className="sim-report" aria-label="All-time per-street report">
      <h2 className="sim-report-title">Per-street record</h2>

      {report == null ? (
        // Skeleton matching the four-row table so nothing jumps on load.
        <div className="sim-report-skel" aria-hidden="true">
          {[0, 1, 2, 3].map((i) => (
            <span key={i} className="sim-report-skel-row" />
          ))}
        </div>
      ) : report.total_decisions === 0 ? (
        <p className="sim-report-empty">
          No graded decisions yet. Play a mapped spot — a heads-up preflop or a
          flop c-bet — and your record fills in here.
        </p>
      ) : (
        <table className="sim-report-table">
          <thead>
            <tr>
              <th scope="col" className="sim-report-street">
                Street
              </th>
              <th scope="col" className="sim-report-acc">
                Acc
              </th>
              <th scope="col" className="sim-report-mix">
                Mix
              </th>
              <th scope="col" className="sim-report-ev">
                ≈EV
              </th>
            </tr>
          </thead>
          <tbody>
            {report.rows.map((row) => {
              const acc = accuracyPct(row);
              return (
                <tr key={row.street} className="sim-report-row">
                  <td className="sim-report-street">
                    <span className="sim-report-street-name">
                      {streetLabel(row.street)}
                    </span>
                    <span className="sim-report-count">
                      {row.graded} graded
                      {row.no_baseline > 0 && (
                        <span className="sim-report-nb">
                          {" · "}
                          {row.no_baseline} no baseline
                        </span>
                      )}
                    </span>
                  </td>
                  <td className="sim-report-acc num">
                    {acc == null ? <span className="sim-report-dash">—</span> : `${acc}%`}
                  </td>
                  <td className="sim-report-mix">
                    {row.graded === 0 ? (
                      <span className="sim-report-dash">—</span>
                    ) : (
                      <span className="sim-report-tally" aria-hidden="true">
                        <span className="sim-tally sim-tier-good" title="best">
                          {row.optimal}
                        </span>
                        <span className="sim-tally sim-tier-neutral" title="ok">
                          {row.acceptable}
                        </span>
                        <span className="sim-tally sim-tier-warn" title="mistake">
                          {row.mistake}
                        </span>
                        <span className="sim-tally sim-tier-bad" title="blunder">
                          {row.blunder}
                        </span>
                      </span>
                    )}
                    {row.graded > 0 && (
                      <span className="sim-sr-only">
                        {row.optimal} best, {row.acceptable} ok, {row.mistake} mistake,{" "}
                        {row.blunder} blunder
                      </span>
                    )}
                  </td>
                  <td className="sim-report-ev num">
                    {row.graded === 0 ? (
                      <span className="sim-report-dash">—</span>
                    ) : (
                      fmtEvLoss(row.ev_loss_bb)
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}
