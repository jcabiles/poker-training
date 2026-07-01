import asyncio
import math

from factories import make_rfi_spot

from app.domain.action import Decision
from app.domain.evaluation import Correctness, Coverage, ProviderKind
from app.domain.leaks import LeakCategory
from app.domain.providers import StrategyProvider, get_provider
from app.domain.spot import ActionType, Position


def _run(coro):
    return asyncio.run(coro)


def test_provider_satisfies_protocol():
    assert isinstance(get_provider(), StrategyProvider)


def test_supports_rfi_preflop():
    p = get_provider()
    assert _run(p.supports(make_rfi_spot(position=Position.CO))) is True


def test_in_range_raise_is_optimal():
    p = get_provider()
    spot = make_rfi_spot(hole_cards=("Ah", "Ks"), position=Position.CO)  # AKs opens CO
    res = _run(p.evaluate(spot, Decision(action=ActionType.RAISE, size_bb=2.5)))
    assert res.correctness == Correctness.OPTIMAL
    assert res.ev_loss_bb == 0.0
    assert res.best_action.action == ActionType.RAISE
    assert res.coverage == Coverage.FULL
    assert res.provider == ProviderKind.HEURISTIC
    assert res.leak_category == int(LeakCategory.RFI_CO)
    # freq + non-null/finite ev contract
    for a in res.per_action:
        assert isinstance(a.ev_bb, float) and math.isfinite(a.ev_bb)
    assert {a.action for a in res.per_action} == {ActionType.RAISE, ActionType.FOLD}


def test_raising_trash_is_an_error():
    # 72o never opens. From a WIDE seat (CO) it's only just off the range edge,
    # so the calibrated grader rates it a mistake (not a blunder). UTG 72o = blunder
    # is covered in test_grading.
    p = get_provider()
    spot = make_rfi_spot(hole_cards=("7c", "2d"), position=Position.CO)
    res = _run(p.evaluate(spot, Decision(action=ActionType.RAISE, size_bb=2.5)))
    assert res.best_action.action == ActionType.FOLD
    assert res.correctness in (Correctness.MISTAKE, Correctness.BLUNDER)
    assert res.ev_loss_bb > 0.5


def test_folding_trash_is_optimal():
    p = get_provider()
    spot = make_rfi_spot(hole_cards=("7c", "2d"), position=Position.CO)
    res = _run(p.evaluate(spot, Decision(action=ActionType.FOLD)))
    assert res.correctness == Correctness.OPTIMAL


def test_optimal_has_no_chosen_eval():
    p = get_provider()
    res = _run(p.optimal(make_rfi_spot(position=Position.CO)))
    assert res.chosen_eval is None
    assert res.best_action is not None


# --- Phase 2a: composite routing ---
def test_composite_routes_preflop_to_heuristic():
    p = get_provider()
    spot = make_rfi_spot(hole_cards=("Ah", "Ks"), position=Position.CO)
    res = _run(p.evaluate(spot, Decision(action=ActionType.RAISE, size_bb=2.5)))
    assert res.correctness == Correctness.OPTIMAL  # graded by preflop heuristic


def test_composite_routes_flop_to_postflop():
    import random

    from app.domain.scenarios import build_cbet_spot

    p = get_provider()
    spot = build_cbet_spot(random.Random(9), eff_bb=100.0)
    assert _run(p.supports(spot)) is True
    res = _run(p.evaluate(spot, Decision(action=ActionType.CHECK)))
    assert res.leak_category == int(LeakCategory.FLOP_CBET)
    assert res.coverage == Coverage.FULL


def test_composite_routes_vs_cbet_to_postflop():
    import random

    from app.domain.scenarios import build_vs_cbet_spot

    p = get_provider()
    spot = build_vs_cbet_spot(random.Random(5), eff_bb=100.0)
    assert _run(p.supports(spot)) is True
    res = _run(p.evaluate(spot, Decision(action=ActionType.CALL)))
    assert res.leak_category == int(LeakCategory.VS_CBET)
    assert res.coverage == Coverage.FULL


