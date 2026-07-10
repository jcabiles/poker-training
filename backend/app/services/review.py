"""SRS review service — records attempts (SM-2) and serves the due queue.

Lives in the service layer (not pure domain) because it touches the DB + the
calendar; the SM-2 math itself stays pure in domain/srs.py.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, select

from app.db.models import SRSItemRow
from app.domain.spot import Spot, Street
from app.domain.srs import (
    faced_bet_bucket,
    quality_from_correctness,
    sm2,
    spot_signature,
    spr_bucket,
)
from app.domain.texture import classify


def _postflop_archetype(
    spot: Spot,
) -> tuple[str, str | None, str | None, str | None, str | None, str | None]:
    """(street, texture_class, spr_bucket, faced_bet_bucket, turn_class, river_class);
    buckets None for preflop. texture_class stays the flop-3-card classification on
    every street; turn_class (S6) is set only for turn/river spots — None for flop;
    river_class (S7) is set only for river spots — None everywhere else."""
    street = spot.street.value
    if spot.street == Street.PREFLOP:
        return street, None, None, None, None, None
    tex = classify(spot.board[:3]).texture_class if len(spot.board) >= 3 else None  # guard <3 cards
    turn = None
    if spot.street in (Street.TURN, Street.RIVER) and len(spot.board) >= 4:
        from app.domain.texture import turn_card_class

        turn = turn_card_class(spot.board)
    river = None
    if spot.street == Street.RIVER and len(spot.board) >= 5:
        from app.domain.texture import river_card_class

        river = river_card_class(spot.board)
    return street, tex, spr_bucket(spot.spr), faced_bet_bucket(spot), turn, river


def record_attempt(
    session: Session,
    spot: Spot,
    correctness: str | None,
    leak_category: int | None = None,
) -> SRSItemRow:
    # Honor an SRS-key override (a reconstructed review spot graduates the SAME row
    # it was rebuilt from, regardless of the reconstructed board's own signature).
    sig = spot.srs_signature or spot_signature(spot)
    quality = quality_from_correctness(correctness)
    street, tex, sprb, facedb, turnc, riverc = _postflop_archetype(spot)
    row = session.get(SRSItemRow, ("", sig))  # composite PK (owner_id, signature)
    if row is None:
        row = SRSItemRow(
            owner_id="",  # '' = the local user (ownership seam)
            signature=sig,
            node_context=spot.node_context[0].value if spot.node_context else "",
            position=spot.hero.position.value,
            facing=spot.facing.value if spot.facing else None,
            limper_count=spot.limper_count,
            villain_type=spot.villain_type.value if spot.villain_type else None,
            leak_category=leak_category,
            street=street,
            texture_class=tex,
            spr_bucket=sprb,
            faced_bet_bucket=facedb,
            turn_class=turnc,
            river_class=riverc,
        )
    elif row.street is None:  # backfill legacy / pre-2c rows on their next attempt
        (
            row.street,
            row.texture_class,
            row.spr_bucket,
            row.faced_bet_bucket,
            row.turn_class,
            row.river_class,
        ) = (street, tex, sprb, facedb, turnc, riverc)
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
    return list(
        session.exec(
            select(SRSItemRow)
            .where(SRSItemRow.owner_id == "")  # local user only (ownership seam)
            .where(SRSItemRow.due_date <= today)
            .order_by(SRSItemRow.due_date)
        )
    )
