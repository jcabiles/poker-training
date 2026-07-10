"""Hand engine — pure 9-max NLHE hand state machine (S2).

Blinds through showdown: betting legality (incl. the incomplete-raise rule),
street advance with auto-runout, side-pot layering, and chip-conserving
settlement. Pure domain: no web/DB imports, no RNG — deterministic given
inputs. Frozen interface + rules: docs/ai-dlc/specs/simulate-s2.md.
"""

from __future__ import annotations

import math

from pydantic import BaseModel

from app.domain.action import Decision
from app.domain.equity import best7
from app.domain.spot import (
    ActionType,
    Card,
    HistoryAction,
    LegalAction,
    PlayerStatus,
    Position,
    Street,
)
from app.domain.table.deck import DealtHand, positions_for_button

_SEATS = 9
_SB = 0.5
_BB = 1.0
_EPS = 1e-9

_NEXT_STREET = {Street.PREFLOP: Street.FLOP, Street.FLOP: Street.TURN, Street.TURN: Street.RIVER}
_REVEAL = {Street.FLOP: 3, Street.TURN: 4, Street.RIVER: 5}


class SeatState(BaseModel):
    seat: int  # 0-8
    position: Position  # from positions_for_button(button_seat)[seat]
    stack_bb: float  # chips behind (not yet invested)
    invested_street_bb: float  # put in THIS street (resets each street)
    invested_total_bb: float  # put in this hand (never resets)
    status: PlayerStatus  # IN / FOLDED / ALLIN
    hole_cards: tuple[Card, Card]


class Pot(BaseModel):
    amount_bb: float
    eligible_seats: list[int]  # seats that can win it (side-pot layering)


class HandState(BaseModel):
    button_seat: int
    street: Street  # PREFLOP -> FLOP -> TURN -> RIVER
    board: list[Card]  # REVEALED cards only: 0/3/4/5 by street
    full_board: list[Card]  # all 5 from DealtHand (internal; never serialized)
    seats: list[SeatState]  # len 9, index = seat
    to_act_seat: int | None  # None => betting closed / hand over
    current_bet_bb: float  # highest invested_street_bb this street
    min_raise_to_bb: float  # legal minimum raise-TO amount
    last_full_raise_bb: float  # size of last full raise increment (min-raise rule)
    action_history: list[HistoryAction]  # POST entries for blinds
    hand_over: bool


class SeatDelta(BaseModel):
    seat: int
    delta_bb: float  # net chips won/lost this hand (2dp)


class Settlement(BaseModel):
    pots: list[Pot]
    winners_by_pot: list[list[int]]  # parallel to pots; ties split
    deltas: list[SeatDelta]  # len 9, sums to 0.0
    showdown_seats: list[int]  # seats whose hands were compared ([] on fold-out)


def start_hand(dealt: DealtHand, button_seat: int, stacks_bb: list[float]) -> HandState:
    """Post blinds (SB 0.5 / BB 1.0) and open preflop action at UTG."""
    positions = positions_for_button(button_seat)
    sb_seat = (button_seat + 1) % _SEATS
    bb_seat = (button_seat + 2) % _SEATS
    if stacks_bb[sb_seat] < _SB - _EPS:
        raise ValueError(f"seat {sb_seat} stack {stacks_bb[sb_seat]} below small blind {_SB}")
    if stacks_bb[bb_seat] < _BB - _EPS:
        raise ValueError(f"seat {bb_seat} stack {stacks_bb[bb_seat]} below big blind {_BB}")
    seats: list[SeatState] = []
    for i in range(_SEATS):
        blind = _SB if i == sb_seat else _BB if i == bb_seat else 0.0
        stack = stacks_bb[i] - blind
        seats.append(
            SeatState(
                seat=i,
                position=positions[i],
                stack_bb=stack,
                invested_street_bb=blind,
                invested_total_bb=blind,
                status=PlayerStatus.ALLIN if blind and stack <= _EPS else PlayerStatus.IN,
                hole_cards=dealt.hole_cards[i],
            )
        )
    history = [
        HistoryAction(
            street=Street.PREFLOP,
            position=positions[sb_seat],
            action=ActionType.POST,
            amount_bb=_SB,
        ),
        HistoryAction(
            street=Street.PREFLOP,
            position=positions[bb_seat],
            action=ActionType.POST,
            amount_bb=_BB,
        ),
    ]
    return HandState(
        button_seat=button_seat,
        street=Street.PREFLOP,
        board=[],
        full_board=list(dealt.board),
        seats=seats,
        to_act_seat=(button_seat + 3) % _SEATS,
        current_bet_bb=_BB,
        min_raise_to_bb=2 * _BB,
        last_full_raise_bb=_BB,
        action_history=history,
        hand_over=False,
    )


