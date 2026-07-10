"""Table dealing — seed-reproducible 9-max deck + dealer-button rotation.

Pure domain: no web/DB imports, no shared RNG state. Callers own the
`random.Random` instance (see `docs/ai-dlc/specs/simulate-s1.md` — per-hand
`random.Random(secrets.randbits(256))`, never a module-level singleton).
"""

from __future__ import annotations

import random

from pydantic import BaseModel, field_validator

from app.domain.spot import RANKS, SUITS, Card, Position, validate_card

_SEATS = 9

# Frozen clockwise order starting at the button (spec worked example).
_ROTATION = [
    Position.BTN,
    Position.SB,
    Position.BB,
    Position.UTG,
    Position.UTG1,
    Position.UTG2,
    Position.LJ,
    Position.HJ,
    Position.CO,
]


class DealtHand(BaseModel):
    hole_cards: list[tuple[Card, Card]]  # len 9, seat order (seat i's hole cards)
    board: list[Card]  # len 5

    @field_validator("hole_cards")
    @classmethod
    def _validate_hole_cards(cls, v):
        return [(validate_card(a), validate_card(b)) for a, b in v]

    @field_validator("board")
    @classmethod
    def _validate_board(cls, v):
        return [validate_card(c) for c in v]


def deal_hand(rng: random.Random) -> DealtHand:
    """Shuffle a fresh 52-card deck once and deal 9x2 hole cards + a 5-card board.

    Deck construction mirrors `equity.py:24`. Deal order: shuffle, pop 18 hole
    cards (2 per seat, seats 0-8), then pop 5 board cards. No reshuffling.
    """
    deck: list[Card] = [r + s for r in RANKS for s in SUITS]
    rng.shuffle(deck)
    hole_cards = [(deck.pop(0), deck.pop(0)) for _ in range(_SEATS)]
    board = [deck.pop(0) for _ in range(5)]
    return DealtHand(hole_cards=hole_cards, board=board)


def positions_for_button(button_seat: int) -> list[Position]:
    """Positions indexed by seat, given the button's seat index.

    Element `i` is seat `i`'s position. Clockwise = ascending seat index,
    wrapping mod 9, starting from `BTN` at `button_seat`.
    """
    return [_ROTATION[(seat - button_seat) % _SEATS] for seat in range(_SEATS)]
