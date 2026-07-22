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


# --------------------------------------------------- M1 funnel levers (L3+L4)


def test_mw_ranges_all_caller_pairs_present():
    # L3: every ordered non-blind (opener, caller) pair — all 21 — resolves
    # `_mw_ranges` (RFI + BB-defense + the VS_RFI caller entry). Pre-M1, 12
    # pairs returned None (RES-I §3 L3: the content gate that killed 100% of
    # the baseline's fully-canonical 3-way arrivals).
    from app.domain.table.grade_map_postflop import _mw_ranges

    order = [
        Position.UTG, Position.UTG1, Position.UTG2, Position.LJ,
        Position.HJ, Position.CO, Position.BTN,
    ]
    for i, opener in enumerate(order[:-1]):
        for caller in order[i + 1 :]:
            # M6: _mw_ranges takes the caller POSITIONS as an iterable.
            assert _mw_ranges(opener, [caller]) is not None, (opener, caller)


def test_recognized_fracs_map_to_res_e_buckets():
    # L4 pass/fail (c): every recognized faced fraction maps to a DEFINED
    # RES-E bucket (never a silent collapse into a neighboring bucket), and
    # hero's offered fractions stay a subset of the recognition grid.
    from app.domain.personas_postflop import SizeBucket, size_bucket
    from app.domain.table.sizing import POSTFLOP_BET_FRACS, RECOGNIZED_BET_FRACS

    expected = {
        0.33: SizeBucket.SMALL,
        0.5: SizeBucket.MEDIUM,
        0.75: SizeBucket.LARGE,
        1.0: SizeBucket.LARGE,
        1.5: SizeBucket.OVERBET,
    }
    assert set(RECOGNIZED_BET_FRACS) == set(expected)  # the full persona grid
    for frac, bucket in expected.items():
        assert size_bucket(frac) is bucket
    for pair in POSTFLOP_BET_FRACS.values():
        assert set(pair) <= set(RECOGNIZED_BET_FRACS)


@pytest.mark.parametrize(
    "frac,bucket_name", [(0.5, "medium"), (1.0, "large"), (1.5, "overbet")]
)
def test_mw_grid_size_cbet_maps_with_true_price(frac, bucket_name):
    # L4: persona-grid c-bet sizes beyond the hero pair (0.33/0.75) now map,
    # and the built spot carries the TRUE bet in its CALL leg + pot math — the
    # graders' price (faced/pot) and `faced_bet_bucket` see the live
    # pot-fraction, never a 0.33-collapsed one (RES-I §5 HIGH flag).
    from app.domain.personas_postflop import size_bucket

    state, cbet = _mw_flop_facing(frac=frac)
    assert state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_CBET]
    fp = _flop_pot(Position.CO)
    call = next(la for la in spot.legal_actions if la.action is ActionType.CALL)
    assert call.min_bb == cbet  # the ACTUAL bet, true price preserved
    assert spot.pot_bb == round(fp + 2 * cbet, 2)
    assert size_bucket(cbet / fp).value == bucket_name  # defined RES-E bucket


def test_off_grid_size_still_gates():
    # A bet off the whole recognition grid (0.42-pot sits between 0.33 and 0.5,
    # outside the 0.06bb tolerance of both at this pot) still returns None.
    state, _cbet = _mw_flop_facing(frac=0.42)
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


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


def test_four_way_hero_closes_now_maps():
    # N5 pinned 4-way as None; M6 (RES-H H2) widened the gate — this exact
    # hero-closes 4-way shape now maps through the dispatcher. The remaining
    # None boundaries (5+-way, live player behind hero) are pinned in
    # tests/domain/test_apply_multiway_opp.py.
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
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None and spot.node_context == [NodeContext.VS_CBET]


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
