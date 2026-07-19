"""N5 — 3-way multiway BB-defense mappers: canonical shapes map, everything
else stays "no baseline yet", and the dormant "mw" signature dimension goes
live without touching HU hashes.

Scope pins (the enumerated still-None matrix from the spec): limped multiway,
donk leads, 4+-way, caller raises (hero faces a raise, not the bet), delayed
c-bets (checked-through flop), and hero-not-BB multiway all return None.
"""

from __future__ import annotations

import random

import pytest

from app.domain.action import Decision
from app.domain.scenarios import _OPEN_SIZE, _SEAT_ORDER
from app.domain.spot import ActionType, NodeContext, Position, Street, players_in_pot
from app.domain.srs import spot_signature
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


def _play(state: HandState, moves) -> HandState:
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


def _raise_to(pos, size):
    return (pos, Decision(action=ActionType.RAISE, size_bb=size))


def _mw_preflop(opener=Position.CO, caller=Position.BTN, stacks=100.0):
    """3-way SRP: opener raises canonical, `caller` cold-calls, BB (hero) calls."""
    state = _state(Position.BB, stacks=stacks)
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        if p is opener:
            moves.append(_raise_to(p, _OPEN_SIZE[opener]))
        elif p is caller:
            moves.append(_call(p))
        else:
            moves.append(_fold(p))
    moves += [_fold(Position.SB), _call(Position.BB)]
    return _play(state, moves), opener, caller


def _flop_pot(opener):
    return round(3 * _OPEN_SIZE[opener] + 0.5, 2)


def _mw_flop_facing(opener=Position.CO, caller=Position.BTN, respond="call", frac=0.33):
    state, opener, caller = _mw_preflop(opener, caller)
    cbet = round(frac * _flop_pot(opener), 1)
    responder = _call(caller) if respond == "call" else _fold(caller)
    return _play(state, [_check(Position.BB), _bet(opener, cbet), responder]), cbet


# ------------------------------------------------------ canonical shapes map


@pytest.mark.parametrize(
    "opener,caller", [(Position.CO, Position.BTN), (Position.UTG, Position.CO)]
)
def test_mw_flop_vs_cbet_maps(opener, caller):
    state, cbet = _mw_flop_facing(opener, caller)
    assert state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_CBET]
    assert players_in_pot(spot) == 3
    assert spot.facing == opener


def test_mw_flop_caller_folded_maps_as_two_live():
    # Caller folds to the c-bet: hero still closes; the spot has 2 live
    # players (plain HU grading) with the caller's dead money in the pot.
    state, cbet = _mw_flop_facing(respond="fold")
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert players_in_pot(spot) == 2
    assert spot.pot_bb == round(_flop_pot(Position.CO) + cbet, 2)


def test_mw_turn_and_river_map_on_continuation_line():
    opener, caller = Position.CO, Position.BTN
    state, _o, _c = _mw_preflop(opener, caller)
    fp = _flop_pot(opener)
    fbet = round(0.33 * fp, 1)
    state = _play(state, [
        _check(Position.BB), _bet(opener, fbet), _call(caller), _call(Position.BB),
    ])
    turn_pot = round(fp + 3 * fbet, 2)
    tbet = round(0.5 * turn_pot, 1)
    state = _play(state, [_check(Position.BB), _bet(opener, tbet), _call(caller)])
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_TURN_BET]
    assert players_in_pot(spot) == 3
    # continue: hero calls; river continuation
    state = apply(state, Decision(action=ActionType.CALL))
    river_pot = round(turn_pot + 3 * tbet, 2)
    rbet = round(0.5 * river_pot, 1)
    state = _play(state, [_check(Position.BB), _bet(opener, rbet), _call(caller)])
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_RIVER_BET]
    assert players_in_pot(spot) == 3


def test_mw_signature_distinct_from_hu_and_stable():
    # The dormant "mw" signature dimension goes live: a 3-live spot hashes
    # differently from an equivalent-shape HU spot, deterministically.
    state, _ = _mw_flop_facing()
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    sig = spot_signature(spot)
    assert sig == spot_signature(spot)  # stable
    hu_like = spot.model_copy(
        update={
            "players": [
                p if p.is_hero or p.position == spot.facing
                else p.model_copy(update={"status": "folded"})
                for p in spot.players
            ]
        }
    )
    assert spot_signature(hu_like) != sig  # "mw" is the differentiator


# ------------------------------------------------------- still-None matrix


def test_limped_multiway_stays_none():
    state = _state(Position.BB)
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        moves.append(_call(p) if p in (Position.CO, Position.BTN) else _fold(p))
    moves += [_fold(Position.SB), _check(Position.BB)]
    state = _play(state, moves)
    pot = round(2.0 * 2 + 2.0 + 0.5, 2)
    state = _play(
        state,
        [_check(Position.BB), _bet(Position.CO, round(0.33 * pot, 1)), _call(Position.BTN)],
    )
    assert map_decision_point(state, HERO_SEAT) is None


def test_donk_lead_stays_none():
    # BB leads into the field — no grader family for donk bets.
    state, opener, caller = _mw_preflop()
    fp = _flop_pot(opener)
    state = _play(state, [_bet(Position.BB, round(0.33 * fp, 1))])
    # hero already acted (hero IS the BB donking) — walk one seat: opener faces.
    # The relevant assertion: a 3-way street whose first action is a BB BET can
    # never reach the hero-closes vs-cbet gate; play it to hero's next node.
    state = _play(state, [_call(opener), _call(caller)])
    # turn: BB donk-leads again; hero decision point is the donk itself — the
    # PRE-decision state (before hero bets) is what the mapper sees:
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_four_way_stays_none():
    state = _state(Position.BB)
    entrants = (Position.HJ, Position.CO, Position.BTN)
    opener = Position.HJ
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        if p is opener:
            moves.append(_raise_to(p, _OPEN_SIZE[opener]))
        elif p in entrants:
            moves.append(_call(p))
        else:
            moves.append(_fold(p))
    moves += [_fold(Position.SB), _call(Position.BB)]
    state = _play(state, moves)
    pot = round(4 * _OPEN_SIZE[opener] + 0.5, 2)
    cbet = round(0.33 * pot, 1)
    state = _play(state, [
        _check(Position.BB), _bet(opener, cbet), _call(Position.CO), _call(Position.BTN),
    ])
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_caller_raise_stays_none():
    # Caller raises the c-bet: hero faces a raise, not the canonical bet.
    state, opener, caller = _mw_preflop()
    fp = _flop_pot(opener)
    cbet = round(0.33 * fp, 1)
    state = _play(state, [
        _check(Position.BB), _bet(opener, cbet), _raise_to(caller, round(3 * cbet, 1)),
    ])
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_delayed_cbet_stays_none():
    # Flop checks through, opener bets the TURN — delayed c-bet, no grader.
    state, opener, caller = _mw_preflop()
    state = _play(state, [_check(Position.BB), _check(opener), _check(caller)])
    fp = _flop_pot(opener)
    tbet = round(0.5 * fp, 1)
    state = _play(state, [_check(Position.BB), _bet(opener, tbet), _call(caller)])
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None
