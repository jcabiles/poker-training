from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.stats import CalendarDay, LeakStat, RecapResponse, StatsSummary
from app.services.stats import calendar, leak_stats, recap, summary

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/leaks", response_model=list[LeakStat])
def get_leaks(session: Session = Depends(get_session)):
    return leak_stats(session)


@router.get("/summary", response_model=StatsSummary)
def get_summary(session: Session = Depends(get_session)):
    return summary(session)


@router.get("/calendar", response_model=list[CalendarDay])
def get_calendar(
    weeks: int = Query(default=8, ge=1, le=26),
    session: Session = Depends(get_session),
):
    return calendar(session, weeks=weeks)


@router.get("/recap", response_model=RecapResponse)
def get_recap(session: Session = Depends(get_session)):
    return recap(session)
