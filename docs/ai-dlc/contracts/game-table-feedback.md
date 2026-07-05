# Contracts — game-table overhaul + feedback readability

Mapped 2026-07-04 by contract-mapper (read-only) ahead of the game-table/feedback slice.
Scope: `Spot.players`/`action_history` consumers, feedback tier composition, PokerTable/FeedbackPanel/Card markup+CSS+ARIA contracts.

## 1. Spot.players / action_history / to_act / facing

- `players` today is ALWAYS "hero + currently-live villains", never FOLDED/ALLIN. `PlayerStatus.FOLDED`/`ALLIN` (`backend/app/domain/spot.py:57-60`) are **dead code** — zero call sites set `status=`. Adding folded seats is net-new territory.
- **Sharpest hazard — `_villain_pos`** (`backend/app/domain/postflop.py:136-140`): returns the **first non-hero entry in `spot.players`**, `spot.facing or BB` fallback only if none. Call sites that would silently break if folded seats precede the real villain:
  - `grade_cbet` (`postflop.py:330,333`) — no facing fallback at all.
  - `grade_vs_check_raise` (`postflop.py:705,711`) — comment at `:702-704` already flags fragility.
  - `grade_vs_cbet` (`postflop.py:527`) is safe: `spot.facing or _villain_pos(spot)`, facing always set.
  - Every builder constructs `players` as exactly `[hero, villain]` in order (`scenarios.py:309-312, :381-384, :466-469`); postflop test fixtures mirror this (`backend/tests/test_postflop.py:42-45,176,275`). No test covers >2 players or folded seats.
  - **Rule: fix `_villain_pos` to filter by status/facing BEFORE any builder emits FOLDED seats**, and add fixture coverage.
- `action_history` never contains FOLD today. Consumers:
  - `srs.py:96-102` `faced_bet_bucket` filters to BET/RAISE — FOLD entries safe (filtered out).
  - `PokerTable.tsx:6-30` `bettingLine` ignores fold/post — being replaced anyway.
- **`spot_signature()` preflop path reads neither `players` nor `action_history`** (`srs.py:48-68`); postflop path touches history only via `faced_bet_bucket` (fold-safe). **Do not touch `srs.py`.**
- Position-uniqueness: `scenarios.py:130-133` `add()` dedupes by Position; tests pin one-seat-per-position (`test_scenarios.py:105,122`). Folded-seat injection must preserve uniqueness.
- `to_act`/`facing` lookups key off `hero.position`+`facing` (`grading.py:112`, `content/registry.py:37`) — unaffected by players/history shape.

## 2. feedback.py tiers / authored rationale

- `compose_tiers` (`feedback.py:177-185`) builds tiers purely from `EvaluationResult` fields; never parses `explanation`.
- `_verdict` (`feedback.py:89-106`): tests assert **substrings only** — `%`/`≈{ev}bb` present (`test_feedback_tiers.py:41-42`), "Blunder"/"Mistake" (`:52`), "Best play" (`:140`), "No strategy content" (`:131`). Restructuring/shortening safe if correctness label (capitalized), freq %, and ≈EV substrings survive.
- `_reasoning` (`feedback.py:109-157`): order today = tag-derived mechanism → `authored_rationale` appended. All tests are containment, order-agnostic → **lede-first reorder is a safe seam.** Output is one flat `" ".join(parts)` string — no structural boundary for FE to split on; multi-line FE reasoning would need a new backend field, not a reorder.
- FE consumers: `FeedbackPanel.tsx:73` `tiers?.verdict ?? explanation` (fallback contract must survive), `:83` reasoning, `:87` deep_dive. `authored_rationale` reaches UI only via `tiers.reasoning`.
- Content path intact regardless: `Entry.rationale` → providers set `result.authored_rationale` (`heuristic.py:51,67`; `postflop.py:382,421,573,611,752,794`) → `_reasoning`.
- New structured fields (e.g. chosen/best EV lines) = new `FeedbackTiers` field → update `backend/app/domain/evaluation.py:48` + hand-maintained `frontend/src/api/types.ts:50-54` together.

## 3. PokerTable / FeedbackPanel / CSS / ARIA / keyboard

- `PokerTable.tsx:33,46-51` already renders non-hero players as `.seat` chips — planned change extends the pattern.
- CSS contracts (`frontend/src/styles/app.css`):
  - `.felt` (`:100-116`) tokens-only; **shared with QuizPanel** (comment `:98-99`) — table-wide `.felt` rules must stay benign for quizzes.
  - `.seats`/`.seat`/`.seat .pos`/`.seat .stack` (`:123-151`) — no hero/status styling hook exists yet.
  - `.line` (`:956-966`) standalone — safe to retire.
  - `.card` structure (`:203-233`): `<span class="card"[ red]><span class="r"><span class="s">` — face-down variant must not collide with `.red` or the r/s child spans. Hero-hand tilt `:186-191` applies to `.cards` only, not `.board`.
  - `.feedback` tone `-bg` classes (`:377-389`) reused by `.quiz-result` (`:1048`) — keep `good-bg`/`warn-bg`/`bad-bg` + `.badge`.
  - `.verdict-row`/`.tier-verdict`/`.tier-reasoning`/`.tier-deepdive` (`:393-463`); `.tier-deepdive summary` shared with `.concept-card summary` (`:442-456`).
- ARIA/live contract: `role="status" aria-live="polite" aria-atomic="true"` (`FeedbackPanel.tsx:59-61`) — panel announcement on grade; must survive restructure.
- Focus contract: mount-only effect autofocuses Next (`FeedbackPanel.tsx:23,30-32`) — valid only while panel mounts fresh per result.
- Keyboard: global Space/N handler `App.tsx:172-197` (guarded `:174-182`); DecisionBar roving tabindex (`DecisionBar.tsx:34-48`) — do not touch. Next button `aria-label` documents Space shortcut (`FeedbackPanel.tsx:117`).

## 4. Card.tsx

`Card.tsx:3-13` — required `card: string` (2-char). Face-down needs new **optional** prop (`faceDown?: boolean`); all call sites pass real cards → backward compatible.

## Integration points

| Data | Producer | Consumer | file:line |
|---|---|---|---|
| `Spot.players` | scenarios builders | `postflop._villain_pos` | `postflop.py:136-140` |
| `Spot.players` | scenarios builders | PokerTable seats | `PokerTable.tsx:33,46-51` |
| `Spot.action_history` | scenarios builders | `srs.faced_bet_bucket` | `srs.py:90-104` |
| `Spot.action_history` | scenarios builders | `PokerTable.bettingLine` | `PokerTable.tsx:6-30` |
| `Spot` (whole) | `drill.py:230` | FE `types.ts:19-38` | hand-maintained |
| `authored_rationale` | providers | `feedback._reasoning` | `feedback.py:125-151` |
| `tiers` | `compose_tiers` | FeedbackPanel | `FeedbackPanel.tsx:73,83,87` |
| Space/N key | `App.tsx:183-187` | `onNext` | `FeedbackPanel.tsx:112-120` |

## Safe seams

- Additive `PlayerState` fields (status set to FOLDED, or `last_action`) — safe IF `_villain_pos` fixed first + postflop fixtures extended.
- `Card.tsx` optional `faceDown` prop — fully backward compatible.
- `.line` CSS block retire — standalone.
- `_reasoning` lede-first reorder — passes all current tests; multi-line reasoning needs a new field (design decision).
- `_verdict` shorten/restructure — safe while label/freq/≈EV substrings remain; structured EV lines = new `FeedbackTiers` field + types.ts update.
