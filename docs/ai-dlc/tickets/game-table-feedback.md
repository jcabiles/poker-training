# Tickets — visual game table + feedback readability

Spec: `docs/ai-dlc/specs/game-table-feedback.md` · Contracts: `docs/ai-dlc/contracts/game-table-feedback.md`
Branch: `feat/game-table-feedback` (stacked on `feat/card-room-polish-ux`). Sequential unless noted.
Backend tickets (T1–T4) get tests-only verification (R6: no design review of old UI against new data); design build loop (ux-ui-designer → design-reviewer) starts at T5.

## T1 — Harden `_villain_pos` before any folded seats exist
`postflop._villain_pos` must select the live (status IN) non-hero player, preferring `spot.facing`, instead of "first non-hero".
- **AC**: returns correct villain for a players list containing FOLDED seats before the real villain; `grade_cbet` + `grade_vs_check_raise` paths covered by new fixtures with >2 players incl. FOLDED seats.
- **Done**: `./scripts/verify.sh` → BACKEND VERIFY OK; `cd backend && ruff check .` clean.
- **Owns**: `backend/app/domain/postflop.py`, `backend/tests/test_postflop.py`.

## T2 — Preflop seat enrichment (build_spot) — after T1
`build_spot` emits all 9 seats (UTG, UTG1, UTG2, LJ, HJ, CO, BTN, SB, BB) with status IN/FOLDED + explicit preflop FOLD entries in `action_history` for every seat that acted-and-folded before hero (canonical order; blinds never fold in these spots).
- **AC**: for each NodeContext: len(players)==9, one seat per position (existing uniqueness tests still pass), statuses match the authored action (e.g. vs_RFI vs UTG: UTG IN, UTG1/UTG2/LJ...folded per position order, blinds IN), FOLD history entries present in canonical order, `spot_signature()` output unchanged for a fixed rng seed (regression assert).
- **Done**: verify.sh green; ruff clean.
- **Owns**: `backend/app/domain/scenarios.py`, `backend/tests/test_scenarios.py`.

## T3 — Postflop seat enrichment (shared helper) — after T2
Shared fold-derivation helper; `build_cbet_spot`, `build_vs_cbet_spot`, `build_check_raise_spot` emit 9 seats + FOLD history (everyone except the opener/caller pairing; SB posted then folded).
- **AC**: all three builders: len(players)==9, exactly 2 IN (pairing), SB FOLDED with a FOLD history entry after its POST, `faced_bet_bucket` unchanged (FOLD filtered), `_villain_pos` returns the pairing villain.
- **Done**: verify.sh green; ruff clean.
- **Owns**: `backend/app/domain/scenarios.py` (sequential with T2), `backend/tests/test_scenarios.py`, `backend/tests/test_postflop.py` (additions only).

## T4 — Feedback lede + reasoning reorder — parallel-safe with T2/T3 (different files), run sequentially anyway
`_verdict` shrinks to one plain-language lede (correctness label capitalized; "Best play"/"No strategy content" paths keep their pinned substrings). `_reasoning` puts authored rationale first in ALL THREE branches (postflop tag-branch, preflop shape-branch, exploit-villain branch — exploit sentence moves to front).
- **AC**: tiers.verdict ≤ ~90 chars typical, no EV/frequency numerals required in it; authored rationale is sentence 1 of tiers.reasoning whenever present (all 3 branches asserted); `tiers?.verdict ?? explanation` fallback path untouched; amend `test_preflop_tiers_carry_chosen_freq_and_ev` if it pins numerals.
- **Done**: verify.sh green; ruff clean.
- **Owns**: `backend/app/domain/feedback.py`, `backend/tests/test_feedback_tiers.py`.

## T5 — Visual table: oval ring, face-down cards, action chips (DESIGN) — after T3
Rewrite PokerTable markup + CSS: elliptical felt, 9 seat pods in seating order, board+pot center, hero pod enlarged bottom-center (face-up cards, to-act affordance), live villains = 2 card backs (`Card` gets optional `faceDown` prop), folded = dimmed pod + fold chip + no cards, latest-action chip per seat (reuse opens/3-bets ladder verbs), dealer button on BTN, `.line` retired, `.ctx` + villain-type line stay.
- **AC**: all four modes (`#/drill`, `#/drill/postflop`, `#/drill/vs_cbet`, `#/drill/exploit`) render seats whose fold/live states match `action_history`; `.felt` changes benign for quizzes (texture + equity quiz visually unchanged); tokens-only CSS; both themes AA; at 1024×768 felt + decision bar fully visible without scrolling.
- **Done**: design-reviewer pass (1440 + 1024, both themes) + `npm run typecheck && npm run build` clean + no raw hex outside tokens.css.
- **Owns**: `frontend/src/components/PokerTable.tsx`, `frontend/src/components/Card.tsx`, `frontend/src/styles/app.css` (table blocks), `frontend/src/styles/tokens.css` (only if new tokens needed — single owner this ticket).

## T6 — Feedback panel: EV comparison block + lede rendering (DESIGN) — after T4 + T5
Tone-colored EV block (your action / best action / EV given up — one line each, mono numerics, ≈ kept) REPLACES `.chosen-eval`; `.verdict-row` badge + EV-loss stat stays top-line (no figure rendered twice); short backend lede renders as `.tier-verdict`; reasoning paragraph shows authored lede first (backend already reordered).
- **AC**: every EV/frequency figure appears exactly once in the panel; tone colors AA in both themes; ARIA contract intact (`role=status`, `aria-live=polite`, `aria-atomic`, mount-focus on Next, Space/N works); `.tier-deepdive summary` styling still shared with `.concept-card summary`; deep-dive mix list unchanged.
- **Done**: design-reviewer pass (1440 + 1024, both themes, graded states: optimal/acceptable/mistake/blunder + mixed) + typecheck/build clean + hex grep clean.
- **Owns**: `frontend/src/components/FeedbackPanel.tsx`, `frontend/src/styles/app.css` (feedback blocks — sequential after T5).

## T7 — Whole-flow sweep + manual data check — after T6
Final design-reviewer sweep across all four drill modes + one quiz (felt regression) at 1440/1024 both themes; manual data check: one hand per mode — seat fold/live states equal what the old text betting line implied.
- **AC**: reviewer verdict pass; zero blockers/majors; deterministic gates all green.
- **Done**: verify.sh + ruff + typecheck/build + hex grep all green; final screenshots delivered to user.
- **Owns**: no files (review-only; fixes route back to T5/T6 owners' files).

## DAG

T1 → T2 → T3 → T5 → T6 → T7, with T4 → T6 (T4 may run between T1 and T5 at any point; kept sequential T3→T4 for simplicity). No parallel execution — `scenarios.py` and `app.css` are single-owner hotspots.
