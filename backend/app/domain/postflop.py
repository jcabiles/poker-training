"""Postflop heuristics + flop c-bet grader (Phase 2a).

A NEW grader (does NOT reuse the preflop range-chart `grade()`): it scores the
HU single-raised-pot flop c-bet decision from texture + a positional range-
advantage rule + the hero hand's made/draw category, and emits the existing
`EvaluationResult` shape (per-action freq + a documented PROXY EV).

Range advantage here is a POSITIONAL + texture rule, NOT equity-backed — the
equity engine is reserved for the equity-estimation drill (perf). Equity-backed
range advantage arrives in 2b.
"""

from __future__ import annotations

from app.domain.action import Decision
from app.domain.evaluation import (
    ActionEval,
    ChosenEval,
    Correctness,
    Coverage,
    EvaluationResult,
    ProviderKind,
)
from app.domain.leaks import LeakCategory
from app.domain.spot import ActionType, NodeContext, Position, Spot
from app.domain.texture import Texture, classify

_RIDX = {r: i for i, r in enumerate("23456789TJQKA")}

# Postflop seat order — later acts last (in position). BTN is most IP.
_POSTFLOP_ORDER = {
    Position.SB: 0,
    Position.BB: 1,
    Position.UTG: 2,
    Position.UTG1: 3,
    Position.UTG2: 4,
    Position.LJ: 5,
    Position.HJ: 6,
    Position.CO: 7,
    Position.BTN: 8,
}

# Postflop correctness thresholds (proxy-EV units, ~bb). Tuned for the c-bet node.
POST_ACCEPTABLE_MAX = 0.6
POST_MISTAKE_MAX = 1.8
POST_MIX = 0.20


def _in_position(hero: Position, villain: Position) -> bool:
    return _POSTFLOP_ORDER.get(hero, 0) > _POSTFLOP_ORDER.get(villain, 0)


def range_advantage(
    node_context: NodeContext, hero_pos: Position, villain_pos: Position, texture: Texture
) -> str:
    """Who holds the range advantage: 'hero' | 'villain' | 'neutral'.

    Positional + texture rule: the preflop aggressor (hero) starts with an edge,
    keeps/extends it on high & dry boards, loses it on low/connected/wet boards,
    and pays an out-of-position penalty.
    """
    score = 1.0  # preflop-aggressor baseline edge
    score += 1.0 if texture.high_board else -1.0
    if texture.wetness == "dry":
        score += 1.0
    elif texture.wetness == "wet":
        score -= 1.0
    if texture.connectedness == "connected":
        score -= 1.0
    if not _in_position(hero_pos, villain_pos):
        score -= 1.0
    if score >= 2.0:
        return "hero"
    if score <= -1.0:
        return "villain"
    return "neutral"


def _villain_pos(spot: Spot) -> Position:
    for p in spot.players:
        if not p.is_hero:
            return p.position
    return spot.facing or Position.BB


def _hand_category(hole: tuple[str, str], board: list[str]) -> str:
    """'strong' | 'weak_made' | 'draw' | 'air' — coarse made/draw tier."""
    hranks = [c[0] for c in hole]
    branks = [c[0] for c in board]
    hsuits = [c[1] for c in hole]
    bsuits = [c[1] for c in board]
    board_top = max(_RIDX[b] for b in branks)

    made = 0
    if hranks[0] == hranks[1]:  # pocket pair
        if hranks[0] in branks:
            made = 3  # set
        elif _RIDX[hranks[0]] > board_top:
            made = 3  # overpair
        else:
            made = 1  # under/middle pocket pair
    else:
        matches = [r for r in hranks if r in branks]
        if len(matches) >= 2:
            made = 3  # two pair
        elif len(matches) == 1:
            made = 2 if _RIDX[matches[0]] == board_top else 1  # top pair vs weak pair

    flush_draw = any(hsuits.count(s) + bsuits.count(s) >= 4 for s in set(hsuits))
    allr = {_RIDX[r] for r in hranks + branks}
    oesd = any(sum(1 for x in (lo, lo + 1, lo + 2, lo + 3) if x in allr) >= 4 for lo in range(10))

    if made >= 2:
        return "strong"
    if made == 1:
        return "weak_made"
    if flush_draw or oesd:
        return "draw"
    return "air"


def _merits(adv: str, texture: Texture, cat: str) -> tuple[float, float, float]:
    """Return (check, bet_small, bet_big) merit scores (proxy EV, ~bb)."""
    value = {"strong": 2.0, "weak_made": 1.0, "draw": 1.2, "air": 0.0}[cat]
    adv_bonus = {"hero": 1.0, "neutral": 0.0, "villain": -1.0}[adv]

    check = 1.0
    if cat == "air":
        check += 1.0
    elif cat == "weak_made":
        check += 0.4
    if adv != "hero":
        check += 0.6
    if texture.wetness == "wet":
        check += 0.4

    bet = value + adv_bonus
    if texture.wetness == "dry":
        bet += 0.4  # range-bet dry boards

    small = bet
    big = bet
    if texture.wetness == "dry":
        small += 0.5  # small range bet preferred on dry boards
        big -= 0.5
    else:  # wet/medium: polarize — big with strong/draws, not with marginal/air
        small += 0.1
        if cat in ("strong", "draw"):
            big += 0.4
        else:
            big -= 0.6
    if cat == "air":
        big -= 1.0  # never barrel big with pure air
    return check, small, big


