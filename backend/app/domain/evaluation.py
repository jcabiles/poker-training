"""EvaluationResult — the grading contract. NEVER boolean.

Every grade is a per-action mix with frequencies + EVs, plus provenance and a
coverage signal so a solver provider can report misses and a HybridProvider can
fall back to heuristics without any interface change.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.domain.spot import ActionType


class Correctness(str, Enum):
    OPTIMAL = "optimal"
    ACCEPTABLE = "acceptable"
    MISTAKE = "mistake"
    BLUNDER = "blunder"


class Coverage(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    NOT_FOUND = "not_found"  # heuristic is authoritative for this spot


class ProviderKind(str, Enum):
    HEURISTIC = "heuristic"
    SOLVER = "solver"
    HYBRID = "hybrid"


class ActionEval(BaseModel):
    action: ActionType
    size_bb: float | None = None
    frequency: float = Field(ge=0.0, le=1.0)
    ev_bb: float


class ChosenEval(BaseModel):
    frequency: float
    ev_bb: float


class EvaluationResult(BaseModel):
    per_action: list[ActionEval]
    best_action: ActionEval
    chosen_eval: ChosenEval | None = None  # None when optimal() is called without a Decision
    ev_loss_bb: float = 0.0
    correctness: Correctness | None = None
    rationale_tags: list[str] = Field(default_factory=list)
    explanation: str = ""
    provider: ProviderKind
    leak_category: int | None = None  # LeakCategory value
    coverage: Coverage = Coverage.FULL
    solver_node_key: str | None = None
    is_mixed: bool = False  # >=2 actions played at meaningful frequency (legit mixed spot)
