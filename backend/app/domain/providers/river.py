"""RiverHeuristicProvider — grades HU river spots (S7).

Delegates to the dedicated river graders (`grade_river_barrel` /
`grade_vs_river_bet`). Same async duck-typed interface + freq/EV/coverage
results as the flop/turn providers, so a solver river provider drops in later
with no downstream changes. NEVER accepts flop or turn node contexts — a
river-street spot tagged with a flop node (e.g. CBET) must stay NOT_FOUND
(test_postflop_provider_rejects_river_street + the tripwire depend on it).
"""

from __future__ import annotations

from app.domain.action import Decision
from app.domain.evaluation import EvaluationResult
from app.domain.postflop import grade_river_barrel, grade_vs_river_bet
from app.domain.spot import NodeContext, Spot, Street

_RIVER_NODES = (NodeContext.RIVER_BARREL, NodeContext.VS_RIVER_BET)


class RiverHeuristicProvider:
    name = "river-heuristic"

    async def supports(self, spot: Spot) -> bool:
        return (
            spot.street == Street.RIVER
            and any(n in spot.node_context for n in _RIVER_NODES)
            and len(spot.board) >= 5
        )

    def _grade(self, spot: Spot, action: Decision | None) -> EvaluationResult:
        if NodeContext.VS_RIVER_BET in spot.node_context:
            grader = grade_vs_river_bet
        else:
            grader = grade_river_barrel
        return grader(spot, spot.hero_range, spot.villain_range, action)

    async def optimal(self, spot: Spot) -> EvaluationResult:
        return self._grade(spot, None)

    async def evaluate(self, spot: Spot, action: Decision) -> EvaluationResult:
        return self._grade(spot, action)
