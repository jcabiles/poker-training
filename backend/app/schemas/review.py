"""API response schema for the read-only "today's plan" endpoint (N7)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class DuePlanItem(BaseModel):
    signature: str
    due_date: date
    last_grade: int | None = None
    label: str  # human-readable spot label, e.g. "RFI (CO)"


class ReviewPlanResponse(BaseModel):
    due_count: int
    items: list[DuePlanItem] = []
