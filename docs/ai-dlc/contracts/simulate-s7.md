# Contract map — S7 river graders (delta vs S6 as-built, at HEAD 2026-07-10)

> Read-only scan on `feat/simulate-wave2`. S6's map (`contracts/simulate-s6.md`) transfers
> as the pattern to clone; this doc records only the river DELTA + what S6's wave-2 code
> actually did.

## Key contracts

1. **Seam already river-labeled.** `composite.py:38` `__init__(preflop, postflop, turn)` —
   add 4th `river` param; `_by_street[Street.RIVER] = postflop` today (`:49`, comment names
   S7). `factory.py:35-39` sole construction site. `providers/__init__.__all__` does NOT
   list TurnHeuristicProvider (factory imports directly) — follow precedent, no drive-by.

2. **`providers/turn.py` (~40 lines) is the exact class template.** `_TURN_NODES` tuple;
   supports = street==TURN + node match + board≥4 (`:24-29`); load-bearing docstring:
   never accepts flop node contexts. River clone: street==RIVER + board≥5 + river nodes only.

3. **Tests pinning river NOT_FOUND today:** `test_provider.py:172-186`
   (river spot w/ CBET ctx → NOT_FOUND) and `test_api.py:264-284` (tripwire — river spot,
   zero writes). Both survive S7 UNCHANGED **only if** the river provider rejects flop
   contexts (same S6 pattern). ⚠️ `test_api.py:272` comment "no provider covers the river
   (S7)" goes stale — comment-only amendment. Pre-authored-ahead-of-code scaffold pattern
   for provider tests: `test_provider.py:200-273` (try/except ImportError + skip).

4. **`_hand_category` on 5-card boards — HIGHEST grading hazard.** Length-agnostic
   arithmetic works, but NEVER exercised at board len 5 (all tests 3-card; turn passes 4).
   On river, `flush_draw`/`oesd` flags still fire → busted draws return `"draw"` which
   carries `_CAT_VALUE["draw"]=1.2` / `_HAND_VALUE["draw"]=1.2` (`postflop.py:236,477`) —
   2nd-highest value tier with ZERO outs remaining. Reusing unmodified overvalues busted
   draws; river needs a category adjustment (busted draw → bluff-candidate/air).
   Roadmap's "4-flush/4-straight spot-check" = NEW 5-card fixtures (none exist).

5. **No river-card classifier exists.** `turn_card_class` hardcodes `board[3]` vs flop
   (`texture.py:92-136`); on a 5-card board it silently ignores `board[4]` (no error).
   `classify()` stays flop-only. S7 needs new `river_card_class(board)` (board[4] vs
   board[:4]).

6. **SRS river blindness (CRITICAL).** `srs.py:138-143`: street in (TURN, RIVER) appends
   `turn_card_class(board)` — a RIVER spot's signature carries TURN-card info only; two
   rivers differing on board[4] (flush vs brick) collapse to one SRS item. Same for
   `SRSItemRow.turn_class` via `review.py:34-38`. Append rule (`srs.py:112-121`) explicitly
   permits a second conditional append for RIVER only + board≥5. If added: `river_class`
   column + migration `0008` (clone 0007). `db/models.py:60-61` turn_class comment needs
   correction either way. Pins untouched; `test_signature.py:226-235` river-vs-flop/turn
   test passes via street at index 2 (not proof of river dimension); clone `:250-260`
   pattern for the new dim.

7. **range_advantage asymmetry.** `_TURN_CTX = (TURN_BARREL, VS_TURN_BET)` (`postflop.py:103`);
   river ctx falls through to FLOP arithmetic today (silently wrong for river aggressor —
   needs a river branch). `range_advantage_defender` (`:480-505`) has zero street dispatch —
   reusable VERBATIM for river bluff-catch.

8. **Street-agnostic helpers reusable as-is:** `_frequencies`/`_bet_sizes` (`:344-357`),
   `_faced_call_and_pot` (`:508-514`), `_match` (`:463-472`). `equity_vs_range` already
   handles board len 5 (`equity.py:120,128`) but turn graders DIDN'T use it (flat constants) —
   spec must freeze flat-constants vs MC for river bluff-catch merits.

9. **NodeContext switch sites (all mirror S6's diff):** `drill.py:91-98` `_POSTFLOP_CTX` +
   `_TURN_CTX` sibling; `drill.py:101-189` rebuild ladder + 2 river branches;
   `providers/river.py` new; `grading.py:70-97` (unknown ctx → VS_RFI mislabel hazard);
   `content/models.py:41-48` enum-typed Entry + `contentpack.schema.json:121-139` (12
   strings, append 2); srs ctx join auto-hashes; FE: no changes (`types.ts:30` string[];
   S6 added NO Home tile and NO concept cards — precedent, roadmap no-go).

10. **feedback.py:** `_NODE` needs 2 river entries; `_ADV` needs ZERO (both label
    vocabularies already present); `_CAT`/`_WET` unchanged if category names stay. Turn-only
    5th-tag branch at `:151-153` (`_TURN_CLASS` dict `:81-87`) — if river tags go 6-wide
    (+river_class), widen the dispatch + add `_RIVER_CLASS`. `test_feedback_tiers.py`
    NOT_FOUND fixture is a TURN spot — unaffected by a river provider.

11. **Leaks:** next free 205/206; TAXONOMY_VERSION 4→5; DUAL mapping sites again
    (grader-local `leak =` at turn precedent `postflop.py:978,1084` + `leak_category_for`).

12. **Rebuild turn branch to clone** (`drill.py:139-178` quoted in full in scan): target
    4-tuple `(texture_class, spr_bucket, faced_bet_bucket, turn_class)` for `_TURN_CTX`
    rows; river rows widen to 5 if river_class column exists. `_key` reads `s.board[:3]`
    for flop texture — generic, no change.

13. **Builders to clone:** `build_turn_barrel_spot` (`scenarios.py:593-657`),
    `build_vs_turn_bet_spot` (`:660-733`). River: sample 5 cards, street=RIVER, one more
    street of history. Turn builders hardcode ONE prior line each — river spec must state
    its single-line assumption explicitly (`faced_bet_bucket` street filter depends on it).

14. **Alembic:** zero migration if no river dimension; `0008_srs_river_class` (additive,
    clone 0007) if yes.

## Ranked decisions the spec must freeze

1. `_hand_category` on river: reuse as-is (mis-values busted draws) vs river-aware demotion.
2. River-card SRS dimension yes/no (+column+migration) — highest silent-data risk.
3. NodeContext naming (baked into leaks/packs/schema/hashes immediately).
4. Tag width 5 vs 6 (cascades feedback dispatch + all grader tag construction).
5. River builders' prior-street action line (affects faced_bet_bucket correctness).
6. Bluff-catch merit basis: flat constants (turn precedent) vs `equity_vs_range` MC.
