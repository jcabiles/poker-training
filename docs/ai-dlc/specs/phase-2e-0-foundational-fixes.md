# Spec — Phase 2e-0: Foundational Fixes (pre-turn/river)

> Delta spec for **Phase 2e-0** only. Builds on 2a–2c (no rebuild, no new migration). Pure technical
> debt paydown — fixes 5 flop-hardcoded/buggy call sites identified by the `contract-mapper` scan
> (`docs/ai-dlc/contracts/postflop-turn-river.md`) before any turn/river grading logic is built on
> top of them. No new user-facing feature. STOP at the plan gate — no code until approved.
> Revised after refuter pass: `faced_bet_bucket` is now raise-aware (not just call-vs-bet-aware),
> `_hand_category`'s top-pair-vs-two-pair conflation is in scope, and the `test_signature.py` fixture
> break the rewrite would otherwise cause is now an explicit owned-file.

## Goal
Make the postflop domain layer safely street-aware (fail loud instead of silently truncating) and
fix two live correctness bugs in the already-shipped 2a/2b graders, so 2e-1 onward can build on a
correct foundation instead of inheriting silent bugs.

## Why now (not deferred to 2f)
`CompositeProvider`/`PostflopHeuristicProvider` today accept any `Spot` with `len(board) >= 3` and
grade it via the flop-only `grade_cbet`/`grade_vs_cbet` — a turn/river spot would be silently
truncated to its flop and graded as if the extra card didn't exist, with no error. Two of the five
fixes below (`faced_bet_bucket`, `_hand_category`) are also load-bearing for 2e-1 (facing a flop
check-raise), which ships in the same session — see "2e-1 dependency" below.

## In scope

1. **`domain/srs.py::faced_bet_bucket()`** — currently scans the ENTIRE `action_history` for the
   largest `ActionType.BET`, missing `ActionType.RAISE` entirely and breaking once a hand has bets
   on multiple streets. **Rewrite to read the CURRENT decision point** from `spot.legal_actions`
   (the amount hero must call right now, `faced = CALL.min_bb`) — but the "pot before the bet"
   denominator is NOT simply `pot_bb - faced` once hero has prior investment on the current street
   (a check-raise, where hero already put in `cbet` this street before villain raised). Refuter
   traced this precisely: naively reusing the c-bet formula for a raise silently miscomputes the
   pre-bet pot, giving an inconsistent small/big boundary. **Correct, general formula:**
   ```
   faced = CALL.min_bb from legal_actions   (0 / "none" if hero has no CALL option — hero is the bettor)
   hero_prior_this_street = sum(h.amount_bb for h in action_history
                                  if h.street == spot.street and h.position == spot.hero.position
                                  and h.action in {BET, RAISE})
   pre_bet_pot = spot.pot_bb - faced - hero_prior_this_street
   bucket = "small" if faced <= 0.5 * pre_bet_pot else "big"
   ```
   For a first bet (vs_cbet), `hero_prior_this_street == 0`, so this reduces exactly to today's
   formula — byte-identical behavior there. For a check-raise (vs_check_raise), it correctly
   recovers the pot the raise is sized against. Works for any facing action (`BET` or `RAISE`).
   **2e-1 dependency:** without this fix, a small vs. big check-raise would collapse into the same
   SRS bucket (today's function doesn't see `RAISE` actions at all) — AND, per the refuter's trace,
   a naive "just read `CALL.min_bb`" fix without the `hero_prior_this_street` term would still
   produce an inconsistent small/big boundary rather than actually fixing the bucketing.
   **Owned test fixture fix (refuter-caught):** `tests/test_signature.py::_vs_cbet_spot()` builds its
   Spot without setting `legal_actions` at all — post-rewrite, `faced_bet_bucket` would find no
   `CALL` action and return `"none"` for every case, collapsing
   `test_faced_bet_size_changes_signature`'s `small != big` assertion to a hard failure. Add
   `legal_actions=[LegalAction(action=CALL, min_bb=cbet)]` to that local fixture helper as part of
   this ticket (matches `build_vs_cbet_spot`'s existing pattern — `test_review.py`'s fixtures already
   go through the real builder and are unaffected).

2. **`domain/postflop.py::_hand_category()`** — THREE bugs, same function (the third found by the
   refuter pass, more consequential than the first two):
   - **Top pair and two-pair/set are both bucketed `"strong"` today** — `if made >= 2: return
     "strong"` catches `made == 2` (ANY top pair, no kicker concept at all) identically to `made == 3`
     (two-pair/set). This is a **live bug already affecting shipped 2b**: the refuter traced a real
     top-pair-vs-big-c-bet spot where `grade_vs_cbet` recommends "never fold" because the category is
     `"strong"`, contradicting the research doc's own guidance that top pair with a marginal kicker
     should sometimes fold to big aggression. **Fix:** demote plain top pair (`made == 2`) to
     `"weak_made"` (joining `made == 1`); reserve `"strong"` for `made >= 3` (two-pair/set) or a made
     straight/flush (below). This is a deliberate, verifiable behavior CHANGE for top-pair hands in
     the existing 2a/2b graders, not a no-op — see Constraints.
   - Never checks for a MADE straight or flush at all. A monotone-flop made flush (e.g. board
     `Ah-Kh-2h`, hero `Qh-Jh`) or an already-made straight scores `made=0` from the pair logic and
     falls through to the `flush_draw`/`oesd` flags, misclassifying it as `"draw"` instead of
     `"strong"`. **Fix:** add explicit made-straight (5 consecutive distinct ranks present across
     hole+board) and made-flush (≥5 cards of one suit present) checks that return `"strong"` directly,
     evaluated BEFORE the pair-based tiers.
   - The `flush_draw`/`oesd` flags don't distinguish "4 of a suit" (drawing) from "5+ of a suit"
     (made) — same conflation for straights (the 4-in-a-window check fires even when a 5th card
     completing it is already present). Once the made-straight/made-flush checks above run first,
     `flush_draw`/`oesd` only need to fire for the genuinely-not-yet-made case, which is already true
     by construction (they're only reached if the made-hand checks didn't already return).
   - **2e-1 dependency:** the check-raise grader (2e-1) calls `_hand_category` for hero's continuing
     range — an unfixed made-hand-as-draw miscategorization would make hero over-fold real value, and
     the top-pair fix directly enables 2e-1's `weak_made` ("fold-leaning") design for plain top pair
     facing a check-raise.

