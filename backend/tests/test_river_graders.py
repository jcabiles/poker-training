"""S7 — river graders (2nd-and-3rd barrel + facing-river-bet).

Authored to the frozen interface in docs/ai-dlc/specs/simulate-s7.md /
docs/ai-dlc/contracts/simulate-s7.md, ahead of T3's domain/spot.py,
domain/postflop.py, domain/texture.py, and domain/providers/river.py landing.
Import failures here (NodeContext.RIVER_BARREL/VS_RIVER_BET, grade_river_barrel,
grade_vs_river_bet, river_card_class, RiverHeuristicProvider) are expected until
T3's slice lands mid-wave.

River spots are constructed via `factories.make_cbet_spot(...).model_copy(...)`
(street=RIVER, board len 5, node_context=[the river ctx]) — the pattern used by
test_turn_graders.py (itself cloned from test_provider.py's NOT_FOUND trio).
"""

from __future__ import annotations

import math

import pytest
from factories import make_cbet_spot

from app.domain.action import Decision
from app.domain.evaluation import Correctness
from app.domain.grading import leak_category_for
from app.domain.leaks import LeakCategory
from app.domain.spot import ActionType, NodeContext, Position, Street

_HAS_RIVER_ENUM = hasattr(NodeContext, "RIVER_BARREL") and hasattr(NodeContext, "VS_RIVER_BET")


def _has_river_graders() -> bool:
    try:
        import app.domain.postflop as _pf  # noqa: PLC0415

        return hasattr(_pf, "grade_river_barrel") and hasattr(_pf, "grade_vs_river_bet")
    except ImportError:
        return False


def _has_river_card_class() -> bool:
    try:
        import app.domain.texture as _tex  # noqa: PLC0415

        return hasattr(_tex, "river_card_class")
    except ImportError:
        return False


def _has_river_provider() -> bool:
    try:
        import app.domain.providers.river  # noqa: F401, PLC0415

        return True
    except ImportError:
        return False


# Individual T3 pieces (spot.py enum, postflop.py graders, texture.py fn,
# providers/river.py) land independently mid-wave — gate the whole module on
# ALL of them so tests degrade to a clean skip rather than an ImportError
# during the fan-in gap, and flip to running once T3's slice is complete.
_T3_READY = (
    _HAS_RIVER_ENUM and _has_river_graders() and _has_river_card_class() and _has_river_provider()
)

pytestmark = pytest.mark.skipif(
    not _T3_READY,
    reason="awaiting T3: spot.py enum / postflop.py graders / texture.py / providers/river.py",
)


def _river_barrel_spot(river_card: str = "2s", hole_cards=("Ah", "Ks")):
    """Hero is the flop c-bettor + turn barreler deciding the river.

    Board: Ac Kd Qh Ts (turn) + river_card.
    """
    flop = make_cbet_spot(hole_cards=hole_cards, position=Position.BTN)
    return flop.model_copy(
        update={
            "street": Street.RIVER,
            "board": [*flop.board, "Ts", river_card],
            "node_context": [NodeContext.RIVER_BARREL],
        }
    )


def _vs_river_bet_spot(river_card: str = "2s", hole_cards=("Ah", "Ks")):
    """Hero called the flop c-bet and turn barrel, now faces a river bet."""
    flop = make_cbet_spot(hole_cards=hole_cards, position=Position.BTN)
    # flop bet (~6bb) + turn bet (~10bb), both called by both players.
    pot = flop.pot_bb + 2 * 6.0 + 2 * 10.0
    bet = round(0.66 * pot, 1)
    return flop.model_copy(
        update={
            "street": Street.RIVER,
            "board": [*flop.board, "Ts", river_card],
            "node_context": [NodeContext.VS_RIVER_BET],
            "pot_bb": round(pot + bet, 2),
            "legal_actions": [
                *[la for la in flop.legal_actions if la.action == ActionType.CHECK],
            ]
            or None,
        }
    )


def _import_graders():
    from app.domain.postflop import grade_river_barrel, grade_vs_river_bet

    return grade_river_barrel, grade_vs_river_bet


def _import_river_card_class():
    from app.domain.texture import river_card_class

    return river_card_class


def _import_river_provider():
    from app.domain.providers.river import RiverHeuristicProvider

    return RiverHeuristicProvider


# --- freq+EV verdicts, never boolean ---


def test_river_barrel_result_is_freq_ev_never_boolean():
    grade_river_barrel, _ = _import_graders()
    spot = _river_barrel_spot()
    res = grade_river_barrel(spot, spot.hero_range, spot.villain_range, None)
    assert res.per_action  # populated
    for a in res.per_action:
        assert isinstance(a.frequency, float)
        assert isinstance(a.ev_bb, float) and math.isfinite(a.ev_bb)
    assert res.correctness is None or res.correctness in (
        Correctness.OPTIMAL,
        Correctness.ACCEPTABLE,
        Correctness.MISTAKE,
        Correctness.BLUNDER,
    )
    assert not isinstance(res.coverage, bool)


