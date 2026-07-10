# Delta spec — Simulate S7: river graders (value/bluff + facing river bets)

> Slice S7 of `docs/ai-dlc/roadmap/simulate-table.md` (Track C, W3 — after S6). Contract
> map: `docs/ai-dlc/contracts/simulate-s7.md` (delta vs S6 as-built). Gate-1 decisions
> 2026-07-10: flat constants + pot odds (turn precedent) · river-card SRS dimension YES
> (turn-dim precedent) · busted-draw demotion · no drill modes/tiles/cards.

**Goal (one line):** river grading — value-bet/bluff aggressor + bluff-catch facing a river
bet — cloned from S6's turn pattern, with busted draws valued honestly, a river-card SRS
dimension, and rebuildable river review spots. Completes per-street coverage (street 4/4).

## Frozen interface

```python
# domain/spot.py — NodeContext gains EXACTLY two members:
RIVER_BARREL = "river_barrel"     # aggressor who bet flop+turn deciding the river
VS_RIVER_BET = "vs_river_bet"     # caller of flop+turn bets facing a river bet

# domain/texture.py — new function (classify() and turn_card_class() untouched):
def river_card_class(board: list[Card]) -> str
# board len >= 5; classifies board[4] against board[:4] into EXACTLY
# "pairing" | "flush" | "straight" | "over" | "blank", same precedence as turn_card_class.

# domain/postflop.py:
def grade_river_barrel(spot, hero_range, villain_range, decision) -> EvaluationResult
def grade_vs_river_bet(spot, hero_range, villain_range, decision) -> EvaluationResult
# range_advantage(): _TURN_CTX-style dispatch gains a river branch (aggressor edge decayed
# further than turn; river-card class shifts it); returns only the 3 canonical labels.
# range_advantage_defender(): reused VERBATIM (already street-agnostic — contract §7).
# Caller convention (refuter-pinned, the S6 check-raiser lesson): both river graders pass
# `spot.facing or _villain_pos(spot)` as the aggressor/villain position — the river BETTOR
# for vs_river_bet, the flop-caller-turned-defender for river_barrel; comment it in code.

# domain/providers/river.py — clone of providers/turn.py:
class RiverHeuristicProvider:  # supports: street==RIVER AND node ∈ {RIVER_BARREL,
                               # VS_RIVER_BET} AND len(board) >= 5 — NEVER flop/turn contexts

# composite.py: __init__(preflop, postflop, turn, river); _by_street[RIVER] = river.
# factory.py constructs it (sole site). providers/__init__.__all__ untouched (precedent).

# domain/srs.py — SECOND conditional append (after the turn_class element):
# if street == Street.RIVER and len(board) >= 5: parts.append(river_card_class(board))
# Flop AND turn hashes byte-unchanged (element omitted); pins stay literal.

# scenarios.py — two builders; prior line pinned:
def build_river_barrel_spot(rng, *, pairing=..., eff_bb=...) -> Spot
#   history: preflop raise+call → flop cbet+call → TURN BARREL + CALL → river to act
def build_vs_river_bet_spot(rng, *, pairing=..., eff_bb=..., bet_frac=...) -> Spot
#   history: hero called flop cbet AND turn barrel → faces river bet (street=RIVER entries
#   so faced_bet_bucket's street filter works); CALL min_bb incremental.
```

## Changes (exact)

1. **Graders:** flop/turn anatomy — same band constants, merit → freq 3dp → EV 2dp →
   correctness ladder; street != RIVER → ValueError guard. Merits = flat constants + pot
   odds via `_faced_call_and_pot` (NO equity_vs_range — Gate-1). **Busted-draw demotion
   (contract §4, top hazard):** `cat = _hand_category(...)`; on river,
   `cat_effective = "air" if cat == "draw" else cat` for BOTH merits and tags — a busted
   draw is a bluff-candidate, never the 1.2 value tier. `_hand_category` itself is NOT
   modified (flop/turn callers unaffected). Barrel merits: river_card_class (scare cards),
   river range_advantage branch, cat_effective, position. Bluff-catch merits: pot odds vs
   texture/scare-tuned bluff-frequency constants, cat_effective, range_advantage_defender.
   **6-wide tags:** `[node, adv, cat_effective, wetness, turn_class, river_class]`.
