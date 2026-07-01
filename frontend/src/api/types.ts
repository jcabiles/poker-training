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
}

export interface NextDrillResponse {
  spot: Spot;
  grid: Record<string, string>; // handclass -> raise|call|fold|mixed
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
}

export type Mode =
  | "random"
  | "review"
  | "leak_focus"
  | "exploit"
  | "postflop"
  | "vs_cbet"
  | "vs_check_raise";

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
