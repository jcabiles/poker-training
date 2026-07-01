# Contract scan — postflop domain, turn/river extension

> Read-only scan by the `contract-mapper` sub-agent, ahead of Inception for epics 2e–2k
> (turn/river/multiway/full-hand). Scope: `backend/app/domain/{spot,texture,postflop,scenarios,srs,leaks}.py`,
> `backend/app/domain/providers/{composite,postflop}.py`, `backend/app/api/v1/drill.py`,
> `backend/app/schemas/drill.py`, `backend/app/services/review.py`, plus the locked tests in
> `backend/tests/{test_signature,test_review,factories}.py`.

## Top-line finding

There is **no street-level dispatch anywhere past preflop today**. `CompositeProvider._route()`
sends flop, turn, and river spots to the exact same `PostflopHeuristicProvider` instance
(`domain/providers/composite.py:42-43`), which further routes only on
`NodeContext.VS_CBET in spot.node_context` vs. everything else
(`domain/providers/postflop.py:28-30`), gated only by `len(spot.board) >= 3`
(`domain/providers/postflop.py:21-26`). A turn/river `Spot` tagged `CBET`/`VS_CBET` today would be
**silently accepted** and graded by `grade_cbet`/`grade_vs_cbet`, both of which do
`board = spot.board[:3]` (`domain/postflop.py:184`, `:363`) — the turn/river card is **silently
discarded**, producing a plausible-but-wrong `EvaluationResult` with no error, no
`Coverage.NOT_FOUND`. `texture.classify()` never raises for boards >3 cards — it does
`cards = board[:3]` (`domain/texture.py:35`) unconditionally. This silent-truncation behavior is
duplicated at **five independent call sites** (`postflop.py:184`, `postflop.py:363`, `srs.py:96`,
`services/review.py:30`, `api/v1/drill.py:111`), all of which must change together.

## (a) Behavioral contracts that must not break

1. **Preflop signature branch is byte-locked.** `spot_signature()` (`srs.py:48-68`) has a hard
   `if spot.street != Street.PREFLOP: return _postflop_signature(spot)` gate at line 49 — the
   preflop path (51-68) is explicitly untouchable. All turn/river work goes through the postflop
   branch only.
2. **Postflop signature tuple is a persisted-data contract, not just a test contract.**
   `_postflop_signature()` (`srs.py:88-109`) hashes
   `[variant, format, street, ctx, hero.position, facing, texture_class, spr_bucket, faced_bet_bucket]`.
   `street` is already in the tuple, so reusing `NodeContext.VS_CBET` for a turn barrel-defense spot
   won't collide with the flop version. But if a new bucket dimension (e.g. a "scare card" flag) is
   added, it must be appended **conditionally for turn/river only** — otherwise every existing flop
   `SRSItemRow.signature` changes, orphaning persisted SM-2 history (`session.get(SRSItemRow, sig)`
   in `services/review.py:45` stops finding old rows). The golden tests in `test_signature.py`
   (97-187) won't catch this — they only compare fixture pairs against each other, not against a
   fixed hash value.
3. **`faced_bet_bucket()` scans the ENTIRE `action_history`, not the current street.**
   (`srs.py:78-81`) — `max(bets)` picks the largest bet in the whole hand. Correct today only
   because a flop `vs_cbet` spot has exactly one `BET` in history. Breaks the moment a turn/river
   spot has both a flop bet and a turn bet. Contrast with `postflop._faced_call_and_pot()`
   (`postflop.py:316-322`), which correctly reads the CURRENT node's `spot.legal_actions` — the
   reusable pattern to follow instead.
4. **`range_advantage(node_context, hero_pos, villain_pos, texture)` has a dead parameter.**
   (`postflop.py:61-84`) — `node_context` is accepted but never referenced in the body. Tagging a
   spot with a new "2nd barrel" node context will NOT change range-advantage behavior unless the
   function body is rewritten.
5. **`_hand_category()` conflates made hands with draws** once 4+ cards of a suit/run are visible
   (`postflop.py:117-119`). Rare/harmless on the flop; breaks river value-betting and
   bluff-catching, which need "made nuts" vs "still drawing" distinguished.
6. **`_rebuild_postflop()` only understands two node contexts** (`api/v1/drill.py:82-119`) — anything
   else returns `None` and `_next_review` (122-142) silently falls back to random rather than
   erroring. New turn/river node contexts need an explicit branch or SRS review silently degrades.
7. **`_rebuild_postflop`'s `_key` closure calls `classify(s.board).texture_class` directly**
   (`api/v1/drill.py:110-111`), bypassing `spot_signature` — inherits the same 3-card truncation.
8. **Provider `supports()` gate is board-length-permissive, not street-aware**
   (`domain/providers/postflop.py:21-26`): `len(spot.board) >= 3` passes 4/5-card boards through.
9. **Correctness thresholds are flop-tuned, not generic.** `POST_ACCEPTABLE_MAX`,
   `POST_MISTAKE_MAX`, `POST_MIX` (`postflop.py:44-46`) are commented "tuned for the c-bet node" —
   mechanically reusable but need their own calibration for turn/river.
