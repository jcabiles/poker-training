# Delta spec — Simulate S8: multiway grading extension

> Slice S8 of `docs/ai-dlc/roadmap/simulate-table.md` (Track D, W4 — strictly after S7;
> shares the C-track grader files, so S8 is their sole owner this wave). Contract scan:
> 2026-07-10 (agent report folded in below). Interview decisions 2026-07-10:
> **binary bucket** (heads-up vs multiway 3+, no 2/3/4+ split) · **both sides**
> (aggressor c-bet/barrel AND facing/bluff-catch graders adjusted).

**Goal (one line):** make the seven postflop graders player-count-aware — a 3-way spot
grades with **fewer acceptable bluffs and a slight value-lean** vs the identical heads-up
spot — via a shared merit adjustment keyed on a **derived** in-pot count, plus a **third
conditional signature append** (`mw`, present only for 3+) that leaves every existing
heads-up signature byte-identical.

## Key scope property (why S8 is small and file-disjoint from S9)

**Multiway spots are never persisted in v1.** Practice builds only heads-up spots
(`_hu_srp_seats`, 2 IN); Simulate writes **no** SRS rows (global no-go). Therefore no
multiway signature is ever stored, so S8 needs **NO** `SRSItemRow` column, **NO**
`_rebuild_postflop` branch, **NO** `review.py::_postflop_archetype` change, and
**NO Alembic migration**. This keeps S9 the sole Alembic owner (0009) and makes S8 a
pure domain-plus-tests slice. (If a future slice ever persists a multiway spot, it must
add the rebuild branch THEN — documented boundary.)

## Frozen interface

```python
# domain/spot.py — new module-level helper (Spot schema UNCHANGED — no new field):
def players_in_pot(spot: Spot) -> int:
    """Count seats still contesting the pot (hero + live villains).
    = sum(1 for p in spot.players if p.status in (PlayerStatus.IN, PlayerStatus.ALLIN)).
    Heads-up spots (every existing postflop fixture via _hu_srp_seats) == 2."""

def is_multiway(spot: Spot) -> bool:   # players_in_pot(spot) > 2

# domain/postflop.py — one shared adjustment, applied inside EVERY grader after base
# merits are computed and BEFORE _frequencies(). New module constants (tune to pass the
# direction tests; values are the maker's, these are the DIRECTIONS):
#   _MW_BLUFF_DAMPEN  in (0,1)   # scales DOWN aggressive merit for bluff-candidate
#                                #   categories (air, and on non-river: draw) multiway
#   _MW_VALUE_LEAN    >= 1.0     # scales UP (or holds) value-category aggressive merit
#   _MW_CATCH_TIGHTEN >= 1.0     # scales UP fold merit for marginal bluff-catchers on
#                                #   the facing-bet graders multiway
# Mechanism: a private helper applied uniformly, e.g.
def _apply_multiway(merits: dict, *, cat_effective: str, facing_side: bool) -> dict
# reads NOTHING but the merit dict + the already-computed category + which side; it must
# NOT read spot.villain_type or any persona data (graders-never-read-persona invariant).
# Graders pass is_multiway(spot) to decide whether to call it.

# domain/srs.py — THIRD conditional append, AFTER the river_class element (fixed order:
# turn_class (S6) -> river_class (S7) -> mw (S8)):
#   if players_in_pot(spot) > 2:
#       parts.append("mw")
# Omitted for every heads-up spot (count == 2) => flop/turn/river HU hashes byte-identical.
# Element counts become: flop 9/10, turn 10/11, river 11/12 (HU/MW). No cross-street
# aliasing (street at index 2 already separates streets).

# domain/scenarios.py — the 7 postflop builders gain ONE optional kwarg (default keeps
# every existing call site byte-identical, i.e. heads-up 2-IN):
def build_cbet_spot(rng, *, ..., players_in_pot: int = 2) -> Spot   # and the other 6
# players_in_pot=2 -> today's _hu_srp_seats exactly. players_in_pot=3 -> _hu_srp_seats
# plus (players_in_pot-2) extra IN seats (a new _multiway_seats helper adds live callers
# without altering the 2 principals' positions/history the graders key on).
```

## Changes (exact)

1. **`spot.py` helpers:** add `players_in_pot(spot)` and `is_multiway(spot)` as pure
   module functions next to `PlayerState` (spot.py is already transitively purity-checked;
   no new module, no `test_domain_purity.py` change). No field added to `Spot`.

