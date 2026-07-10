"""Persona postflop engine (S4) — analytic strength ladder + lever-shaped
mixed decisions.

Pure domain, no Monte-Carlo in the hot loop: `strength_bucket` classifies a
hand analytically (best-5 rank tuples + rank/suit counting), and
`sample_postflop_decision` maps (bucket, draw, facing state) through a shared
merit table shaped multiplicatively by the pack's postflop levers. Mechanics
(the merit numbers) live here; every persona-differentiating number lives in
`content/personas/*.json` (PersonaPack.postflop). The rng is the HAND's
injected `random.Random` — same convention as `personas.py`.

Frozen interface + behavior rules: docs/ai-dlc/specs/simulate-s4.md.
"""

from __future__ import annotations

import itertools
import random
from enum import StrEnum

from app.domain.action import Decision
from app.domain.content.models import PersonaPack
from app.domain.equity import _RIDX, _eval5
from app.domain.spot import ActionType, Card, LegalAction

_ACE = 12  # rank index of the ace in equity.RANKS
_KING = 11


class StrengthBucket(StrEnum):
    """7-rung made-hand ladder — disjoint by construction (spec-pinned):
    sets are ALWAYS monster, never two_pair_plus; straights on paired boards
    stay monster; a pocket pair below the top board card is always
    middle_pair (never overpair_tptk/top_pair)."""

    MONSTER = "monster"
    TWO_PAIR_PLUS = "two_pair_plus"
    OVERPAIR_TPTK = "overpair_tptk"
    TOP_PAIR = "top_pair"
    MIDDLE_PAIR = "middle_pair"
    ACE_HIGH = "ace_high"
    AIR = "air"


class DrawCategory(StrEnum):
    NONE = "none"
    WEAK = "weak"  # gutshot / backdoor-flush+overcard class
    STRONG = "strong"  # flush draw / OESD / combo


_RUNG = {
    StrengthBucket.AIR: 0,
    StrengthBucket.ACE_HIGH: 1,
    StrengthBucket.MIDDLE_PAIR: 2,
    StrengthBucket.TOP_PAIR: 3,
    StrengthBucket.OVERPAIR_TPTK: 4,
    StrengthBucket.TWO_PAIR_PLUS: 5,
    StrengthBucket.MONSTER: 6,
}


def _best5(cards: list[Card]) -> tuple:
    """Best 5-card rank tuple over 5/6/7 cards (analytic, no MC)."""
    rs = [_RIDX[c[0]] for c in cards]
    ss = [c[1] for c in cards]
    best: tuple | None = None
    for idx in itertools.combinations(range(len(cards)), 5):
        v = _eval5([rs[i] for i in idx], [ss[i] for i in idx])
        if best is None or v > best:
            best = v
    return best  # type: ignore[return-value]  # len(cards) >= 5 always


def _high_card_bucket(hole_hi: int) -> StrengthBucket:
    return StrengthBucket.ACE_HIGH if hole_hi >= _KING else StrengthBucket.AIR


def _pair_bucket(pair_rank: int, kicker: int, board_top: int) -> StrengthBucket:
    if pair_rank != board_top:
        return StrengthBucket.MIDDLE_PAIR
    # Top pair: top kicker = ace, or king when top pair IS aces.
    top_kicker = _ACE if pair_rank != _ACE else _KING
    return StrengthBucket.OVERPAIR_TPTK if kicker >= top_kicker else StrengthBucket.TOP_PAIR