2. **Feedback:** `_NODE` += river_barrel/vs_river_bet entries; new `_RIVER_CLASS` dict.
   **Dispatch (refuter-clarified):** river nodes surface BOTH cards — widen the existing
   turn_class gate's node tuple to include the river nodes (so tags[4] still yields the
   turn-card sentence: a barrel through a scare turn keeps that context) AND add the
   river gate (`node in ("river_barrel","vs_river_bet") and len(tags) >= 6` → tags[5]
   via `_RIVER_CLASS`). Turn-node output byte-unchanged. `_ADV`/`_CAT`/`_WET` unchanged.
   `test_feedback_tiers.py` passes UNMODIFIED; a river tiers test asserts both the turn-
   and river-card sentences appear.
3. **SRS:** second conditional append per frozen interface; append-rule docstring updated
   to record both dims; `SRSItemRow.river_class` nullable column + **additive migration
   0008** (clone 0007); `review.py::_postflop_archetype` populates river_class for RIVER
   spots (None for flop/turn); fix the now-ambiguous turn_class comment
   (`db/models.py:60-61`). Pinned literals `6832a54693ba5f6c`/`0cdf437e044b0bc5` NEVER
   change; existing turn-class signature tests pass unmodified.
4. **Rebuild:** `_POSTFLOP_CTX` += both river members; `_RIVER_CTX` sibling tuple; river
   rows match the 5-wide target `(texture_class, spr_bucket, faced_bet_bucket, turn_class,
   river_class)`; two `_rebuild_postflop` branches via the new builders (VS_RIVER_BET
   derives bet_frac from faced_bet_bucket like the turn branch). **Refuter warning made
   explicit: river rows must get their OWN `if row.node_context in _RIVER_CTX:` branch —
   do NOT fold river into the existing `_TURN_CTX` tuple/target check (turn rows carry
   `river_class=None`; a widened shared branch silently degrades turn rebuild to
   tier-b/c fallback).** Turn/flop branches byte-untouched.
5. **Leaks:** `RIVER_BARREL = 205`, `VS_RIVER_BET = 206`; `TAXONOMY_VERSION 4 → 5`; BOTH
   mapping sites (grader-local `leak =` + `grading.py::leak_category_for`). No Home.tsx
   tile, no concept cards (S6 precedent + no-go).
6. **Content:** `content/postflop/river.json` (`id: "postflop-river", version: 1`) — prose
   rationale entries keyed (node_context, position, facing) for both contexts (value-bet
   discipline, bluff-catch pot-odds coaching); hand-edit `contentpack.schema.json`
   NodeContext enum += 2 values (no generator).
7. **Tests:** clone S6's patterns — river provider gating tests (pre-authored scaffold
   style, `test_provider.py:200-273`); NOT_FOUND trio + tripwire assertions byte-unchanged
   (river provider rejects the CBET-context fixtures) with the ONE permitted comment
   amendment at `test_api.py:272` ("no provider covers the river" → stale);
   `test_river_due_row_rebuilds_matching_archetype` (non-tautological: node/street/
   texture/turn_class/river_class match); river-class signature divergence tests (clone
   `test_signature.py:250-260`); **new 5-card `_hand_category` fixtures**: 4-flush and
   4-straight boards where the river completes vs bricks a draw (roadmap regression guard)
   + busted-draw-demotion grading test (busted flush draw facing a river bet grades fold
   as best action, never a value line).

## Files

`domain/spot.py` · `domain/texture.py` · `domain/postflop.py` · `domain/providers/river.py`
(new) · `providers/composite.py` · `providers/factory.py` · `domain/feedback.py` ·
`domain/leaks.py` · `domain/grading.py` · `domain/srs.py` · `domain/scenarios.py` ·
`api/v1/drill.py` · `app/services/review.py` · `app/db/models.py` ·
`backend/alembic/versions/0008_*` (new) · `content/postflop/river.json` (new) ·
`content/schema/contentpack.schema.json` · tests: `test_river_graders.py` (new),
`test_signature.py`/`test_api.py`/`test_provider.py`/`test_postflop.py` (additions only +
the one comment amendment). No `test_domain_purity.py` change (providers covered
transitively — S6-verified).

## Out of scope (S7 no-gos)

Multiway (S8) · no Practice drill modes / Mode union / tiles / concept cards · no
equity_vs_range in graders · no `_hand_category` body changes · no flop/turn grader output
changes (byte-identical) · no preflop signature changes · EVs approximate.

## Verify-by

Full `pytest -q` green; pins unchanged as literals; NOT_FOUND trio + tripwire + feedback
NOT_FOUND assertions unmodified; river spots grade freq+EV with rationale naming the
river-card class; busted-draw demotion test green; due river row rebuilds matching all 5
archetype fields; migration 0008 applies cleanly; two rivers differing only in river-card
class hash differently, flop/turn hashes untouched; ruff clean; `./scripts/verify.sh` →
BACKEND VERIFY OK.
