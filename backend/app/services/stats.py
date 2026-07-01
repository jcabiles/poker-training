"""Leak tracking + summary aggregation over DrillAttempt rows."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, select

from app.db.models import DrillAttempt, SRSItemRow
from app.domain.leaks import LeakCategory

_GOOD = {"optimal", "acceptable"}


def _name(cat: int) -> str:
    try:
        return LeakCategory(cat).name
    except ValueError:
        return str(cat)


def leak_stats(session: Session) -> list[dict]:
    rows = list(session.exec(select(DrillAttempt)))
    by: dict[int, list[DrillAttempt]] = defaultdict(list)
    for r in rows:
        if r.leak_category is not None:
            by[r.leak_category].append(r)

    out = []
    for cat, items in by.items():
        n = len(items)
        good = sum(1 for i in items if i.correctness in _GOOD)
        out.append(
            {
                "category": cat,
                "name": _name(cat),
                "attempts": n,
                "accuracy": round(good / n, 3) if n else 0.0,
                "avg_ev_loss": round(sum(i.ev_loss_bb for i in items) / n, 3) if n else 0.0,
            }
        )
    out.sort(key=lambda x: (x["accuracy"], -x["attempts"]))  # worst first
    return out


def _accuracy(items: list[DrillAttempt]) -> float:
    if not items:
        return 0.0
    return sum(1 for i in items if i.correctness in _GOOD) / len(items)


def summary(session: Session, today: date | None = None) -> dict:
    # DrillAttempt.created_at is stamped in UTC; compare the streak in UTC too so
    # "today" matches the stored dates (avoids a UTC-vs-local date-boundary gap).
    today = today or datetime.now(UTC).date()
    rows = list(session.exec(select(DrillAttempt)))
    ordered = sorted(rows, key=lambda r: r.created_at)

    days = {r.created_at.date() for r in rows}
    streak, d = 0, today
    while d in days:
        streak += 1
        d -= timedelta(days=1)

    due = len(list(session.exec(select(SRSItemRow).where(SRSItemRow.due_date <= today))))
    trend = round(_accuracy(ordered[-20:]) - _accuracy(ordered[-40:-20]), 3)

    return {
        "total_attempts": len(rows),
        "accuracy": round(_accuracy(rows), 3),
        "due_count": due,
        "streak_days": streak,
        "trend": trend,
    }
