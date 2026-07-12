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
    # Phase 2e-0 T3 / S6: routed through get_provider() -> composite -> the
    # TURN provider now handles this street, but its supports() gate rejects
    # flop-node contexts (CBET) by design, so a turn spot carrying a flop
    # context must still return NOT_FOUND end-to-end.
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


# --- S6: TurnHeuristicProvider gating (authored ahead of T3's providers/turn.py;
# skips until app.domain.providers.turn + NodeContext.TURN_BARREL exist) ---

try:
    from app.domain.providers.turn import TurnHeuristicProvider

    _HAS_TURN_PROVIDER = True
except ImportError:
    _HAS_TURN_PROVIDER = False

from app.domain.spot import NodeContext, Street  # noqa: E402

_HAS_TURN_CTX = hasattr(NodeContext, "TURN_BARREL")


def test_turn_provider_supports_turn_barrel_spot():
    if not (_HAS_TURN_PROVIDER and _HAS_TURN_CTX):
        import pytest

        pytest.skip("awaiting T3: providers/turn.py / NodeContext.TURN_BARREL")
    from factories import make_cbet_spot

    p = TurnHeuristicProvider()
    flop = make_cbet_spot()
    turn_spot = flop.model_copy(
        update={
            "street": Street.TURN,
            "board": [*flop.board, "2s"],
            "node_context": [NodeContext.TURN_BARREL],
        }
    )
    assert _run(p.supports(turn_spot)) is True


def test_turn_provider_rejects_flop_street():
    if not _HAS_TURN_PROVIDER:
        import pytest

        pytest.skip("awaiting T3: providers/turn.py")
    from factories import make_cbet_spot

    p = TurnHeuristicProvider()
    assert _run(p.supports(make_cbet_spot())) is False  # street=FLOP


def test_turn_provider_rejects_flop_contexts_on_turn_board():
    if not (_HAS_TURN_PROVIDER and _HAS_TURN_CTX):
        import pytest

        pytest.skip("awaiting T3: providers/turn.py / NodeContext.TURN_BARREL")
    from factories import make_cbet_spot

    p = TurnHeuristicProvider()
    flop = make_cbet_spot()
    turn_spot = flop.model_copy(
        update={"street": Street.TURN, "board": [*flop.board, "2s"]}  # node_context stays [CBET]
    )
    assert _run(p.supports(turn_spot)) is False


def test_turn_provider_rejects_board_len_three():
    if not (_HAS_TURN_PROVIDER and _HAS_TURN_CTX):
        import pytest

        pytest.skip("awaiting T3: providers/turn.py / NodeContext.TURN_BARREL")
    from factories import make_cbet_spot

    p = TurnHeuristicProvider()
    flop = make_cbet_spot()
    short_turn = flop.model_copy(
        update={"street": Street.TURN, "node_context": [NodeContext.TURN_BARREL]}
        # board deliberately left at length 3
    )
    assert _run(p.supports(short_turn)) is False


# --- S7: RiverHeuristicProvider gating (authored ahead of T3's providers/river.py;
# skips until app.domain.providers.river + NodeContext.RIVER_BARREL exist) ---

try:
    from app.domain.providers.river import RiverHeuristicProvider

    _HAS_RIVER_PROVIDER = True
except ImportError:
    _HAS_RIVER_PROVIDER = False

_HAS_RIVER_CTX = hasattr(NodeContext, "RIVER_BARREL")


def test_river_provider_supports_river_barrel_spot():
    if not (_HAS_RIVER_PROVIDER and _HAS_RIVER_CTX):
        import pytest

        pytest.skip("awaiting T3: providers/river.py / NodeContext.RIVER_BARREL")
    from factories import make_cbet_spot

    p = RiverHeuristicProvider()
    flop = make_cbet_spot()
    river_spot = flop.model_copy(
        update={
            "street": Street.RIVER,
            "board": [*flop.board, "2s", "3d"],
            "node_context": [NodeContext.RIVER_BARREL],
        }
    )
    assert _run(p.supports(river_spot)) is True


def test_river_provider_rejects_flop_street():
    if not _HAS_RIVER_PROVIDER:
        import pytest

        pytest.skip("awaiting T3: providers/river.py")
    from factories import make_cbet_spot

    p = RiverHeuristicProvider()
    assert _run(p.supports(make_cbet_spot())) is False  # street=FLOP


def test_river_provider_rejects_flop_and_turn_contexts_on_river_board():
    if not (_HAS_RIVER_PROVIDER and _HAS_RIVER_CTX):
        import pytest

        pytest.skip("awaiting T3: providers/river.py / NodeContext.RIVER_BARREL")
    from factories import make_cbet_spot

    p = RiverHeuristicProvider()
    flop = make_cbet_spot()
    river_flop_ctx = flop.model_copy(
        update={"street": Street.RIVER, "board": [*flop.board, "2s", "3d"]}
        # node_context stays [CBET]
    )
    assert _run(p.supports(river_flop_ctx)) is False
    river_turn_ctx = flop.model_copy(
        update={
            "street": Street.RIVER,
            "board": [*flop.board, "2s", "3d"],
            "node_context": [NodeContext.TURN_BARREL],
        }
    )
    assert _run(p.supports(river_turn_ctx)) is False


def test_river_provider_rejects_board_len_four():
    if not (_HAS_RIVER_PROVIDER and _HAS_RIVER_CTX):
        import pytest

        pytest.skip("awaiting T3: providers/river.py / NodeContext.RIVER_BARREL")
    from factories import make_cbet_spot

    p = RiverHeuristicProvider()
    flop = make_cbet_spot()
    short_river = flop.model_copy(
        update={
            "street": Street.RIVER,
            "board": [*flop.board, "2s"],
            "node_context": [NodeContext.RIVER_BARREL],
        }
        # board deliberately left at length 4
    )
    assert _run(p.supports(short_river)) is False


# --- S8: a multiway c-bet is graded (FOUND freq+EV), never NOT_FOUND ---
# Authored to T4's frozen `players_in_pot` builder kwarg
# (docs/ai-dlc/specs/simulate-s8.md) ahead of T4's scenarios.py landing
# mid-wave. Import/TypeError here (kwarg not yet added) is EXPECTED — report,
# do not patch T4's files.


def test_composite_routes_multiway_cbet_to_graded_verdict_not_not_found():
    import random

    from app.domain.scenarios import build_cbet_spot

    try:
        spot = build_cbet_spot(random.Random(9), eff_bb=100.0, players_in_pot=3)
    except TypeError:
        import pytest

        pytest.skip("T4 multiway seams (players_in_pot kwarg) not yet landed")

    p = get_provider()
    assert _run(p.supports(spot)) is True
    res = _run(p.optimal(spot))
    assert res.coverage == Coverage.FULL
    assert res.coverage != Coverage.NOT_FOUND
    assert res.provider == ProviderKind.HEURISTIC