def _acted_seats(state: HandState) -> set[int]:
    """Seats that have acted this street since the last reopen.

    Derived by replaying this street's history (POST never counts as acting);
    a complete bet/raise reopens action — the acted set resets to the raiser.
    """
    pos2seat = {s.position: s.seat for s in state.seats}
    # Chips a seat had available for this street at street start.
    avail = {s.seat: s.stack_bb + s.invested_street_bb for s in state.seats}
    invested = dict.fromkeys(range(_SEATS), 0.0)
    cur = 0.0
    last_full = _BB
    acted: set[int] = set()
    for h in state.action_history:
        if h.street is not state.street:
            continue
        s = pos2seat[h.position]
        if h.action is ActionType.POST:
            invested[s] += h.amount_bb
            cur = max(cur, invested[s])
        elif h.action in (ActionType.BET, ActionType.RAISE):
            invested[s] += h.amount_bb
            new_bet = invested[s]
            all_in = avail[s] - invested[s] <= _EPS
            if all_in and new_bet - cur < last_full - _EPS:
                acted.add(s)  # incomplete all-in raise: no reopen
            else:
                last_full = new_bet - cur
                acted = {s}  # complete: reopens action for everyone else
            cur = new_bet
        else:  # FOLD / CHECK / CALL
            if h.action is ActionType.CALL:
                invested[s] += h.amount_bb
            acted.add(s)
    return acted


def _raise_action(min_raise_to: float, all_in_to: float) -> LegalAction:
    """RAISE shape; jam encoding RAISE(min=max=all-in-TO) below the min raise."""
    if all_in_to < min_raise_to - _EPS:
        return LegalAction(
            action=ActionType.RAISE, min_bb=round(all_in_to, 2), max_bb=round(all_in_to, 2)
        )
    return LegalAction(
        action=ActionType.RAISE, min_bb=round(min_raise_to, 2), max_bb=round(all_in_to, 2)
    )


def legal_actions(state: HandState) -> list[LegalAction]:
    """Legal actions for state.to_act_seat, in Practice's LegalAction shape."""
    if state.hand_over or state.to_act_seat is None:
        return []
    seat = state.seats[state.to_act_seat]
    all_in_to = seat.invested_street_bb + seat.stack_bb
    cur = state.current_bet_bb
    to_call = cur - seat.invested_street_bb
    if cur <= _EPS:  # unopened street
        lo = min(state.min_raise_to_bb, all_in_to)
        return [
            LegalAction(action=ActionType.CHECK),
            LegalAction(action=ActionType.BET, min_bb=round(lo, 2), max_bb=round(all_in_to, 2)),
        ]
    if to_call <= _EPS:  # matched but holds the option (e.g. BB in a limped pot)
        return [
            LegalAction(action=ActionType.CHECK),
            _raise_action(state.min_raise_to_bb, all_in_to),
        ]
    # Facing chips.
    out = [
        LegalAction(action=ActionType.FOLD),
        LegalAction(action=ActionType.CALL, min_bb=round(min(to_call, seat.stack_bb), 2)),
    ]
    can_raise = all_in_to > cur + _EPS and seat.seat not in _acted_seats(state)
    if can_raise:
        out.append(_raise_action(state.min_raise_to_bb, all_in_to))
    return out


def _pay(seat: SeatState, amount: float) -> None:
    seat.stack_bb -= amount
    seat.invested_street_bb += amount
    seat.invested_total_bb += amount
    if seat.stack_bb <= _EPS:
        seat.stack_bb = 0.0
        seat.status = PlayerStatus.ALLIN


def _close_street(state: HandState) -> None:
    """Advance the street, or run out / end the hand. Fold-out handled by caller."""
    in_seats = [s for s in state.seats if s.status is PlayerStatus.IN]
    if state.street is Street.RIVER:
        state.to_act_seat = None
        state.hand_over = True
        return
    if len(in_seats) <= 1:  # everyone else folded/all-in: auto-runout to settlement
        state.street = Street.RIVER
        state.board = list(state.full_board)
        for s in state.seats:
            s.invested_street_bb = 0.0
        state.current_bet_bb = 0.0
        state.min_raise_to_bb = _BB
        state.last_full_raise_bb = _BB
        state.to_act_seat = None
        state.hand_over = True
        return
    state.street = _NEXT_STREET[state.street]
    state.board = list(state.full_board[: _REVEAL[state.street]])
    for s in state.seats:
        s.invested_street_bb = 0.0
    state.current_bet_bb = 0.0
    state.min_raise_to_bb = _BB
    state.last_full_raise_bb = _BB
    sb_seat = (state.button_seat + 1) % _SEATS
    for i in range(_SEATS):
        seat = state.seats[(sb_seat + i) % _SEATS]
        if seat.status is PlayerStatus.IN:
            state.to_act_seat = seat.seat
            return


