"""PostflopHeuristicProvider — grades flop c-bet spots (Phase 2a).

Delegates to the dedicated postflop grader (`grade_cbet`). Same async interface
+ freq/EV/coverage results as the preflop provider, so a solver postflop
provider drops in later with no downstream changes.
"""

from __future__ import annotations

from app.domain.action import Decision
from app.domain.evaluation import EvaluationResult
from app.domain.postflop import grade_cbet
from app.domain.spot import NodeContext, Spot, Street


class PostflopHeuristicProvider:
    name = "postflop-heuristic"

    async def supports(self, spot: Spot) -> bool:
        return (
            spot.street != Street.PREFLOP
            and NodeContext.CBET in spot.node_context
            and len(spot.board) >= 3
        )

    async def optimal(self, spot: Spot) -> EvaluationResult:
        return grade_cbet(spot, spot.hero_range, spot.villain_range, None)

    async def evaluate(self, spot: Spot, action: Decision) -> EvaluationResult:
        return grade_cbet(spot, spot.hero_range, spot.villain_range, action)
