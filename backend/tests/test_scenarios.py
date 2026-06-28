import asyncio
import random

from app.domain.content.models import ActionRange, Entry
from app.domain.providers import get_provider
from app.domain.scenarios import (
    RFI_POSITIONS,
    _entries,
    build_spot,
    sample_rfi_spot,
    sample_spot,
)
from app.domain.spot import ActionType, NodeContext, Position


def test_sample_rfi_is_valid():
    spot = sample_rfi_spot(random.Random(42))
    assert spot.hero.position in RFI_POSITIONS
    assert NodeContext.RFI in spot.node_context
    assert spot.hero.hole_cards[0] != spot.hero.hole_cards[1]
    assert any(a.action == ActionType.RAISE for a in spot.legal_actions)


def test_sample_is_deterministic_with_seed():
    a = sample_spot(random.Random(7))
    b = sample_spot(random.Random(7))
    assert a.hero.position == b.hero.position
    assert a.hero.hole_cards == b.hero.hole_cards
    assert a.node_context == b.node_context


def test_sample_varies_across_draws():
    rng = random.Random(123)
    hands = {sample_spot(rng).hero.hole_cards for _ in range(20)}
    assert len(hands) > 1


def test_every_entry_samples_to_full_coverage():
    """Content-driven sampling => every spot has a matching grading node."""
    provider = get_provider()
    rng = random.Random(0)
    for entry in _entries():
        spot = build_spot(entry, rng)
        assert asyncio.run(provider.supports(spot)) is True
        assert asyncio.run(provider.optimal(spot)).coverage.value == "full"


def test_golden_vs_rfi_spot():
    entry = Entry(
        node_context=NodeContext.VS_RFI,
        position=Position.CO,
        facing=Position.UTG,
        actions=[ActionRange(action=ActionType.RAISE, combos="QQ+", frequency=1.0)],
        sizing_bb=10.0,
    )
    spot = build_spot(entry, random.Random(1))
    assert spot.facing == Position.UTG
    assert spot.node_context == [NodeContext.VS_RFI]
    assert any(
        h.action == ActionType.RAISE and h.position == Position.UTG for h in spot.action_history
    )
    assert {la.action for la in spot.legal_actions} == {
        ActionType.FOLD,
        ActionType.CALL,
        ActionType.RAISE,
    }
    assert spot.pot_bb == 1.5 + 3.0  # UTG open = 3.0bb


def test_golden_vs_limpers_spot():
    entry = Entry(
        node_context=NodeContext.VS_LIMPERS,
        position=Position.BTN,
        limper_count=2,
        actions=[ActionRange(action=ActionType.RAISE, combos="77+", frequency=1.0)],
        sizing_bb=6.0,
    )
    spot = build_spot(entry, random.Random(1))
    assert spot.limper_count == 2
    limps = [h for h in spot.action_history if h.action == ActionType.CALL and h.amount_bb == 1.0]
    assert len(limps) == 2
    assert spot.pot_bb == 1.5 + 2.0
    assert {la.action for la in spot.legal_actions} == {
        ActionType.FOLD,
        ActionType.CALL,
        ActionType.RAISE,
    }


# --- Phase 1b: facing-aggression sampler ---
def test_golden_vs_3bet_spot():
    entry = Entry(
        node_context=NodeContext.VS_3BET,
        position=Position.CO,
        facing=Position.BTN,
        actions=[ActionRange(action=ActionType.RAISE, combos="QQ+", frequency=1.0)],
        sizing_bb=22.0,
    )
    spot = build_spot(entry, random.Random(1))
    assert spot.pot_bb == 11.5  # 1.5 + 2.5 open + 7.5 3bet
    call = next(la for la in spot.legal_actions if la.action == ActionType.CALL)
    assert call.min_bb == 5.0  # 7.5 - 2.5 (incremental)
    raise_ = next(la for la in spot.legal_actions if la.action == ActionType.RAISE)
    assert raise_.min_bb == 22.0
    assert sum(1 for p in spot.players if p.position == Position.BTN) == 1  # facing once