2. **`postflop.py` merit adjustment:** every grader (`grade_cbet`, `grade_vs_cbet`,
   `grade_vs_check_raise`, `grade_turn_barrel`, `grade_vs_turn_bet`, `grade_river_barrel`,
   `grade_vs_river_bet`) computes its base merit vector unchanged, then — if
   `is_multiway(spot)` — routes it through `_apply_multiway(...)` before `_frequencies()`.
   Aggressor graders (cbet/turn_barrel/river_barrel): dampen aggressive merit for
   bluff-candidate categories, hold/lean value. Facing graders (vs_cbet/vs_turn_bet/
   vs_river_bet/vs_check_raise): tighten bluff-catch (raise fold merit for marginal
   catchers). **Heads-up output is byte-identical** (adjustment gated behind
   `is_multiway`, which is False at count 2 — the existing turn/river/flop grader tests
   must pass UNMODIFIED). Results stay freq+EV + `Correctness` ladder — never a boolean.
   The busted-draw river demotion (`cat_effective = "air" if cat == "draw"`) is upstream
   and unchanged; multiway dampen reads `cat_effective`.

3. **`srs.py` third append:** per frozen interface; extend the APPEND-RULE docstring to
   record the `mw` dim (three conditional dims now, fixed order). Pinned literals
   `6832a54693ba5f6c` / `0cdf437e044b0bc5` / `9c1aae003ae79de0` NEVER change (verify by
   recomputing, not by trust). No collision: flop-MW(10) vs turn-HU(10) differ at index 2
   (street); turn-MW(11) vs river-HU(11) differ at index 2.

4. **`scenarios.py` multiway seams:** the optional `players_in_pot` kwarg + a
   `_multiway_seats(...)` helper that starts from `_hu_srp_seats` and appends
   (`players_in_pot - 2`) additional IN `PlayerState`s at unused positions (never mutating
   the opener/caller the graders read via `_villain_pos`/`spot.facing`). Default 2 =>
   existing behavior byte-identical.

5. **Leaks/feedback: NO changes.** No new `LeakCategory`, `TAXONOMY_VERSION` stays **5**,
   no `grading.py::leak_category_for` change (a multiway over-barrel buckets into the same
   behavioral leak as its HU twin — the stricter threshold is what flags it). No
   `feedback.py` change (multiway shifts the numeric verdict/freq only; adding a
   multiway tag would collide with the fixed positional-tag semantics — hazard, out of
   scope). Prose stays street-generic.

6. **Providers: NO changes.** A multiway c-bet is *graded* (with dampened bluffs), not
   `NOT_FOUND` — every player count ≥ 2 maps to a bucket. `NOT_FOUND` remains reserved for
   unsupported node contexts (unchanged). `supports()` untouched.

## Files

`domain/spot.py` · `domain/postflop.py` · `domain/srs.py` · `domain/scenarios.py` ·
tests (T5): `tests/test_multiway.py` (new) · `tests/test_signature.py` (additions only) ·
`tests/test_provider.py` (additions only). **No** migration, **no** `db/models.py`, **no**
`review.py`, **no** `drill.py`, **no** `leaks.py`/`grading.py`/`feedback.py`, **no**
`content/*`, **no** `test_domain_purity.py` change.

## Tests (T5, direction + invariance)

- **Direction (the pass/fail):** for a representative grader on each side and street —
  cbet (flop aggressor), vs_cbet (flop facing), turn_barrel + vs_turn_bet, river_barrel +
  vs_river_bet — assert the multiway spot's acceptable-**bluff** frequency is **strictly
  lower** than the identical heads-up spot's, and value frequency is **≥** the HU value
  frequency (same seed, same board/hole/history, only `players_in_pot` differs).
- **Graded, not NOT_FOUND:** a multiway c-bet returns `Coverage`-FOUND freq+EV (never
  `NOT_FOUND`, never byte-identical to its HU twin).
- **Signature invariance:** recompute and assert the three pinned literals unchanged;
  add companion `test_*_signature_unchanged_by_multiway_dimension` for flop/turn/river
  (HU hash == pinned/prior literal after the `mw` append lands); a multiway spot's hash
  ≠ its HU twin; two multiway spots that differ only in count (3-way vs 4-way, binary
  bucket) hash **identically** (both != HU).
- **No persona read:** a static assertion/inspection that `_apply_multiway` and the
  graders' multiway branch never reference `villain_type`/persona modules.
- Existing `test_postflop.py` / `test_turn_graders.py` / `test_river_graders.py` /
  `test_feedback_tiers.py` / the pinned signature tests pass **UNMODIFIED**.

## Out of scope (S8 no-gos)

Finer than binary (2/3/4+) buckets · any persisted multiway row (no migration/model/
rebuild/archetype change) · new leak categories or `TAXONOMY_VERSION` bump · feedback
prose changes · provider/`supports()`/`NOT_FOUND` changes · persona-aware grading · any
heads-up output change (byte-identical) · preflop signature changes · EVs approximate.

## Verify-by

Full `pytest -q` green; the three pinned hashes recomputed and unchanged as literals;
HU grader outputs byte-identical; multiway direction tests green (bluff freq strictly
down, value ≥, both sides, all three streets); multiway c-bet graded not NOT_FOUND;
3-way and 4-way hash identically and differ from HU; `TAXONOMY_VERSION == 5`; no new
migration; ruff clean; `./scripts/verify.sh` → BACKEND VERIFY OK.