def apply(state: HandState, decision: Decision) -> HandState:
    """Apply a decision for state.to_act_seat. Pure: returns a NEW HandState."""
    if state.hand_over or state.to_act_seat is None:
        raise ValueError("cannot act: hand is over")
    legal = legal_actions(state)
    kinds = {la.action for la in legal}
    if decision.action not in kinds:
        if decision.action is ActionType.RAISE and kinds == {ActionType.FOLD, ActionType.CALL}:
            raise ValueError("raise not allowed: incomplete raise did not reopen action")
        raise ValueError(
            f"illegal action {decision.action.value!r}; "
            f"legal: {sorted(k.value for k in kinds)}"
        )
    new = state.model_copy(deep=True)
    seat = new.seats[new.to_act_seat]
    all_in_to = seat.invested_street_bb + seat.stack_bb

    if decision.action is ActionType.FOLD:
        seat.status = PlayerStatus.FOLDED
        increment = 0.0
    elif decision.action is ActionType.CHECK:
        increment = 0.0
    elif decision.action is ActionType.CALL:
        increment = min(new.current_bet_bb - seat.invested_street_bb, seat.stack_bb)
        _pay(seat, increment)
    else:  # BET / RAISE
        if decision.size_bb is None:
            raise ValueError("engine requires size_bb")
        size = decision.size_bb
        lo = min(new.min_raise_to_bb, all_in_to)
        hi = all_in_to
        if all_in_to < new.min_raise_to_bb - _EPS:  # jam encoding: only all-in-TO legal
            lo = all_in_to
        if size < lo - _EPS or size > hi + _EPS:
            raise ValueError(
                f"{decision.action.value} size {size} outside [{round(lo, 2)}, {round(hi, 2)}]"
            )
        increment = min(size - seat.invested_street_bb, seat.stack_bb)
        _pay(seat, increment)
        prev_bet = new.current_bet_bb
        new.current_bet_bb = size
        all_in = seat.status is PlayerStatus.ALLIN
        if not (all_in and size - prev_bet < new.last_full_raise_bb - _EPS):
            # Complete bet/raise: reopens action, resets the min-raise ladder.
            new.last_full_raise_bb = size - prev_bet
            new.min_raise_to_bb = size + new.last_full_raise_bb
        # Incomplete all-in raise: current_bet moves; min_raise/last_full unchanged.

    new.action_history.append(
        HistoryAction(
            street=new.street,
            position=seat.position,
            action=decision.action,
            amount_bb=increment,
        )
    )

    if sum(1 for s in new.seats if s.status is not PlayerStatus.FOLDED) == 1:
        new.to_act_seat = None
        new.hand_over = True  # fold-out: uncontested
        return new

    acted = _acted_seats(new)
    for i in range(1, _SEATS + 1):
        nxt = new.seats[(seat.seat + i) % _SEATS]
        if nxt.status is PlayerStatus.IN and (
            nxt.invested_street_bb < new.current_bet_bb - _EPS or nxt.seat not in acted
        ):
            new.to_act_seat = nxt.seat
            return new
    _close_street(new)
    return new


def _floor2(x: float) -> float:
    return math.floor(x * 100 + _EPS) / 100


def settle(state: HandState) -> Settlement:
    """Side pots, showdown, and chip-conserving payouts. Only when hand_over."""
    if not state.hand_over:
        raise ValueError("cannot settle: hand not over")
    contrib = [s.invested_total_bb for s in state.seats]
    non_folded = [s.seat for s in state.seats if s.status is not PlayerStatus.FOLDED]

    # Side-pot layers at ascending invested_total of live seats; folded chips = dead money.
    levels: list[float] = []
    for v in sorted(contrib[s] for s in non_folded):
        if v > _EPS and (not levels or v - levels[-1] > _EPS):
            levels.append(v)
    pots: list[Pot] = []
    prev = 0.0
    for level in levels:
        amount = sum(min(c, level) - min(c, prev) for c in contrib)
        eligible = [s for s in non_folded if contrib[s] >= level - _EPS]
        pots.append(Pot(amount_bb=round(amount, 2), eligible_seats=eligible))
        prev = level

    showdown: set[int] = set()
    winners_by_pot: list[list[int]] = []
    if len(non_folded) == 1:  # fold-out: hole cards never compared
        winners_by_pot = [[non_folded[0]] for _ in pots]
    else:
        ranks = {
            s: best7(list(state.seats[s].hole_cards) + list(state.board)) for s in non_folded
        }
        for pot in pots:
            if len(pot.eligible_seats) == 1:  # uncalled top layer returns to bettor
                winners_by_pot.append(list(pot.eligible_seats))
                continue
            best = max(ranks[s] for s in pot.eligible_seats)
            winners_by_pot.append([s for s in pot.eligible_seats if ranks[s] == best])
            showdown.update(pot.eligible_seats)

    # Rounding: floor each share to 2dp; residual to the eligible winner nearest SB.
    payout = [0.0] * _SEATS
    for pot, winners in zip(pots, winners_by_pot, strict=True):
        share = _floor2(pot.amount_bb / len(winners))
        for w in winners:
            payout[w] += share
        residual = round(pot.amount_bb - share * len(winners), 2)
        if residual > _EPS:
            payout[min(winners, key=lambda s: (s - state.button_seat - 1) % _SEATS)] += residual

    deltas = [SeatDelta(seat=i, delta_bb=round(payout[i] - contrib[i], 2)) for i in range(_SEATS)]
    return Settlement(
        pots=pots,
        winners_by_pot=winners_by_pot,
        deltas=deltas,
        showdown_seats=sorted(showdown),
    )
