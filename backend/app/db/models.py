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
    # Ownership seam: '' = the local user (no accounts yet, sentinel only).
    owner_id: str = Field(default="")
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
    # Attempt origin (S10): 'practice' (default, matches all historical rows) or
    # 'simulate'. Practice stats reads filter on it so sim rows never skew them.
    # NOTE: DB column is intentionally nullable (migration 0010 add-column
    # pattern) — readers must treat NULL as 'practice' (stats.py does).
    source: str = Field(default="practice")


class SimSession(SQLModel, table=True):
    """One persistent Simulate table session (S9)."""

    __tablename__ = "sim_session"

    id: str = Field(primary_key=True)  # uuid4 hex
    # Ownership seam: '' = the local user (no accounts yet, sentinel only).
    owner_id: str = Field(default="", index=True)
    button_seat: int
    hand_no: int
    status: str = Field(default="active")  # "active" | "ended"
    created_at: datetime = Field(default_factory=_utcnow)


class SimSeat(SQLModel, table=True):
    """Per-seat carry-over stack + buy-in ledger; 9 rows per session."""

    __tablename__ = "sim_seat"

    session_id: str = Field(primary_key=True, foreign_key="sim_session.id")
    seat_index: int = Field(primary_key=True)  # 0..8 (composite PK)
    is_hero: bool
    persona_type: str | None = Field(default=None)  # VillainType value; None = hero
    stack_bb: float  # carry-over current stack
    buyins_bb: float  # cumulative chips brought in


class SimHand(SQLModel, table=True):
    """One dealt hand; `state_json` holds the live HandState (server-side ONLY —
    all 9 seats' hole cards + full_board; never serialized to the wire)."""

    __tablename__ = "sim_hand"

    id: int | None = Field(default=None, primary_key=True)  # autoincrement
    session_id: str = Field(foreign_key="sim_session.id", index=True)
    hand_no: int
    button_seat: int
    rng_seed: str  # 256-bit deal seed (str: overflows SQLite INTEGER)
    status: str = Field(default="in_progress")  # "in_progress" | "complete"
    state_json: str | None = None  # serialized live HandState
    created_at: datetime = Field(default_factory=_utcnow)


class SimDecision(SQLModel, table=True):
    """One graded hero decision inside a Simulate hand (S10).

    Every hero decision gets a row — including spots the grader can't map or
    has no baseline for (coverage 'unmappable' / 'not_found', correctness
    None), so the recap and per-street report can show honest coverage. Only
    baseline-graded rows ALSO produce a tagged DrillAttempt(source='simulate').
    """

    __tablename__ = "sim_decision"

    id: int | None = Field(default=None, primary_key=True)
    # Ownership seam: '' = the local user (no accounts yet, sentinel only).
    owner_id: str = Field(default="")
    session_id: str = Field(foreign_key="sim_session.id", index=True)
    sim_hand_id: int = Field(foreign_key="sim_hand.id", index=True)
    street: str  # preflop / flop / turn / river
    ordinal: int  # 0-based decision order within the hand
    chosen_action: str
    # None = "no baseline yet" (coverage not_found or unmappable).
    correctness: str | None = Field(default=None)
    ev_loss_bb: float = 0.0
    leak_category: int | None = Field(default=None)
    # Coverage.value ('full'/'partial'/'not_found') or 'unmappable' (the spot
    # mapper returned None — no canonical Spot could be built at all).
    coverage: str
    created_at: datetime = Field(default_factory=_utcnow)


class SRSItemRow(SQLModel, table=True):
    """SM-2 spaced-repetition state, one row per spot archetype (signature)."""

    __tablename__ = "srs_item"

    # Composite PK (owner_id, signature): owner_id first so the identity key for
    # session.get() is ("", sig). '' = the local user (ownership seam, 0006).
    owner_id: str = Field(default="", primary_key=True)
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
    # Card-class dims, each "pairing|flush|straight|over|blank":
    # turn_class (S6) = the TURN card's class, set for turn AND river rows
    # (NULL for preflop/flop); river_class (S7) = the RIVER card's class, set
    # for river rows ONLY (NULL everywhere else).
    turn_class: str | None = Field(default=None)
    river_class: str | None = Field(default=None)
    ease_factor: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    due_date: date = Field(default_factory=_today)
    last_grade: int | None = Field(default=None)
    updated_at: datetime = Field(default_factory=_utcnow)