def test_composite_routes_vs_check_raise_to_postflop():
    import random

    from app.domain.scenarios import build_check_raise_spot

    p = get_provider()
    spot = build_check_raise_spot(random.Random(0), eff_bb=100.0)
    assert _run(p.supports(spot)) is True
    res = _run(p.evaluate(spot, Decision(action=ActionType.CALL)))
    assert res.leak_category == int(LeakCategory.VS_CHECK_RAISE)
    assert res.coverage == Coverage.FULL


def test_postflop_cbet_still_grades_after_vs_check_raise_added():
    # Confirm Phase 2a cbet routing still works after adding VS_CHECK_RAISE support.
    import random

    from app.domain.scenarios import build_cbet_spot

    p = get_provider()
    spot = build_cbet_spot(random.Random(9), eff_bb=100.0)
    res = _run(p.evaluate(spot, Decision(action=ActionType.CHECK)))
    assert res.leak_category == int(LeakCategory.FLOP_CBET)
    assert res.coverage == Coverage.FULL


def test_postflop_vs_cbet_still_grades_after_vs_check_raise_added():
    # Confirm Phase 2b vs_cbet routing still works after adding VS_CHECK_RAISE support.
    import random

    from app.domain.scenarios import build_vs_cbet_spot

    p = get_provider()
    spot = build_vs_cbet_spot(random.Random(5), eff_bb=100.0)
    res = _run(p.evaluate(spot, Decision(action=ActionType.CALL)))
    assert res.leak_category == int(LeakCategory.VS_CBET)
    assert res.coverage == Coverage.FULL


def test_composite_unknown_flop_node_is_not_found():
    # A turn spot with no postflop node -> routed provider doesn't support -> NOT_FOUND.
    from app.domain.spot import Street

    spot = make_rfi_spot(position=Position.CO).model_copy(
        update={"street": Street.TURN, "board": ["As", "Kd", "2c", "7h"], "node_context": []}
    )
    p = get_provider()
    res = _run(p.optimal(spot))
    assert res.coverage == Coverage.NOT_FOUND


def test_postflop_provider_rejects_turn_street():
    # Phase 2e-0 T3: PostflopHeuristicProvider only supports FLOP, not TURN.
    # A turn spot with CBET context must still return NOT_FOUND.
    from factories import make_cbet_spot
    from app.domain.spot import Street

    p = get_provider()
    flop_spot = make_cbet_spot()
    turn_spot = flop_spot.model_copy(
        update={"street": Street.TURN, "board": ["Ac", "Kd", "Qh", "2s"]}
    )
    res = _run(p.optimal(turn_spot))
    assert res.coverage == Coverage.NOT_FOUND
    assert res.explanation == "No content for this spot."


def test_postflop_provider_rejects_river_street():
    # Phase 2e-0 T3: PostflopHeuristicProvider only supports FLOP, not RIVER.
    # A river spot with CBET context must still return NOT_FOUND.
    from factories import make_cbet_spot
    from app.domain.spot import Street

    p = get_provider()
    flop_spot = make_cbet_spot()
    river_spot = flop_spot.model_copy(
        update={"street": Street.RIVER, "board": ["Ac", "Kd", "Qh", "2s", "3d"]}
    )
    res = _run(p.optimal(river_spot))
    assert res.coverage == Coverage.NOT_FOUND
    assert res.explanation == "No content for this spot."


def test_postflop_provider_still_grades_flop():
    # Phase 2e-0 T3: Verify that FLOP spots with CBET still grade normally.
    from factories import make_cbet_spot

    p = get_provider()
    spot = make_cbet_spot()
    res = _run(p.optimal(spot))
    assert res.coverage == Coverage.FULL
    assert res.provider == ProviderKind.HEURISTIC
