// Hand-written mirror of the backend contract (kept in sync with openapi.json;
// `npm run gen:api` can regenerate full types from it).

export type ActionType = "fold" | "check" | "call" | "bet" | "raise" | "post";

export interface LegalAction {
  action: ActionType;
  min_bb?: number | null;
  max_bb?: number | null;
}

export interface HistoryAction {
  street: string;
  position: string;
  action: ActionType;
  amount_bb: number;
}

export interface Spot {
  game: { stakes: { sb: number; bb: number }; table_size: number };
  street: string;
  board: string[];
  pot_bb: number;
  hero: { position: string; hole_cards: [string, string]; stack_bb: number };
  players: { position: string; stack_bb: number; is_hero: boolean; status: string }[];
  effective_stack_bb: number;
  spr?: number | null;
  to_act: string;
  legal_actions: LegalAction[];
  node_context: string[];
  facing?: string | null;
  limper_count: number;
  villain_type?: string | null;
  hero_range?: string | null;
  villain_range?: string | null;
  srs_signature?: string | null; // SRS-key override for review spots; echoed back on grade
  action_history: HistoryAction[];
}

export interface ActionEval {
  action: ActionType;
  size_bb?: number | null;
  frequency: number;
  ev_bb: number;
}

// N1 tiered teaching feedback: verdict -> reasoning -> deep-dive, composed
// backend-side by the TieredFeedbackProvider wrapper (never parsed from
// `explanation`, which is kept for backward compat).
export interface FeedbackTiers {
  verdict: string;
  reasoning: string;
  deep_dive: string;
}

export interface EvaluationResult {
  per_action: ActionEval[];
  best_action: ActionEval;
  chosen_eval?: { frequency: number; ev_bb: number } | null;
  ev_loss_bb: number;
  correctness?: "optimal" | "acceptable" | "mistake" | "blunder" | null;
  rationale_tags: string[];
  explanation: string;
  provider: string;
  leak_category?: number | null;
  coverage: string;
  is_mixed: boolean;
  authored_rationale?: string | null; // content-pack rationale prose, when present
  tiers?: FeedbackTiers | null;
}

export interface NextDrillResponse {
  spot: Spot;
  grid: Record<string, Record<string, number>>; // handclass -> {action: freq}, freqs sum to ~1.0
}

export interface Decision {
  action: ActionType;
  size_bb?: number;
}

export interface LeakStat {
  category: number;
  name: string;
  attempts: number;
  accuracy: number;
  avg_ev_loss: number;
}

export interface StatsSummary {
  total_attempts: number;
  accuracy: number;
  due_count: number;
  streak_days: number;
  trend: number;
  ev_given_up_today_bb: number; // T8: sum of today's ev_loss_bb (local day), 2dp; approximate
}

// T8 — practice heat-calendar: one entry per day, Monday-aligned, zero days
// included (full grid). accuracy is 0 on zero-attempt days.
export interface CalendarDay {
  date: string; // "YYYY-MM-DD"
  attempts: number;
  accuracy: number; // 0..1
}

// T8 — most-recent practice day's recap. `day` is null when no attempts exist;
// `biggest_miss` is null when the day had no graded misses.
export interface RecapResponse {
  day: string | null; // "YYYY-MM-DD" or null (empty history)
  hands: number;
  accuracy: number; // 0..1
  bb_given_up: number; // approximate
  biggest_miss: { label: string; ev_loss_bb: number } | null;
}

export type Mode =
  | "random"
  | "review"
  | "leak_focus"
  | "exploit"
  | "challenge"
  | "postflop"
  | "vs_cbet"
  | "vs_check_raise"
  // preflop learning-path families (home-hub path nodes)
  | "rfi"
  | "vs_rfi"
  | "blind_defense"
  | "vs_limpers"
  | "vs_3bet";

// --- Foundational quizzes (Phase 2a) ---
export type QuizKind = "texture" | "equity";

