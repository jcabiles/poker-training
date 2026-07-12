"""Simulate endpoints (S9 — hero plays / session persistence / stacks / ledger).

POST /simulate/session               -> create a session, deal hand 1.
GET  /simulate/session/{id}          -> restore the live decision point.
POST /simulate/session/{id}/action   -> hero acts; bots advance to the next
                                         hero decision (or hand end).
POST /simulate/session/{id}/hand     -> deal the next hand (carry-over stacks).
POST /simulate/session/{id}/leave    -> end the session (no longer restorable).
GET  /simulate/report/streets        -> all-time per-street grading report (S10).
GET  /simulate/{id}/preflop-chart    -> baseline range chart for the hero's
                                         current preflop decision (chart slice C1).
GET  /simulate/{id}/villain-range/{seat} -> live estimated hand-range for a
                                         non-hero, non-folded villain seat
                                         (villain-range V2).

All state lives in the DB (`app.services.sim_session`); this module only
translates HTTP <-> service calls. No auth: `owner_id=""`. See
`docs/ai-dlc/specs/simulate-s9.md`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.domain.action import Decision
from app.schemas.simulate import PreflopChartView, SessionView, StreetReportView, VillainRangeView
from app.services import sim_session
from app.services.sim_session import SessionNotFound

router = APIRouter(prefix="/simulate", tags=["simulate"])

_OWNER_ID = ""


@router.post("/session", response_model=SessionView)
async def create_session(db: Session = Depends(get_session)) -> SessionView:
    return sim_session.create_session(db, owner_id=_OWNER_ID)


@router.get("/session/{session_id}", response_model=SessionView)
async def get_session_view(
    session_id: str, db: Session = Depends(get_session)
) -> SessionView:
    view = sim_session.restore_session(db, session_id, owner_id=_OWNER_ID)
    if view is None:
        raise HTTPException(status_code=404, detail="session not found")
    return view


@router.post("/session/{session_id}/action", response_model=SessionView)
async def post_hero_action(
    session_id: str, decision: Decision, db: Session = Depends(get_session)
) -> SessionView:
    try:
        return await sim_session.apply_hero_action(db, session_id, decision, owner_id=_OWNER_ID)
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/session/{session_id}/hand", response_model=SessionView)
async def next_hand(session_id: str, db: Session = Depends(get_session)) -> SessionView:
    try:
        return sim_session.deal_next_hand(db, session_id, owner_id=_OWNER_ID)
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


@router.post("/session/{session_id}/leave", status_code=204)
async def leave(session_id: str, db: Session = Depends(get_session)) -> None:
    sim_session.leave_session(db, session_id, owner_id=_OWNER_ID)


@router.get("/report/streets", response_model=StreetReportView)
async def street_report(db: Session = Depends(get_session)) -> StreetReportView:
    return sim_session.street_report(db, owner_id=_OWNER_ID)


@router.get("/{session_id}/preflop-chart", response_model=PreflopChartView)
async def preflop_chart(
    session_id: str, db: Session = Depends(get_session)
) -> PreflopChartView:
    # Availability (not-hero-turn / postflop / unmappable / hand over) is a
    # 200-body concern; 404 stays SessionNotFound-only.
    try:
        return sim_session.preflop_chart(db, session_id, owner_id=_OWNER_ID)
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc


@router.get("/{session_id}/villain-range/{seat_index}", response_model=VillainRangeView)
async def villain_range(
    session_id: str,
    seat_index: int,
    through_action: int | None = None,
    db: Session = Depends(get_session),
) -> VillainRangeView:
    # Availability (hero seat / folded / hand over / no persona) is a
    # 200-body concern; 404 stays SessionNotFound-only (spec refuter low-1).
    try:
        return sim_session.villain_range(
            db, session_id, seat_index, through_action=through_action, owner_id=_OWNER_ID
        )
    except SessionNotFound as exc:
        raise HTTPException(status_code=404, detail="session not found") from exc
