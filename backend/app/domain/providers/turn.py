"""TurnHeuristicProvider — grades HU turn spots (S6).

Delegates to the dedicated turn graders (`grade_turn_barrel` /
`grade_vs_turn_bet`). Same async duck-typed interface + freq/EV/coverage
results as the flop provider, so a solver turn provider drops in later with no
downstream changes. NEVER accepts flop node contexts — a turn-street spot
tagged with a flop node (e.g. CBET) must stay NOT_FOUND
(test_postflop_provider_rejects_turn_street depends on it).
"""

from __future__ import annotations

from app.domain.action import Decision
from app.domain.evaluation import EvaluationResult
from app.domain.postflop import grade_turn_barrel, grade_vs_turn_bet
from app.domain.spot import NodeContext, Spot, Street

_TURN_NODES = (NodeContext.TURN_BARREL, NodeContext.VS_TURN_BET)


class TurnHeuristicProvider:
    name = "turn-heuristic"

    async def supports(self, spot: Spot) -> bool:
        return (
            spot.street == Street.TURN
            and any(n in spot.node_context for n in _TURN_NODES)
            and len(spot.board) >= 4
        )

    def _grade(self, spot: Spot, action: Decision | None) -> EvaluationResult:
        if NodeContext.VS_TURN_BET in spot.node_context:
            grader = grade_vs_turn_bet
        else:
            grader = grade_turn_barrel
        return grader(spot, spot.hero_range, spot.villain_range, action)

    async def optimal(self, spot: Spot) -> EvaluationResult:
        return self._grade(spot, None)

    async def evaluate(self, spot: Spot, action: Decision) -> EvaluationResult:
        return self._grade(spot, action)
