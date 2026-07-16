import { useCallback, useEffect, useRef, useState } from "react";

import { getPostflopChart } from "../../api/client";
import type { PostflopChartView } from "../../api/types";

// Simulate postflop action-mix chart (R5) — SimRangeChart's panel chrome
// (collapse / localStorage / fetch-on-expand / stale-guard, verbatim idiom)
// with a NEW body: one bar per grader action (freq width + ≈EV), plus the
// hero's hand-category caption. It renders the grader's OWN per_action —
// chart==grader by construction; nothing is re-derived client-side.
//
// Point-of-need contract (mirrors SimRangeChart):
//  • Collapsed by DEFAULT, own localStorage key "simPostflopChart.collapsed".
//  • ZERO fetches while collapsed; fetch on first expand; while expanded,
//    REFETCH when a new hero postflop turn arrives (identityKey change —
//    session#hand#street#pot discriminates decision points within a hand).
//  • STALE-RESPONSE GUARD: responses stamped with a superseded identity are
//    discarded. Fire-and-forget — never blocks the action bar.

const COLLAPSED_KEY = "simPostflopChart.collapsed"; // R5-owned key
const TITLE_ID = "sim-pfchart-title";
const BODY_ID = "sim-pfchart-body";

// Grader verbs → the three action hues the room already speaks
// (RangeGrid/SimRangeChart tokens): aggression, continue, give-up.
const ACTION_HUE: Record<string, string> = {
  bet: "action-raise",
  raise: "action-raise",
  call: "action-call",
  check: "action-call",
  fold: "action-fold",
};

const CATEGORY_LABEL: Record<string, string> = {
  strong: "strong made hand",
  weak_made: "weak made hand",
  draw: "draw",
  air: "air (bluff candidate)",
};

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(COLLAPSED_KEY) !== "false";
  } catch {
    return true;
  }
}

function writeCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(COLLAPSED_KEY, collapsed ? "true" : "false");
  } catch {
    /* private-mode storage — collapse state just won't persist */
  }
}

function actionLabel(action: string, sizeBb: number | null): string {
  return sizeBb != null ? `${action} ${sizeBb}` : action;
}

function evLabel(ev: number): string {
  return `≈${ev >= 0 ? "+" : ""}${ev.toFixed(2)} bb`;
}

export default function SimPostflopChart({
  sessionId,
  identityKey,
}: {
  sessionId: string;
  /** ${session}#${hand}#${street}#${pot_bb} — changes per postflop decision
   * point (pot strictly grows between hero turns on a street; street advances
   * otherwise). Drives refetch-while-expanded + the stale-response guard. */
  identityKey: string;
}) {
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [chart, setChart] = useState<PostflopChartView | null>(null);
  const [loading, setLoading] = useState(false);
  const [errored, setErrored] = useState(false);

  const liveIdentity = useRef(identityKey);
  liveIdentity.current = identityKey;

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      writeCollapsed(next);
      return next;
    });
  }, []);

  useEffect(() => {
    if (collapsed) return;

    const stamp = identityKey;
    let cancelled = false;
    setLoading(true);
    setErrored(false);

    getPostflopChart(sessionId)
      .then((res) => {
        if (cancelled || stamp !== liveIdentity.current) return;
        setChart(res);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled || stamp !== liveIdentity.current) return;
        setChart(null);
        setErrored(true);
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [collapsed, identityKey, sessionId]);

  const available = chart?.available === true && chart.actions.length > 0;
  const category = chart?.hand_category ? (CATEGORY_LABEL[chart.hand_category] ?? chart.hand_category) : null;

  return (
    <div className="gridwrap sim-chart sim-pfchart">
      <button
        type="button"
        className="gridtoggle"
        aria-expanded={!collapsed}
        aria-controls={BODY_ID}
        onClick={toggleCollapsed}
      >
        <span className="gridhead">
          <span className="gridhead-eyebrow">Baseline Play</span>
          <span className="gridhead-label" id={TITLE_ID}>
            {available && chart?.node_label ? chart.node_label : "This spot"}
          </span>
        </span>
        <span className="gridtoggle-aside">
          <span className="gridhead-approx" aria-hidden="true">
            approx.
          </span>
          <span className="gridchevron" aria-hidden="true">
            {collapsed ? "▸" : "▾"}
          </span>
        </span>
      </button>

      <div id={BODY_ID} hidden={collapsed}>
        {loading && !chart ? (
          <p className="sim-chart-status" role="status">
            Reading the line…
          </p>
        ) : errored ? (
          <p className="sim-chart-status sim-chart-status-quiet" role="status">
            Chart unavailable right now.
          </p>
        ) : available && chart ? (
          <>
            <ul className="sim-pfchart-list" aria-labelledby={TITLE_ID}>
              {chart.actions.map((a) => {
                const label = actionLabel(a.action, a.size_bb);
                const pct = Math.round(a.frequency * 100);
                return (
                  <li
                    key={label}
                    className="sim-pfchart-row"
                    aria-label={`${label}: ${pct}%, ${evLabel(a.ev_bb)}`}
                  >
                    <span className="sim-pfchart-action">{label}</span>
                    <span className="sim-pfchart-bar" aria-hidden="true">
                      <span
                        className={`sim-pfchart-fill ${ACTION_HUE[a.action] ?? "action-call"}`}
                        style={{ width: `${pct}%` }}
                      />
                    </span>
                    <span className="sim-pfchart-nums">
                      <span className="num">{pct}%</span>
                      <span className="sim-pfchart-ev num">{evLabel(a.ev_bb)}</span>
                    </span>
                  </li>
                );
              })}
            </ul>
            {category && (
              <p className="sim-pfchart-cat">
                Your hand here: <strong>{category}</strong> · EVs approximate
              </p>
            )}
          </>
        ) : (
          <p className="sim-chart-status sim-chart-status-quiet" role="status">
            No baseline yet for this spot.
          </p>
        )}
      </div>
    </div>
  );
}
