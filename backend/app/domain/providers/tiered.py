"""TieredFeedbackProvider — the shared teaching seam (N1).

Wraps ANY StrategyProvider and composes the verdict/reasoning/deep-dive tiers
(`app.domain.feedback.compose_tiers`) onto its results, so a future solver or
hybrid provider inherits the teaching layer without changes. Mounted once in
the factory; it does not touch `explanation` (backward compat) and never
double-appends the exploit enrichment — it reads `authored_rationale` instead.
"""

from __future__ import annotations

from app.domain.action import Decision
from app.domain.evaluation import EvaluationResult
from app.domain.feedback import compose_tiers
from app.domain.spot import Spot


class TieredFeedbackProvider:
    def __init__(self, inner):
        self._inner = inner
        self.name = inner.name

    async def supports(self, spot: Spot) -> bool:
        return await self._inner.supports(spot)

    async def optimal(self, spot: Spot) -> EvaluationResult:
        result = await self._inner.optimal(spot)
        result.tiers = compose_tiers(spot, result)
        return result

    async def evaluate(self, spot: Spot, action: Decision) -> EvaluationResult:
        result = await self._inner.evaluate(spot, action)
        result.tiers = compose_tiers(spot, result, action)
        return result
