# Spec — Phase 2e-1: Facing a Flop Check-Raise

> Delta spec for **Phase 2e-1** only. Builds on 2a–2c + 2e-0 (no rebuild, no new migration). The
> other side of the 2a c-bet spot: hero c-bet the flop, defender check-raised, hero (the ORIGINAL
> aggressor) now decides **fold / call / raise (4-bet)**. Closes the flop c-bet loop before turn
> play (2f). Strategy source: `docs/research/02-postflop-strategy.md` §4.4 (check-raise sizing) +
> §10.3 (live $1/$2 check-raise psychology — reused as-is; no new research needed per Gate 1
> confirmation). STOP at the plan gate — no code until approved.
> Revised after refuter pass: `range_advantage()`'s third argument is villain's position (not
> "aggressor_pos" — hero is the aggressor here, a naming risk the refuter caught), the builder's
> `CALL` sizing is now the incremental delta (matching the `VS_3BET`/`VS_4BET` precedent, not the
> check-raise's raw total), a `raise_mult` param mirrors `build_vs_cbet_spot`'s `cbet_frac`, and the
> betting-line verb counter needs a street-scoped fix so a flop check-raise doesn't inherit "3-bets"
> from the preflop open.

## Goal
Add the **facing-a-check-raise decision** (HU SRP, hero = the flop c-bettor, defender check-raised)
graded by **hand category + a check-raise-strength prior + texture-conditioned bluff plausibility**,
with a `vs_check_raise` drill mode and frontend. Same heuristic family as 2a/2b — NOT equity-backed.

## Key decision (from Gate 1 interview)
- **Live $1/$2 check-raises are rarely bluffs** (research §10.3: "check-raises almost universally
  mean a very strong hand... unless you have a strong draw or big hand, fold"). This is a **stronger,
  more independent prior than `range_advantage`/`range_advantage_defender`** — a check-raise is new
  information (the defender chose to raise, not just call), not just a static board read. The merit
  function's fold baseline must be meaningfully higher than `grade_vs_cbet`'s (0.6) to reflect this.
  Texture still modulates it: check-raise bluffs are more plausible on low/connected/wet boards
  (§4.4: "best on low-connected two-tone boards... on rainbow dry boards, check-raise bluffs are rare
  and risky") — texture shifts the fold/call balance, but never overrides a clear air-hand fold on a
  dry board.
- **Raise (4-bet) is sized, not jam-only** (Gate 1 confirmed): mirrors 2b's `RAISE` shape
  (`min_bb`/`max_bb`), consistent with every other decision in the app being frequency-graded, not
  binary.
- **`range_advantage()` (2a's aggressor-view function) is reused for context**, not
  `range_advantage_defender()` — hero is still the original preflop+flop aggressor here; the new
  factor layered on top is the check-raise-strength prior, not a fresh who-has-the-edge computation.

## In scope
1. **Contracts (additive):** `NodeContext.VS_CHECK_RAISE = "vs_check_raise"` (facing a check-raise
   as the original bettor — distinct from `VS_CBET`, which is facing a bet, not a raise-after-my-bet).
   `LeakCategory.VS_CHECK_RAISE = 202` (postflop 200-299 namespace; next free slot after 201). Bump
   `TAXONOMY_VERSION`. `leak_category_for` gains a `VS_CHECK_RAISE → VS_CHECK_RAISE` case.
   `_postflop_signature` needs a `faced_bet_bucket` value for this node too — reuses the 2e-0-fixed
   `faced_bet_bucket()` unchanged (it now reads the current `CALL` legal-action amount, which works
   identically for "facing a raise" as it does for "facing a bet").
2. **Grader** `domain/postflop.py::grade_vs_check_raise(spot, hero_range, villain_range, decision) ->
   EvaluationResult`:
   - Inputs: board (flop only, `spot.board[:3]`), hero hole cards, the faced check-raise size + pot
     (via `_faced_call_and_pot`, reused unchanged from 2b), `hero_range` (hero's own RFI/opening
     range — hero is the aggressor here), `villain_range` (defender's blind-defense/calling range).
   - Compute `texture`, `adv = range_advantage(ctx, spot.hero.position, _villain_pos(spot), texture)`
     (2a's function, reused **with the existing `_villain_pos(spot)` helper** — the third argument is
     villain's/the check-raiser's position, NOT hero's own; hero is the aggressor being graded here,
     and passing hero's own position for both args would corrupt `_in_position()`'s IP/OOP read),
     hero `_hand_category` (2e-0-fixed version — this grader's `weak_made`/`strong` split for top pair
     vs. two-pair+ only works correctly once that fix lands), and pot odds (`faced_raise / pot`).
   - New merit function `_merits_vs_check_raise(value, adv, price, texture, cat)` (mirrors
     `_merits_vs_cbet`'s shape but with the higher fold baseline + texture-conditioned bluff
     plausibility described above): recommend **fold / call / raise (4-bet)** with per-action
     frequency + a documented PROXY EV + correctness, output as the existing `EvaluationResult`
     shape (per_action over FOLD/CALL/RAISE, freq+EV, leak `VS_CHECK_RAISE`, rationale + "why").
     Heuristic shape (`cat` values per 2e-0's corrected `_hand_category`: `strong` now means
     two-pair/set/made-straight/made-flush ONLY — plain top pair is `weak_made`):
     - **strong** (two-pair+/set/made straight/made flush) → raise (value 4-bet) / call mix; never
       fold.
     - **draw** (combo draws — FD+OESD, or FD+pair) → call; raise (semibluff jam-ish sizing) only on
       low-connected-wet boards where check-raise bluffs are plausible.
     - **weak_made** (top pair any kicker, or a weaker pair) → fold-leaning; call only vs a small
       check-raise on a dry, aggressor-favored board where a bluff-catch is defensible.
     - **air** → fold by default; the higher fold baseline should make this close to universal except
       on very wet/connected boards with genuine backdoor value.
3. **Provider routing** `domain/providers/postflop.py`: `PostflopHeuristicProvider.supports()`
   accepts `CBET`, `VS_CBET`, or `VS_CHECK_RAISE` (still gated to `Street.FLOP` per 2e-0's fix);
   `evaluate()/optimal()` dispatch adds a `VS_CHECK_RAISE → grade_vs_check_raise` arm.
4. **Spot builder** `domain/scenarios.py::build_check_raise_spot(rng, pairing=None, eff_bb=100.0,
   raise_mult=None)`** — extends the existing `build_cbet_spot()` flow: after hero's c-bet
   (`cbet`), the defender check-raises to a total of `raise_to = raise_mult * cbet` (`raise_mult`
   defaults to `rng.choice([2.5, 3.0])` per research §4.4; **explicit param added so tests can
   construct a specific small vs. big check-raise**, mirroring `build_vs_cbet_spot`'s `cbet_frac`
   pattern) — new `HistoryAction` with `ActionType.RAISE`, `amount_bb=raise_to`. `pot_bb` recomputed
   as `flop_pot + cbet + raise_to` (matches the "pot includes everything committed so far" convention
   from `build_vs_cbet_spot`). **`legal_actions.CALL.min_bb = round(raise_to - cbet, 2)`** — the
   INCREMENTAL amount hero owes, NOT `raise_to` itself (hero already has `cbet` invested this street;
   this matches the existing `VS_3BET`/`VS_4BET` builder precedent — `CALL.min_bb = tbet - osize` —
   not `build_vs_cbet_spot`'s zero-prior-investment shortcut, which would double-count hero's own
   c-bet if copied naively here). `legal_actions.RAISE.min_bb ≈ 3x raise_to` (a further 4-bet),
   `max_bb = remaining stack`. `node_context=[VS_CHECK_RAISE]`; `facing` = defender's position (the
   check-raiser); `to_act = hero` (still the original aggressor); `hero_range`/`villain_range` reused
   from the same preflop-content lookup as `build_cbet_spot`. A `sample_check_raise_spot()`.
5. **Drill wiring** `api/v1/drill.py`: `/drill/next?mode=vs_check_raise` → `sample_check_raise_spot`
   (grid `{}`, like all postflop). `/drill/grade` already routes through the composite provider — no
   change. `_rebuild_postflop`/`_POSTFLOP_CTX` gain a `VS_CHECK_RAISE` branch so SRS review can
   reconstruct this archetype (mirrors the existing `CBET`/`VS_CBET` branches).
6. **Frontend:** add a **"Facing check-raise"** drill mode; betting-line rendering needs to show
   "hero bets X, villain raises to Y". **Refuter-caught bug:** `bettingLine()`'s raise-verb escalation
   counter (`opens → 3-bets → 4-bets → ...`) increments across the ENTIRE `action_history`, not
   per-street — a check-raise spot's full history (preflop open → call → flop bet → flop raise) hits
   the flop `RAISE` with the counter already at 1 (from the preflop open), rendering it as "3-bets"
   instead of a check-raise. **Fix:** reset the raise counter per street inside `bettingLine()` (or
   special-case a flop-street `RAISE` with its own verb, e.g. "raises to"/"check-raises to"). Decision
   bar already handles fold/call/raise (2b).

## Contract changes
- `NodeContext.VS_CHECK_RAISE = "vs_check_raise"` (additive).
- `LeakCategory.VS_CHECK_RAISE = 202` (additive; postflop 200-299 namespace).
- `leak_category_for`: `VS_CHECK_RAISE → LeakCategory.VS_CHECK_RAISE` (additive).
- No `_postflop_signature` shape change — `faced_bet_bucket` (fixed in 2e-0) already generalizes to
  "facing a raise" without a new bucket dimension. No migration.

## Out of scope (deferred)
Turn/river · multiway · equity-backed range advantage · facing a 3-bet-raise (hero re-raises,
defender re-raises again) · donk-betting lines · solver · mastery-gating.

## Constraints
Live/simplified · grading behind `StrategyProvider` via the composite · domain pure · no equity calls
in the grader (hand-category + pot-odds + check-raise-strength-prior only, same family as 2a/2b) ·
content reused from existing preflop packs (no new content files) · no new migration · CSS tokens +
AA contrast (any new UI) · any new deps → `RUN-THESE-COMMANDS.md` (target: none).

## Verify-by
1. `pytest` green incl.:
   - **grader anchors** — (a) strong hand (set/two-pair) vs a check-raise → raise or call, never
     fold; (b) pure air on a high/dry board vs a check-raise → fold is the clear best action; (c) a
     combo draw on a low-connected-wet board → call, with raise (semibluff) a defensible mix; (d)
     **fold-baseline check**: for a fixed marginal (`weak_made`) hand + a DRY board, fold frequency
     here must be higher than the analogous `grade_vs_cbet` spot's fold frequency for the same hand
     category + texture (the check-raise-strength prior is doing real work, not a no-op); (e) leak =
     `VS_CHECK_RAISE (202)`.
   - **`_hand_category` integration** — a made flush/straight (fixed in 2e-0) correctly reads as
     `"strong"` here, not `"draw"`; **plain top pair (any kicker) reads as `weak_made`, not `strong`**
     (the specific 2e-0 fix this grader's fold-leaning design depends on) — both exercised from this
     grader's call site, not just `_hand_category`'s own unit tests.
   - **Builder:** valid flop check-raise spot; hero = original aggressor (`is_hero`); defender's
     `RAISE` in `action_history`; `spot.facing` = defender; legal = fold/call/raise; **`CALL.min_bb`
     equals the incremental delta (`raise_to - cbet`), not `raise_to` itself** — assert this
     explicitly, it's the refuter-caught sizing bug; raise has a concrete `min_bb`; cards disjoint;
     `pot_bb == flop_pot + cbet + raise_to`.
   - **Signature:** stable across same-texture/different-board; **distinguishes a 2.5x from a wider
     (e.g. 4x) check-raise across at least two different `cbet` baselines** (via the 2e-0-corrected
     `faced_bet_bucket`, using the builder's `raise_mult` param — a single baseline can pass by
     coincidence per the refuter's trace); preflop signatures untouched.
   - **Provider:** `vs_check_raise` spots grade via the postflop provider; 2a/2b spots unaffected.
2. Backend boots; `/drill/next?mode=vs_check_raise` returns a valid spot that grades + persists; 2a/2b
   postflop + preflop modes + quizzes unaffected.
3. Frontend builds + typechecks; live (Playwright): the Facing-check-raise mode shows the board +
   "hero bets X, villain raises to Y" line + Fold/Call/Raise bar + grades with a sane "why".
4. CSS contrast/token check passes (no raw hex in new CSS).