def test_vs_river_bet_result_is_freq_ev_never_boolean():
    _, grade_vs_river_bet = _import_graders()
    spot = _vs_river_bet_spot()
    res = grade_vs_river_bet(spot, spot.hero_range, spot.villain_range, None)
    assert res.per_action
    for a in res.per_action:
        assert isinstance(a.frequency, float)
        assert isinstance(a.ev_bb, float) and math.isfinite(a.ev_bb)


# --- correctness ladder ---


def test_river_barrel_optimal_exact_match():
    grade_river_barrel, _ = _import_graders()
    spot = _river_barrel_spot()
    optimal_res = grade_river_barrel(spot, spot.hero_range, spot.villain_range, None)
    best = optimal_res.best_action
    decision = Decision(action=best.action, size_bb=best.size_bb)
    res = grade_river_barrel(spot, spot.hero_range, spot.villain_range, decision)
    assert res.correctness == Correctness.OPTIMAL
    assert res.ev_loss_bb == 0.0


def test_vs_river_bet_blunder_folding_strong_hand_at_great_price():
    """Folding a very strong hand (top two pair) getting great odds vs a river
    bet is a clearly bad line -> blunder."""
    _, grade_vs_river_bet = _import_graders()
    spot = _vs_river_bet_spot(hole_cards=("Ah", "Ks"))  # top two pair on AcKdQhTs2s
    res = grade_vs_river_bet(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.FOLD)
    )
    assert res.correctness in (Correctness.MISTAKE, Correctness.BLUNDER)
    assert res.ev_loss_bb > 0.0


# --- busted-draw demotion (contract §4, top hazard) ---


def test_vs_river_bet_busted_flush_draw_best_action_is_not_value():
    """A busted flush-draw hand (4 hearts across hole+board, no 5th heart on
    the river) facing a river bet: best action must be FOLD (or a bluff-raise
    at meaningful mass), never a value line. tags[2] must read "air", not
    "draw" -- the busted-draw demotion (Gate-1 top hazard)."""
    _, grade_vs_river_bet = _import_graders()
    # Ah-Kh hole; board Qh-9h-2c-Ts-3d has 3 hearts on it (2 hole + 3 board = 5
    # hearts?) -- construct explicitly so the flush draw busts (4 hearts total,
    # no 5th) on the river.
    hole_cards = ("Ah", "Kh")
    flop = make_cbet_spot(hole_cards=hole_cards, position=Position.BTN)
    board = ["Qh", "9h", "2c", "Ts", "3d"]  # 2 hole hearts + 2 board hearts = 4, bricked river
    pot = flop.pot_bb + 2 * 6.0 + 2 * 10.0
    bet = round(0.66 * pot, 1)
    spot = flop.model_copy(
        update={
            "street": Street.RIVER,
            "board": board,
            "node_context": [NodeContext.VS_RIVER_BET],
            "pot_bb": round(pot + bet, 2),
            "legal_actions": [
                *[la for la in flop.legal_actions if la.action == ActionType.CHECK],
            ]
            or None,
        }
    )
    res = grade_vs_river_bet(spot, spot.hero_range, spot.villain_range, None)
    assert res.best_action.action in (ActionType.FOLD, ActionType.RAISE)
    tags = res.rationale_tags
    assert tags[2] == "air"


def test_river_barrel_busted_draw_demotion_not_a_value_bet():
    """Same busted-flush-draw hand as the river aggressor: cat_effective must
    demote to 'air' (never the 1.2 value tier a raw 'draw' category carries)."""
    grade_river_barrel, _ = _import_graders()
    hole_cards = ("Ah", "Kh")
    flop = make_cbet_spot(hole_cards=hole_cards, position=Position.BTN)
    board = ["Qh", "9h", "2c", "Ts", "3d"]
    spot = flop.model_copy(
        update={
            "street": Street.RIVER,
            "board": board,
            "node_context": [NodeContext.RIVER_BARREL],
        }
    )
    res = grade_river_barrel(spot, spot.hero_range, spot.villain_range, None)
    tags = res.rationale_tags
    assert tags[2] == "air"


# --- range_advantage differs river-vs-flop (non-tautological) ---


def test_range_advantage_differs_flop_vs_river_context():
    from app.domain.postflop import range_advantage
    from app.domain.texture import classify

    board = ["7c", "6d", "2h"]  # low, connected, wet-ish — favors defender/villain on flop
    tex = classify(board)
    flop_label = range_advantage(NodeContext.CBET, Position.BTN, Position.BB, tex)
    river_label = range_advantage(NodeContext.RIVER_BARREL, Position.BTN, Position.BB, tex)
    assert flop_label != river_label


# --- rationale/tiers name BOTH the turn-card and river-card class ---