def _frequencies(merits: list[float]) -> list[float]:
    pos = [max(0.0, m) for m in merits]
    total = sum(pos)
    if total <= 0:
        # degenerate — default to a pure check
        return [1.0 if i == 0 else 0.0 for i in range(len(merits))]
    return [p / total for p in pos]


def _bet_sizes(spot: Spot) -> tuple[float | None, float | None]:
    bets = sorted((la.min_bb or 0.0) for la in spot.legal_actions if la.action == ActionType.BET)
    small = bets[0] if bets else None
    big = bets[-1] if len(bets) > 1 else small
    return small, big


def grade_cbet(
    spot: Spot, hero_range: str | None, villain_range: str | None, decision: Decision | None
) -> EvaluationResult:
    board = spot.board[:3]
    tex = classify(board)
    ctx = spot.node_context[0] if spot.node_context else NodeContext.CBET
    adv = range_advantage(ctx, spot.hero.position, _villain_pos(spot), tex)
    cat = _hand_category(spot.hero.hole_cards, board)
    small, big = _bet_sizes(spot)

    m_check, m_small, m_big = _merits(adv, tex, cat)
    merits = [m_check, m_small, m_big]
    freqs = _frequencies(merits)

    specs = [
        (ActionType.CHECK, None, m_check, freqs[0]),
        (ActionType.BET, small, m_small, freqs[1]),
        (ActionType.BET, big, m_big, freqs[2]),
    ]
    evals = [
        ActionEval(action=a, size_bb=size, frequency=round(f, 3), ev_bb=round(m, 2))
        for a, size, m, f in specs
    ]
    best = max(evals, key=lambda e: e.ev_bb)
    is_mixed = sum(1 for f in freqs if f > POST_MIX) >= 2
    leak = int(LeakCategory.FLOP_CBET)

    base_kwargs = dict(
        per_action=evals,
        best_action=best,
        provider=ProviderKind.HEURISTIC,
        coverage=Coverage.FULL,
        leak_category=leak,
        is_mixed=is_mixed,
    )

    def _size_label(size: float | None) -> str:
        if size is None:
            return "check"
        if big and small and big != small:
            return "big bet" if size >= big else "small bet"
        return "bet"

    if decision is None:
        return EvaluationResult(
            **base_kwargs,
            rationale_tags=["cbet", adv, cat, tex.wetness],
            explanation=(
                f"{tex.texture_class.split('|')[0]} board, {adv} range advantage; "
                f"hero has {cat}: {_size_label(best.size_bb)} is the play."
            ),
        )

    chosen = _match(evals, decision, small, big)
    ev_loss = max(0.0, round(best.ev_bb - chosen.ev_bb, 2))
    chosen_freq = chosen.frequency

    if chosen.action == best.action and chosen.size_bb == best.size_bb:
        correctness = Correctness.OPTIMAL
    elif chosen_freq > POST_MIX:
        correctness = Correctness.ACCEPTABLE
    elif ev_loss <= POST_ACCEPTABLE_MAX:
        correctness = Correctness.ACCEPTABLE
    elif ev_loss <= POST_MISTAKE_MAX:
        correctness = Correctness.MISTAKE
    else:
        correctness = Correctness.BLUNDER

    if correctness == Correctness.OPTIMAL:
        why = (
            f"{cat} on a {tex.wetness} board with {adv} range advantage: "
            f"{_size_label(best.size_bb)} is the play."
        )
    else:
        why = (
            f"{cat} on a {tex.wetness} board ({adv} range advantage): best is "
            f"{_size_label(best.size_bb)}; you chose {_size_label(chosen.size_bb)} "
            f"(-{ev_loss}bb)."
        )

    return EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen_freq, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        rationale_tags=["cbet", adv, cat, tex.wetness],
        explanation=why,
    )


def _match(evals: list[ActionEval], decision: Decision, small, big) -> ActionEval:
    """Resolve the chosen ActionEval, disambiguating small vs big bets by size."""
    if decision.action == ActionType.CHECK:
        return next(e for e in evals if e.action == ActionType.CHECK)
    # a bet: pick the bet eval whose size is nearest the chosen size
    target = decision.size_bb
    bet_evals = [e for e in evals if e.action == ActionType.BET]
    if target is None:
        return bet_evals[0]
    return min(bet_evals, key=lambda e: abs((e.size_bb or 0.0) - target))
