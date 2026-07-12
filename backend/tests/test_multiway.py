"""S8 — multiway grading direction + graded-not-NOT_FOUND + no-persona-read tests.

Authored to T4's FROZEN interface (docs/ai-dlc/specs/simulate-s8.md) ahead of
T4's domain/spot.py, domain/postflop.py, domain/scenarios.py landing mid-wave.
Import failures here (players_in_pot, is_multiway, the `players_in_pot=`
builder kwarg, `_apply_multiway`) are EXPECTED until T4's commits land — report,
do not patch T4's files.

Direction contract (the pass/fail): build the IDENTICAL spot at
players_in_pot=2 (heads-up) and players_in_pot=3 (multiway) — same seed, board,
hole cards, action history — grade both, and assert the multiway spot's
acceptable-bluff signal is STRICTLY weaker than the heads-up spot's, and its
value signal is >= the heads-up value signal. A no-op multiway dampen (e.g.
_MW_BLUFF_DAMPEN == 1.0 / _MW_CATCH_TIGHTEN == 1.0) must make each test FAIL —
these are not tautologies (verified by hand against the current tuning).

Hand categories are forced via model_copy AFTER building via T4's builder, so
the comparison isolates the multiway merit adjustment from random hand/board
variance drawn by the seeded rng (the builder itself only varies which seats
are IN — it never touches the opener/caller's position or action history).

Metric note (vs_turn_bet / vs_river_bet air case): with the current merit
tuning, a pure "air" hand's call/raise merit is ALWAYS negative for these two
graders (no texture-conditioned bump exists there, unlike vs_cbet's occasional
check-raise-bluff allowance) — so its continue frequency is already floored at
0.0 heads-up, and fold frequency is already ceilinged at 1.0. A frequency-based
"strictly lower" assertion is structurally unobservable for air on exactly
these two graders. `_MW_CATCH_TIGHTEN` still measurably scales the fold MERIT
(and therefore its EV) up multiway even while both frequencies stay pinned at
their floor/ceiling, so those two tests assert on the fold action's EV instead
— still a direct, non-tautological probe of the same "tighten bluff-catch"
mechanism (confirmed to fail under a no-op _MW_CATCH_TIGHTEN).
"""

from __future__ import annotations

import inspect
import random

import pytest
from factories import make_cbet_spot

from app.domain.evaluation import Coverage
from app.domain.spot import ActionType, Hero, Street

pytestmark = pytest.mark.filterwarnings("ignore")

_AIR_HAND = ("2h", "3c")  # air on Ac Kd Qh — no pair, no draw (see _hand_category)
_STRONG_HAND = ("Ah", "Ks")  # top two pair on Ac Kd Qh — "strong"


def _require_multiway_seams(builder_name: str = "build_cbet_spot"):
    """Skip with a clear reason if T4's slice hasn't landed yet for THIS
    builder (dependency, not a real failure) — otherwise import errors /
    TypeErrors would look like broken tests. T4's 7 builders may land the
    `players_in_pot` kwarg independently mid-wave, so this checks the specific
    builder each test needs, not just one representative builder."""
    try:
        from app.domain import scenarios
        from app.domain.spot import is_multiway, players_in_pot  # noqa: F401

        builder = getattr(scenarios, builder_name)
        builder(random.Random(1), players_in_pot=3)
    except (ImportError, TypeError, AttributeError) as e:
        pytest.skip(f"T4 multiway seams not yet landed for {builder_name}: {e}")


def _hu_and_mw(builder_name: str, *, seed: int, hole):
    """Build the identical spot at players_in_pot=2 and =3 via T4's frozen
    builder kwarg (same seed -> same board/history/hero position), then force
    a specific hand category on both via model_copy so the comparison isolates
    the multiway merit adjustment."""
    from app.domain import scenarios

    builder = getattr(scenarios, builder_name)
    hu = builder(random.Random(seed), players_in_pot=2)
    mw = builder(random.Random(seed), players_in_pot=3)

    update = {"hero": Hero(position=hu.hero.position, hole_cards=hole, stack_bb=hu.hero.stack_bb)}
    hu = hu.model_copy(update=update)
    mw = mw.model_copy(update=update)
    return hu, mw


