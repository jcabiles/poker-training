"""W3-a — postflop situational context derivations (A2/A3/A4).

Pure-domain helpers that turn the live hand state + action history into the
three "just-ahead" inputs the position/street/texture mechanics (W3-b/c/d) will
consume. Threaded through `sample_postflop_decision` now as a walking skeleton:
`bot_decision` derives a `PostflopContext` and hands it to the sampler, but NO
sampler branch reads it yet — so every existing suite stays byte-identical (no
consumer, no rng-stream displacement, no fixture re-record). W3-b consumes
`in_position`, W3-c `bet_prev_street` + `busted_draw`.

No web/DB import (domain purity). Reuses the ONE strength classifier
(`personas_postflop.strength_bucket`) — never a second taxonomy.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, NamedTuple

from app.domain.personas_postflop import DrawCategory, StrengthBucket, strength_bucket
from app.domain.spot import ActionType, Card, HistoryAction, PlayerStatus, Position, Street

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.domain.table.engine import HandState


class BustedDraw(IntEnum):
    """Provenance of a draw that missed by the river, preserved past the
    river's `DrawCategory.NONE` reset. Ordered so a W3-c consumer can prefer a
    busted STRAIGHT (more disguised) over a busted FLUSH (the missed suit is
    visible on board): STRAIGHT > FLUSH > NONE. A PROXY — validate via the LBR
    harness before treating the preference as hard.
    """

    NONE = 0
    FLUSH = 1
    STRAIGHT = 2


class PostflopContext(NamedTuple):
    """The three W3-a situational inputs. Defaults = today's behavior, so an
    un-opted caller (every existing test, the range estimator) is unaffected."""

    in_position: bool = False
    bet_prev_street: bool = False
    busted_draw: BustedDraw = BustedDraw.NONE


# The postflop-order predecessor of each street (preflop has none). A seat that
# BET/RAISED on the previous street is continuing initiative (a barrel /
# c-bet); one that did not is making a delayed stab. Preflop RAISE counts — the
# flop's previous-street aggressor IS the preflop raiser.
_PREV_STREET: dict[Street, Street] = {
    Street.FLOP: Street.PREFLOP,
    Street.TURN: Street.FLOP,
    Street.RIVER: Street.TURN,
}


def _postflop_rank(seat: int, button_seat: int, n: int) -> int:
    """Postflop acting order, 0 = first to act (SB, button+1) … n-1 = last
    (the button). A higher rank acts later = closer to in-position."""
    return (seat - button_seat - 1) % n


def derive_in_position(
    seats: Sequence, button_seat: int, seat: int
) -> bool:
    """A2 — true iff no still-live opponent acts after `seat` this street.

    Only `PlayerStatus.IN` seats can still act; FOLDED and ALLIN seats are
    excluded (an all-in player is done acting, so it never keeps `seat` out of
    position). `seat` is the last live actor iff its postflop rank is the max
    among IN seats — which makes BB in position vs SB (BB acts after SB
    postflop) and, 3+-handed, the last live seat in position. If `seat` is the
    only IN seat (everyone else folded/all-in) it is trivially in position.
    """
    n = len(seats)
    my_rank = _postflop_rank(seat, button_seat, n)
    return all(
        _postflop_rank(s.seat, button_seat, n) <= my_rank
        for s in seats
        if s.status is PlayerStatus.IN
    )


def bet_prev_street(
    action_history: Sequence[HistoryAction], street: Street, position: Position
) -> bool:
    """A3 — did `position` make a BET or RAISE on the street immediately
    before `street`? Per-street aggressor memory: distinguishes a barrel
    (bet the previous street → True) from a delayed stab (checked it → False),
    the signal a correct c-bet-vs-barrel sizing-node needs. Fixes the
    whole-hand `is_aggressor` mislabel (F17) at its source; W3-c consumes it.
    """
    prev = _PREV_STREET.get(street)
    if prev is None:
        return False
    return any(
        h.street is prev
        and h.position == position
        and h.action in (ActionType.BET, ActionType.RAISE)
        for h in action_history
    )


def _has_flush_draw(hole: tuple[Card, Card], board: list[Card]) -> bool:
    """Four cards to a flush using a hole suit (the flush-draw half of
    `personas_postflop._draw_category`, kept minimal to avoid a second
    taxonomy)."""
    hole_suits = {c[1] for c in hole}
    counts: dict[str, int] = {}
    for c in list(hole) + list(board):
        counts[c[1]] = counts.get(c[1], 0) + 1
    return any(n == 4 and s in hole_suits for s, n in counts.items())


def busted_draw_kind(hole: tuple[Card, Card], board: list[Card]) -> BustedDraw:
    """A4 — on the RIVER, the provenance of a draw that missed; NONE otherwise.

    A hand qualifies iff (1) the board is complete (5 cards), (2) the turn
    subboard held a STRONG or WEAK draw, and (3) the river left it unmade — the
    final hand is still AIR / ACE_HIGH (a draw that paired or completed is not a
    busted-air bluff candidate). Type: FLUSH if the turn draw had a flush
    component (its missed suit is visible on board), else STRAIGHT.
    """
    if len(board) != 5:  # a busted draw is a river concept — complete board only
        return BustedDraw.NONE
    made, _ = strength_bucket(hole, board)
    if made not in (StrengthBucket.AIR, StrengthBucket.ACE_HIGH):
        return BustedDraw.NONE
    turn_board = board[:4]
    _, turn_draw = strength_bucket(hole, turn_board)
    if turn_draw is DrawCategory.NONE:
        return BustedDraw.NONE
    return BustedDraw.FLUSH if _has_flush_draw(hole, turn_board) else BustedDraw.STRAIGHT


def derive_postflop_context(state: HandState, seat: int) -> PostflopContext:
    """Bundle the three W3-a inputs for the seat about to act postflop."""
    seat_state = state.seats[seat]
    return PostflopContext(
        in_position=derive_in_position(state.seats, state.button_seat, seat),
        bet_prev_street=bet_prev_street(
            state.action_history, state.street, seat_state.position
        ),
        busted_draw=busted_draw_kind(seat_state.hole_cards, state.board),
    )
