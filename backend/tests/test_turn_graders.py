"""S6 — turn graders (2nd-barrel + facing-turn-bet).

Authored to the frozen interface in docs/ai-dlc/specs/simulate-s6.md /
docs/ai-dlc/contracts/simulate-s6.md, ahead of T3's domain/spot.py,
domain/postflop.py, domain/texture.py, and domain/providers/turn.py landing.
Import failures here (NodeContext.TURN_BARREL/VS_TURN_BET, grade_turn_barrel,
grade_vs_turn_bet, turn_card_class, TurnHeuristicProvider) are expected until
T3's slice lands mid-wave.

Turn spots are constructed via `factories.make_cbet_spot(...).model_copy(...)`
(street=TURN, board len 4, node_context=[the turn ctx]) — the pattern used by
test_provider.py's NOT_FOUND trio.
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

_HAS_TURN_ENUM = hasattr(NodeContext, "TURN_BARREL") and hasattr(NodeContext, "VS_TURN_BET")


def _has_turn_graders() -> bool:
    try:
        import app.domain.postflop as _pf  # noqa: PLC0415

        return hasattr(_pf, "grade_turn_barrel") and hasattr(_pf, "grade_vs_turn_bet")
    except ImportError:
        return False


def _has_turn_card_class() -> bool:
    try:
        import app.domain.texture as _tex  # noqa: PLC0415

        return hasattr(_tex, "turn_card_class")
    except ImportError:
        return False


def _has_turn_provider() -> bool:
    try:
        import app.domain.providers.turn  # noqa: F401, PLC0415

        return True
    except ImportError:
        return False


# Individual T3 pieces (spot.py enum, postflop.py graders, texture.py fn,
# providers/turn.py) land independently mid-wave — gate the whole module on
# ALL of them so tests degrade to a clean skip rather than an ImportError
# during the fan-in gap, and flip to running once T3's slice is complete.
_T3_READY = (
    _HAS_TURN_ENUM and _has_turn_graders() and _has_turn_card_class() and _has_turn_provider()
)

pytestmark = pytest.mark.skipif(
    not _T3_READY,
    reason="awaiting T3: spot.py enum / postflop.py graders / texture.py / providers/turn.py",
)


def _turn_barrel_spot(turn_card: str = "2s", hole_cards=("Ah", "Ks")):
    """Hero is the flop c-bettor+turn aggressor. Board: Ac Kd Qh + turn_card."""
    flop = make_cbet_spot(hole_cards=hole_cards, position=Position.BTN)
    return flop.model_copy(
        update={
            "street": Street.TURN,
            "board": [*flop.board, turn_card],
            "node_context": [NodeContext.TURN_BARREL],
        }
    )


def _vs_turn_bet_spot(turn_card: str = "2s", hole_cards=("Ah", "Ks")):
    """Hero called the flop c-bet and now faces a turn bet.

    Reuses make_check_raise_spot's shape only for its multi-street action
    history convenience; instead we build directly off make_cbet_spot with
    hero as the flop CALLER (mirrors vs_cbet's caller role) facing a turn bet.
    """
    flop = make_cbet_spot(hole_cards=hole_cards, position=Position.BTN)
    # Hero becomes the flop caller / turn facing-bet player: swap roles so
    # `facing` is the aggressor and hero has CALL/FOLD/RAISE legal actions.
    pot = flop.pot_bb + 2 * 6.0  # flop bet (~6bb) called by both
    bet = round(0.66 * pot, 1)
    return flop.model_copy(
        update={
            "street": Street.TURN,
            "board": [*flop.board, turn_card],
            "node_context": [NodeContext.VS_TURN_BET],
            "pot_bb": round(pot + bet, 2),
            "legal_actions": [
                *[la for la in flop.legal_actions if la.action == ActionType.CHECK],
            ]
            or None,
        }
    )


def _import_graders():
    from app.domain.postflop import grade_turn_barrel, grade_vs_turn_bet

    return grade_turn_barrel, grade_vs_turn_bet


def _import_turn_card_class():
    from app.domain.texture import turn_card_class

    return turn_card_class


def _import_turn_provider():
    from app.domain.providers.turn import TurnHeuristicProvider

    return TurnHeuristicProvider


# --- freq+EV verdicts, never boolean ---


def test_turn_barrel_result_is_freq_ev_never_boolean():
    grade_turn_barrel, _ = _import_graders()
    spot = _turn_barrel_spot()
    res = grade_turn_barrel(spot, spot.hero_range, spot.villain_range, None)
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


def test_vs_turn_bet_result_is_freq_ev_never_boolean():
    _, grade_vs_turn_bet = _import_graders()
    spot = _vs_turn_bet_spot()
    res = grade_vs_turn_bet(spot, spot.hero_range, spot.villain_range, None)
    assert res.per_action
    for a in res.per_action:
        assert isinstance(a.frequency, float)
        assert isinstance(a.ev_bb, float) and math.isfinite(a.ev_bb)


# --- correctness ladder ---


def test_turn_barrel_optimal_exact_match():
    grade_turn_barrel, _ = _import_graders()
    spot = _turn_barrel_spot()
    optimal_res = grade_turn_barrel(spot, spot.hero_range, spot.villain_range, None)
    best = optimal_res.best_action
    decision = Decision(action=best.action, size_bb=best.size_bb)
    res = grade_turn_barrel(spot, spot.hero_range, spot.villain_range, decision)
    assert res.correctness == Correctness.OPTIMAL
    assert res.ev_loss_bb == 0.0


def test_vs_turn_bet_blunder_folding_strong_hand_at_great_price():
    """Folding a very strong hand (top two pair) getting great odds vs a small
    turn bet is a clearly bad line -> blunder."""
    _, grade_vs_turn_bet = _import_graders()
    spot = _vs_turn_bet_spot(hole_cards=("Ah", "Ks"))  # top two pair on AcKdQh2s
    res = grade_vs_turn_bet(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.FOLD)
    )
    assert res.correctness in (Correctness.MISTAKE, Correctness.BLUNDER)
    assert res.ev_loss_bb > 0.0


# --- range_advantage differs by node context (non-tautological) ---


def test_range_advantage_differs_flop_vs_turn_context():
    from app.domain.postflop import range_advantage
    from app.domain.texture import classify

    board = ["7c", "6d", "2h"]  # low, connected, wet-ish — favors defender/villain on flop
    tex = classify(board)
    flop_label = range_advantage(NodeContext.CBET, Position.BTN, Position.BB, tex)
    turn_label = range_advantage(NodeContext.TURN_BARREL, Position.BTN, Position.BB, tex)
    assert flop_label != turn_label


# --- rationale/tiers name the turn-card class for a scare-card barrel spot ---


def test_turn_barrel_rationale_tags_name_scare_card():
    grade_turn_barrel, _ = _import_graders()
    turn_card_class = _import_turn_card_class()
    spot = _turn_barrel_spot(turn_card="Ts")  # As Kd Qh Ts -> completes a straight
    res = grade_turn_barrel(spot, spot.hero_range, spot.villain_range, None)
    assert len(res.rationale_tags) == 5
    node, adv, cat, wetness, turn_class = res.rationale_tags
    assert node == "turn_barrel"
    assert turn_class == turn_card_class(spot.board)
    assert turn_class in ("pairing", "flush", "straight", "over", "blank")


def test_turn_barrel_tiers_name_turn_card_class():
    from app.domain.feedback import compose_tiers

    grade_turn_barrel, _ = _import_graders()
    spot = _turn_barrel_spot(turn_card="Ts")  # straight-completing scare card
    res = grade_turn_barrel(spot, spot.hero_range, spot.villain_range, None)
    tiers = compose_tiers(spot, res, None)
    assert "straight" in tiers.reasoning.lower() or "scare" in tiers.reasoning.lower()


# --- leak_category wiring (both mapping sites) ---


def test_turn_barrel_leak_category_is_203():
    grade_turn_barrel, _ = _import_graders()
    spot = _turn_barrel_spot()
    res = grade_turn_barrel(spot, spot.hero_range, spot.villain_range, None)
    assert res.leak_category == 203
    assert res.leak_category == int(LeakCategory.TURN_BARREL)


def test_vs_turn_bet_leak_category_is_204():
    _, grade_vs_turn_bet = _import_graders()
    spot = _vs_turn_bet_spot()
    res = grade_vs_turn_bet(spot, spot.hero_range, spot.villain_range, None)
    assert res.leak_category == 204
    assert res.leak_category == int(LeakCategory.VS_TURN_BET)


def test_leak_category_for_maps_both_turn_contexts():
    # Proves the SECOND mapping site (grading.py::leak_category_for), the one
    # this ticket owns — independent of the grader-local hardcoded leak= lines.
    assert leak_category_for(NodeContext.TURN_BARREL, Position.BTN) == int(
        LeakCategory.TURN_BARREL
    )
    assert leak_category_for(NodeContext.VS_TURN_BET, Position.BTN) == int(
        LeakCategory.VS_TURN_BET
    )


# --- TurnHeuristicProvider (supports gating) ---


def test_turn_provider_supports_turn_barrel_spot():
    import asyncio

    TurnHeuristicProvider = _import_turn_provider()
    p = TurnHeuristicProvider()
    spot = _turn_barrel_spot()
    assert asyncio.run(p.supports(spot)) is True


def test_turn_provider_rejects_flop_street():
    import asyncio

    TurnHeuristicProvider = _import_turn_provider()
    p = TurnHeuristicProvider()
    spot = make_cbet_spot()  # street=FLOP, node_context=[CBET]
    assert asyncio.run(p.supports(spot)) is False


def test_turn_provider_rejects_flop_context_on_turn_board():
    import asyncio

    TurnHeuristicProvider = _import_turn_provider()
    p = TurnHeuristicProvider()
    flop = make_cbet_spot()
    turn_spot = flop.model_copy(
        update={
            "street": Street.TURN,
            "board": [*flop.board, "2s"],
            "node_context": [NodeContext.CBET],  # flop ctx, not a turn ctx
        }
    )
    assert asyncio.run(p.supports(turn_spot)) is False


def test_turn_provider_rejects_short_board():
    import asyncio

    TurnHeuristicProvider = _import_turn_provider()
    p = TurnHeuristicProvider()
    flop = make_cbet_spot()
    short_turn = flop.model_copy(
        update={
            "street": Street.TURN,
            "node_context": [NodeContext.TURN_BARREL],
            # board deliberately left at flop length (3) — len(board) >= 4 required
        }
    )
    assert asyncio.run(p.supports(short_turn)) is False