def _bet_or_raise_freq(result, categories=(ActionType.BET, ActionType.RAISE)):
    return sum(a.frequency for a in result.per_action if a.action in categories)


def _fold_ev(result):
    return next(a.ev_bb for a in result.per_action if a.action == ActionType.FOLD)


# --- Direction: aggressor graders (bluff = betting/raising an air hand) ---


def test_cbet_multiway_air_bluff_freq_strictly_lower_value_freq_geq():
    _require_multiway_seams("build_cbet_spot")
    from app.domain.postflop import grade_cbet

    hu, mw = _hu_and_mw("build_cbet_spot", seed=3, hole=_AIR_HAND)
    hu_bluff = grade_cbet(hu, hu.hero_range, hu.villain_range, None)
    mw_bluff = grade_cbet(mw, mw.hero_range, mw.villain_range, None)
    assert _bet_or_raise_freq(mw_bluff) < _bet_or_raise_freq(hu_bluff)

    hu_v, mw_v = _hu_and_mw("build_cbet_spot", seed=5, hole=_STRONG_HAND)
    hu_value = grade_cbet(hu_v, hu_v.hero_range, hu_v.villain_range, None)
    mw_value = grade_cbet(mw_v, mw_v.hero_range, mw_v.villain_range, None)
    assert _bet_or_raise_freq(mw_value) >= _bet_or_raise_freq(hu_value)


def test_turn_barrel_multiway_air_bluff_freq_strictly_lower_value_freq_geq():
    _require_multiway_seams("build_turn_barrel_spot")
    from app.domain.postflop import grade_turn_barrel

    hu, mw = _hu_and_mw("build_turn_barrel_spot", seed=3, hole=_AIR_HAND)
    hu_bluff = grade_turn_barrel(hu, hu.hero_range, hu.villain_range, None)
    mw_bluff = grade_turn_barrel(mw, mw.hero_range, mw.villain_range, None)
    assert _bet_or_raise_freq(mw_bluff) < _bet_or_raise_freq(hu_bluff)

    hu_v, mw_v = _hu_and_mw("build_turn_barrel_spot", seed=5, hole=_STRONG_HAND)
    hu_value = grade_turn_barrel(hu_v, hu_v.hero_range, hu_v.villain_range, None)
    mw_value = grade_turn_barrel(mw_v, mw_v.hero_range, mw_v.villain_range, None)
    assert _bet_or_raise_freq(mw_value) >= _bet_or_raise_freq(hu_value)


def test_river_barrel_multiway_air_bluff_freq_strictly_lower_value_freq_geq():
    _require_multiway_seams("build_river_barrel_spot")
    from app.domain.postflop import grade_river_barrel

    hu, mw = _hu_and_mw("build_river_barrel_spot", seed=18, hole=_AIR_HAND)
    hu_bluff = grade_river_barrel(hu, hu.hero_range, hu.villain_range, None)
    mw_bluff = grade_river_barrel(mw, mw.hero_range, mw.villain_range, None)
    assert _bet_or_raise_freq(mw_bluff) < _bet_or_raise_freq(hu_bluff)

    hu_v, mw_v = _hu_and_mw("build_river_barrel_spot", seed=2, hole=_STRONG_HAND)
    hu_value = grade_river_barrel(hu_v, hu_v.hero_range, hu_v.villain_range, None)
    mw_value = grade_river_barrel(mw_v, mw_v.hero_range, mw_v.villain_range, None)
    assert _bet_or_raise_freq(mw_value) >= _bet_or_raise_freq(hu_value)


# --- Direction: facing graders (bluff = raising/bluff-catching with air; the
# spec's "tighten bluff-catch" mechanism -> a marginal/air hand should fold
# MORE (raise/call less) multiway) ---


