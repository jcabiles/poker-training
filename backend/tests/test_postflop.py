from app.domain.action import Decision
from app.domain.evaluation import Correctness
from app.domain.leaks import LeakCategory
from app.domain.postflop import grade_cbet, range_advantage
from app.domain.spot import (
    ActionType,
    GameConfig,
    Hero,
    LegalAction,
    NodeContext,
    PlayerState,
    Position,
    Spot,
    Stakes,
    Street,
)
from app.domain.texture import classify

SMALL, BIG = 2.0, 4.5


def _cbet_spot(hole, board, hero_pos=Position.BTN, villain_pos=Position.BB):
    return Spot(
        game=GameConfig(stakes=Stakes(sb=0.5, bb=1.0), table_size=9),
        street=Street.FLOP,
        board=board,
        pot_bb=6.0,
        hero=Hero(position=hero_pos, hole_cards=hole, stack_bb=100),
        players=[
            PlayerState(position=hero_pos, stack_bb=100, is_hero=True),
            PlayerState(position=villain_pos, stack_bb=100),
        ],
        effective_stack_bb=100,
        spr=15.0,
        to_act=hero_pos,
        node_context=[NodeContext.CBET],
        facing=villain_pos,
        legal_actions=[
            LegalAction(action=ActionType.CHECK),
            LegalAction(action=ActionType.BET, min_bb=SMALL),
            LegalAction(action=ActionType.BET, min_bb=BIG),
        ],
        hero_range="22+,A2s+,KTs+,ATo+,KQo",
        villain_range="22-99,A2s-AJs,KTs+,QJs,ATo-AJo,KJo+",
    )


def test_range_advantage_high_dry_favors_hero():
    tex = classify(["As", "Kd", "2c"])
    assert range_advantage(NodeContext.CBET, Position.BTN, Position.BB, tex) == "hero"


def test_range_advantage_low_connected_favors_villain():
    tex = classify(["7h", "6h", "5c"])
    adv = range_advantage(NodeContext.CBET, Position.BTN, Position.BB, tex)
    assert adv in ("villain", "neutral")


def test_dry_range_adv_small_bet_is_optimal():
    spot = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])  # top pair, dry, hero adv
    res = grade_cbet(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.BET, size_bb=SMALL)
    )
    assert res.correctness == Correctness.OPTIMAL
    assert res.best_action.action == ActionType.BET
    assert res.best_action.size_bb == SMALL
    assert res.leak_category == int(LeakCategory.FLOP_CBET)


def test_big_bet_oop_air_wet_is_worse():
    # CO opens, BTN calls -> hero (CO) is OOP; wet low board; pure air; barrel big.
    spot = _cbet_spot(
        ("As", "Kd"), ["9h", "8h", "6c"], hero_pos=Position.CO, villain_pos=Position.BTN
    )
    res = grade_cbet(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.BET, size_bb=BIG)
    )
    assert res.best_action.action == ActionType.CHECK
    assert res.correctness in (Correctness.MISTAKE, Correctness.BLUNDER)
    assert res.ev_loss_bb > POST_LOSS_FLOOR


def test_optimal_call_without_decision_has_no_chosen():
    spot = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])
    res = grade_cbet(spot, spot.hero_range, spot.villain_range, None)
    assert res.chosen_eval is None
    assert res.best_action is not None
    assert {e.action for e in res.per_action} == {ActionType.CHECK, ActionType.BET}


def test_frequencies_normalized():
    spot = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])
    res = grade_cbet(spot, spot.hero_range, spot.villain_range, None)
    total = sum(e.frequency for e in res.per_action)
    assert abs(total - 1.0) < 1e-6


POST_LOSS_FLOOR = 0.6