3. **`domain/texture.py::classify()`** — currently silently truncates any board to `board[:3]`
   regardless of the caller's intent. **Fail loud instead of silently wrong**: keep `classify()`'s
   contract as "classifies exactly the first 3 cards it's given" (rename its doc to say so
   explicitly) and make every call site pass `spot.board[:3]` deliberately (already true at 2 of 5
   sites; the other 3 get fixed below). Do NOT attempt turn/river-aware texture classification here —
   that's a genuine new-feature design question for 2f/2h (does a turn spot need "flop texture" +
   "did the turn shift range advantage," or a wholly new 4/5-card texture scheme?), not a bug fix.
   Deferred explicitly to keep this ticket's scope mechanical.

4. **`domain/providers/postflop.py::PostflopHeuristicProvider.supports()`** — currently
   `len(spot.board) >= 3`, accepting 4/5-card boards. **Add an explicit street guard**:
   `supports()` returns `False` (→ `Coverage.NOT_FOUND` via `CompositeProvider`) for any spot where
   `spot.street not in (Street.FLOP,)` until a turn/river-specific provider exists in 2f+. This turns
   today's silent-wrong-grade into an honest "not covered yet" — the correct interim contract.

5. **`services/review.py::_postflop_archetype()`** and **`api/v1/drill.py::_rebuild_postflop`'s
   `_key` closure** — both independently call `classify(spot.board)` without slicing, inheriting the
   truncation. Fix both to call `classify(spot.board[:3])` explicitly (same fix as #3, applied at
   its other 2 call sites, so all 5 identified sites are now consistent).

## Out of scope (deferred)
Turn/river-aware texture classification (genuine new design, → 2f/2h) · new leak categories (none
needed — no new grader here) · any new `NodeContext` (→ 2e-1) · migration (none needed — no schema
change).

## Constraints
Domain stays pure (no web/DB imports) · **`_hand_category`'s output DELIBERATELY changes for three
input classes** (made flush → `"strong"`, made straight → `"strong"`, plain top pair → `"weak_made"`
instead of `"strong"`) — all other hand categories must produce byte-identical results, and each
changed class needs its own explicit Verify-by anchor (not just "tests stay green") since existing
2a/2b fixtures that happen to use top-pair or made-flush/straight hands will change their expected
`correctness`/`ev_loss_bb` output · `faced_bet_bucket`'s rewrite must be byte-identical to today's
behavior for `hero_prior_this_street == 0` (every existing vs_cbet case) · `test_signature.py`'s
local `_vs_cbet_spot()` fixture gets a `legal_actions` field added (see item 1) — this is a required
test-file change, not an incidental one · `test_review.py`'s fixtures are unaffected (already go
through the real builders) · no persisted-hash / signature-shape risk (no new bucket dimension).

## Verify-by
1. `pytest` green incl.:
   - **`faced_bet_bucket`**: a spot facing a `RAISE` (check-raise, hero has prior street investment)
     buckets by the corrected formula (verify against a hand-computed expected ratio, not just "it
     runs") and differentiates a 2.5x vs. a wider check-raise across **at least two different
     cbet-size baselines** (refuter-flagged: a single baseline can pass by coincidence); a spot facing
     a first `BET` (`hero_prior_this_street == 0`) produces byte-identical output to today.
   - **`_hand_category`**: a monotone-flop made flush → `"strong"` (not `"draw"`); a made straight →
     `"strong"`; plain top pair (any kicker) → `"weak_made"` (not `"strong"` — explicit regression
     anchor for the refuter-caught bug); an unchanged flush-draw (exactly 4 of a suit, no 5th) →
     still `"draw"`; two-pair/set → still `"strong"`; existing 2a/2b anchor tests that don't touch
     top-pair/made-flush/made-straight hands stay green byte-for-byte.
   - **`grade_cbet`/`grade_vs_cbet` regression**: re-run their existing anchor fixtures; any fixture
     using a top-pair or made-flush/straight hero hand gets its expected `correctness`/`ev_loss_bb`
     updated to the corrected (intentionally different) output, with a comment noting why.
   - **`supports()`**: a `Street.TURN`/`Street.RIVER` spot with `CBET`/`VS_CBET` context now returns
     `Coverage.NOT_FOUND` instead of a silently-wrong grade; flop spots unaffected.
   - **`test_signature.py::_vs_cbet_spot()`**: updated fixture (adds `legal_actions`) — confirm
     `test_faced_bet_size_changes_signature` still asserts `small != big` and passes.
   - **regression**: full existing 2a/2b/2c test suite stays green after the above expected-output
     updates — this ticket changes no signature shape, no schema, no new tables.
2. `scripts/verify.sh` → `BACKEND VERIFY OK`.
