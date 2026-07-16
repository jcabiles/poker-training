import type { ActionType, Spot } from "../api/types";

export interface DecisionOption {
  action: ActionType;
  size_bb?: number | null;
  key: string; // keyboard shortcut (uppercase)
  label: string;
  primary: boolean;
}

const BASE_KEY: Record<string, string> = {
  fold: "F",
  call: "C",
  raise: "R",
  check: "K",
  bet: "B",
};

// Resolve the legal actions into labelled, keyboard-mapped options. Handles the
// postflop case of TWO bet sizes (small/big) — which collide on action alone —
// by sizing the label and giving the big bet its own key (V).
export function legalDecisions(spot: Spot): DecisionOption[] {
  const bets = spot.legal_actions.filter((l) => l.action === "bet");
  const minBet = Math.min(...bets.map((b) => b.min_bb ?? Number.POSITIVE_INFINITY));
  return spot.legal_actions.map((la) => {
    if (la.action === "bet" && bets.length > 1) {
      const small = (la.min_bb ?? 0) === minBet;
      return {
        action: "bet",
        size_bb: la.min_bb,
        key: small ? "B" : "V",
        label: `${small ? "Bet small" : "Bet big"} ${la.min_bb}bb`,
        primary: !small,
      };
    }
    const name = la.action.charAt(0).toUpperCase() + la.action.slice(1);
    // R2: prefer the server's realistic suggested size for bet/raise; call has none.
    const suggested = la.size_bb ?? la.min_bb;
    const sized =
      (la.action === "raise" || la.action === "bet" || la.action === "call") && suggested
        ? ` ${suggested}bb`
        : "";
    return {
      action: la.action,
      size_bb: suggested,
      key: BASE_KEY[la.action] ?? "?",
      label: name + sized,
      primary: la.action === "raise" || la.action === "bet",
    };
  });
}