export interface QuizItem {
  quiz_id: string;
  kind: QuizKind;
  board: string[];
  prompt: string;
  options: string[];
  hero_cards?: [string, string] | null;
  villain_range?: string | null;
}

export interface QuizAnswer {
  kind: QuizKind;
  board: string[];
  choice?: string;
  estimate_pct?: number;
  hero_cards?: [string, string] | null;
  villain_range?: string | null;
}

export interface QuizResult {
  kind: string;
  correct: boolean;
  correctness: string;
  expected: string;
  your_answer: string;
  delta?: number | null;
  explanation: string;
  leak_category: number;
}

// N8 — point-of-need concept cards. leak_category + rationale_tags key the
// match (see backend/app/services/concept_cards.py); drill_mode is where
// "drill this" navigates via hash routing (#/drill/<mode>).
export interface ConceptCard {
  id: string;
  version: number;
  title: string;
  summary: string;
  body: string;
  leak_categories: number[];
  rationale_tags: string[];
  drill_mode: Mode;
  source_doc: string;
}

export interface CardMatchResponse {
  card: ConceptCard | null;
}

// N7 — read-only "today's plan" surfacing of the SM-2 due queue.
export interface DuePlanItem {
  signature: string;
  due_date: string;
  last_grade?: number | null;
  label: string;
}

export interface ReviewPlanResponse {
  due_count: number;
  items: DuePlanItem[];
}

// Simulate S9 — hand-authored mirror of backend/app/schemas/simulate.py (the
// superset that REPLACES the S1 shape). The playable, persistent session: per
// -seat stacks/status/ledger, revealed board, hero action bar, bot event log,
// and showdown reveals. Privacy invariant is structural on the wire: the ONLY
// hole cards present are `hero.hole_cards` plus, at showdown, each
// `ShowdownSeatView.hole_cards`. Folded villains are never revealed.

// One seat, all 9 present every response. `persona_type` is the villain-bot
// archetype (badge); null for the hero. `status` is IN | FOLDED | ALLIN.
export interface SeatView {
  seat_index: number; // 0..8; hero is seat 0
  position: string; // UTG..BB
  persona_type: string | null; // villain archetype badge; null = hero
  is_hero: boolean;
  stack_bb: number; // carry-over current stack
  status: string; // "IN" | "FOLDED" | "ALLIN"
  invested_street_bb: number; // this street's commitment (chips-in-front)
  net_bb: number; // stack_bb - buyins_bb (ledger P&L)
}

// Only present for seats that reached showdown (settlement.showdown_seats).
// Folded villains never appear here — this is the sole villain-card reveal.
export interface ShowdownSeatView {
  seat_index: number;
  hole_cards: [string, string];
  delta_bb: number; // this seat's chip delta for the hand
}

// A single bot action since the last hero decision (static event log; S9 has
// no pacing/animation). No hole cards — safe to serialize.
export interface EventView {
  seat_index: number;
  position: string;
  action: string; // "fold" | "check" | "call" | "bet" | "raise" | "post"
  amount_bb: number;
  street: string;
}

export interface SimulateHandView {
  hand_no: number; // 1-based, increments per hand
  button_seat: number; // seat index holding the dealer button
  street: string; // "preflop" | "flop" | "turn" | "river"
  board: string[]; // REVEALED community cards only (never the full board)
  pot_bb: number;
  seats: SeatView[]; // all 9 seats
  hero: { position: string; hole_cards: [string, string]; stack_bb: number };
  to_act_seat: number | null; // seat index to act, or null when hand_over
  is_hero_turn: boolean; // hero action bar shows iff true
  legal_actions: LegalAction[]; // populated only when is_hero_turn
  events: EventView[]; // bot actions since the last hero decision
  hand_over: boolean;
  showdown: ShowdownSeatView[]; // [] until hand_over; folded villains never listed
}

export interface SessionView {
  session_id: string; // uuid4 hex
  hand: SimulateHandView;
}
