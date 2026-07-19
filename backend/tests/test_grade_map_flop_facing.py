"""N4b — flop facing mappers (`map_flop_vs_cbet` / `map_flop_vs_check_raise`)
+ dispatcher widening.

Simulate's first flop facing-node coverage: hero-as-BB facing a canonical
c-bet (RAISE legs = flop check_raise mults 2.5x/3.5x the c-bet) and
hero-as-opener facing a check-raise (RAISE legs = plain raise mults
2.5x/3.0x the raise-to, CALL = the INCREMENTAL raise_to - cbet). Gate matrix:
off-size c-bet / multiway / off-line shapes stay None ("no baseline yet").
"""

from __future__ import annotations

import random

import pytest

from app.domain.action import Decision
from app.domain.scenarios import (
    _OPEN_SIZE,
    _SEAT_ORDER,
    build_check_raise_spot,
    build_vs_cbet_spot,
)
from app.domain.spot import ActionType, NodeContext, Position, Street
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, apply, start_hand
from app.domain.table.grade_map import map_decision_point

HERO_SEAT = 0
_BLINDS = {Position.SB, Position.BB}
_BUTTON_FOR_HERO = {
    Position.BTN: 0, Position.SB: 8, Position.BB: 7,
    Position.UTG: 6, Position.UTG1: 5, Position.UTG2: 4,
    Position.LJ: 3, Position.HJ: 2, Position.CO: 1,
}


def _state(hero_pos: Position, seed: int = 7, stacks: float = 100.0) -> HandState:
    dealt = deal_hand(random.Random(seed))
    return start_hand(
        dealt, button_seat=_BUTTON_FOR_HERO[hero_pos], stacks_bb=[stacks] * 9
    )


def _play(state: HandState, moves: list[tuple[Position, Decision]]) -> HandState:
    for pos, dec in moves:
        seat = next(s.seat for s in state.seats if s.position is pos)
        assert state.to_act_seat == seat, f"expected {pos} to act"
        state = apply(state, dec)
    return state


def _fold(pos):
    return (pos, Decision(action=ActionType.FOLD))


def _check(pos):
    return (pos, Decision(action=ActionType.CHECK))


def _call(pos):
    return (pos, Decision(action=ActionType.CALL))


def _bet(pos, size):
    return (pos, Decision(action=ActionType.BET, size_bb=size))


def _raise(pos, size):
    return (pos, Decision(action=ActionType.RAISE, size_bb=size))


def _before(pos):
    return _SEAT_ORDER[: _SEAT_ORDER.index(pos)]


def _flop_pot(opener: Position) -> float:
    return round(2 * _OPEN_SIZE[opener] + 0.5, 2)


def _srp_preflop_moves(opener: Position, osize: float) -> list:
    moves = [_fold(p) for p in _before(opener) if p not in _BLINDS]
    moves.append(_raise(opener, osize))
    moves += [
        _fold(p)
        for p in _SEAT_ORDER[_SEAT_ORDER.index(opener) + 1 :]
        if p not in _BLINDS
    ]
    moves += [_fold(Position.SB), _call(Position.BB)]
    return moves


def _vs_cbet_state(
    opener: Position,
    cbet_frac: float = 0.33,
    cbet_override: float | None = None,
    stacks: float = 100.0,
) -> HandState:
    """Hero = BB (seat 0) who called the open, checked the flop, and now faces
    the opener's c-bet."""
    state = _state(Position.BB, stacks=stacks)
    state = _play(state, _srp_preflop_moves(opener, _OPEN_SIZE[opener]))
    fp = _flop_pot(opener)
    cbet = cbet_override if cbet_override is not None else round(cbet_frac * fp, 1)
    return _play(state, [_check(Position.BB), _bet(opener, cbet)])


def _vs_check_raise_state(
    hero_pos: Position,
    cbet_frac: float = 0.33,
    raise_mult: float = 3.0,
    stacks: float = 100.0,
) -> HandState:
    """Hero (seat 0) opened, c-bet the flop, and the BB check-raised."""
    state = _state(hero_pos, stacks=stacks)
    state = _play(state, _srp_preflop_moves(hero_pos, _OPEN_SIZE[hero_pos]))
    fp = _flop_pot(hero_pos)
    cbet = round(cbet_frac * fp, 1)
    raise_to = round(raise_mult * cbet, 1)
    return _play(
        state,
        [_check(Position.BB), _bet(hero_pos, cbet), _raise(Position.BB, raise_to)],
    )


# --------------------------------------------------- canonical shapes map