def test_vs_cbet_multiway_air_bluffcatch_freq_strictly_lower():
    _require_multiway_seams("build_vs_cbet_spot")
    from app.domain.postflop import grade_vs_cbet

    # This board (paired/connected/wet) gives air a nonzero occasional
    # check-raise-bluff merit heads-up (vs_cbet's texture-conditioned bump) —
    # the only one of the three facing graders where that bump exists, so it's
    # the one where a frequency-based "strictly lower" assertion is possible
    # for pure air (see module docstring for vs_turn_bet/vs_river_bet's
    # structural floor-at-zero and their EV-based fallback).
    hu, mw = _hu_and_mw("build_vs_cbet_spot", seed=17, hole=_AIR_HAND)
    hu_res = grade_vs_cbet(hu, hu.hero_range, hu.villain_range, None)
    mw_res = grade_vs_cbet(mw, mw.hero_range, mw.villain_range, None)
    hu_continue = _bet_or_raise_freq(hu_res, categories=(ActionType.CALL, ActionType.RAISE))
    mw_continue = _bet_or_raise_freq(mw_res, categories=(ActionType.CALL, ActionType.RAISE))
    assert mw_continue < hu_continue

    hu_v, mw_v = _hu_and_mw("build_vs_cbet_spot", seed=5, hole=_STRONG_HAND)
    hu_value = grade_vs_cbet(hu_v, hu_v.hero_range, hu_v.villain_range, None)
    mw_value = grade_vs_cbet(mw_v, mw_v.hero_range, mw_v.villain_range, None)
    hu_value_continue = _bet_or_raise_freq(
        hu_value, categories=(ActionType.CALL, ActionType.RAISE)
    )
    mw_value_continue = _bet_or_raise_freq(
        mw_value, categories=(ActionType.CALL, ActionType.RAISE)
    )
    assert mw_value_continue >= hu_value_continue


def test_vs_turn_bet_multiway_air_fold_ev_strictly_higher():
    _require_multiway_seams("build_vs_turn_bet_spot")
    from app.domain.postflop import grade_vs_turn_bet

    # See module docstring: pure air's call/raise merit is structurally
    # negative for this grader (both HU frequencies already floored/ceilinged
    # at 0.0/1.0), so the direction proof is the fold action's EV, which
    # _MW_CATCH_TIGHTEN still measurably raises multiway.
    hu, mw = _hu_and_mw("build_vs_turn_bet_spot", seed=3, hole=_AIR_HAND)
    hu_res = grade_vs_turn_bet(hu, hu.hero_range, hu.villain_range, None)
    mw_res = grade_vs_turn_bet(mw, mw.hero_range, mw.villain_range, None)
    assert _fold_ev(mw_res) > _fold_ev(hu_res)

    hu_v, mw_v = _hu_and_mw("build_vs_turn_bet_spot", seed=5, hole=_STRONG_HAND)
    hu_value = grade_vs_turn_bet(hu_v, hu_v.hero_range, hu_v.villain_range, None)
    mw_value = grade_vs_turn_bet(mw_v, mw_v.hero_range, mw_v.villain_range, None)
    hu_value_continue = _bet_or_raise_freq(
        hu_value, categories=(ActionType.CALL, ActionType.RAISE)
    )
    mw_value_continue = _bet_or_raise_freq(
        mw_value, categories=(ActionType.CALL, ActionType.RAISE)
    )
    assert mw_value_continue >= hu_value_continue


def test_vs_river_bet_multiway_air_fold_ev_strictly_higher():
    _require_multiway_seams("build_vs_river_bet_spot")
    from app.domain.postflop import grade_vs_river_bet

    # See module docstring: same structural floor as vs_turn_bet.
    hu, mw = _hu_and_mw("build_vs_river_bet_spot", seed=3, hole=_AIR_HAND)
    hu_res = grade_vs_river_bet(hu, hu.hero_range, hu.villain_range, None)
    mw_res = grade_vs_river_bet(mw, mw.hero_range, mw.villain_range, None)
    assert _fold_ev(mw_res) > _fold_ev(hu_res)

    hu_v, mw_v = _hu_and_mw("build_vs_river_bet_spot", seed=2, hole=_STRONG_HAND)
    hu_value = grade_vs_river_bet(hu_v, hu_v.hero_range, hu_v.villain_range, None)
    mw_value = grade_vs_river_bet(mw_v, mw_v.hero_range, mw_v.villain_range, None)
    hu_value_continue = _bet_or_raise_freq(
        hu_value, categories=(ActionType.CALL, ActionType.RAISE)
    )
    mw_value_continue = _bet_or_raise_freq(
        mw_value, categories=(ActionType.CALL, ActionType.RAISE)
    )
    assert mw_value_continue >= hu_value_continue


