# Spec — Phase 2a: Flop C-Bet + Foundational Postflop Drills

> Delta spec for **Phase 2a** only (first postflop slice). Builds on Phase 0–1c (no rebuild). Strategy source: `docs/research/02-postflop-strategy.md`. STOP at the plan gate — no code until approved.
> Revised after refuter pass: range sourcing pinned, equity perf de-risked, postflop grading/signature/composite all specified.

## Goal
Enter postflop with the flop **c-bet decision (HU single-raised pots)** graded by **texture + range-advantage heuristics**, plus the two foundational drills (**board-texture classification**, **equity estimation**) on a **pure-Python equity engine**.

## Key de-risking decisions (from refuter)
- **Range advantage in 2a is a POSITIONAL + texture heuristic, NOT equity-backed** (avoids the range-vs-range perf bomb). Equity-backed range advantage → 2b.
- **The equity engine is used only for the equity-estimation drill** (single hero hand vs a range): bounded to ≤ **2000** sampled iterations, its OWN seeded `random.Random` (never shared with spot construction).
- Quiz drills persist as `DrillAttempt` rows (provider `"quiz"`) — **no new table**.

## In scope
1. **Equity engine** `domain/equity.py` (pure Python, no deps):
   - 7-card evaluator: best-5-of-7 → comparable `(category, kickers)`.
   - `equity_vs_range(hero: tuple[str,str], board: list[str], villain_combos, iters, rng) -> float`. Handles `len(board)` ∈ {0,3,4,5}. **Dead-card order:** `dead = set(hero) | set(board)`; filter villain_combos to those disjoint from `dead` BEFORE the loop; each iteration draws the runout from `deck − dead − villain_combo`. Win + tie/2. Deterministic for a fixed `rng` seed.
2. **Texture classifier** `domain/texture.py`: flop → `{wetness, pairing, suitedness, connectedness, high_card}` + a short `texture_class` label (used by the signature) via documented rules.
3. **Postflop heuristics + grader** `domain/postflop.py`:
   - `range_advantage(node_context, hero_pos, villain_pos, texture) -> hero|villain|neutral` — **positional + texture rule** (preflop aggressor has range advantage on high/dry boards; loses it on low/connected boards; OOP penalty). No equity.
   - `grade_cbet(spot, hero_range, villain_range, decision) -> EvaluationResult` — a NEW grader (does NOT reuse preflop `grade()`): from texture + range advantage + the hero hand's made-hand/draw category, recommend check / bet(small|big) with per-action frequencies + a documented proxy EV + correctness thresholds. Outputs the existing `EvaluationResult` shape (per_action over CHECK/BET, freq+EV, leak `FLOP_CBET`, rationale + "why").
4. **CompositeProvider** `domain/providers/composite.py`: routes by `spot.street` — preflop → `HeuristicProvider`, flop → `PostflopHeuristicProvider`. `supports()` = the routed sub-provider's `supports()`; if the routed provider doesn't support → return a `coverage=not_found` result. `get_provider()` returns the composite.
5. **Flop spot builder** `domain/scenarios.py`: build a HU SRP flop spot from a preflop opener×caller pairing — hero = preflop raiser; deal hole cards + a 3-card flop disjoint from hole cards; **set `spot.hero_range` and `spot.villain_range`** (compact range strings, resolved from the preflop content: opener RFI range, caller call range); `street=flop`, `node_context=[CBET]`, legal = check / bet(33%) / bet(75%); `to_act=hero`.
6. **Foundational quiz drills** (persist as `DrillAttempt`, provider `"quiz"`):
   - **Texture classification**: flop → multiple-choice texture labels → graded vs classifier (leak `BOARD_TEXTURE`).
   - **Equity estimation**: hero hand + board + villain-range descriptor → numeric % → graded by **tolerance bands** (OPTIMAL ≤5, ACCEPTABLE ≤10, MISTAKE ≤15, BLUNDER >15 percentage points) vs the equity engine (leak `EQUITY_EST`).
   - New `QuizItem`/`QuizResult` schemas + `/drill/quiz/next` + `/drill/quiz/grade`.

## Contract changes (additive)
- `Spot`: add `hero_range: str | None = None`, `villain_range: str | None = None` (range-notation strings for the flop grader). `NodeContext.CBET`.
- `spot_signature`: **branch by street** — preflop path UNCHANGED (do not append, preserves existing hashes); postflop path = `(variant, format, street, ctx, hero.position, facing, texture_class, spr_bucket)` (excludes exact board + hole cards). Pin SPR buckets: ≤3, 3–6, 6–13, >13.
- `LeakCategory` (postflop 200–299): `FLOP_CBET=200`, `BOARD_TEXTURE=210`, `EQUITY_EST=211`. `leak_category_for` gains a `CBET → FLOP_CBET` case.
- `range_grid` is **preflop-only**: `/drill/next` returns `grid={}` for non-preflop spots (frontend hides it).
- `_next_review`: in 2a, skip postflop SRS reconstruction → fall back to random (postflop review = 2b, needs texture/SPR columns).

## Out of scope (deferred)
- Turn/river, facing a c-bet, check-raise (2b/2c) · multiway · 3-bet-pot postflop · equity-backed range advantage (2b) · postflop SRS review-mode · solver · mastery-gating · squeeze.

## Constraints
Live/simplified · grading behind `StrategyProvider` via `CompositeProvider` · domain pure (equity/texture/postflop) · content as data · **no new migration** (quiz → DrillAttempt) · equity calls bounded + own RNG · CSS tokens + AA contrast (board cards + quiz UI) · any new deps → `RUN-THESE-COMMANDS.md` (target: none).

## Verify-by
1. `pytest` green incl: **equity** correctness (AA vs KK preflop ≈ 0.82 ± tolerance; nut hand = 1.0; a hero crushed = ~0; dead-card filtering removes blocked combos) + determinism with a seed + a perf guard (equity-estimation call < ~150ms at the capped iters); **texture** anchors (A♠K♦2♣ = dry/rainbow/unpaired; 9♥8♥7♥ = wet/monotone/connected); **range-advantage** heuristic (BTN-open vs BB-call on A-high → hero; on 7♥6♥5♣ → neutral/villain); **c-bet grader** anchors (dry + range-adv → small bet OPTIMAL; big bet OOP with air on a wet board → worse); **quiz** grading (texture multiple-choice; equity tolerance bands); postflop `spot_signature` stability (same texture class, different exact board → same signature) AND preflop signatures unchanged; domain purity (equity/texture/postflop).
2. Backend boots; flop c-bet spots grade via the composite provider; `/drill/quiz/*` works; preflop modes + `/drill/next` grid unaffected.
3. Frontend builds; live (Playwright): a flop c-bet spot shows the board + Check/Bet bar + grades; a texture quiz + an equity quiz round-trip.
4. CSS contrast/token check passes.
