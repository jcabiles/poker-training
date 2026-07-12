import { useCallback, useEffect, useRef, useState } from "react";

import { getPreflopChart } from "../../api/client";
import type { PreflopChartView } from "../../api/types";
import { RANK_ORDER, handClass } from "../../lib/poker";

// Simulate preflop range chart (C2) — a sim-owned COPY of Practice's
// RangeGrid collapsible-plate idiom (SimTable↔PokerTable precedent). It renders
// the same `.gridwrap/.gridtoggle/.grid/.cell/.gridlegend` markup + classes
// READ-ONLY (never edits RangeGrid.tsx), plus a `.sim-chart-*` shell of its own.
//
// Point-of-need contract:
//  • Collapsed by DEFAULT, own localStorage key "simChart.collapsed" (spec
//    low-1 — never reuse Practice's "rangeGrid.collapsed").
//  • ZERO fetches while collapsed, across ALL turns (spec med-2). The fetch
//    effect early-returns when collapsed; it only reaches the network once the
//    panel is expanded.
//  • Fetch on first expand; while expanded, REFETCH when a new hero preflop
//    turn arrives (identityKey change).
//  • STALE-RESPONSE GUARD (spec high-1): each request is stamped with the
//    identityKey live at fire time; a response whose stamp != the current
//    identity is DISCARDED (hero already acted / hand advanced). The fetch is
//    fire-and-forget — it never blocks the action bar.

const COLLAPSED_KEY = "simChart.collapsed"; // sim-owned; NOT Practice's key
const TITLE_ID = "sim-chart-title";
const BODY_ID = "sim-chart-body";

const LEGEND: [string, string][] = [
  ["action-raise", "raise"],
  ["action-call", "call"],
  ["action-fold", "fold"],
];

// Fixed stacking order so a mixed-frequency hand's segments render consistently
// (mirrors RangeGrid / grading.py:range_grid).
const ACTION_ORDER = ["raise", "call", "fold"];

function readCollapsed(): boolean {
  try {
    // Default collapsed: anything but an explicit "false" keeps it closed.
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

export default function SimRangeChart({
  sessionId,
  identityKey,
  heroCards,
}: {
  sessionId: string;
  /** (session_id, hand_no, is_hero_turn) snapshot — changes when the hero acts
   * or the hand advances. Drives the refetch (while expanded) and the
   * stale-response guard. */
  identityKey: string;
  /** live hero hole cards — the highlighted "your hand" cell in the grid. */
  heroCards: [string, string];
}) {
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [chart, setChart] = useState<PreflopChartView | null>(null);
  const [loading, setLoading] = useState(false);
  const [errored, setErrored] = useState(false);

  // The identity a rendered chart belongs to. A response is only adopted when
  // its stamp still equals the LIVE identity (guarded below); this ref lets the
  // async resolver read that live value without re-subscribing.
  const liveIdentity = useRef(identityKey);
  liveIdentity.current = identityKey;

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      writeCollapsed(next);
      return next;
    });
  }, []);

  // Fetch-on-expand + refetch-per-identity. While collapsed this effect fires
  // but early-returns before any network call, so a collapsed panel costs zero
  // fetches no matter how many turns pass. On expand (or a new hero turn while
  // expanded) it fires the request, stamped with the identity live at fire
  // time; the resolver discards its result if the identity has since changed.
  useEffect(() => {
    if (collapsed) return;

    const stamp = identityKey;
    let cancelled = false; // unmount / effect-cleanup guard
    setLoading(true);
    setErrored(false);

    getPreflopChart(sessionId)
      .then((res) => {
        // Stale-response guard: drop late responses for a resolved decision.
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
    // identityKey is the refetch trigger (new hero preflop turn). sessionId is
    // stable within a session but included for correctness across a 404-recovery
    // into a fresh session.
  }, [collapsed, identityKey, sessionId]);

  const hero = handClass(heroCards[0], heroCards[1]);
  const available = chart?.available === true && chart.grid != null;
  const grid = chart?.grid ?? null;
  const note = chart?.exploit_note ?? null;

  return (
    <div className="gridwrap sim-chart">
      <button
        type="button"
        className="gridtoggle"
        aria-expanded={!collapsed}
        aria-controls={BODY_ID}
        onClick={toggleCollapsed}
      >
        <span className="gridhead">
          <span className="gridhead-eyebrow">Baseline Range</span>
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
            Reading the range…
          </p>
        ) : errored ? (
          <p className="sim-chart-status sim-chart-status-quiet" role="status">
            Chart unavailable right now.
          </p>
        ) : available && grid ? (
          <>
            {/* APG "table" semantics (RangeGrid precedent): static read-only
                lookups, so no interactive grid pattern. Rows are role="row"
                kept out of the box tree via `.gridrow { display: contents }`. */}
            <div className="grid" role="table" aria-labelledby={TITLE_ID}>
              {RANK_ORDER.map((r1, i) => (
                <div className="gridrow" role="row" key={`row-${i}`}>
                  {RANK_ORDER.map((r2, j) => {
                    const cls =
                      i === j
                        ? r1 + r2
                        : i < j
                          ? r1 + r2 + "s"
                          : RANK_ORDER[j] + RANK_ORDER[i] + "o";
                    const mix = grid[cls] ?? { fold: 1 };
                    const segments = ACTION_ORDER.filter((a) => (mix[a] ?? 0) > 0).map((a) => ({
                      action: a,
                      freq: mix[a],
                    }));
                    const isHero = cls === hero;
                    const mixLabel = segments
                      .map((s) => `${s.action} ${Math.round(s.freq * 100)}%`)
                      .join(", ");
                    return (
                      <div
                        key={`${i}-${j}`}
                        role="cell"
                        className={`cell${isHero ? " hero" : ""}`}
                        title={`${cls}: ${mixLabel}`}
                        aria-label={`${cls}: ${mixLabel}${isHero ? ", your hand" : ""}`}
                      >
                        <div className="cell-segments" aria-hidden="true">
                          {segments.map((s) => (
                            <span
                              key={s.action}
                              className={`cell-segment action-${s.action}`}
                              style={{ flex: `${s.freq} 0 0%` }}
                            />
                          ))}
                        </div>
                        <span className="cell-label">{cls}</span>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>

            {note && (
              <p className="sim-chart-exploit">
                <span className="sim-chart-exploit-villain">vs {note.villain_label}</span>
                <span className="sim-chart-exploit-rationale">{note.rationale}</span>
              </p>
            )}

            <div className="gridlegend">
              {LEGEND.map(([c, label]) => (
                <span key={c} className="lgi">
                  <span className={`cell sample ${c}`} aria-hidden="true" /> {label}
                </span>
              ))}
              <span className="lgi lgi-hero">
                <span className="cell sample sample-hero" aria-hidden="true" /> your hand{" "}
                <span className="num">{hero}</span>
              </span>
            </div>
          </>
        ) : (
          <p className="sim-chart-status sim-chart-status-quiet" role="status">
            No chart for this spot yet.
          </p>
        )}
      </div>
    </div>
  );
}
