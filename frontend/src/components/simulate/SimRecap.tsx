import type { GradeView } from "../../api/types";
import { fmtEvLoss, isMiss, streetLabel, tierOf } from "./simGrade";

// Simulate S10 — the coach's margin ledger. Mounts beside SimShowdown on
// hand_over: one ruled row per hero decision in ordinal order (street · action ·
// verdict · ≈EV-loss), and beneath a mistake/blunder row, the gilt-ruled "why"
// note — the teaching moment. "No baseline yet" rows (multiway / off-pack /
// unmappable spots the grader never ran on) are listed distinctly, never faked
// into a tier.
//
// AGGREGATE RULE (spec Gate-1 / refuter low-4): the SUMMARY line — accuracy and
// total ≈EV lost — counts ONLY graded rows (correctness != null). No-baseline
// rows carry ev_loss_bb 0 and no correctness; folding them in would dilute both
// figures and misreport coverage. They still appear in the per-decision list.
//
// TIER SURVIVAL: on the live path SimulateView merges each decision's live
// `last_grade` (which carries the verdict/reasoning text) into the recap by
// ordinal, so misses show their "why". After a mid-session reload the persisted
// rows have no tier text (freq/EV/correctness survive) — this component then
// degrades gracefully: the verdict word + ≈EV-loss still render, the "why" note
// just isn't there to expand. Accepted v1.

function actionLabel(action: string): string {
  return action.charAt(0).toUpperCase() + action.slice(1);
}

export default function SimRecap({ recap }: { recap: GradeView[] }) {
  if (recap.length === 0) return null;

  const graded = recap.filter((g) => g.correctness != null);
  const gradedCount = graded.length;
  const correct = graded.filter(
    (g) => g.correctness === "optimal" || g.correctness === "acceptable",
  ).length;
  const evLost = graded.reduce((sum, g) => sum + g.ev_loss_bb, 0);
  const noBaseline = recap.length - gradedCount;

  return (
    <section className="sim-recap panel" aria-label="Decision recap">
      <h2 className="sim-recap-title">Your decisions</h2>

      {gradedCount > 0 ? (
        <p className="sim-recap-summary">
          <span className="sim-recap-stat">
            <span className="sim-recap-stat-val num">
              {Math.round((correct / gradedCount) * 100)}%
            </span>
            <span className="sim-recap-stat-key">on baseline</span>
          </span>
          <span className="sim-recap-stat">
            <span className="sim-recap-stat-val num">{fmtEvLoss(evLost)}</span>
            <span className="sim-recap-stat-key">given up</span>
          </span>
          {noBaseline > 0 && (
            <span className="sim-recap-stat">
              <span className="sim-recap-stat-val num">{noBaseline}</span>
              <span className="sim-recap-stat-key">no baseline</span>
            </span>
          )}
        </p>
      ) : (
        <p className="sim-recap-summary sim-recap-summary-none">
          No mapped spots this hand — nothing to grade yet.
        </p>
      )}

      <ol className="sim-recap-list">
        {recap.map((g) => {
          const meta = tierOf(g.correctness);
          const miss = isMiss(g.correctness);
          const rowGraded = g.correctness != null;
          return (
            <li key={g.ordinal} className="sim-recap-row">
              <div className="sim-recap-line">
                <span className="sim-recap-street">{streetLabel(g.street)}</span>
                <span className="sim-recap-action">{actionLabel(g.chosen_action)}</span>
                <span className={"sim-badge sim-badge-inline sim-tier-" + meta.tone}>
                  <span className="sim-badge-word">{meta.label}</span>
                </span>
                {/* N3: preflop sizing verdict — a secondary sub-note directly
                    beside the action verdict badge, never altering it. Placed
                    BEFORE the margin-left:auto EV figure so it always sits next
                    to the verdict, not stranded at the row's right edge. Only
                    when hero raised at a two-size node. */}
                {g.sizing_correctness != null && (
                  <span className="sim-recap-size">
                    · size: {tierOf(g.sizing_correctness).label}
                  </span>
                )}
                {rowGraded && g.ev_loss_bb > 0 && (
                  <span className="sim-recap-ev num">{fmtEvLoss(g.ev_loss_bb)}</span>
                )}
              </div>
              {/* The teaching moment: only misses expand their "why", and only
                  when the reasoning text survived (live path — a reload drops
                  it and the row degrades to the verdict line above). */}
              {miss && g.reasoning && (
                <p className="sim-recap-why">{g.reasoning}</p>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
