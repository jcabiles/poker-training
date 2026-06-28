"""StrategyProvider — the one grading contract.

ASYNC from day 1: solver providers (Phase 3) do I/O-bound table lookups, and
making this sync now would force a rewrite of every provider + fixture later.
Downstream code never knows which provider graded a spot.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.action import Decision
from app.domain.evaluation import EvaluationResult
from app.domain.spot import Spot


@runtime_checkable
class StrategyProvider(Protocol):
    name: str

    async def supports(self, spot: Spot) -> bool:
        """True if this provider can grade this spot."""
        ...

    async def optimal(self, spot: Spot) -> EvaluationResult:
        """The action mix at this spot (no chosen action)."""
        ...

    async def evaluate(self, spot: Spot, action: Decision) -> EvaluationResult:
        """Grade a chosen action at this spot."""
        ...