@pytest.mark.parametrize("opener", [Position.UTG, Position.CO, Position.BTN])
@pytest.mark.parametrize("frac", [0.33, 0.75])
def test_vs_cbet_maps_with_builder_ranges(opener, frac):
    state = _vs_cbet_state(opener, cbet_frac=frac)
    assert state.street is Street.FLOP and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    built = build_vs_cbet_spot(
        random.Random(0), pairing=(opener, Position.BB), eff_bb=100.0
    )
    assert spot.hero_range == built.hero_range  # BB blind-defense call range
    assert spot.villain_range == built.villain_range  # opener RFI raise range
    assert spot.facing == built.facing == opener
    assert spot.node_context == [NodeContext.VS_CBET]
    assert spot.board == state.board and len(spot.board) == 3
    fp = _flop_pot(opener)
    cbet = round(frac * fp, 1)
    assert spot.pot_bb == round(fp + cbet, 2)  # pot INCLUDES the c-bet
    # Hero's raise is a CHECK-RAISE: flop-scoped RES-B mults 2.5x/3.5x the c-bet.
    assert [(la.action, la.min_bb) for la in spot.legal_actions] == [
        (ActionType.FOLD, None),
        (ActionType.CALL, cbet),
        (ActionType.RAISE, round(2.5 * cbet, 1)),
        (ActionType.RAISE, round(3.5 * cbet, 1)),
    ]


@pytest.mark.parametrize("hero_pos", [Position.UTG, Position.CO, Position.BTN])
@pytest.mark.parametrize("raise_mult", [2.5, 3.0])
def test_vs_check_raise_maps_with_incremental_call(hero_pos, raise_mult):
    state = _vs_check_raise_state(hero_pos, raise_mult=raise_mult)
    assert state.street is Street.FLOP and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    built = build_check_raise_spot(
        random.Random(0), pairing=(hero_pos, Position.BB), eff_bb=100.0
    )
    assert spot.hero_range == built.hero_range  # opener RFI raise range
    assert spot.villain_range == built.villain_range  # BB defend range
    assert spot.facing == built.facing == Position.BB
    assert spot.node_context == [NodeContext.VS_CHECK_RAISE]
    fp = _flop_pot(hero_pos)
    cbet = round(0.33 * fp, 1)
    raise_to = round(raise_mult * cbet, 1)
    assert spot.pot_bb == round(fp + cbet + raise_to, 2)
    # Refuter HIGH-1: CALL is the INCREMENTAL amount hero owes (hero already
    # invested the c-bet this street) — NOT the full raise-to. Hero's re-raise
    # is a plain facing-bet raise: 2.5x/3.0x the raise-to.
    assert [(la.action, la.min_bb) for la in spot.legal_actions] == [
        (ActionType.FOLD, None),
        (ActionType.CALL, round(raise_to - cbet, 2)),
        (ActionType.RAISE, round(2.5 * raise_to, 1)),
        (ActionType.RAISE, round(3.0 * raise_to, 1)),
    ]


def test_flop_cbet_node_still_maps_cbet():
    # Dispatcher disjointness: the hero-as-opener c-bet decision keeps mapping
    # to CBET (map_flop_cbet fires first and the facing mappers never claim it).
    state = _state(Position.BTN)
    state = _play(state, _srp_preflop_moves(Position.BTN, _OPEN_SIZE[Position.BTN]))
    state = _play(state, [_check(Position.BB)])
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.CBET]


# --------------------------------------------------- gate matrix → None


def test_off_size_cbet_gates_vs_cbet():
    # 0.5-pot is not a canonical flop c-bet bucket (0.33/0.75) → no baseline.
    fp = _flop_pot(Position.BTN)
    state = _vs_cbet_state(Position.BTN, cbet_override=round(0.5 * fp, 1))
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_three_way_bb_defense_now_maps_multiway():
    # N4b pinned this exact shape as None; N5's 3-way BB-defense mapper turns
    # it ON: opener + cold-caller + BB(hero), opener c-bets canonical, caller
    # responds, hero closes — maps as a 3-live multiway VS_CBET spot.
    from app.domain.spot import players_in_pot

    state = _state(Position.BB)
    opener = Position.CO
    moves = [_fold(p) for p in _before(opener) if p not in _BLINDS]
    moves.append(_raise(opener, _OPEN_SIZE[opener]))
    moves.append(_call(Position.BTN))  # cold-caller
    moves += [_fold(Position.SB), _call(Position.BB)]
    state = _play(state, moves)
    fp = round(3 * _OPEN_SIZE[opener] + 0.5, 2)
    cbet = round(0.33 * fp, 1)
    state = _play(
        state, [_check(Position.BB), _bet(opener, cbet), _call(Position.BTN)]
    )
    assert state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_CBET]
    assert players_in_pot(spot) == 3
    assert spot.facing == opener
    assert spot.pot_bb == round(fp + 2 * cbet, 2)  # bet + caller's call included
    # hero's raise legs: flop check-raise mults on the c-bet
    legs = [la.min_bb for la in spot.legal_actions if la.action is ActionType.RAISE]
    assert legs == [round(2.5 * cbet, 1), round(3.5 * cbet, 1)]


