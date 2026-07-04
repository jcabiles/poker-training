# Delta spec — visual game table + feedback readability

**Goal (one line):** replace the drill view's text betting line with a 9-seat oval table (face-down cards, per-seat action chips, hero to-act) and restructure the feedback panel (multi-line tone-colored EV comparison + lede-first reasoning).

Contracts map: `docs/ai-dlc/contracts/game-table-feedback.md` (2026-07-04).
Interview: Gate 1 confirmed 2026-07-04. Branch: `feat/game-table-feedback` stacked on `feat/card-room-polish-ux`.

## Design commitment (inherited — card-room-polish, Gate 1 2026-07-03)

Refined card-room aesthetic (upscale private card room; felt greens, brass/cream, Fraunces/Source Sans 3), dark primary + light, subtle reduced-motion-guarded motion, WCAG 2.2 AA, breakpoints 1440 + 1024, no skeuomorphic casino kitsch, no density loss on drill/grid views.

## Requirements

### F1 — visual game table (drill view)

1. **Backend seat enrichment** (`backend/app/domain/scenarios.py`):
   - Every builder — `build_spot` (all node contexts) AND the three postflop builders `build_cbet_spot`, `build_vs_cbet_spot`, `build_check_raise_spot` (R1: exact name; it exists and is required — used by the vs_check_raise drill mode + SRS rebuild `drill.py:126-129`) — emits **all 9 seats** in `Spot.players`: `UTG, UTG1, UTG2, LJ, HJ, CO, BTN, SB, BB`, each with `status` = `IN` (still in hand) or `FOLDED`.
   - `action_history` gains explicit `FOLD` entries for every seat that had the opportunity to act before hero's decision point and is not in the hand (canonical preflop order; blinds fold only if they faced a raise, i.e. never in these spots unless authored so).
   - **R2 — postflop enrichment is its own sub-task**, not "extend the pattern": the postflop builders hardcode 2-entry player lists (`scenarios.py:309-312, 381-384, 466-469`) with no fold-derivation machinery. They need a shared helper enumerating folded positions (everyone except the opener/caller pairing; SB folds after posting in these HU-SRP spots) + matching preflop FOLD history entries, with its own acceptance test (9 seats, correct FOLD history incl. SB).
   - `spot_signature()` / `srs.py`: **untouched** (verified: preflop path reads neither field; `faced_bet_bucket` filters FOLD out).
2. **`_villain_pos` hardening FIRST** (`backend/app/domain/postflop.py:136-140`): filter to non-hero players with `status == IN`, prefer `spot.facing`; land with regression fixtures (>2 players incl. FOLDED seats) in `backend/tests/test_postflop.py` **before** any builder emits folded seats. Preserve one-seat-per-position invariant (`test_scenarios.py:105,122`).
3. **Frontend table** (`frontend/src/components/PokerTable.tsx`, CSS in `app.css`):
   - Oval ring: 9 seat pods in seating order around an elliptical felt; board + pot dead-center; hero pod enlarged bottom-center with face-up hole cards + "you are to act" affordance.
   - Live villains: two face-down card backs (new optional `faceDown` prop on `Card.tsx` — backward compatible). Folded seats: dimmed pod, "fold" chip, no cards.
   - Per-seat action chip = **latest action only** ("raise 2.5", "calls", "bet 4.1", "fold"); preflop escalation verbs (opens/3-bets/4-bets/jams) may be reused from `bettingLine`'s ladder logic.
   - Dealer button marker on BTN pod.
   - `.line` text betting line **retired** (CSS block `app.css:956-966` standalone — safe). Context header (`.ctx`) and villain-type line stay.
   - `.felt` changes must stay benign for QuizPanel (shared class).