def _made_bucket(hole: tuple[Card, Card], board: list[Card]) -> StrengthBucket:
    r1, r2 = _RIDX[hole[0][0]], _RIDX[hole[1][0]]
    hole_hi = max(r1, r2)
    pocket = r1 == r2
    board_ranks = {_RIDX[c[0]] for c in board}
    board_top = max(board_ranks)
    rank = _best5(list(hole) + list(board))
    cat = rank[0]

    if cat >= 4:  # straight/flush/boat/quads — monster even on paired boards
        return StrengthBucket.MONSTER
    if cat == 3:  # trips: set or trips (hole card plays) = monster; board trips: high card
        return StrengthBucket.MONSTER if rank[1] in (r1, r2) else _high_card_bucket(hole_hi)
    if cat == 2:  # two pair
        if pocket:  # pocket pair + board pair (below set strength)
            return StrengthBucket.TWO_PAIR_PLUS
        if r1 in board_ranks and r2 in board_ranks:  # both hole cards playing
            return StrengthBucket.TWO_PAIR_PLUS
        if r1 in board_ranks or r2 in board_ranks:  # one pair + board pair
            pair_rank = r1 if r1 in board_ranks else r2
            kicker = r2 if pair_rank == r1 else r1
            return _pair_bucket(pair_rank, kicker, board_top)
        return _high_card_bucket(hole_hi)  # plays the board's two pair
    if cat == 1:  # one pair
        if pocket:  # can't equal board_top (that would be a set)
            return (
                StrengthBucket.OVERPAIR_TPTK if r1 > board_top else StrengthBucket.MIDDLE_PAIR
            )
        if rank[1] in (r1, r2):  # a hole card pairs the board
            pair_rank = rank[1]
            kicker = r2 if pair_rank == r1 else r1
            return _pair_bucket(pair_rank, kicker, board_top)
        return _high_card_bucket(hole_hi)  # board-paired, hero unpaired
    return _high_card_bucket(hole_hi)


def _straight_out_ranks(hole_ranks: set[int], all_ranks: set[int]) -> int:
    """Count distinct ranks that would complete a 5-high-run straight using at
    least one hole card. >=2 => OESD/double-gutter class, ==1 => gutshot."""
    outs = 0
    for out in range(13):
        if out in all_ranks:
            continue
        new = all_ranks | {out}
        for lo in range(-1, 9):  # lo == -1 is the wheel (A-2-3-4-5)
            window = {r if r >= 0 else _ACE for r in range(lo, lo + 5)}
            if window <= new and out in window and window & hole_ranks:
                outs += 1
                break
    return outs


def _draw_category(hole: tuple[Card, Card], board: list[Card]) -> DrawCategory:
    cards = list(hole) + list(board)
    suit_counts: dict[str, int] = {}
    for c in cards:
        suit_counts[c[1]] = suit_counts.get(c[1], 0) + 1
    hole_suits = {c[1] for c in hole}
    flush_draw = any(n == 4 and s in hole_suits for s, n in suit_counts.items())

    hole_ranks = {_RIDX[c[0]] for c in hole}
    all_ranks = {_RIDX[c[0]] for c in cards}
    straight_outs = _straight_out_ranks(hole_ranks, all_ranks)

    if flush_draw or straight_outs >= 2:
        return DrawCategory.STRONG
    backdoor_flush = len(board) == 3 and any(
        n == 3 and s in hole_suits for s, n in suit_counts.items()
    )
    overcard = max(hole_ranks) > max(_RIDX[c[0]] for c in board)
    if straight_outs == 1 or (backdoor_flush and overcard):
        return DrawCategory.WEAK
    return DrawCategory.NONE


def strength_bucket(
    hole: tuple[Card, Card], board: list[Card]
) -> tuple[StrengthBucket, DrawCategory]:
    """Analytic (bucket, draw) classification for hole cards on a 3/4/5-card
    board. On the RIVER (board len 5) DrawCategory is always NONE — busted
    draws land in AIR/ACE_HIGH by made strength."""
    made = _made_bucket(hole, board)
    draw = DrawCategory.NONE if len(board) >= 5 else _draw_category(hole, board)
    return made, draw


# --------------------------------------------------------------------------
# Merit tables — SHARED game mechanics (behavior rule 4). Levers from the
# pack shape these multiplicatively; no persona-specific number lives here.
# Base masses are pre-normalization merits (components > 1 are fine).
# --------------------------------------------------------------------------

