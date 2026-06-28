"""SRS review service — records attempts (SM-2) and serves the due queue.

Lives in the service layer (not pure domain) because it touches the DB + the
calendar; the SM-2 math itself stays pure in domain/srs.py.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, select

from app.db.models import SRSItemRow
from app.domain.spot import Spot
from app.domain.srs import quality_from_correctness, sm2, spot_signature


def record_attempt(
    session: Session,
    spot: Spot,
    correctness: str | None,
    leak_category: int | None = None,
) -> SRSItemRow:
    sig = spot_signature(spot)
    quality = quality_from_correctness(correctness)
    row = session.get(SRSItemRow, sig)
    if row is None:
        row = SRSItemRow(
            signature=sig,
            node_context=spot.node_context[0].value if spot.node_context else "",
            position=spot.hero.position.value,
            facing=spot.facing.value if spot.facing else None,
            limper_count=spot.limper_count,
            villain_type=spot.villain_type.value if spot.villain_type else None,
            leak_category=leak_category,
        )
    ease, interval, reps = sm2(row.ease_factor, row.interval_days, row.repetitions, quality)
    row.ease_factor, row.interval_days, row.repetitions = ease, interval, reps
    row.due_date = date.today() + timedelta(days=interval)
    row.last_grade = quality
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def due_items(session: Session, today: date | None = None) -> list[SRSItemRow]:
    today = today or date.today()
    return list(session.exec(select(SRSItemRow).where(SRSItemRow.due_date <= today)))