def test_short_stack_collapses_to_one_raise_leg():
    # Stacks 7.0: BB remaining on the flop = 4.5; small leg 2.5x1.8 = 4.5 —
    # big clamps onto small → ONE raise leg (the N4a collapse rule).
    state = _vs_cbet_state(Position.CO, stacks=7.0)
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    legs = [la.min_bb for la in spot.legal_actions if la.action is ActionType.RAISE]
    assert legs == [4.5]


def test_too_shallow_for_small_leg_gates_none():
    # Stacks 6.9: BB remaining 4.4 < the 4.5 small leg → no baseline at all.
    state = _vs_cbet_state(Position.CO, stacks=6.9)
    assert map_decision_point(state, HERO_SEAT) is None


def test_mid_stack_vs_check_raise_maps_via_all_in_ceiling():
    # Refuter-on-diff HIGH: hero (the c-bettor) already has the c-bet invested
    # this street, so raise-TO affordability keys on invested + stack (all-in-TO),
    # NOT chips behind. CO opens 2.5, c-bets 4.1 (0.75 pot), BB raises to 12.3;
    # small leg 2.5x = 30.8. Stacks 35: chips behind 28.4 < 30.8 but all-in-TO
    # 32.5 covers it -> the node MUST map (two legs, big clamped to 32.5).
    state = _vs_check_raise_state(
        Position.CO, cbet_frac=0.75, raise_mult=3.0, stacks=35.0
    )
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    legs = [la.min_bb for la in spot.legal_actions if la.action is ActionType.RAISE]
    assert legs == [30.8, 32.5]
    assert all(
        la.max_bb == 32.5
        for la in spot.legal_actions
        if la.action is ActionType.RAISE
    )


def test_mid_stack_vs_check_raise_collapse_and_gate():
    # Stacks 33.3: all-in-TO = 30.8 == the small leg -> big clamps onto small,
    # ONE leg. Stacks 33.2: all-in-TO 30.7 < 30.8 -> no baseline.
    collapsed = _vs_check_raise_state(
        Position.CO, cbet_frac=0.75, raise_mult=3.0, stacks=33.3
    )
    spot = map_decision_point(collapsed, HERO_SEAT)
    assert spot is not None
    legs = [la.min_bb for la in spot.legal_actions if la.action is ActionType.RAISE]
    assert legs == [30.8]

    too_shallow = _vs_check_raise_state(
        Position.CO, cbet_frac=0.75, raise_mult=3.0, stacks=33.2
    )
    assert map_decision_point(too_shallow, HERO_SEAT) is None


def test_bot_rounded_cbet_maps():
    # Design-review HIGH (reachability): bots size bets as round(f*pot, 2) —
    # e.g. 0.33 x 5.5 = 1.81/1.82bb — while the canonical value is the 1-dp 1.8.
    # The fraction gate must recognize the 2-dp bot rounding or every live
    # villain c-bet fails the gate and no facing node ever maps in play.
    fp = _flop_pot(Position.CO)
    for bot_cbet in (round(0.33 * fp, 2), round(0.33 * fp + 0.005, 2)):
        state = _vs_cbet_state(Position.CO, cbet_override=bot_cbet)
        spot = map_decision_point(state, HERO_SEAT)
        assert spot is not None, f"bot-style c-bet {bot_cbet} must map"
        assert spot.node_context == [NodeContext.VS_CBET]


# --------------------------------- N5: flop c-bet gate band alignment (A1)


def test_noncanonical_inband_open_maps_flop_cbet_with_actual_pot():
    # N5 refuter HIGH: a 2.5bb open from UTG (canonical 3.0) is in the same
    # standard band the turn/river mappers accept — the flop c-bet node must
    # now map too, with pot/bet math keyed on the ACTUAL 2.5 open.
    state = _state(Position.UTG)
    state = _play(state, _srp_preflop_moves(Position.UTG, 2.5))
    state = _play(state, [_check(Position.BB)])
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.CBET]
    pot = round(2 * 2.5 + 0.5, 2)  # actual open, NOT the canonical 3.0
    assert spot.pot_bb == pot
    bets = [la.min_bb for la in spot.legal_actions if la.action is ActionType.BET]
    assert bets == [round(0.33 * pot, 1), round(0.75 * pot, 1)]


def test_out_of_band_open_still_gates_flop_cbet():
    # Oversized opens (e.g. 4.0bb persona opens) stay unmapped — band cap holds.
    state = _state(Position.UTG)
    state = _play(state, _srp_preflop_moves(Position.UTG, 4.0))
    state = _play(state, [_check(Position.BB)])
    assert map_decision_point(state, HERO_SEAT) is None
