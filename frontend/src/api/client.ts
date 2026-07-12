import type {
  CalendarDay,
  CardMatchResponse,
  Decision,
  EvaluationResult,
  LeakStat,
  Mode,
  NextDrillResponse,
  PreflopChartView,
  QuizAnswer,
  QuizItem,
  QuizKind,
  QuizResult,
  RecapResponse,
  ReviewPlanResponse,
  SessionView,
  Spot,
  StatsSummary,
  StreetReportView,
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

// T8 — practice heat-calendar (Monday-aligned, zero days included). Home fetches
// this best-effort/fire-and-forget: the calendar hides if it fails.
export async function getCalendar(weeks = 8): Promise<CalendarDay[]> {
  return json(await fetch(`${BASE}/stats/calendar?weeks=${weeks}`));
}

// T8 — most-recent practice day's recap. Best-effort like the calendar; the
// House Recap card empty-states when `day` is null or the fetch fails.
export async function getRecap(): Promise<RecapResponse> {
  return json(await fetch(`${BASE}/stats/recap`));
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

// N7 — today's-plan (SM-2 due queue), fire-and-forget/best-effort like stats.
export async function getPlan(): Promise<ReviewPlanResponse> {
  return json(await fetch(`${BASE}/review/plan`));
}

// N8 — point-of-need concept-card lookup. Callers should treat this as
// fire-and-forget/non-blocking: feedback must render even if this fails.
export async function matchCard(
  leakCategory: number,
  tags: string[],
): Promise<CardMatchResponse> {
  const params = new URLSearchParams({ leak_category: String(leakCategory) });
  if (tags.length > 0) params.set("tags", tags.join(","));
  return json(await fetch(`${BASE}/cards/match?${params.toString()}`));
}

// Simulate S9 — playable, persistent session. The server seeds each hand and
// advances all bots up to the hero's turn (or hand end) within each request;
// no seed/full-board/villain hole cards ever cross the wire. All five calls
// return the full SessionView (its `hand` is the live decision point).

// Create a fresh session (mints a session_id; deals hand 1; advances to hero).
export async function postSimulateSession(): Promise<SessionView> {
  return json(await fetch(`${BASE}/simulate/session`, { method: "POST" }));
}

// Restore an existing session by id (reload recovery). Throws "... -> 404" when
// the session is missing or ended — SimulateView clears storage on that.
export async function getSession(sessionId: string): Promise<SessionView> {
  return json(await fetch(`${BASE}/simulate/session/${sessionId}`));
}

// Apply the hero's chosen action; the server resolves bots to the next hero
// turn (or hand-over) and returns the resulting live view.
export async function postHeroAction(
  sessionId: string,
  action: Decision,
): Promise<SessionView> {
  return json(
    await fetch(`${BASE}/simulate/session/${sessionId}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(action),
    }),
  );
}

// Deal the next hand (only after the current hand is complete) — carries over
// stacks, moves the button, increments hand_no.
export async function postNextHand(sessionId: string): Promise<SessionView> {
  return json(await fetch(`${BASE}/simulate/session/${sessionId}/hand`, { method: "POST" }));
}

// Leave the table: ends the session server-side (subsequent restore → 404).
export async function leaveSession(sessionId: string): Promise<void> {
  const r = await fetch(`${BASE}/simulate/session/${sessionId}/leave`, { method: "POST" });
  if (!r.ok) throw new Error(`${r.url} -> ${r.status}`);
}

// S10 — all-time per-street grading report (across every session). Session
// -independent, so no session_id: the panel fetches it on mount and refetches
// when a hand completes. Always returns all four street rows.
export async function getStreetReport(): Promise<StreetReportView> {
  return json(await fetch(`${BASE}/simulate/report/streets`));
}

// Preflop chart (C1/C2) — the baseline range chart for the hero's CURRENT
// preflop decision on this session. Server-side state only (no spot params):
// the endpoint reads the live decision point. `available=false` (with a null
// grid) is a normal 200 body for a non-hero-preflop / unmappable spot — only a
// missing/ended session 404s. The panel fetches this on first expand and
// refetches per new hero preflop turn while expanded.
export async function getPreflopChart(sessionId: string): Promise<PreflopChartView> {
  return json(await fetch(`${BASE}/simulate/${sessionId}/preflop-chart`));
}
