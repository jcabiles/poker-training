import type { GradeView } from "../../api/types";

// Simulate S10 — the shared verdict vocabulary. One source of truth for how a
// `correctness` value maps to the word the player reads and the tone class the
// CSS paints, so the hero badge, the end-of-hand recap, and the per-street
// report never drift apart. `correctness === null` is the "no baseline yet"
// state: the spot was multiway / off-pack / unmappable, so the grader never
// ran. The WORD always carries the meaning; the tone tint is redundant (color
// is never load-bearing — a color-blind reader loses nothing).

export type Tier = "optimal" | "acceptable" | "mistake" | "blunder" | "none";

export interface TierMeta {
  tier: Tier;
  label: string; // the word shown on the badge / recap row
  tone: "good" | "neutral" | "warn" | "bad" | "muted"; // → .sim-tier-<tone>
}

const META: Record<Tier, TierMeta> = {
  optimal: { tier: "optimal", label: "Best", tone: "good" },
  acceptable: { tier: "acceptable", label: "OK", tone: "neutral" },
  mistake: { tier: "mistake", label: "Mistake", tone: "warn" },
  blunder: { tier: "blunder", label: "Blunder", tone: "bad" },
  none: { tier: "none", label: "No baseline yet", tone: "muted" },
};

export function tierOf(correctness: GradeView["correctness"]): TierMeta {
  if (correctness == null) return META.none;
  return META[correctness];
}

// A mistake or blunder is the teaching moment — the recap expands its "why".
export function isMiss(correctness: GradeView["correctness"]): boolean {
  return correctness === "mistake" || correctness === "blunder";
}

// Street display order — the report always renders all four; the recap orders
// its rows by ordinal (server-supplied), but shares this label casing.
export function streetLabel(street: string): string {
  return street.charAt(0).toUpperCase() + street.slice(1);
}

// EV-loss figures are ≈ approximate (heuristic provider). One formatter so the
// "≈" label and the 1-dp rounding read the same everywhere. Sub-0.05bb rounds
// to a clean "0.0" — an on-baseline decision that gave up nothing.
export function fmtEvLoss(bb: number): string {
  return `≈${bb.toFixed(1)}bb`;
}
