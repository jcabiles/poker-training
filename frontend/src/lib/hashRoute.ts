// N6: minimal hash routing — `#/<view>` plus an optional drill-mode segment
// `#/drill/<mode>`. The hash IS the persistence (deep-link + reload restore).
// N7: invalid or empty hashes fall back to `home` (the new default view); a
// recognized `drill` view with a bogus/missing mode segment still falls back
// to drill/random, unchanged from N6 — only the unrecognized-VIEW fallback
// moved from "drill" to "home".
import type { Mode } from "../api/types";

export type View = "home" | "drill" | "texture" | "equity";

const VIEW_IDS: readonly View[] = ["home", "drill", "texture", "equity"];

const MODE_IDS: readonly Mode[] = [
  "random",
  "review",
  "leak_focus",
  "exploit",
  "challenge",
  "postflop",
  "vs_cbet",
  "vs_check_raise",
  "rfi",
  "vs_rfi",
  "blind_defense",
  "vs_limpers",
  "vs_3bet",
];

export interface Route {
  view: View;
  mode: Mode;
}

export function parseHash(hash: string): Route {
  const [rawView, rawMode] = hash.replace(/^#\/?/, "").split("/");
  const view = VIEW_IDS.find((v) => v === rawView) ?? "home";
  const mode = (view === "drill" && MODE_IDS.find((m) => m === rawMode)) || "random";
  return { view, mode };
}

export function formatHash(view: View, mode: Mode): string {
  return view === "drill" ? `#/drill/${mode}` : `#/${view}`;
}
