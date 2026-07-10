import { useCallback, useEffect, useState } from "react";

import { quizGrade, quizNext } from "../api/client";
import type { QuizItem, QuizKind, QuizResult } from "../api/types";
import { expandChip, groupRange } from "../lib/rangeGroups";
import Card from "./Card";

// Sublabels for the texture answers (reference: "few draws" / "some
// connectivity" / "flush & straight draws"). Keyed on the option's lead word so
// it survives casing/wording drift; unknown options render without a sublabel.
const TEXTURE_HINTS: Record<string, string> = {
  dry: "few draws",
  medium: "some connectivity",
  wet: "flush & straight draws",
};

function textureHint(option: string): string | undefined {
  return TEXTURE_HINTS[option.trim().toLowerCase()];
}

function quizTone(res: QuizResult): "good" | "warn" | "bad" {
  if (res.correct) return "good";
  return res.correctness.toLowerCase() === "acceptable" ? "warn" : "bad";
}

export default function QuizPanel({ kind }: { kind: QuizKind }) {
  const [item, setItem] = useState<QuizItem | null>(null);
  const [res, setRes] = useState<QuizResult | null>(null);
  const [estimate, setEstimate] = useState("");
  const [chosen, setChosen] = useState<string | null>(null);
  const [inputError, setInputError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRes(null);
    setEstimate("");
    setChosen(null);
    setInputError(null);
    setError(null);
    try {
      setItem(await quizNext(kind));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [kind]);

  useEffect(() => {
    load();
  }, [load]);

  const answerTexture = async (choice: string) => {
    if (!item || res) return;
    setChosen(choice);
    try {
      setRes(await quizGrade({ kind: "texture", board: item.board, choice }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const answerEquity = async () => {
    if (!item || res) return;
    const pct = parseFloat(estimate);
    // type=number min/max only constrain the spinner — typed values arrive
    // unclamped, so validate here instead of grading a 4500% "equity".
    if (Number.isNaN(pct) || pct < 0 || pct > 100) {
      setInputError("Enter an equity between 0 and 100.");
      return;
    }
    try {
      setRes(
        await quizGrade({
          kind: "equity",
          board: item.board,
          hero_cards: item.hero_cards,
          villain_range: item.villain_range,
          estimate_pct: pct,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  if (error)
    return <div className="panel bad-bg">Error: {error}. Is the backend running on :8008?</div>;
  if (!item) return <div className="panel">Loading…</div>;

  const eyebrow = item.kind === "equity" ? "Equity estimation" : "Board reading";
  const groups = item.villain_range ? groupRange(item.villain_range) : null;

  return (
    <div className="quizpanel">
      <p className="quiz-eyebrow">{eyebrow}</p>

      {/* Staged board — the felt sits inside the dark stage frame + glow, the
          same lit-table idiom the drill uses (T4), quiz-scoped here. */}
      <div className="stage quiz-stage">
        <div className="felt felt-staged quiz-felt">
          {item.kind === "equity" && item.hero_cards && (
            <>
              <div className="ctx">Hero holds</div>
              <div className="cards">
                {item.hero_cards.map((c, i) => (
                  <Card key={i} card={c} />
                ))}
              </div>
            </>
          )}
          <div className="ctx quiz-spacer">The flop</div>
          <div className="board">
            {item.board.map((c, i) => (
              <Card key={i} card={c} />
            ))}
          </div>
        </div>
      </div>

      {/* Villain range as grouped chips (was a raw comma list). Sits below the
          staged board on equity spots only. */}
      {item.kind === "equity" && groups && (
        <div className="villain-range">
          <div className="villain-range-head">
            <p className="quiz-eyebrow">Villain's range</p>
            <span className="villain-combos">
              <span className="num">{groups.combos}</span> combos · grouped
            </span>
          </div>
          {groups.pairs.length > 0 && (
            <ChipGroup name="Pocket pairs" tone="pair" chips={groups.pairs} />
          )}
          {groups.suited.length > 0 && (
            <ChipGroup name="Suited" tone="suited" chips={groups.suited} />
          )}
          {groups.offsuit.length > 0 && (
            <ChipGroup name="Offsuit" tone="offsuit" chips={groups.offsuit} />
          )}
        </div>
      )}

      <p className="prompt">{item.prompt}</p>

      {item.kind === "texture" ? (
        <div className="decisionbar quiz-answers">
          {item.options.map((o) => {
            const hint = textureHint(o);
            // After grading, mark the correct answer and (if different) the
            // user's wrong pick directly on the buttons — the verdict text
            // alone shouldn't be needed to reconstruct what happened.
            const graded = res
              ? o === res.expected
                ? " answer-correct"
                : o === chosen
                  ? " answer-wrong"
                  : ""
              : "";
            return (
              <button
                key={o}
                className={"btn answer-btn" + graded}
                disabled={!!res}
                onClick={() => answerTexture(o)}
              >
                <span className="answer-label">{o}</span>
                {hint && <span className="answer-hint">{hint}</span>}
              </button>
            );
          })}
        </div>
      ) : (
        <div className="decisionbar quiz-equity-input">
          <input
            className="input"
            type="number"
            min={0}
            max={100}
            value={estimate}
            placeholder="equity %"
            aria-label="Your equity estimate, percent"
            aria-invalid={inputError != null}
            disabled={!!res}
            onChange={(e) => {
              setEstimate(e.target.value);
              setInputError(null);
            }}
            onKeyDown={(e) => e.key === "Enter" && answerEquity()}
          />
          <button className="btn btn-primary" disabled={!!res} onClick={answerEquity}>
            Submit estimate
          </button>
          {inputError && (
            <span className="input-error" role="alert">
              {inputError}
            </span>
          )}
        </div>
      )}

      {res && (
        // Partial credit ("acceptable") reads as a caution, not an error —
        // warn tone; only a plain miss gets the bad tone.
        <div className={`panel quiz-result ${quizTone(res)}-bg`}>
          <div className="verdict-row">
            <span className={`stamp ${quizTone(res)}`}>{res.correctness.toUpperCase()}</span>
            <span>
              expected{" "}
              <strong className={res.kind === "equity" ? "num" : undefined}>{res.expected}</strong>,
              you said{" "}
              <strong className={res.kind === "equity" ? "num" : undefined}>
                {res.your_answer}
              </strong>
              {res.delta != null && (
                <>
                  {" "}
                  (off by <span className="num">{res.delta}</span>pp)
                </>
              )}
            </span>
          </div>
          <p className="why">{res.explanation}</p>
          <button className="btn btn-primary" onClick={load}>
            Next ▸
          </button>
        </div>
      )}
    </div>
  );
}

function ChipGroup({
  name,
  tone,
  chips,
}: {
  name: string;
  tone: "pair" | "suited" | "offsuit";
  chips: string[];
}) {
  return (
    <div className="range-group">
      <div className="grp-label">
        <span className="grp-name">{name}</span>
        <span className="grp-count num">{chips.reduce((n, c) => n + expandChip(c).length, 0)}</span>
      </div>
      <div className="hand-chips">
        {chips.map((c) => (
          <span key={c} className={`h-chip h-chip-${tone}`}>
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}
