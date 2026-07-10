"""Frequency-tolerant preflop grading engine.

Correctness is chart-membership driven; per-action freq + a documented PROXY EV
populate the EvaluationResult (the solver provider replaces the EVs in Phase 3).
See docs/ai-dlc/specs/phase-1a-preflop-trainer.md for the model.
"""

from __future__ import annotations

from app.domain.action import Decision
from app.domain.archetypes import VillainType
from app.domain.content.models import Entry
from app.domain.content.notation import all_hands, hole_cards_to_class, parse_range
from app.domain.evaluation import (
    ActionEval,
    ChosenEval,
    Correctness,
    Coverage,
    EvaluationResult,
    ProviderKind,
)
from app.domain.hand_rank import hand_rank
from app.domain.leaks import LeakCategory
from app.domain.spot import ActionType, NodeContext, Position, Spot

# Tunable constants (documented placeholder EV model).
PEN_MIX = 0.3
FOLD_OFF_BASE, FOLD_OFF_SLOPE = 0.3, 3.2  # folding a should-play hand; stronger = worse
OFF_BASE, OFF_SLOPE = 0.5, 4.0  # off-chart call/raise; scaled by distance below the range edge
ACCEPTABLE_MAX, MISTAKE_MAX = 0.5, 2.0
MIX_THRESHOLD = 0.15
DEFAULT_FLOOR = 0.85  # range edge when the node is pure-fold / no content

_PRIORITY = {
    ActionType.RAISE: 3,
    ActionType.BET: 3,
    ActionType.CALL: 2,
    ActionType.CHECK: 2,
    ActionType.FOLD: 1,
    ActionType.POST: 0,
}

_RFI_LEAK = {
    Position.UTG: LeakCategory.RFI_EP,
    Position.UTG1: LeakCategory.RFI_EP,
    Position.UTG2: LeakCategory.RFI_EP,
    Position.LJ: LeakCategory.RFI_MP,
    Position.HJ: LeakCategory.RFI_MP,
    Position.CO: LeakCategory.RFI_CO,
    Position.BTN: LeakCategory.RFI_BTN,
    Position.SB: LeakCategory.RFI_SB,
    Position.BB: LeakCategory.RFI_EP,
}