10. **`NextDrillResponse.grid` is already correctly street-gated** (`api/v1/drill.py:171-173`) — the
    precedent for how new street-aware branches should look.
11. **Schema/wire-contract layer needs zero changes.** `Spot`, `Decision`, `EvaluationResult` are
    reused directly as wire DTOs; `Street.TURN`/`Street.RIVER` already exist (`spot.py:41-45`),
    `HistoryAction.street` is per-action, `board`/`action_history` are unbounded lists.

## (b) Integration points a turn/river slice must touch

- `domain/spot.py` — `NodeContext` enum (63-78): only `CBET`/`VS_CBET` exist.
- `domain/texture.py` — `classify()` (31-87): single source of `Texture`.
- `domain/postflop.py` — `grade_cbet` (181-268), `grade_vs_cbet` (360-443), `range_advantage` (61-84),
  `range_advantage_defender` (288-313), `_hand_category` (94-127), `_merits`/`_merits_vs_cbet`
  (130-162, 325-357), `_bet_sizes` (174-178), `_faced_call_and_pot` (316-322) — new graders live here.
- `domain/scenarios.py` — `build_cbet_spot` (259-313), `build_vs_cbet_spot` (325-383), `_blinds`/
  `_raise` helpers (reusable), `_CBET_PAIRINGS`, `_find_entry`/`_combos_for`.
- `domain/srs.py` — `spot_signature`/`_postflop_signature` (48-68, 88-109), `spr_bucket` (36-45,
  reusable), `faced_bet_bucket` (71-85, buggy for multi-street).
- `domain/leaks.py` — `LeakCategory` (18-46): postflop 200-299 uses 200/201/210/211; 96 numbers free.
  Bump `TAXONOMY_VERSION` (line 15) per the module's own rule.
- `domain/providers/composite.py` — `CompositeProvider._route` (42-43): needs a street-aware branch.
- `domain/providers/postflop.py` — `supports`/`_grade` (21-30): needs a street/context arm for
  turn/river graders instead of falling through to `grade_cbet`/`grade_vs_cbet`.
- `api/v1/drill.py` — `_next_postflop`/`_next_vs_cbet` (71-77), `_POSTFLOP_CTX` (79),
  `_rebuild_postflop` (82-119), `_next_review` (122-142), `next_drill` mode routing (154-173) — the
  "one sampler function + one `mode` arm" pattern new drill modes must follow. `grade_drill`
  (176-198) needs no changes — already street-agnostic.
- `services/review.py` — `_postflop_archetype` (25-31, duplicate truncating `classify()` call).
- `db/models.py` — `SRSItemRow` (35-57): `street`/`texture_class`/`spr_bucket`/`faced_bet_bucket`
  already nullable strings — no migration needed unless a new bucket dimension is added.
- `tests/factories.py` — `make_cbet_spot` (48-90, flop-hardcoded) — needs turn/river siblings.
- `tests/test_signature.py` / `test_review.py` — no turn/river coverage today.
- Frontend: `frontend/src/App.tsx` `MODES` array mirrors `drill.py` mode strings — needs new entries.
  `frontend/src/components/PokerTable.tsx:45-47` already renders boards of any length — reusable.

## (c) Flop-hardcoded vs. street-agnostic

**Flop-hardcoded — silently misbehaves on a turn/river `Spot` today:**
`texture.classify()` (35) · `postflop.grade_cbet`/`grade_vs_cbet` (184, 363) ·
`srs._postflop_signature` (96) · `services.review._postflop_archetype` (30) ·
`srs.faced_bet_bucket` (78-81) · `providers.postflop.supports` (26) ·
`providers.composite._route` (42-43) · `api/v1/drill._rebuild_postflop` (91-105) ·
`postflop._hand_category` (117-119) · `postflop.range_advantage`/`range_advantage_defender`
(61-84, 288-313 — no scare-card/prior-action awareness, dead `node_context` param) ·
`scenarios.build_cbet_spot`/`build_vs_cbet_spot` (290-313, 341-383 — hardcode `Street.FLOP`,
3-card sample, single-bet history) · `tests/factories.make_cbet_spot` (65).

**Street-agnostic — reusable as-is:**
`spot.py` `Spot`/`HistoryAction`/`LegalAction` schema · `domain/action.py` `Decision` ·
`domain/evaluation.py` `EvaluationResult`/`ActionEval`/`ChosenEval`/`Coverage`/`ProviderKind`/
`Correctness` (no street field at all) · `schemas/drill.py` DTOs ·
`postflop._bet_sizes`/`_frequencies`/`_match` (pure, generic over `legal_actions`/merit lists) ·
`postflop._faced_call_and_pot` (correct current-node pattern) ·
`srs.spr_bucket`/`stack_bucket` (pure numeric bucketing) · `leaks.py` taxonomy convention ·
`providers/postflop.py`'s async `supports`/`optimal`/`evaluate` interface shape ·
`api/v1/drill.grade_drill` · `services/review.record_attempt` (persistence/SM-2 machinery) ·
`db/models.SRSItemRow` (nullable string columns) · `PokerTable.tsx` board rendering.
