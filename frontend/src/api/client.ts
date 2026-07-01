import type {
  Decision,
  EvaluationResult,
  LeakStat,
  Mode,
  NextDrillResponse,
  QuizAnswer,
  QuizItem,
  QuizKind,
  QuizResult,
  Spot,
  StatsSummary,
} from "./types";

const BASE = "/api/v1"; // proxied to FastAPI :8008 in dev

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.url} -> ${r.status}`);
  return r.json() as Promise<T>;
}

export async function getNext(mode: Mode = "random"): Promise<NextDrillResponse> {
  return json(await fetch(`${BASE}/drill/next?mode=${mode}`));
}

export async function grade(spot: Spot, action: Decision): Promise<EvaluationResult> {
  return json(
    await fetch(`${BASE}/drill/grade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spot, action }),
    }),
  );
}

export async function getLeaks(): Promise<LeakStat[]> {
  return json(await fetch(`${BASE}/stats/leaks`));
}

export async function getSummary(): Promise<StatsSummary> {
  return json(await fetch(`${BASE}/stats/summary`));
}

export async function quizNext(kind: QuizKind | "random" = "random"): Promise<QuizItem> {
  return json(await fetch(`${BASE}/drill/quiz/next?kind=${kind}`));
}

export async function quizGrade(answer: QuizAnswer): Promise<QuizResult> {
  return json(
    await fetch(`${BASE}/drill/quiz/grade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(answer),
    }),
  );
}
