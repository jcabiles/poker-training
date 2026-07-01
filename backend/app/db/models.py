"""Persistence models (SQLModel).

DrillAttempt is one graded decision. Keyed for analytics by spot_signature
(the SRS-stable id) and leak_category (the namespaced taxonomy value).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _today() -> date:
    return date.today()


class DrillAttempt(SQLModel, table=True):
    __tablename__ = "drill_attempt"

    id: int | None = Field(default=None, primary_key=True)
    spot_signature: str = Field(index=True)
    leak_category: int | None = Field(default=None)
    chosen_action: str
    correctness: str | None = Field(default=None)
    ev_loss_bb: float = 0.0
    provider: str
    created_at: datetime = Field(default_factory=_utcnow)
    # Hand class (e.g. "AKo", "77") derived from hero's hole cards at grade time
    # (Phase: Challenge mode T1). Nullable — not backfilled for historical rows.
    hand_class: str | None = Field(default=None)


class SRSItemRow(SQLModel, table=True):
    """SM-2 spaced-repetition state, one row per spot archetype (signature)."""

    __tablename__ = "srs_item"

    signature: str = Field(primary_key=True)
    node_context: str
    position: str
    facing: str | None = Field(default=None)
    limper_count: int = 0
    villain_type: str | None = Field(default=None)
    leak_category: int | None = Field(default=None)
    # Postflop archetype (Phase 2c) — nullable; preflop rows leave these NULL.
    street: str | None = Field(default=None)
    texture_class: str | None = Field(default=None)
    spr_bucket: str | None = Field(default=None)
    faced_bet_bucket: str | None = Field(default=None)
    ease_factor: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    due_date: date = Field(default_factory=_today)
    last_grade: int | None = Field(default=None)
    updated_at: datetime = Field(default_factory=_utcnow)
