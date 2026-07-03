"""API request/response schemas for the drill endpoints.

Domain models (Spot, Decision, EvaluationResult) are Pydantic and are reused
directly as the wire contract — no parallel DTOs to drift.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.action import Decision
from app.domain.spot import Spot


class NextDrillResponse(BaseModel):
    spot: Spot
    grid: dict[str, dict[str, float]] = {}  # handclass -> {action: freq}, for grid coloring


class GradeRequest(BaseModel):
    spot: Spot
    action: Decision


# --- Foundational quizzes (Phase 2a) — stateless: the answer carries the spot ---
class QuizItem(BaseModel):
    quiz_id: str
    kind: str  # "texture" | "equity"
    board: list[str]
    prompt: str
    options: list[str] = []  # texture multiple-choice
    hero_cards: tuple[str, str] | None = None  # equity
    villain_range: str | None = None  # equity (range descriptor)


class QuizAnswer(BaseModel):
    kind: str
    board: list[str]
    choice: str | None = None  # texture label chosen
    estimate_pct: float | None = None  # equity estimate (0-100)
    hero_cards: tuple[str, str] | None = None
    villain_range: str | None = None


class QuizResult(BaseModel):
    kind: str
    correct: bool
    correctness: str
    expected: str
    your_answer: str
    delta: float | None = None  # percentage-point miss (equity)
    explanation: str
    leak_category: int