# Postflop seat order (later = in position) for the vs_3bet IP/OOP split.
_SEAT_ORDER = {
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


def leak_category_for(
    ctx: NodeContext | None, position: Position, facing: Position | None = None
) -> int:
    if ctx == NodeContext.RFI:
        return int(_RFI_LEAK.get(position, LeakCategory.RFI_EP))
    if ctx == NodeContext.VS_RFI:
        in_blinds = position in (Position.SB, Position.BB)
        return int(LeakCategory.BLIND_DEFENSE if in_blinds else LeakCategory.VS_RFI)
    if ctx == NodeContext.BLIND_DEFENSE:
        return int(LeakCategory.BLIND_DEFENSE)
    if ctx == NodeContext.VS_LIMPERS:
        return int(LeakCategory.VS_LIMPERS)
    if ctx == NodeContext.VS_3BET:
        ip = facing is not None and _SEAT_ORDER.get(position, 0) > _SEAT_ORDER.get(facing, 0)
        return int(LeakCategory.VS_3BET_IP if ip else LeakCategory.VS_3BET_OOP)
    if ctx == NodeContext.VS_4BET:
        return int(LeakCategory.FOURBET_RESPONSE)
    if ctx == NodeContext.CBET:
        return int(LeakCategory.FLOP_CBET)
    if ctx == NodeContext.VS_CBET:
        return int(LeakCategory.VS_CBET)
    if ctx == NodeContext.VS_CHECK_RAISE:
        return int(LeakCategory.VS_CHECK_RAISE)
    return int(LeakCategory.VS_RFI)


_EXPLOIT_LEAK = {
    VillainType.CALLING_STATION: LeakCategory.CALLING_STATION_EXPLOIT,
    VillainType.NIT: LeakCategory.NIT_EXPLOIT,
    VillainType.LAG: LeakCategory.LAG_EXPLOIT,
    VillainType.PASSIVE_FISH: LeakCategory.PASSIVE_FISH_EXPLOIT,
    VillainType.TAG: LeakCategory.TAG_EXPLOIT,
    VillainType.MANIAC: LeakCategory.MANIAC_EXPLOIT,
}


def archetype_leak(villain_type: VillainType) -> int:
    return int(_EXPLOIT_LEAK.get(villain_type, LeakCategory.CALLING_STATION_EXPLOIT))


def _leak_for(spot: Spot) -> int:
    if spot.villain_type is not None:
        return archetype_leak(spot.villain_type)
    ctx = spot.node_context[0] if spot.node_context else None
    return leak_category_for(ctx, spot.hero.position, spot.facing)


def _chart_mix(entry: Entry | None, hand: str) -> dict[ActionType, float]:
    """Non-fold actions the chart plays for this hand, with frequency."""
    mix: dict[ActionType, float] = {}
    if entry:
        for ar in entry.actions:
            if ar.action == ActionType.FOLD or ar.frequency <= 0:
                continue
            if hand in parse_range(ar.combos):
                mix[ar.action] = max(mix.get(ar.action, 0.0), ar.frequency)
    return mix


def _range_floor(entry: Entry | None) -> float:
    """Strength (hand_rank) of the weakest hand the chart plays — the range edge."""
    if entry is None:
        return DEFAULT_FLOOR
    hands: set[str] = set()
    for ar in entry.actions:
        if ar.action != ActionType.FOLD and ar.frequency > 0:
            hands |= parse_range(ar.combos)
    return min((hand_rank(h) for h in hands), default=DEFAULT_FLOOR)


def _tags(chosen: ActionType, top: ActionType, correctness: Correctness) -> list[str]:
    if correctness == Correctness.OPTIMAL:
        return ["correct"]
    if chosen == ActionType.FOLD and top != ActionType.FOLD:
        return ["over_fold"]
    if chosen in (ActionType.RAISE, ActionType.BET) and top != chosen:
        return ["over_aggressive"]
    if chosen in (ActionType.CALL, ActionType.CHECK) and top in (ActionType.RAISE, ActionType.BET):
        return ["under_aggressive"]
    if chosen in (ActionType.CALL, ActionType.CHECK) and top == ActionType.FOLD:
        return ["loose_call"]
    return ["off_chart"]


def grade(spot: Spot, entry: Entry | None, decision: Decision | None) -> EvaluationResult:
    hand = hole_cards_to_class(*spot.hero.hole_cards)
    rank = hand_rank(hand)
    legal = [la.action for la in spot.legal_actions] or [ActionType.FOLD]
    if ActionType.FOLD not in legal:
        legal = [*legal, ActionType.FOLD]
    sizes = {la.action: la.min_bb for la in spot.legal_actions}

    mix = _chart_mix(entry, hand)
    full = dict(mix)
    full[ActionType.FOLD] = max(0.0, 1.0 - sum(mix.values()))
    top = max(full, key=lambda a: (full[a], _PRIORITY.get(a, 0)))
    top_freq = full[top]
    floor = _range_floor(entry)  # range edge

    evals: list[ActionEval] = []
    for a in legal:
        f = full.get(a, 0.0)
        if f > 0:
            ev = -PEN_MIX * (top_freq - f)
        elif a == ActionType.FOLD:
            ev = -(
                FOLD_OFF_BASE + FOLD_OFF_SLOPE * rank
            )  # folding a should-play hand; strong = worse
        else:
            dist = max(0.0, floor - rank)  # how far below the range edge this hand is
            ev = -(OFF_BASE + OFF_SLOPE * dist)  # near-edge call/raise = small, far = big
        evals.append(
            ActionEval(action=a, size_bb=sizes.get(a), frequency=round(f, 3), ev_bb=round(ev, 2))
        )

    best = max(evals, key=lambda e: e.ev_bb)
    is_mixed = sum(1 for v in full.values() if v > MIX_THRESHOLD) >= 2
    leak = _leak_for(spot)

    if decision is None:
        return EvaluationResult(
            per_action=evals,
            best_action=best,
            provider=ProviderKind.HEURISTIC,
            coverage=Coverage.FULL,
            leak_category=leak,
            is_mixed=is_mixed,
            rationale_tags=["chart"],
            explanation=f"{hand} from {spot.hero.position.value}: {top.value} is the play.",
        )

    ce = next((e for e in evals if e.action == decision.action), None)
    if ce is None:
        chosen = ChosenEval(frequency=0.0, ev_bb=min(e.ev_bb for e in evals) - 1.0)
    else:
        chosen = ChosenEval(frequency=ce.frequency, ev_bb=ce.ev_bb)
    ev_loss = max(0.0, round(best.ev_bb - chosen.ev_bb, 2))

    if decision.action == top:
        correctness = Correctness.OPTIMAL
    elif full.get(decision.action, 0.0) > MIX_THRESHOLD:
        correctness = Correctness.ACCEPTABLE
    elif ev_loss <= ACCEPTABLE_MAX:
        correctness = Correctness.ACCEPTABLE
    elif ev_loss <= MISTAKE_MAX:
        correctness = Correctness.MISTAKE
    else:
        correctness = Correctness.BLUNDER

    tags = _tags(decision.action, top, correctness)
    if correctness == Correctness.OPTIMAL:
        why = f"{hand}: {top.value} is the play from {spot.hero.position.value}."
    else:
        why = (
            f"{hand} from {spot.hero.position.value}: best is {top.value}; "
            f"you chose {decision.action.value} (-{ev_loss}bb)."
        )

    return EvaluationResult(
        per_action=evals,
        best_action=best,
        chosen_eval=chosen,
        ev_loss_bb=ev_loss,
        correctness=correctness,
        provider=ProviderKind.HEURISTIC,
        coverage=Coverage.FULL,
        leak_category=leak,
        is_mixed=is_mixed,
        rationale_tags=tags,
        explanation=why,
    )


def range_grid(entry: Entry | None) -> dict[str, dict[str, float]]:
    """Per-handclass action-frequency mix for the node: hand -> {action: freq}.

    Only actions with freq > 0 are included (values sum to ~1.0). Used to
    render the 13x13 grid as proportional per-action segments so it teaches
    the node's whole range, not a single collapsed label.
    """
    grid: dict[str, dict[str, float]] = {}
    for hand in all_hands():
        mix = _chart_mix(entry, hand)
        full = dict(mix)
        full[ActionType.FOLD] = max(0.0, 1.0 - sum(mix.values()))
        grid[hand] = {a.value: round(v, 3) for a, v in full.items() if v > 0}
    return grid
