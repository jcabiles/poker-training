import asyncio as _asyncio
import random as _random

from factories import make_rfi_spot

from app.domain.action import Decision
from app.domain.archetypes import VillainType
from app.domain.content.models import ActionRange, Entry
from app.domain.content.registry import build_index as _build_index
from app.domain.content.registry import load_preflop_packs as _load
from app.domain.evaluation import Correctness
from app.domain.grading import grade, leak_category_for
from app.domain.hand_rank import hand_rank
from app.domain.leaks import LeakCategory
from app.domain.providers import get_provider as _get_provider
from app.domain.scenarios import build_spot as _build_spot
from app.domain.spot import ActionType, LegalAction, NodeContext, Position


def rfi_entry(pos: Position, combos: str) -> Entry:
    return Entry(
        node_context=NodeContext.RFI,
        position=pos,
        actions=[ActionRange(action=ActionType.RAISE, combos=combos, frequency=1.0)],
        sizing_bb=2.5,
    )


# --- hand_rank sanity ---
def test_hand_rank_orders_aa_top_trash_bottom():
    assert hand_rank("AA") == 1.0
    assert hand_rank("72o") < 0.2
    assert hand_rank("AA") > hand_rank("AKs") > hand_rank("A5s") > hand_rank("72o")


# --- named-hand grading anchors (from the spec) ---
def test_aa_fold_utg_is_blunder():
    spot = make_rfi_spot(hole_cards=("Ah", "Ad"), position=Position.UTG)
    res = grade(
        spot, rfi_entry(Position.UTG, "77+, AJs+, AQo+, KQs"), Decision(action=ActionType.FOLD)
    )
    assert res.correctness == Correctness.BLUNDER
    assert "over_fold" in res.rationale_tags


def test_72o_raise_utg_is_blunder():
    spot = make_rfi_spot(hole_cards=("7h", "2c"), position=Position.UTG)
    res = grade(
        spot,
        rfi_entry(Position.UTG, "77+, AJs+, AQo+, KQs"),
        Decision(action=ActionType.RAISE, size_bb=3.0),
    )
    assert res.correctness == Correctness.BLUNDER


def test_aks_raise_co_is_optimal():
    spot = make_rfi_spot(hole_cards=("Ah", "Kh"), position=Position.CO)  # AKs
    res = grade(
        spot,
        rfi_entry(Position.CO, "22+, A2s+, AKo"),
        Decision(action=ActionType.RAISE, size_bb=2.5),
    )
    assert res.correctness == Correctness.OPTIMAL
    assert res.best_action.action == ActionType.RAISE


def test_folding_trash_with_no_play_is_optimal():
    spot = make_rfi_spot(hole_cards=("7h", "2c"), position=Position.CO)
    res = grade(spot, rfi_entry(Position.CO, "22+, A2s+, AKo"), Decision(action=ActionType.FOLD))
    assert res.correctness == Correctness.OPTIMAL


# --- mixed spot (3-bet / call) ---
def _mixed_vs_rfi_spot():
    spot = make_rfi_spot(hole_cards=("Ah", "5h"), position=Position.BB)  # A5s
    return spot.model_copy(
        update={
            "node_context": [NodeContext.VS_RFI],
            "facing": Position.BTN,
            "legal_actions": [
                LegalAction(action=ActionType.FOLD),
                LegalAction(action=ActionType.CALL, min_bb=3.0),
                LegalAction(action=ActionType.RAISE, min_bb=9.0, max_bb=100.0),
            ],
        }
    )


def _mixed_entry() -> Entry:
    return Entry(
        node_context=NodeContext.VS_RFI,
        position=Position.BB,
        facing=Position.BTN,
        actions=[
            ActionRange(action=ActionType.RAISE, combos="A5s", frequency=0.6),
            ActionRange(action=ActionType.CALL, combos="A5s", frequency=0.4),
        ],
        sizing_bb=9.0,
    )


def test_mixed_top_action_optimal_alt_acceptable():
    spot, entry = _mixed_vs_rfi_spot(), _mixed_entry()
    raised = grade(spot, entry, Decision(action=ActionType.RAISE, size_bb=9.0))
    called = grade(spot, entry, Decision(action=ActionType.CALL, size_bb=3.0))
    assert raised.correctness == Correctness.OPTIMAL  # 3-bet is top (0.6)
    assert raised.is_mixed is True
    assert called.correctness == Correctness.ACCEPTABLE  # call played at 0.4


# --- leak mapping ---
def test_leak_category_mapping():
    co = make_rfi_spot(position=Position.CO)
    assert grade(co, rfi_entry(Position.CO, "22+"), None).leak_category == int(LeakCategory.RFI_CO)
    # BB facing an open -> blind defense, not vs_rfi
    spot, entry = _mixed_vs_rfi_spot(), _mixed_entry()
    assert grade(spot, entry, None).leak_category == int(LeakCategory.BLIND_DEFENSE)


