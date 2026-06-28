"""CompositeProvider — routes a spot to the right sub-provider by street.

Preflop -> HeuristicProvider; postflop (flop) -> PostflopHeuristicProvider.
If the routed provider doesn't support the spot, returns a NOT_FOUND result so
downstream code (drill/stats) never has to know which provider graded what — the
same contract a HybridProvider will use in Phase 3.
"""

from __future__ import annotations

from app.domain.action import Decision
from app.domain.evaluation import (
    ActionEval,
    ChosenEval,
    Coverage,
    EvaluationResult,
    ProviderKind,
)
from app.domain.spot import ActionType, Spot, Street


def _not_found(spot: Spot, decision: Decision | None = None) -> EvaluationResult:
    legal = [la.action for la in spot.legal_actions] or [ActionType.FOLD]
    evals = [ActionEval(action=a, frequency=0.0, ev_bb=0.0) for a in legal]
    return EvaluationResult(
        per_action=evals,
        best_action=evals[0],
        chosen_eval=ChosenEval(frequency=0.0, ev_bb=0.0) if decision is not None else None,
        provider=ProviderKind.HEURISTIC,
        coverage=Coverage.NOT_FOUND,
        explanation="No content for this spot.",
    )


class CompositeProvider:
    name = "composite"

    def __init__(self, preflop, postflop):
        self._preflop = preflop
        self._postflop = postflop

    def _route(self, spot: Spot):
        return self._preflop if spot.street == Street.PREFLOP else self._postflop

    async def supports(self, spot: Spot) -> bool:
        return await self._route(spot).supports(spot)

    async def optimal(self, spot: Spot) -> EvaluationResult:
        sub = self._route(spot)
        if not await sub.supports(spot):
            return _not_found(spot)
        return await sub.optimal(spot)

    async def evaluate(self, spot: Spot, action: Decision) -> EvaluationResult:
        sub = self._route(spot)
        if not await sub.supports(spot):
            return _not_found(spot, action)
        return await sub.evaluate(spot, action)
