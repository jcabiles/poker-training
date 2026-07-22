"""PostflopHeuristicProvider — grades flop c-bet spots (Phase 2a).

Delegates to the dedicated postflop grader (`grade_cbet`). Same async interface
+ freq/EV/coverage results as the preflop provider, so a solver postflop
provider drops in later with no downstream changes.
"""

from __future__ import annotations

from app.domain.action import Decision
from app.domain.evaluation import EvaluationResult
from app.domain.postflop import (
    grade_cbet,
    grade_limped_lead,
    grade_limped_vs_lead,
    grade_vs_cbet,
    grade_vs_check_raise,
)
from app.domain.spot import NodeContext, Spot, Street

_POSTFLOP_NODES = (
    NodeContext.CBET,
    NodeContext.VS_CBET,
    NodeContext.VS_CHECK_RAISE,
    NodeContext.LIMPED_LEAD,  # M5: HU limped-pot flop lead
    NodeContext.LIMPED_VS_LEAD,  # M5: HU limped-pot flop, facing a lead
)


class PostflopHeuristicProvider:
    name = "postflop-heuristic"

    async def supports(self, spot: Spot) -> bool:
        return (
            spot.street == Street.FLOP
            and any(n in spot.node_context for n in _POSTFLOP_NODES)
            and len(spot.board) >= 3
        )

    def _grade(self, spot: Spot, action: Decision | None) -> EvaluationResult:
        if NodeContext.VS_CHECK_RAISE in spot.node_context:
            grader = grade_vs_check_raise
        elif NodeContext.VS_CBET in spot.node_context:
            grader = grade_vs_cbet
        elif NodeContext.LIMPED_LEAD in spot.node_context:
            grader = grade_limped_lead
        elif NodeContext.LIMPED_VS_LEAD in spot.node_context:
            grader = grade_limped_vs_lead
        else:
            grader = grade_cbet
        return grader(spot, spot.hero_range, spot.villain_range, action)

    async def optimal(self, spot: Spot) -> EvaluationResult:
        return self._grade(spot, None)

    async def evaluate(self, spot: Spot, action: Decision) -> EvaluationResult:
        return self._grade(spot, action)
