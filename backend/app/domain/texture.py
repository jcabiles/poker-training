"""Board-texture classifier (Phase 2a).

Pure, rule-based flop classification used by the c-bet grader and the
texture-classification quiz, and to derive a stable `texture_class` label for
the postflop spot signature (so same-texture boards map to one SRS bucket).
"""

from __future__ import annotations

from dataclasses import dataclass

RANKS = "23456789TJQKA"
_RIDX = {r: i for i, r in enumerate(RANKS)}


@dataclass(frozen=True)
class Texture:
    wetness: str  # dry | medium | wet
    pairing: str  # unpaired | paired | trips
    suitedness: str  # rainbow | two-tone | monotone
    connectedness: str  # disconnected | semi-connected | connected
    high_card: str  # rank char of the top card, e.g. "A"
    texture_class: str  # compact, board-independent label for the signature

    @property
    def high_board(self) -> bool:
        """True for broadway-topped boards (T or higher)."""
        return _RIDX[self.high_card] >= _RIDX["T"]


def classify(board: list[str]) -> Texture:
    """Classifies exactly the FIRST 3 cards of `board` (the flop). Callers with a longer board
    must slice deliberately — this function does not know which 3 cards are the 'flop' beyond
    position. Raises if fewer than 3 cards."""
    if len(board) < 3:
        raise ValueError(f"texture.classify needs >=3 board cards, got {len(board)}")
    cards = board[:3]
    rs = [_RIDX[c[0]] for c in cards]
    ss = [c[1] for c in cards]

    distinct = sorted(set(rs), reverse=True)
    if len(distinct) == 1:
        pairing = "trips"
    elif len(distinct) == 2:
        pairing = "paired"
    else:
        pairing = "unpaired"

    suitedness = {1: "monotone", 2: "two-tone", 3: "rainbow"}[len(set(ss))]

    span = distinct[0] - distinct[-1] if len(distinct) > 1 else 0
    if len(distinct) == 3 and span <= 4:
        connectedness = "connected"
    elif len(distinct) >= 2 and span <= 2:
        connectedness = "connected"
    elif len(distinct) == 3 and span <= 6:
        connectedness = "semi-connected"
    else:
        connectedness = "disconnected"

    high_card = RANKS[distinct[0]]

    score = 0
    if suitedness == "monotone":
        score += 2
    elif suitedness == "two-tone":
        score += 1
    if connectedness == "connected":
        score += 2
    elif connectedness == "semi-connected":
        score += 1
    if pairing == "paired":  # paired boards offer fewer draws — play drier
        score -= 1
    if score >= 2:
        wetness = "wet"
    elif score <= 0:
        wetness = "dry"
    else:
        wetness = "medium"

    texture_class = f"{wetness}|{suitedness}|{connectedness}|{pairing}"
    return Texture(
        wetness=wetness,
        pairing=pairing,
        suitedness=suitedness,
        connectedness=connectedness,
        high_card=high_card,
        texture_class=texture_class,
    )


def turn_card_class(board: list[str]) -> str:
    """Classify the turn card (board[3]) against the flop (board[:3]) into exactly
    one of "pairing" | "flush" | "straight" | "over" | "blank" (S6).

    Precedence in that order: a board-pairing card beats a flush-completing card
    beats a straight-completing card beats an overcard to the flop beats a blank.
    Raises if fewer than 4 board cards. `classify()` above stays flop-only.
    """
    if len(board) < 4:
        raise ValueError(f"texture.turn_card_class needs >=4 board cards, got {len(board)}")
    flop, turn = board[:3], board[3]
    turn_rank, turn_suit = _RIDX[turn[0]], turn[1]
    flop_ranks = [_RIDX[c[0]] for c in flop]

    # 1. pairing — the turn matches a flop rank (trips/boats now possible)
    if turn_rank in flop_ranks:
        return "pairing"

    # 2. flush-completing — the turn makes 3+ of one suit on the board
    if sum(1 for c in flop if c[1] == turn_suit) >= 2:
        return "flush"

    # 3. straight-completing — the turn plus two flop cards fit a 5-rank window,
    # so a two-card holding can now complete a straight through the turn card.
    # Aces count both high and low (wheel).
    def _straighty(ranks: list[int], t: int) -> bool:
        for i, a in enumerate(ranks):
            for b in ranks[i + 1 :]:
                if a != b and max(a, b, t) - min(a, b, t) <= 4:
                    return True
        return False

    def _low(r: int) -> int:  # ace-low remap for wheel straights
        return -1 if r == _RIDX["A"] else r

    if _straighty(flop_ranks, turn_rank) or _straighty(
        [_low(r) for r in flop_ranks], _low(turn_rank)
    ):
        return "straight"

    # 4. overcard to the flop
    if turn_rank > max(flop_ranks):
        return "over"

    return "blank"


def river_card_class(board: list[str]) -> str:
    """Classify the river card (board[4]) against the first four cards (board[:4])
    into exactly one of "pairing" | "flush" | "straight" | "over" | "blank" (S7).

    Same precedence as `turn_card_class`: pairing beats flush-completing beats
    straight-completing beats overcard beats blank. Raises if fewer than 5 board
    cards. `classify()` stays flop-only and `turn_card_class()` is untouched.
    """
    if len(board) < 5:
        raise ValueError(f"texture.river_card_class needs >=5 board cards, got {len(board)}")
    prior, river = board[:4], board[4]
    river_rank, river_suit = _RIDX[river[0]], river[1]
    prior_ranks = [_RIDX[c[0]] for c in prior]

    # 1. pairing — the river matches a rank already on board
    if river_rank in prior_ranks:
        return "pairing"

    # 2. flush-completing — the river makes 3+ of one suit on the board
    if sum(1 for c in prior if c[1] == river_suit) >= 2:
        return "flush"

    # 3. straight-completing — the river plus two prior board cards fit a 5-rank
    # window, so a two-card holding can now complete a straight through it.
    # Aces count both high and low (wheel).
    def _straighty(ranks: list[int], t: int) -> bool:
        for i, a in enumerate(ranks):
            for b in ranks[i + 1 :]:
                if a != b and max(a, b, t) - min(a, b, t) <= 4:
                    return True
        return False

    def _low(r: int) -> int:  # ace-low remap for wheel straights
        return -1 if r == _RIDX["A"] else r

    if _straighty(prior_ranks, river_rank) or _straighty(
        [_low(r) for r in prior_ranks], _low(river_rank)
    ):
        return "straight"

    # 4. overcard to the board so far
    if river_rank > max(prior_ranks):
        return "over"

    return "blank"