# Unopened / matched-with-option: aggressive (bet or raise) vs check merit.
_AGG_BASE = {
    StrengthBucket.MONSTER: 0.85,
    StrengthBucket.TWO_PAIR_PLUS: 0.75,
    StrengthBucket.OVERPAIR_TPTK: 0.70,
    StrengthBucket.TOP_PAIR: 0.55,
    StrengthBucket.MIDDLE_PAIR: 0.30,
    StrengthBucket.ACE_HIGH: 0.05,
    StrengthBucket.AIR: 0.05,
}
_CHECK_BASE = {
    StrengthBucket.MONSTER: 0.15,
    StrengthBucket.TWO_PAIR_PLUS: 0.25,
    StrengthBucket.OVERPAIR_TPTK: 0.30,
    StrengthBucket.TOP_PAIR: 0.45,
    StrengthBucket.MIDDLE_PAIR: 0.70,
    StrengthBucket.ACE_HIGH: 0.95,
    StrengthBucket.AIR: 0.95,
}
# Facing chips: fold / call / raise merit. Calibration (refuter round 2):
# tuned so a stickiness ~1.0 persona folds to a flop c-bet ~0.45-0.55 and
# stickiness 1.8 lands ~0.25-0.35; call floors keep low-stickiness personas
# (nit, 0.6) calling with real pairs so AF isn't call-starved.
_FOLD_BASE = {
    StrengthBucket.MONSTER: 0.0,
    StrengthBucket.TWO_PAIR_PLUS: 0.05,
    StrengthBucket.OVERPAIR_TPTK: 0.05,
    StrengthBucket.TOP_PAIR: 0.12,
    StrengthBucket.MIDDLE_PAIR: 0.35,
    StrengthBucket.ACE_HIGH: 0.60,
    StrengthBucket.AIR: 0.75,
}
_CALL_BASE = {
    StrengthBucket.MONSTER: 0.35,
    StrengthBucket.TWO_PAIR_PLUS: 0.55,
    StrengthBucket.OVERPAIR_TPTK: 0.70,
    StrengthBucket.TOP_PAIR: 0.78,
    StrengthBucket.MIDDLE_PAIR: 0.60,
    StrengthBucket.ACE_HIGH: 0.40,
    StrengthBucket.AIR: 0.25,
}
_RAISE_BASE = {
    StrengthBucket.MONSTER: 0.65,
    StrengthBucket.TWO_PAIR_PLUS: 0.40,
    StrengthBucket.OVERPAIR_TPTK: 0.25,
    StrengthBucket.TOP_PAIR: 0.10,
    StrengthBucket.MIDDLE_PAIR: 0.05,
    StrengthBucket.ACE_HIGH: 0.02,
    StrengthBucket.AIR: 0.02,
}
# Draw bonuses (semi-bluff aggression + drawing calls), added pre-lever.
_DRAW_AGG_BONUS = {DrawCategory.NONE: 0.0, DrawCategory.WEAK: 0.15, DrawCategory.STRONG: 0.35}
_DRAW_RAISE_BONUS = {DrawCategory.NONE: 0.0, DrawCategory.WEAK: 0.05, DrawCategory.STRONG: 0.15}
_DRAW_CALL_BONUS = {DrawCategory.NONE: 0.0, DrawCategory.WEAK: 0.20, DrawCategory.STRONG: 0.55}
# Structural constants (shared mechanics).
_BLUFF_RAISE_FACTOR = 0.3  # bluff-raising is structurally rarer than bluff-betting
_COMMIT_AGG_BOOST = 3.0  # SPR-commit shift toward call/jam