4. Density gate: at 1024×768 the felt + decision bar remain fully visible without scrolling past the decision bar (measure like card-room slice's 900px gate).

### F2 — feedback panel readability

5. **EV comparison block** (`frontend/src/components/FeedbackPanel.tsx`): replace the rendered long verdict sentence with a structured, tone-colored block built from existing fields (`chosen_eval`, `best_action`, `ev_loss_bb`, `correctness`):
   - line 1: your action + frequency + EV; line 2: best action + frequency + EV; line 3: EV given up. Mono/tabular numerics; `≈` prefix convention kept; tone colors from `--good/--warn/--bad` tokens (both themes AA).
   - **R4 — no duplicate numbers**: the block REPLACES the existing `.chosen-eval` line (`FeedbackPanel.tsx:74-80`); the `.verdict-row` badge + EV-loss stat stays as the top-line summary (designer may visually merge it with the block, but EV/frequency figures must each render exactly once in the panel).
   - ARIA contract preserved: `role="status" aria-live="polite" aria-atomic="true"`, mount-focus on Next, Space/N shortcuts untouched.
6. **Backend short lede** (`backend/app/domain/feedback.py:_verdict`): shrink to one plain-language sentence (e.g. "Acceptable — call works here, but fold earns more."). Keep test-pinned substrings: capitalized correctness label, "Best play" (no-decision path), "No strategy content" (fallback path). Numeric detail moves to the FE block; the freq%/≈EV assertions in `test_preflop_tiers_carry_chosen_freq_and_ev` (`test_feedback_tiers.py`) may be amended if the lede drops numbers (tests assert composition, not UX copy). **R5: cite test FUNCTIONS, not line numbers — refuter found the spec's line refs already drifted.**
7. **Reasoning lede-first** (`backend/app/domain/feedback.py:_reasoning`): authored rationale (hand-specific) becomes sentence 1; tag-derived mechanism template follows. All current tests order-agnostic (verified).
   - **R3 — all three branches**: the reorder covers the postflop tag-branch, the preflop shape-branch, AND the exploit-villain branch (`feedback.py:148-156`) — the "Versus a {villain}: {authored_rationale}" sentence moves to the FRONT in exploit mode (it is the hand-specific lede there), not appended last.
8. `tiers?.verdict ?? explanation` FE fallback preserved.

## Files to touch

- `backend/app/domain/scenarios.py` — seat enrichment + fold history
- `backend/app/domain/postflop.py` — `_villain_pos` hardening
- `backend/app/domain/feedback.py` — `_verdict` lede + `_reasoning` reorder
- `backend/tests/` — new/updated fixtures + assertions (test_postflop, test_scenarios, test_feedback_tiers)
- `frontend/src/components/PokerTable.tsx`, `Card.tsx`, `FeedbackPanel.tsx`
- `frontend/src/styles/app.css` (+ `tokens.css` only if new tokens needed — single-owner)
- `frontend/src/api/types.ts` — only if wire shape changes (status field already exists in FE type)

## Out of scope

Turn/river engine · new drill modes · solver EVs · equity-input clamp bug (pre-existing) · mobile breakpoints · quizzes redesign · lessons library · auth/hosting · `srs.py` / `spot_signature()` · RangeGrid · DecisionBar behavior.

## Constraints

Repo invariants (profile): domain core no web/DB imports · results freq+EV never boolean · grading behind async StrategyProvider · strategy in content/ · tokens-only CSS (raw hex only tokens.css) · WCAG AA + visible focus both themes · `spot_signature()` frozen · types.ts hand-maintained · EVs labeled approximate. Auth: none (local app).
Contract map rules: `_villain_pos` fixed before folded seats emitted; `.felt` benign for quizzes; ARIA/live/focus/keyboard contracts preserved; `.tier-deepdive summary` shared with `.concept-card summary`.

## Verify-by

- `./scripts/verify.sh` → "BACKEND VERIFY OK"; `cd backend && ruff check .`; `cd frontend && npm run typecheck && npm run build`.
- Grep gate: no raw hex outside `tokens.css`.
- `design-reviewer` pass at 1440 + 1024, both themes, on: `#/drill` (preflop RFI + vs_RFI graded states), `#/drill/postflop`, `#/drill/vs_cbet`, `#/drill/exploit` — checks: 9 seats correct fold/live states vs `action_history`, hero to-act affordance, EV block contrast (AA), lede-first reasoning rendered, decision bar visible at 1024 without scroll.
- Manual data check: one hand per mode — seat statuses match the betting line the old UI would have shown.

## Refuter findings (2026-07-04, verdict: pass-with-issues — all folded in above)

- **R1 (major)**: spec named nonexistent `build_vs_check_raise_spot` with an "if present" hedge — real name `build_check_raise_spot` (`scenarios.py:416`), required target. → fixed in F1.1.
- **R2 (major)**: postflop builders have no fold-derivation machinery (hardcoded 2-entry lists) — enrichment there is its own sub-task with its own AC. → F1.1 bullet 3.
- **R3 (major)**: `_reasoning` has a THIRD branch (exploit-villain, `feedback.py:148-156`) the reorder description missed — exploit sentence moves to front too. → F2.7.
- **R4 (medium)**: new EV block overlaps existing `.chosen-eval` line + `.verdict-row` EV badge — block replaces `.chosen-eval`; each figure renders once. → F2.5.
- **R5 (minor)**: spec/contract line-number refs already drifted — cite test function names. → F2.6.
- **R6 (minor)**: old PokerTable renders every non-hero player unconditionally (`PokerTable.tsx:33`) — backend enrichment + FE table rewrite must land in the same PR/branch (they do), and the backend ticket's review is tests-only (no design review of the old UI against new data).
- Baseline confirmed green before changes: 240 backend tests + boot probe, FE typecheck clean.
