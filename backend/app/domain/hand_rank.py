"""HAND_RANK — each of the 169 starting hands mapped to a strength percentile
in [0,1] (AA=1.0, weakest≈0.0).

This is a documented equity-vs-random *proxy* (a monotonic strength ordering),
not exact solver equity. It scales grading penalties (folding strong hands hurts
more; raising weak hands hurts more). Phase 3's solver provider can replace this
with true equities without touching the grading interface.
"""

from __future__ import annotations

from app.domain.content.notation import all_hands

_RANKS = "23456789TJQKA"
_IDX = {r: i for i, r in enumerate(_RANKS)}


def _strength(hand: str) -> float:
    if len(hand) == 2 and hand[0] == hand[1]:  # pair
        # Coefficient bumped 0.030 -> 0.045 (doc 08): computed equity-vs-random
        # shows pairs climb in value faster than a flat linear slope implies
        # (set-mining/made-hand-today value), so the old same-slope-as-high-card
        # term systematically underrated mid pockets (55/66/77 worst, ~+17-22
        # rank positions too weak). Base offset (0.55) is untouched since
        # AA/KK/QQ/JJ were already well-calibrated (doc 08 §1.3). This fixes the
        # decisive mis-orderings 77/66 > QJs and preserves 55 > Q7s.
        return 0.55 + 0.045 * _IDX[hand[0]]
    r1, r2 = hand[0], hand[1]
    if _IDX[r1] < _IDX[r2]:
        r1, r2 = r2, r1
    s = 0.20 + 0.030 * _IDX[r1] + 0.018 * _IDX[r2]
    if hand.endswith("s"):
        s += 0.04
    if _IDX[r1] - _IDX[r2] - 1 <= 1:  # connected
        s += 0.02
    return s


_SORTED = sorted(all_hands(), key=_strength)
HAND_RANK: dict[str, float] = {h: i / (len(_SORTED) - 1) for i, h in enumerate(_SORTED)}


def hand_rank(hand: str) -> float:
    return HAND_RANK.get(hand, 0.5)
