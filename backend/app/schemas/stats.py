from __future__ import annotations

from pydantic import BaseModel


class LeakStat(BaseModel):
    category: int
    name: str
    attempts: int
    accuracy: float  # fraction graded optimal/acceptable
    avg_ev_loss: float


class StatsSummary(BaseModel):
    total_attempts: int
    accuracy: float
    due_count: int
    streak_days: int
    trend: float  # last-20 accuracy minus prior-20
