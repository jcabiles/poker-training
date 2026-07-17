"""EvaluationResult — the grading contract. NEVER boolean.

Every grade is a per-action mix with frequencies + EVs, plus provenance and a
coverage signal so a solver provider can report misses and a HybridProvider can
fall back to heuristics without any interface change.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.spot import ActionType


class Correctness(StrEnum):
    OPTIMAL = "optimal"
    ACCEPTABLE = "acceptable"
    MISTAKE = "mistake"
    BLUNDER = "blunder"


class Coverage(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    NOT_FOUND = "not_found"  # heuristic is authoritative for this spot


class ProviderKind(StrEnum):
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


class FeedbackTiers(BaseModel):
    """Tiered teaching feedback: verdict -> reasoning -> deep-dive.

    Distinct structured fields (never parsed out of the flat `explanation`,
    which is kept for backward compat). Composed post-hoc from any provider's
    result by app.domain.feedback.compose_tiers.
    """

    verdict: str  # what happened: chosen action's freq/EV vs the best action
    reasoning: str  # why: composed from rationale_tags + authored rationale
    deep_dive: str  # the numbers: full per-action mix, mixedness, coverage


class EvaluationResult(BaseModel):
    per_action: list[ActionEval]
    best_action: ActionEval
    chosen_eval: ChosenEval | None = None  # None when optimal() is called without a Decision
    ev_loss_bb: float = 0.0
    correctness: Correctness | None = None
    # Preflop sizing verdict (N3): separate from the action `correctness`. None
    # unless the graded spot offers >=2 RAISE sizes and hero raised.
    sizing_correctness: Correctness | None = None
    rationale_tags: list[str] = Field(default_factory=list)
    explanation: str = ""
    provider: ProviderKind
    leak_category: int | None = None  # LeakCategory value
    coverage: Coverage = Coverage.FULL
    solver_node_key: str | None = None
    is_mixed: bool = False  # >=2 actions played at meaningful frequency (legit mixed spot)
    # Authored content-pack rationale prose (Entry.rationale), when a provider has
    # one for this spot. Raw material for the tier composer — providers set it;
    # only compose_tiers reads it (avoids re-parsing `explanation`).
    authored_rationale: str | None = None
    tiers: FeedbackTiers | None = None  # set by the TieredFeedbackProvider wrapper
