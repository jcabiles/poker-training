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
    """Classify a flop (first 3 cards). Raises if fewer than 3 cards."""
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
