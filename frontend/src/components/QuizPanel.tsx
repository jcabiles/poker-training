import { useCallback, useEffect, useState } from "react";

import { quizGrade, quizNext } from "../api/client";
import type { QuizItem, QuizKind, QuizResult } from "../api/types";
import Card from "./Card";

export default function QuizPanel({ kind }: { kind: QuizKind }) {
  const [item, setItem] = useState<QuizItem | null>(null);
  const [res, setRes] = useState<QuizResult | null>(null);
  const [estimate, setEstimate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRes(null);
    setEstimate("");
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
    try {
      setRes(await quizGrade({ kind: "texture", board: item.board, choice }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const answerEquity = async () => {
    if (!item || res) return;
    const pct = parseFloat(estimate);
    if (Number.isNaN(pct)) return;
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

  return (
    <div className="quizpanel">
      <div className="felt">
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
        <div className="ctx quiz-spacer">Flop</div>
        <div className="board">
          {item.board.map((c, i) => (
            <Card key={i} card={c} />
          ))}
        </div>
        {item.kind === "equity" && item.villain_range && (
          <div className="herometa">Villain range: {item.villain_range}</div>
        )}
      </div>

      <p className="prompt">{item.prompt}</p>

      {item.kind === "texture" ? (
        <div className="decisionbar">
          {item.options.map((o) => (
            <button key={o} className="btn" disabled={!!res} onClick={() => answerTexture(o)}>
              {o}
            </button>
          ))}
        </div>
      ) : (
        <div className="decisionbar">
          <input
            className="input"
            type="number"
            min={0}
            max={100}
            value={estimate}
            placeholder="equity %"
            disabled={!!res}
            onChange={(e) => setEstimate(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && answerEquity()}
          />
          <button className="btn btn-primary" disabled={!!res} onClick={answerEquity}>
            Submit
          </button>
        </div>
      )}

      {res && (
        <div className={`panel quiz-result ${res.correct ? "good-bg" : "bad-bg"}`}>
          <div className="verdict-row">
            <span className={`badge ${res.correct ? "good" : "bad"}`}>
              {res.correctness.toUpperCase()}
            </span>
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