def test_golden_vs_4bet_spot():
    entry = Entry(
        node_context=NodeContext.VS_4BET,
        position=Position.BTN,
        facing=Position.CO,
        actions=[ActionRange(action=ActionType.RAISE, combos="AA", frequency=1.0)],
        sizing_bb=100.0,
    )
    spot = build_spot(entry, random.Random(1), eff_bb=100.0)
    assert spot.pot_bb == 28.75  # 1.5 + 2.5 + 7.5 + 17.25
    call = next(la for la in spot.legal_actions if la.action == ActionType.CALL)
    assert call.min_bb == 9.75  # 17.25 - 7.5
    jam = next(la for la in spot.legal_actions if la.action == ActionType.RAISE)
    assert jam.min_bb == 100.0 and jam.max_bb == 100.0  # jam = eff stack
    assert sum(1 for p in spot.players if p.position == Position.CO) == 1  # facing once


def test_bb_call_open_is_incremental():
    entry = Entry(
        node_context=NodeContext.BLIND_DEFENSE,
        position=Position.BB,
        facing=Position.BTN,
        actions=[ActionRange(action=ActionType.CALL, combos="22+", frequency=1.0)],
        sizing_bb=11.0,
    )
    spot = build_spot(entry, random.Random(1))
    call = next(la for la in spot.legal_actions if la.action == ActionType.CALL)
    assert call.min_bb == 1.5  # 2.5 open - 1.0 BB already posted


def test_depth_variety_yields_multiple_buckets():
    rng = random.Random(5)
    depths = {sample_spot(rng).effective_stack_bb for _ in range(30)}
    assert len(depths) >= 2


# --- Phase 1c: pool isolation ---
def test_baseline_pool_excludes_exploit_entries():
    from app.domain.scenarios import _entries

    assert _entries()
    assert all(e.villain_type is None for e in _entries())


def test_exploit_sampler_sets_villain_type():
    from app.domain.scenarios import sample_exploit_spot

    s = sample_exploit_spot(random.Random(3))
    assert s.villain_type is not None


# --- Phase 2a: flop c-bet spot ---
def test_cbet_spot_is_valid_flop_with_ranges():
    from app.domain.scenarios import build_cbet_spot
    from app.domain.spot import Street

    s = build_cbet_spot(random.Random(7), eff_bb=100.0)
    assert s.street == Street.FLOP
    assert len(s.board) == 3
    assert s.node_context == [NodeContext.CBET]
    assert s.hero_range and s.villain_range
    # hole cards and board are disjoint, all 5 distinct
    cards = list(s.hero.hole_cards) + s.board
    assert len(set(cards)) == 5
    # legal = check + two bet sizes
    actions = [la.action for la in s.legal_actions]
    assert actions.count(ActionType.BET) == 2
    assert ActionType.CHECK in actions
    assert s.spr is not None and s.spr > 0


def test_cbet_spot_signature_stable_across_seeds():
    from app.domain.scenarios import build_cbet_spot
    from app.domain.srs import spot_signature

    # Same pairing + same depth -> texture/SPR-bucketed signature should land in a
    # small stable set (not unique per board).
    sigs = {
        spot_signature(
            build_cbet_spot(random.Random(i), pairing=(Position.BTN, Position.BB), eff_bb=100.0)
        )
        for i in range(40)
    }
    assert len(sigs) < 40  # boards collapse into texture/SPR buckets


def test_cbet_spot_grades_via_provider():
    from app.domain.action import Decision
    from app.domain.providers import get_provider
    from app.domain.scenarios import build_cbet_spot

    s = build_cbet_spot(random.Random(11), eff_bb=100.0)
    p = get_provider()
    res = asyncio.run(p.evaluate(s, Decision(action=ActionType.CHECK)))
    assert res.leak_category == 200  # FLOP_CBET
    assert res.correctness is not None