def test_river_barrel_rationale_tags_are_6_wide_with_river_class():
    grade_river_barrel, _ = _import_graders()
    river_card_class = _import_river_card_class()
    spot = _river_barrel_spot(river_card="Js")  # Ac Kd Qh Ts Js -> completes a straight
    res = grade_river_barrel(spot, spot.hero_range, spot.villain_range, None)
    assert len(res.rationale_tags) == 6
    node, adv, cat, wetness, turn_class, river_class = res.rationale_tags
    assert node == "river_barrel"
    assert river_class == river_card_class(spot.board)
    assert river_class in ("pairing", "flush", "straight", "over", "blank")


def test_river_barrel_tiers_name_both_turn_and_river_card_class():
    from app.domain.feedback import _RIVER_CLASS, _TURN_CLASS, compose_tiers
    from app.domain.texture import river_card_class, turn_card_class

    grade_river_barrel, _ = _import_graders()
    # Ac Kd Qh Ts (straight-completing turn) + 2s (river bricks) — turn_class
    # and river_class deliberately DIFFER here ("straight" vs "blank"), so a
    # test that only exercised one of the two dispatch gates could not pass
    # by accident on a fixture where both classes happen to be equal.
    spot = _river_barrel_spot(river_card="2s")
    tclass = turn_card_class(spot.board)
    rclass = river_card_class(spot.board)
    assert tclass != rclass  # guards the fixture's own premise

    res = grade_river_barrel(spot, spot.hero_range, spot.villain_range, None)
    tiers = compose_tiers(spot, res, None)
    reasoning = tiers.reasoning

    # Exact sentence strings for THIS fixture's classes — no `or` fallback —
    # so the assertion only passes if BOTH the turn-class gate (tags[4]) and
    # the river-class gate (tags[5]) actually fired.
    assert _TURN_CLASS[tclass] in reasoning
    assert _RIVER_CLASS[rclass] in reasoning


# --- leak_category wiring (both mapping sites) ---


def test_river_barrel_leak_category_is_205():
    grade_river_barrel, _ = _import_graders()
    spot = _river_barrel_spot()
    res = grade_river_barrel(spot, spot.hero_range, spot.villain_range, None)
    assert res.leak_category == 205
    assert res.leak_category == int(LeakCategory.RIVER_BARREL)


def test_vs_river_bet_leak_category_is_206():
    _, grade_vs_river_bet = _import_graders()
    spot = _vs_river_bet_spot()
    res = grade_vs_river_bet(spot, spot.hero_range, spot.villain_range, None)
    assert res.leak_category == 206
    assert res.leak_category == int(LeakCategory.VS_RIVER_BET)


def test_leak_category_for_maps_both_river_contexts():
    # Proves the SECOND mapping site (grading.py::leak_category_for), the one
    # this ticket owns — independent of the grader-local hardcoded leak= lines.
    assert leak_category_for(NodeContext.RIVER_BARREL, Position.BTN) == int(
        LeakCategory.RIVER_BARREL
    )
    assert leak_category_for(NodeContext.VS_RIVER_BET, Position.BTN) == int(
        LeakCategory.VS_RIVER_BET
    )


# --- RiverHeuristicProvider (supports gating) ---


def test_river_provider_supports_river_barrel_spot():
    import asyncio

    RiverHeuristicProvider = _import_river_provider()
    p = RiverHeuristicProvider()
    spot = _river_barrel_spot()
    assert asyncio.run(p.supports(spot)) is True


def test_river_provider_rejects_flop_street():
    import asyncio

    RiverHeuristicProvider = _import_river_provider()
    p = RiverHeuristicProvider()
    spot = make_cbet_spot()  # street=FLOP, node_context=[CBET]
    assert asyncio.run(p.supports(spot)) is False


def test_river_provider_rejects_flop_context_on_river_board():
    import asyncio

    RiverHeuristicProvider = _import_river_provider()
    p = RiverHeuristicProvider()
    flop = make_cbet_spot()
    river_spot = flop.model_copy(
        update={
            "street": Street.RIVER,
            "board": [*flop.board, "Ts", "2s"],
            "node_context": [NodeContext.CBET],  # flop ctx, not a river ctx
        }
    )
    assert asyncio.run(p.supports(river_spot)) is False


def test_river_provider_rejects_turn_context_on_river_board():
    import asyncio

    RiverHeuristicProvider = _import_river_provider()
    p = RiverHeuristicProvider()
    flop = make_cbet_spot()
    river_spot = flop.model_copy(
        update={
            "street": Street.RIVER,
            "board": [*flop.board, "Ts", "2s"],
            "node_context": [NodeContext.TURN_BARREL],  # turn ctx, not a river ctx
        }
    )
    assert asyncio.run(p.supports(river_spot)) is False


def test_river_provider_rejects_short_board():
    import asyncio

    RiverHeuristicProvider = _import_river_provider()
    p = RiverHeuristicProvider()
    flop = make_cbet_spot()
    short_river = flop.model_copy(
        update={
            "street": Street.RIVER,
            "node_context": [NodeContext.RIVER_BARREL],
            # board deliberately left at length 4 — len(board) >= 5 required
            "board": [*flop.board, "Ts"],
        }
    )
    assert asyncio.run(p.supports(short_river)) is False