# --- Graded, not NOT_FOUND ---


def test_multiway_cbet_is_graded_not_not_found_and_not_hu_identical():
    _require_multiway_seams("build_cbet_spot")
    from app.domain.postflop import grade_cbet

    hu, mw = _hu_and_mw("build_cbet_spot", seed=3, hole=_AIR_HAND)
    hu_res = grade_cbet(hu, hu.hero_range, hu.villain_range, None)
    mw_res = grade_cbet(mw, mw.hero_range, mw.villain_range, None)
    assert mw_res.coverage == Coverage.FULL
    assert mw_res.coverage != Coverage.NOT_FOUND
    assert mw_res != hu_res
    assert [a.frequency for a in mw_res.per_action] != [a.frequency for a in hu_res.per_action]


def test_multiway_cbet_provider_routes_to_graded_verdict_not_not_found():
    _require_multiway_seams("build_cbet_spot")
    import asyncio

    from app.domain.providers import get_provider
    from app.domain.scenarios import build_cbet_spot

    spot = build_cbet_spot(random.Random(3), players_in_pot=3)
    provider = get_provider()
    supported = asyncio.run(provider.supports(spot))
    assert supported is True
    res = asyncio.run(provider.optimal(spot))
    assert res.coverage != Coverage.NOT_FOUND


# --- No persona read ---


def test_apply_multiway_reads_no_villain_type_or_persona_module():
    """Static inspection: _apply_multiway's source never references
    villain_type or a persona module — the graders-never-read-persona
    invariant applies to the multiway branch too."""
    _require_multiway_seams("build_cbet_spot")
    from app.domain import postflop

    assert hasattr(postflop, "_apply_multiway"), "T4's _apply_multiway helper not found"
    src = inspect.getsource(postflop._apply_multiway)
    assert "villain_type" not in src
    assert "archetypes" not in src
    assert "personas" not in src


def test_multiway_grading_identical_regardless_of_villain_type_value():
    """Grading a multiway spot with villain_type=None vs a set VillainType must
    produce an identical result — the multiway branch never reads persona
    data (a behavioral companion to the static-inspection test above)."""
    _require_multiway_seams("build_cbet_spot")
    from app.domain.archetypes import VillainType
    from app.domain.postflop import grade_cbet
    from app.domain.scenarios import build_cbet_spot

    base = build_cbet_spot(random.Random(9), players_in_pot=3)
    base = base.model_copy(
        update={
            "hero": Hero(
                position=base.hero.position, hole_cards=_AIR_HAND, stack_bb=base.hero.stack_bb
            )
        }
    )
    no_persona = base.model_copy(update={"villain_type": None})
    with_persona = base.model_copy(update={"villain_type": VillainType.CALLING_STATION})

    res_no_persona = grade_cbet(no_persona, no_persona.hero_range, no_persona.villain_range, None)
    res_with_persona = grade_cbet(
        with_persona, with_persona.hero_range, with_persona.villain_range, None
    )
    assert res_no_persona == res_with_persona


def test_postflop_module_imports_no_persona_module_at_module_level():
    """Sanity: importing postflop.py alongside the multiway seams doesn't pull
    in a persona module-level import (static source check)."""
    _require_multiway_seams("build_cbet_spot")
    from app.domain import postflop

    src = inspect.getsource(postflop)
    # module-level import of archetypes/personas would be a persona-read leak
    assert "import app.domain.personas" not in src
    assert "from app.domain.personas" not in src


def test_make_cbet_spot_factory_still_heads_up_by_default():
    """Sanity check unrelated to T4's landing: the existing factory helper is
    untouched and stays a 2-IN heads-up spot (guards against accidental drift
    in a shared fixture)."""
    spot = make_cbet_spot()
    assert spot.street == Street.FLOP
    assert sum(1 for p in spot.players if p.status.value == "in") == 2
