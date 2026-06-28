from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.stats import LeakStat, StatsSummary
from app.services.stats import leak_stats, summary

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/leaks", response_model=list[LeakStat])
def get_leaks(session: Session = Depends(get_session)):
    return leak_stats(session)


@router.get("/summary", response_model=StatsSummary)
def get_summary(session: Session = Depends(get_session)):
    return summary(session)