# --- Phase 1b: facing-aggression nodes ---
def _vs4bet_spot(hole):
    spot = make_rfi_spot(hole_cards=hole, position=Position.BTN)
    return spot.model_copy(
        update={
            "node_context": [NodeContext.VS_4BET],
            "facing": Position.CO,
            "legal_actions": [
                LegalAction(action=ActionType.FOLD),
                LegalAction(action=ActionType.CALL, min_bb=10.0),
                LegalAction(action=ActionType.RAISE, min_bb=100.0, max_bb=100.0),
            ],
        }
    )


def _vs4bet_entry():
    return Entry(
        node_context=NodeContext.VS_4BET,
        position=Position.BTN,
        facing=Position.CO,
        actions=[
            ActionRange(action=ActionType.RAISE, combos="AA, KK, AKs", frequency=1.0),
            ActionRange(action=ActionType.CALL, combos="QQ, AKo", frequency=1.0),
        ],
        sizing_bb=100.0,
    )


def test_aa_jam_vs_4bet_is_optimal():
    res = grade(
        _vs4bet_spot(("Ah", "Ad")),
        _vs4bet_entry(),
        Decision(action=ActionType.RAISE, size_bb=100.0),
    )
    assert res.correctness == Correctness.OPTIMAL


def test_72o_jam_vs_4bet_is_blunder():
    res = grade(
        _vs4bet_spot(("7h", "2c")),
        _vs4bet_entry(),
        Decision(action=ActionType.RAISE, size_bb=100.0),
    )
    assert res.correctness == Correctness.BLUNDER


def test_vs3bet_ip_oop_and_4bet_leak_mapping():
    assert leak_category_for(NodeContext.VS_3BET, Position.CO, Position.BTN) == int(
        LeakCategory.VS_3BET_OOP
    )
    assert leak_category_for(NodeContext.VS_3BET, Position.BTN, Position.BB) == int(
        LeakCategory.VS_3BET_IP
    )
    assert leak_category_for(NodeContext.VS_4BET, Position.BTN, Position.CO) == int(
        LeakCategory.FOURBET_RESPONSE
    )


def test_exploit_spot_leak_is_per_archetype():
    from app.domain.archetypes import VillainType

    spot = make_rfi_spot(position=Position.CO).model_copy(update={"villain_type": VillainType.NIT})
    res = grade(spot, rfi_entry(Position.CO, "22+"), None)
    assert res.leak_category == int(LeakCategory.NIT_EXPLOIT)


# --- Phase 1c: exploit grading (via provider, real content) ---
_EIDX = _build_index(_load())


def _exploit_spot(node, pos, facing, limper, villain, hole):
    entry = _EIDX[(node, pos, facing, limper or 0, villain)]
    spot = _build_spot(entry, _random.Random(1))
    return spot.model_copy(update={"hero": spot.hero.model_copy(update={"hole_cards": hole})})


def test_thin_value_iso_vs_station_is_optimal():
    p = _get_provider()
    spot = _exploit_spot(
        NodeContext.VS_LIMPERS, Position.CO, None, 1, VillainType.CALLING_STATION, ("Jh", "9h")
    )
    res = _asyncio.run(p.evaluate(spot, Decision(action=ActionType.RAISE, size_bb=6.0)))
    assert res.correctness == Correctness.OPTIMAL
    assert "exploit" in res.rationale_tags
    assert res.leak_category == int(LeakCategory.CALLING_STATION_EXPLOIT)


def test_3bet_bluff_vs_station_worse_than_baseline():
    p = _get_provider()
    exploit_spot = _exploit_spot(
        NodeContext.VS_RFI,
        Position.BTN,
        Position.CO,
        None,
        VillainType.CALLING_STATION,
        ("Ah", "5h"),
    )
    base_spot = exploit_spot.model_copy(update={"villain_type": None})
    dec = Decision(action=ActionType.RAISE, size_bb=8.0)
    ex = _asyncio.run(p.evaluate(exploit_spot, dec))
    ba = _asyncio.run(p.evaluate(base_spot, dec))
    assert ex.ev_loss_bb > ba.ev_loss_bb  # 3-bet-bluffing a station is a leak; baseline it's fine


def test_exploit_explanation_carries_rationale():
    p = _get_provider()
    spot = _exploit_spot(
        NodeContext.VS_RFI,
        Position.BTN,
        Position.CO,
        None,
        VillainType.CALLING_STATION,
        ("Ah", "5h"),
    )
    res = _asyncio.run(p.optimal(spot))
    assert "exploit" in res.rationale_tags
    assert "station" in res.explanation.lower()


def test_marginal_offchart_call_is_not_a_blunder():
    # Q5o calling a CO open from the BB is a loose/thin call, not a blunder (calibration).
    p = _get_provider()
    entry = _EIDX[(NodeContext.BLIND_DEFENSE, Position.BB, Position.CO, 0, None)]
    base = _build_spot(entry, _random.Random(1))
    spot = base.model_copy(
        update={"hero": base.hero.model_copy(update={"hole_cards": ("Qd", "5s")})}
    )
    res = _asyncio.run(p.evaluate(spot, Decision(action=ActionType.CALL, size_bb=1.5)))
    assert res.correctness is not Correctness.BLUNDER
