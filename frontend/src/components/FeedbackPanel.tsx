import { useEffect, useRef, useState } from "react";

import { matchCard } from "../api/client";
import type { ConceptCard as ConceptCardData, Decision, EvaluationResult } from "../api/types";
import ConceptCardView from "./ConceptCard";
import RationaleTags from "./RationaleTags";

const TONE: Record<string, string> = {
  optimal: "good",
  acceptable: "good",
  mistake: "warn",
  blunder: "bad",
};

function actionLabel(action: string, sizeBb?: number | null): string {
  return sizeBb ? `${action} ${sizeBb}bb` : action;
}

// EV figures render with a true minus (U+2212), matching the masthead ledger
// and recap figures — number stringification would emit an ASCII hyphen.
function fmtEv(n: number): string {
  return String(n).replace("-", "−");
}

export default function FeedbackPanel({
  result,
  chosen,
  onNext,
}: {
  result: EvaluationResult;
  chosen: Decision | null;
  onNext: () => void;
}) {
  const tone = TONE[result.correctness ?? "optimal"] ?? "warn";
  const nextRef = useRef<HTMLButtonElement>(null);
  const [card, setCard] = useState<ConceptCardData | null>(null);

  // CW-7: the decision button the user just clicked is now disabled, which
  // would otherwise strand keyboard focus on <body>. This panel only ever
  // mounts fresh (App.tsx renders it only while `result` is set, and grading
  // can't re-fire while a result exists), so a mount-only effect is enough.
  useEffect(() => {
    nextRef.current?.focus();
  }, []);

  // N8 — point-of-need concept card: only for missed reps, fire-and-forget so
  // feedback still renders if the card fetch fails or leak_category is absent.
  useEffect(() => {
    if (
      (result.correctness !== "mistake" && result.correctness !== "blunder") ||
      result.leak_category == null
    ) {
      return;
    }
    let cancelled = false;
    matchCard(result.leak_category, result.rationale_tags)
      .then((res) => {
        if (!cancelled) setCard(res.card);
      })
      .catch(() => {
        /* non-blocking — feedback renders regardless */
      });
    return () => {
      cancelled = true;
    };
  }, [result.correctness, result.leak_category, result.rationale_tags]);

  const best = result.best_action;
  const choseBest =
    chosen != null && chosen.action === best.action && (chosen.size_bb ?? null) === (best.size_bb ?? null);

  return (
    <div
      className={"panel feedback " + tone + "-bg"}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {/* Tier 0 — correctness stamp chip. The numbers live in the EV ledger
          below (R4: every figure renders exactly once in the panel). */}
      <div className="verdict-row">
        <span className={"stamp " + tone}>{(result.correctness ?? "").toUpperCase()}</span>
      </div>
      {/* Tier 1 — verdict as a serif headline. The backend sends a plain
          sentence (tiers.verdict / explanation); it isn't split into action
          words, so the whole line is set as the headline rather than parsed. */}
      <p className="tier-verdict">{result.tiers?.verdict ?? result.explanation}</p>
      {result.is_mixed && (
        <p className="mixed">Mixed spot — more than one action is defensible here.</p>
      )}
      {/* EV comparison — a settled ledger: one row per decision (YOU / BEST /
          COST) on a dark plate behind a gold left rule, mono figures right.
          Replaces the old one-sentence number pile and .chosen-eval line. */}
      {result.chosen_eval && chosen && (
        <div className={"ev-ledger " + tone + "-edge"}>
          <div className={"ev-row " + tone}>
            <span className="ev-who">You</span>
            <span className="ev-act">
              {actionLabel(chosen.action, chosen.size_bb)}
              <span className="ev-played">
                played <span className="num">{Math.round(result.chosen_eval.frequency * 100)}%</span>
              </span>
            </span>
            <span className="ev-nums">
              EV <span className="num">≈{fmtEv(result.chosen_eval.ev_bb)}</span>bb
            </span>
            {choseBest && <span className="best">best</span>}
          </div>
          {!choseBest && (
            <>
              <div className="ev-row good">
                <span className="ev-who">Best</span>
                <span className="ev-act">
                  {actionLabel(best.action, best.size_bb)}
                  <span className="ev-played">
                    played <span className="num">{Math.round(best.frequency * 100)}%</span>
                  </span>
                </span>
                <span className="ev-nums">
                  EV <span className="num">≈{fmtEv(best.ev_bb)}</span>bb
                </span>
              </div>
              <div className="ev-row cost">
                <span className="ev-who">Cost</span>
                <span className="ev-act ev-cost-note">bb given up on this decision</span>
                <span className="ev-nums">
                  <span className="num">≈{result.ev_loss_bb}</span>bb
                </span>
              </div>
            </>
          )}
        </div>
      )}
      {/* N1 tier 2 — reasoning: why, composed from tags + authored rationale
          (backend now leads with the hand-specific sentence). */}
      <RationaleTags tags={result.rationale_tags} />
      {result.tiers && <p className="tier-reasoning">{result.tiers.reasoning}</p>}
      {/* N1 tier 3 — deep dive: the full numbers, collapsed by default. */}
      <details className="tier-deepdive">
        <summary>Deep dive — full action mix</summary>
        {result.tiers && <p className="deepdive-text">{result.tiers.deep_dive}</p>}
        <ul className="mix">
          {result.per_action.map((a, i) => (
            <li key={i}>
              <b>
                {a.action}
                {a.size_bb ? <span className="num"> {a.size_bb}bb</span> : ""}
              </b>
              <span className="num mix-freq">{Math.round(a.frequency * 100)}%</span>
              <span className="mix-ev">
                EV <span className="num">≈{fmtEv(a.ev_bb)}</span>bb
              </span>
              {a.action === result.best_action.action &&
                a.size_bb === result.best_action.size_bb && <span className="best">best</span>}
            </li>
          ))}
        </ul>
        {/* N2/CW-2b: EVs are a heuristic proxy, not solver-exact -- the "≈"
            prefixes above plus this note keep that honest until Phase 3. */}
        {/* T6: own class — .studytest-hint is StudyTestToggle's (hazard 6). */}
        <p className="ev-disclaimer">EV values are approximate (proxy, not solver-exact).</p>
      </details>
      {/* N8 — point-of-need concept card, below the tiers; absent when no
          card matches (thin leaks) or the fetch hasn't resolved/failed. */}
      {card && <ConceptCardView card={card} />}
      <button
        ref={nextRef}
        type="button"
        className="btn btn-primary"
        onClick={onNext}
        aria-label="Next spot (shortcut Space)"
      >
        Next <kbd aria-hidden="true">Space</kbd>
      </button>
    </div>
  );
}
