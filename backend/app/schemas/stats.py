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
    ev_given_up_today_bb: float  # sum of today's ev_loss_bb (local day)


class CalendarDay(BaseModel):
    date: str  # "YYYY-MM-DD"
    attempts: int
    accuracy: float


class BiggestMiss(BaseModel):
    label: str
    ev_loss_bb: float


class RecapResponse(BaseModel):
    day: str | None  # "YYYY-MM-DD" or None if the DB has no attempts
    hands: int
    accuracy: float
    bb_given_up: float
    biggest_miss: BiggestMiss | None
