"""Simulate endpoints (S9 — hero plays / session persistence / stacks / ledger).

POST /simulate/session               -> create a session, deal hand 1.
GET  /simulate/session/{id}          -> restore the live decision point.
POST /simulate/session/{id}/action   -> hero acts; bots advance to the next
                                         hero decision (or hand end).
POST /simulate/session/{id}/hand     -> deal the next hand (carry-over stacks).
POST /simulate/session/{id}/leave    -> end the session (no longer restorable).

All state lives in the DB (`app.services.sim_session`); this module only
translates HTTP <-> service calls. No auth: `owner_id=""`. See
`docs/ai-dlc/specs/simulate-s9.md`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.domain.action import Decision
from app.schemas.simulate import SessionView
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
        return sim_session.apply_hero_action(db, session_id, decision, owner_id=_OWNER_ID)
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
