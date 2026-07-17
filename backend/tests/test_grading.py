import asyncio as _asyncio
import random as _random

from factories import make_rfi_spot

from app.domain.action import Decision
from app.domain.archetypes import VillainType
from app.domain.content.models import ActionRange, Entry
from app.domain.content.registry import build_index as _build_index
from app.domain.content.registry import load_preflop_packs as _load
from app.domain.evaluation import Correctness
from app.domain.grading import grade, leak_category_for, range_grid
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


# --- N5: range_grid returns per-action frequency mix, not a collapsed label ---
def test_range_grid_mixed_handclass_returns_per_action_freqs():
    grid = range_grid(_mixed_entry())
    mix = grid["A5s"]
    assert mix == {"raise": 0.6, "call": 0.4}
    assert abs(sum(mix.values()) - 1.0) < 1e-6


def test_range_grid_pure_handclass_returns_single_entry():
    grid = range_grid(rfi_entry(Position.CO, "22+, A2s+, AKo"))
    assert grid["AA"] == {"raise": 1.0}
    assert grid["72o"] == {"fold": 1.0}


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
    # N1: the exploit adjustment also reaches the tiered reasoning surface
    assert res.tiers is not None
    assert "station" in res.tiers.reasoning.lower()


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
    assert "station" in res.explanation.lower()  # flat explanation kept for backward compat
    # N1: the authored rationale now ALSO lands in the reasoning tier (the
    # user-facing surface), sourced from authored_rationale — not re-parsed prose.
    assert res.tiers is not None
    assert "station" in res.tiers.reasoning.lower()


# --- N3: per-RAISE eval-build + nearest-size _match + sizing verdict ---
def _two_size_rfi_spot():
    """An RFI spot carrying TWO RAISE legal actions (Simulate two-size case)."""
    spot = make_rfi_spot(hole_cards=("Ah", "Kh"), position=Position.CO)  # AKs
    return spot.model_copy(
        update={
            "legal_actions": [
                LegalAction(action=ActionType.FOLD),
                LegalAction(action=ActionType.RAISE, min_bb=2.5, max_bb=100.0),
                LegalAction(action=ActionType.RAISE, min_bb=3.5, max_bb=100.0),
            ],
        }
    )


def test_two_raise_sizes_recommended_is_optimal_bigger_is_acceptable():
    spot = _two_size_rfi_spot()
    entry = rfi_entry(Position.CO, "22+, A2s+, AKo")
    small = grade(spot, entry, Decision(action=ActionType.RAISE, size_bb=2.5))
    big = grade(spot, entry, Decision(action=ActionType.RAISE, size_bb=3.5))
    # action verdict unchanged (raising AKs is optimal either way)
    assert small.correctness == Correctness.OPTIMAL
    assert big.correctness == Correctness.OPTIMAL
    # sizing verdict distinguishes the two: smallest = recommended = OPTIMAL
    assert small.sizing_correctness == Correctness.OPTIMAL
    assert big.sizing_correctness == Correctness.ACCEPTABLE


def test_two_raise_match_picks_nearest_size():
    spot = _two_size_rfi_spot()
    entry = rfi_entry(Position.CO, "22+, A2s+, AKo")
    # chosen size 3.4 is nearest the 3.5 (bigger) eval -> ACCEPTABLE
    res = grade(spot, entry, Decision(action=ActionType.RAISE, size_bb=3.4))
    assert res.sizing_correctness == Correctness.ACCEPTABLE
    # chosen size 2.6 is nearest the 2.5 (recommended) eval -> OPTIMAL
    res2 = grade(spot, entry, Decision(action=ActionType.RAISE, size_bb=2.6))
    assert res2.sizing_correctness == Correctness.OPTIMAL


def test_standard_4bet_vs_shove_no_longer_grade_identically():
    """Direction test for the collision fix: two RAISE sizes at one node yield
    distinct evals (the old sizes-dict collapsed them into one)."""
    spot = make_rfi_spot(hole_cards=("Ah", "Ad"), position=Position.BTN).model_copy(
        update={
            "node_context": [NodeContext.VS_3BET],
            "facing": Position.CO,
            "legal_actions": [
                LegalAction(action=ActionType.FOLD),
                LegalAction(action=ActionType.CALL, min_bb=10.0),
                LegalAction(action=ActionType.RAISE, min_bb=22.0, max_bb=100.0),  # standard 4-bet
                LegalAction(action=ActionType.RAISE, min_bb=100.0, max_bb=100.0),  # shove
            ],
        }
    )
    entry = rfi_entry(Position.BTN, "AA, KK")
    res = grade(spot, entry, None)
    raise_evals = [e for e in res.per_action if e.action == ActionType.RAISE]
    # BOTH RAISE evals survive with distinct sizes (no action-keyed collision)
    assert len(raise_evals) == 2
    assert {e.size_bb for e in raise_evals} == {22.0, 100.0}


def test_single_raise_spot_has_no_sizing_verdict():
    """VS_4BET (cap): a single RAISE legal -> sizing_correctness stays None."""
    res = grade(
        _vs4bet_spot(("Ah", "Ad")),
        _vs4bet_entry(),
        Decision(action=ActionType.RAISE, size_bb=100.0),
    )
    assert res.correctness == Correctness.OPTIMAL
    assert res.sizing_correctness is None


def test_strict_superset_single_raise_byte_identical():
    """With <=1 RAISE legal, grade() output must match the pre-N3 next(...) match
    exactly (Practice + 4-bet+ unchanged). Assert full result equality against a
    hand-computed reference on a single-RAISE spot."""
    spot = make_rfi_spot(hole_cards=("Ah", "Kh"), position=Position.CO)  # AKs, single RAISE
    entry = rfi_entry(Position.CO, "22+, A2s+, AKo")
    dec = Decision(action=ActionType.RAISE, size_bb=2.5)
    res = grade(spot, entry, dec)
    # the chosen eval is the sole RAISE eval; no sizing verdict on a single raise
    raise_evals = [e for e in res.per_action if e.action == ActionType.RAISE]
    assert len(raise_evals) == 1
    assert res.sizing_correctness is None
    assert res.chosen_eval is not None
    assert res.chosen_eval.ev_bb == raise_evals[0].ev_bb
    assert res.chosen_eval.frequency == raise_evals[0].frequency


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
