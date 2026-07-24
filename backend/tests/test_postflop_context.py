"""W3-a — unit tests for the postflop context derivations (A2/A3/A4).

Pure-derivation tests: they assert the three inputs are computed correctly.
The byte-identity half of W3-a's pass/fail (no consumer yet ⇒ every existing
suite unchanged) is covered by the untouched golden/coverage/limper fixtures,
which also exercise `derive_postflop_context` on real HandStates via the live
bot loop.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.spot import ActionType, HistoryAction, PlayerStatus, Position, Street
from app.domain.table.postflop_context import (
    BustedDraw,
    bet_prev_street,
    busted_draw_kind,
    derive_in_position,
    derive_postflop_context,
)


def _seat(i: int, status: PlayerStatus = PlayerStatus.IN) -> SimpleNamespace:
    return SimpleNamespace(seat=i, status=status)


def _ring(button: int, live: dict[int, PlayerStatus]) -> list[SimpleNamespace]:
    """9-seat ring; seats in `live` get their status, all others FOLDED."""
    return [
        _seat(i, live.get(i, PlayerStatus.FOLDED)) for i in range(9)
    ]


# ------------------------------------------------------------------ A2


def test_in_position_bvb_bb_is_ip_over_sb():
    # button 0 → SB seat 1 (acts first), BB seat 2 (acts last). BvB.
    seats = _ring(0, {1: PlayerStatus.IN, 2: PlayerStatus.IN})
    assert derive_in_position(seats, 0, 2) is True  # BB in position vs SB
    assert derive_in_position(seats, 0, 1) is False  # SB out of position


def test_in_position_multiway_last_live_seat_is_ip():
    # button 0; live SB(1), BB(2), CO(6). Postflop ranks 0,1,5 → seat 6 last.
    seats = _ring(0, {1: PlayerStatus.IN, 2: PlayerStatus.IN, 6: PlayerStatus.IN})
    assert derive_in_position(seats, 0, 6) is True
    assert derive_in_position(seats, 0, 2) is False
    assert derive_in_position(seats, 0, 1) is False


def test_in_position_allin_opponent_excluded():
    # An all-in seat that acts later does NOT keep me out of position.
    seats = _ring(0, {3: PlayerStatus.IN, 6: PlayerStatus.ALLIN})
    assert derive_in_position(seats, 0, 3) is True


def test_in_position_folded_opponent_excluded():
    seats = _ring(0, {3: PlayerStatus.IN, 7: PlayerStatus.FOLDED})
    assert derive_in_position(seats, 0, 3) is True


def test_in_position_button_acts_last():
    # button 4 is the last postflop actor regardless of live seats before it.
    seats = _ring(4, {4: PlayerStatus.IN, 5: PlayerStatus.IN, 7: PlayerStatus.IN})
    assert derive_in_position(seats, 4, 4) is True
    assert derive_in_position(seats, 4, 5) is False


def test_in_position_lone_live_seat_is_ip():
    seats = _ring(0, {5: PlayerStatus.IN})
    assert derive_in_position(seats, 0, 5) is True


# ------------------------------------------------------------------ A3


def _bet(street: Street, pos: Position) -> HistoryAction:
    return HistoryAction(street=street, position=pos, action=ActionType.BET, amount_bb=2.0)


def _check(street: Street, pos: Position) -> HistoryAction:
    return HistoryAction(street=street, position=pos, action=ActionType.CHECK, amount_bb=0.0)


def test_bet_prev_street_barrel_vs_delayed_stab():
    # CO bet the flop, then it is the turn: CO is barrelling (True); a seat
    # that only checked the flop (BB) is making a delayed stab (False). This is
    # exactly the barrel-vs-stab signal the sizing node needs — the whole-hand
    # is_aggressor label cannot separate them.
    hist = [_bet(Street.FLOP, Position.CO), _check(Street.FLOP, Position.BB)]
    assert bet_prev_street(hist, Street.TURN, Position.CO) is True
    assert bet_prev_street(hist, Street.TURN, Position.BB) is False


def test_bet_prev_street_preflop_raise_is_flop_aggressor():
    # The flop's previous street is preflop: the PFR "bet" the previous street.
    hist = [
        HistoryAction(
            street=Street.PREFLOP, position=Position.BTN, action=ActionType.RAISE, amount_bb=3.0
        )
    ]
    assert bet_prev_street(hist, Street.FLOP, Position.BTN) is True
    assert bet_prev_street(hist, Street.FLOP, Position.SB) is False


def test_bet_prev_street_turn_raise_carries_to_river():
    hist = [
        HistoryAction(
            street=Street.TURN, position=Position.SB, action=ActionType.RAISE, amount_bb=8.0
        )
    ]
    assert bet_prev_street(hist, Street.RIVER, Position.SB) is True


def test_bet_prev_street_preflop_has_no_predecessor():
    hist = [_bet(Street.PREFLOP, Position.CO)]
    assert bet_prev_street(hist, Street.PREFLOP, Position.CO) is False


def test_bet_prev_street_ignores_same_street_and_two_streets_back():
    # A bet TWO streets back (flop) does not count for the river; only the
    # immediately-preceding street (turn) does.
    hist = [_bet(Street.FLOP, Position.CO), _check(Street.TURN, Position.CO)]
    assert bet_prev_street(hist, Street.RIVER, Position.CO) is False


# ------------------------------------------------------------------ A4

# Turn flush draw (Jh Th + 2h 5h) that misses on a blank, non-pairing river.
_BUSTED_FLUSH = (("Jh", "Th"), ["2h", "5h", "9c", "3s", "8d"])
# Turn OESD (8c 9d + 6-7) with no flush; river Q misses (needs 5 or T).
_BUSTED_STRAIGHT = (("8c", "9d"), ["6h", "7s", "Kc", "2d", "Qs"])
# Same OESD but the river 5 completes the straight → not busted.
_COMPLETED_STRAIGHT = (("8c", "9d"), ["6h", "7s", "Kc", "2d", "5s"])
# No draw ever; air by the river.
_NO_DRAW = (("2c", "7d"), ["Kh", "9s", "4c", "Jd", "3s"])


def test_busted_flush_kind():
    assert busted_draw_kind(*_BUSTED_FLUSH) is BustedDraw.FLUSH


def test_busted_straight_kind():
    assert busted_draw_kind(*_BUSTED_STRAIGHT) is BustedDraw.STRAIGHT


def test_completed_straight_is_not_busted():
    assert busted_draw_kind(*_COMPLETED_STRAIGHT) is BustedDraw.NONE


def test_no_draw_is_not_busted():
    assert busted_draw_kind(*_NO_DRAW) is BustedDraw.NONE


def test_busted_draw_none_before_river():
    hole, board = _BUSTED_FLUSH
    assert busted_draw_kind(hole, board[:4]) is BustedDraw.NONE  # turn: still live
    assert busted_draw_kind(hole, board[:3]) is BustedDraw.NONE  # flop


def test_busted_ordering_prefers_straight_over_flush():
    # The IntEnum ordering a W3-c consumer relies on.
    assert BustedDraw.STRAIGHT > BustedDraw.FLUSH > BustedDraw.NONE


# ------------------------------------------------------------------ bundle


def test_derive_postflop_context_bundles_all_three():
    hole, board = _BUSTED_FLUSH  # river board
    seats = _ring(0, {1: PlayerStatus.IN, 2: PlayerStatus.IN})
    # seat 2 = BB (in position); flop-bet by BB so bet_prev_street on turn... but
    # this state is the river, prev street = turn. Put a turn bet by BB.
    seat_objs = [
        SimpleNamespace(
            seat=s.seat,
            status=s.status,
            position=Position.BB if s.seat == 2 else Position.SB,
            hole_cards=hole,
        )
        for s in seats
    ]
    state = SimpleNamespace(
        seats=seat_objs,
        button_seat=0,
        street=Street.RIVER,
        board=board,
        action_history=[
            HistoryAction(
                street=Street.TURN, position=Position.BB, action=ActionType.BET, amount_bb=4.0
            )
        ],
    )
    ctx = derive_postflop_context(state, 2)
    assert ctx.in_position is True
    assert ctx.bet_prev_street is True
    assert ctx.busted_draw is BustedDraw.FLUSH