def sample_postflop_decision(
    pack: PersonaPack,
    hole: tuple[Card, Card],
    board: list[Card],
    legal: list[LegalAction],
    pot_bb: float,
    stack_bb: float,
    opponents: int,
    rng: random.Random,
    noise: float = 1.0,
    current_bet_to: float = 0.0,
) -> Decision:
    """Draw a frequency-mixed postflop decision from the pack's levers.

    Facing state is derived from the `legal` shapes (unopened: CHECK+BET;
    matched-with-option: CHECK+RAISE; facing chips: FOLD+CALL[+RAISE]).
    Merits: clamp >= 0, normalize by the sum (sum 0 => CHECK if legal else
    FOLD), then ALWAYS `rng.choices` — mixed, never argmax.

    Sizing (spec-pinned): pot-fraction `f` sampled from pack sizing weights,
    independent of bucket. BET: `f * pot_bb`. RAISE:
    `raise_to = current_bet_to + f * (pot_bb + to_call)` where `to_call` is
    the CALL entry's min_bb and `current_bet_to` is the caller-supplied
    street current bet-TO amount (HandState.current_bet_bb; 0.0 = unopened —
    it is NOT derivable from the legal bracket, whose RAISE min_bb is
    min_raise_to, not the bet being raised). Legality is guaranteed by
    rounding 2dp then clamping into [min_bb, max_bb]; a jam bracket
    (min == max) resolves to it.
    """
    pf = pack.postflop
    if pf is None:
        raise ValueError(f"persona pack {pack.id!r} has no postflop block")
    bucket, draw = strength_bucket(hole, board)
    by_kind = {la.action: la for la in legal}

    bluff_cell = bucket in (StrengthBucket.AIR, StrengthBucket.ACE_HIGH) and (
        draw is DrawCategory.NONE
    )
    bluff_mass = pf.bluff_freq * noise * pf.multiway_bluff_damp ** max(opponents - 1, 0)
    agg_scale = pf.aggression * noise

    entries: list[tuple[ActionType, float]] = []
    if ActionType.FOLD in by_kind:  # facing chips
        entries.append((ActionType.FOLD, _FOLD_BASE[bucket]))
        entries.append(
            (ActionType.CALL, (_CALL_BASE[bucket] + _DRAW_CALL_BONUS[draw]) * pf.stickiness)
        )
        if ActionType.RAISE in by_kind:
            raise_merit = (
                _BLUFF_RAISE_FACTOR * bluff_mass
                if bluff_cell
                else (_RAISE_BASE[bucket] + _DRAW_RAISE_BONUS[draw]) * agg_scale
            )
            entries.append((ActionType.RAISE, raise_merit))
    else:  # unopened (CHECK+BET) or matched-with-option (CHECK+RAISE)
        agg_action = ActionType.BET if ActionType.BET in by_kind else ActionType.RAISE
        if bluff_cell:  # bluff_freq SETS the air bet/raise mass (rule 1)
            agg_merit = bluff_mass
            check_merit = max(1.0 - bluff_mass, 0.0)
        else:
            agg_merit = (_AGG_BASE[bucket] + _DRAW_AGG_BONUS[draw]) * agg_scale
            check_merit = _CHECK_BASE[bucket]
        entries.append((ActionType.CHECK, check_merit))
        entries.append((agg_action, agg_merit))

    # SPR commit (rule 2): shift to call/jam, no fold mass. Live SPR only —
    # never srs.spr_bucket (frozen SRS contract).
    if stack_bb / pot_bb <= pf.spr_commit and (
        _RUNG[bucket] >= _RUNG[StrengthBucket.OVERPAIR_TPTK] or draw is DrawCategory.STRONG
    ):
        entries = [
            (
                a,
                0.0
                if a is ActionType.FOLD
                else m * (_COMMIT_AGG_BOOST if a in (ActionType.BET, ActionType.RAISE) else 1.0),
            )
            for a, m in entries
        ]

    # Normalize (rule 1, pinned): clamp >= 0, divide by sum; sum 0 fallback.
    weights = [max(m, 0.0) for _, m in entries]
    total = sum(weights)
    if total <= 0.0:
        fallback = ActionType.CHECK if ActionType.CHECK in by_kind else ActionType.FOLD
        return Decision(action=fallback)
    action = rng.choices([a for a, _ in entries], weights=[w / total for w in weights], k=1)[0]

    if action not in (ActionType.BET, ActionType.RAISE):
        return Decision(action=action)

    # Sizing draw — independent of bucket (rule 3).
    fracs = [(float(k), w) for k, w in pf.sizing.items()]
    f = rng.choices([fr for fr, _ in fracs], weights=[w for _, w in fracs], k=1)[0]
    if action is ActionType.BET:
        size = f * pot_bb
    else:
        to_call = by_kind[ActionType.CALL].min_bb or 0.0 if ActionType.CALL in by_kind else 0.0
        size = current_bet_to + f * (pot_bb + to_call)  # spec formula, exact
    bracket = by_kind[action]
    size = min(max(round(size, 2), bracket.min_bb), bracket.max_bb)
    return Decision(action=action, size_bb=size)
