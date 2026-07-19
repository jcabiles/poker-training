import { useEffect, useState } from "react";

import { getLeakReport, getStreetReport } from "../../api/client";
import type { LeakReportView, StreetReportView } from "../../api/types";
import { aggregateRates, fmtEvLoss, goodPct, optimalPct, streetLabel } from "./simGrade";

// N1 — the north-star Dashboard. A standalone view (no session, no props) that
// answers "how good are my decisions, and where do I leak?" from the same
// all-time getStreetReport() rows the side panel reads. Two KPI cards on top —
// Good Decision Rate (primary hero) + Optimal Play Rate (secondary) — then a
// by-street ledger below. Rates are EXACT verdict ratios (no ≈); only the
// optional per-street EV-loss carries the ≈ treatment. graded===0 renders "—",
// never 0%/NaN — sparse coverage reads honestly. Mount-fetch lifecycle mirrors
// SimStreetReport: skeleton while null, best-effort note on failure.

// A rate is either an integer % or null (nothing graded). One formatter so every
// value path renders "NN%" or an em dash — never "0%"/"NaN" for a no-data cell.
function fmtRate(pct: number | null): string {
  return pct == null ? "—" : `${pct}%`;
}

export default function SimDashboard() {
  const [report, setReport] = useState<StreetReportView | null>(null);
  const [failed, setFailed] = useState(false);
  // N7 — worst-spot leaks. Fetched independently (best-effort); a failure just
  // hides the panel rather than blocking the KPI cards.
  const [leaks, setLeaks] = useState<LeakReportView | null>(null);

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
        // Best-effort like the side panel: surface a muted note rather than a
        // blank page or a thrown error.
        if (!cancelled) setFailed(true);
      });
    getLeakReport()
      .then((r) => {
        if (!cancelled) setLeaks(r);
      })
      .catch(() => {
        if (!cancelled) setLeaks(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const agg = report ? aggregateRates(report.rows) : null;
  const hasData = report != null && report.total_decisions > 0 && agg != null && agg.graded > 0;

  return (
    <main className="dash" aria-labelledby="dash-title">
      <header className="dash-head">
        <h1 id="dash-title" className="dash-title">
          Dashboard
        </h1>
        <p className="dash-sub">
          Your all-time record across every graded Simulate decision — how often
          you make a good call, and where the leaks are.
        </p>
      </header>

      {report == null ? (
        failed ? (
          <p className="dash-note" role="status">
            Couldn&rsquo;t load your record just now. It&rsquo;ll reappear once the
            connection recovers.
          </p>
        ) : (
          // Skeleton shaped to the real layout (two KPI cards, four ledger rows)
          // so nothing jumps when the record resolves.
          <div className="dash-skel" aria-hidden="true">
            <div className="dash-skel-kpis">
              <span className="dash-skel-block dash-skel-primary" />
              <span className="dash-skel-block dash-skel-secondary" />
            </div>
            <div className="dash-skel-rows">
              {[0, 1, 2, 3].map((i) => (
                <span key={i} className="dash-skel-block dash-skel-row" />
              ))}
            </div>
          </div>
        )
      ) : !hasData ? (
        <div className="dash-empty">
          <p className="dash-empty-lead">No graded decisions yet.</p>
          <p className="dash-empty-body">
            Play some mapped spots — a heads-up preflop or a flop c-bet — and your
            record fills in here.
          </p>
          {agg != null && agg.no_baseline > 0 && (
            <p className="dash-empty-nb">
              {agg.no_baseline} decision{agg.no_baseline === 1 ? "" : "s"} seen so
              far had no baseline to grade against.
            </p>
          )}
        </div>
      ) : (
        <>
          {/* ── Top: two KPI cards ─────────────────────────────────────────── */}
          <section className="dash-kpis" aria-label="Overall decision rates">
            <article className="dash-kpi dash-kpi-primary">
              <p className="dash-kpi-label">Good Decision Rate</p>
              <p className="dash-kpi-value">
                <span className="dash-kpi-num">{fmtRate(agg.goodPct)}</span>
              </p>
              <p className="dash-kpi-meta">
                optimal + acceptable, over {agg.graded} graded decision
                {agg.graded === 1 ? "" : "s"}
              </p>
              {agg.no_baseline > 0 && (
                <p className="dash-kpi-nb">
                  +{agg.no_baseline} with no baseline — not counted
                </p>
              )}
            </article>

            <article className="dash-kpi dash-kpi-secondary">
              <p className="dash-kpi-label">Optimal Play Rate</p>
              <p className="dash-kpi-value">
                <span className="dash-kpi-num">{fmtRate(agg.optimalPct)}</span>
              </p>
              <p className="dash-kpi-meta">
                the best line, over {agg.graded} graded
              </p>
            </article>
          </section>

          {/* ── Below: by-street breakdown ─────────────────────────────────── */}
          <section className="dash-streets" aria-label="Breakdown by street">
            <h2 className="dash-streets-title">By street</h2>
            <ul className="dash-street-list">
              {report.rows.map((row) => {
                const good = goodPct(row);
                const optimal = optimalPct(row);
                const graded = row.graded > 0;
                return (
                  <li key={row.street} className="dash-street">
                    <div className="dash-street-head">
                      <span className="dash-street-name">
                        {streetLabel(row.street)}
                      </span>
                      <span className="dash-street-count">
                        {row.graded} graded
                        {row.no_baseline > 0 && (
                          <span className="dash-street-nb">
                            {" · "}
                            {row.no_baseline} no baseline
                          </span>
                        )}
                      </span>
                    </div>

                    {/* Proportional bar — fill width tracks the primary (Good)
                        rate. Empty track when nothing is graded. */}
                    <div
                      className="dash-bar"
                      role="img"
                      aria-label={
                        good == null
                          ? `${streetLabel(row.street)}: no graded decisions yet`
                          : `${streetLabel(row.street)}: ${good}% good decisions`
                      }
                    >
                      {good != null && (
                        <span
                          className="dash-bar-fill"
                          style={{ width: `${good}%` }}
                        />
                      )}
                    </div>

                    <div className="dash-street-rates" aria-hidden="true">
                      <span className="dash-rate dash-rate-good">
                        <span className="dash-rate-k">Good</span>
                        <span className={good == null ? "dash-rate-v dash-rate-v--empty" : "dash-rate-v"}>
                          {fmtRate(good)}
                        </span>
                      </span>
                      <span className="dash-rate dash-rate-optimal">
                        <span className="dash-rate-k">Optimal</span>
                        <span className="dash-rate-v">{fmtRate(optimal)}</span>
                      </span>
                      {graded && (
                        <span className="dash-rate dash-rate-ev">
                          <span className="dash-rate-k">EV lost</span>
                          <span className="dash-rate-v">
                            {fmtEvLoss(row.ev_loss_bb)}
                          </span>
                        </span>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
            <p className="dash-foot">
              Rates are exact verdict ratios. EV-loss figures are ≈ approximate
              (heuristic baseline).
            </p>
          </section>

          {/* ── Your leaks: worst spot families → drill them in Practice ────── */}
          <section className="dash-leaks" aria-label="Your worst spots">
            <h2 className="dash-streets-title">Your leaks</h2>
            {leaks == null || leaks.rows.length === 0 ? (
              <p className="dash-note">
                Not enough graded decisions in any single spot yet — keep playing
                and your weakest spots surface here to drill.
              </p>
            ) : (
              <ul className="dash-leak-list">
                {leaks.rows.map((row) => (
                  <li key={`${row.node_context}:${row.position}`} className="dash-leak">
                    <div className="dash-leak-main">
                      <span className="dash-leak-label">{row.node_label}</span>
                      <span className="dash-leak-street">{streetLabel(row.street)}</span>
                    </div>
                    {/* Screen readers get the full severity sentence; the
                        numerals below are visual-only (aria-hidden) so AT hears
                        it once, cleanly (design-review high — 1.3.1/1.1.1). */}
                    <span className="sim-sr-only">
                      {row.node_label} on the {streetLabel(row.street).toLowerCase()}:{" "}
                      {Math.round(row.good_rate * 100)}% good over {row.graded} graded
                      decision{row.graded === 1 ? "" : "s"}, {fmtEvLoss(row.ev_loss_bb)} lost.
                    </span>
                    <div className="dash-leak-stats" aria-hidden="true">
                      <span className="dash-leak-rate">
                        {Math.round(row.good_rate * 100)}% good
                      </span>
                      <span className="dash-leak-count">
                        {row.graded} graded · {fmtEvLoss(row.ev_loss_bb)} lost
                      </span>
                    </div>
                    {row.drill_mode ? (
                      <a
                        className="dash-leak-drill"
                        href={`#/drill/${row.drill_mode}`}
                        aria-label={`Drill ${row.node_label}`}
                      >
                        Drill this
                      </a>
                    ) : (
                      <span className="dash-leak-only">Simulate only</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </main>
  );
}
