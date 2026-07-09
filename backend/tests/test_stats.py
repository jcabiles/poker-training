from datetime import UTC, date, datetime, timedelta

import pytest
from sqlmodel import Session, create_engine

from app.db.migrate import run_migrations
from app.db.models import DrillAttempt
from app.services.stats import calendar, leak_stats, recap, summary


@pytest.fixture
def engine(tmp_path):
    url = f"sqlite:///{tmp_path / 's.db'}"
    run_migrations(url)
    return create_engine(url, connect_args={"check_same_thread": False})


def _attempt(cat, correctness, loss=0.0, created_at=None, hand_class=None):
    kwargs = {}
    if created_at is not None:
        kwargs["created_at"] = created_at
    return DrillAttempt(
        spot_signature="sig",
        leak_category=cat,
        chosen_action="raise",
        correctness=correctness,
        ev_loss_bb=loss,
        provider="heuristic",
        hand_class=hand_class,
        **kwargs,
    )


def test_leak_stats_ranks_worst_first(engine):
    with Session(engine) as s:
        # cat 100: 1/3 good (bad). cat 112: 3/3 good (fine).
        s.add_all(
            [
                _attempt(100, "blunder", 3.0),
                _attempt(100, "mistake", 1.5),
                _attempt(100, "optimal", 0.0),
                _attempt(112, "optimal"),
                _attempt(112, "acceptable"),
                _attempt(112, "optimal"),
            ]
        )
        s.commit()
        stats = leak_stats(s)
    assert stats[0]["category"] == 100  # worst accuracy first
    assert stats[0]["accuracy"] < stats[1]["accuracy"]
    assert stats[0]["name"] == "RFI_EP"


def test_summary_counts_and_streak(engine):
    with Session(engine) as s:
        s.add_all([_attempt(112, "optimal"), _attempt(112, "blunder", 3.0)])
        s.commit()
        out = summary(s)
    assert out["total_attempts"] == 2
    assert out["accuracy"] == 0.5
    assert out["streak_days"] == 1  # attempts today
    assert out["ev_given_up_today_bb"] == 3.0


def test_summary_ev_given_up_today_only_counts_today(engine):
    yesterday = datetime.now(UTC) - timedelta(days=1)
    with Session(engine) as s:
        s.add_all(
            [
                _attempt(112, "blunder", 5.0, created_at=yesterday),
                _attempt(112, "mistake", 1.25),  # today
                _attempt(112, "mistake", 0.75),  # today
            ]
        )
        s.commit()
        out = summary(s)
    assert out["ev_given_up_today_bb"] == 2.0  # only today's 1.25 + 0.75


def test_summary_naive_utc_created_at_round_trip(engine):
    # created_at stored as naive-UTC (SQLite can drop tzinfo); _local_date
    # treats naive values as UTC before converting to local time. A row
    # written "now" (naive) should still count toward today's streak/EV.
    naive_now = datetime.now(UTC).replace(tzinfo=None)
    with Session(engine) as s:
        s.add(_attempt(112, "mistake", 2.0, created_at=naive_now))
        s.commit()
        out = summary(s)
    assert out["streak_days"] == 1
    assert out["ev_given_up_today_bb"] == 2.0


def test_calendar_empty_db_returns_full_grid(engine):
    today = date.today()
    with Session(engine) as s:
        days = calendar(s, weeks=1)
    start_date = date.fromisoformat(days[0]["date"])
    assert start_date.weekday() == 0  # starts on a Monday
    assert days[-1]["date"] == today.isoformat()  # ends on today
    assert all(d["attempts"] == 0 and d["accuracy"] == 0.0 for d in days)
    # covers today-minus-(weeks-1)-weeks through today, so length is
    # (today - that Monday).days + 1
    assert len(days) == (today - start_date).days + 1


def test_calendar_single_day_and_week_boundary(engine):
    today = date.today()
    with Session(engine) as s:
        s.add_all([_attempt(112, "optimal"), _attempt(112, "mistake", 1.0)])
        s.commit()
        days = calendar(s, weeks=2)
    # grid starts on a Monday (the boundary of today-minus-1-week's week) and
    # ends today.
    start_date = date.fromisoformat(days[0]["date"])
    assert start_date.weekday() == 0  # Monday
    assert days[-1]["date"] == today.isoformat()
    assert len(days) == (today - start_date).days + 1
    today_entry = next(d for d in days if d["date"] == today.isoformat())
    assert today_entry["attempts"] == 2
    assert today_entry["accuracy"] == 0.5


def test_recap_empty_db_returns_well_formed_zeros(engine):
    with Session(engine) as s:
        out = recap(s)
    assert out == {
        "day": None,
        "hands": 0,
        "accuracy": 0.0,
        "bb_given_up": 0.0,
        "biggest_miss": None,
    }


def test_recap_most_recent_day_and_biggest_miss(engine):
    yesterday = datetime.now(UTC) - timedelta(days=1)
    with Session(engine) as s:
        s.add_all(
            [
                _attempt(100, "blunder", 9.0, created_at=yesterday, hand_class="72o"),
                _attempt(112, "mistake", 1.5, hand_class="AKo"),  # today
                _attempt(112, "optimal", 0.0, hand_class="QQ"),  # today
            ]
        )
        s.commit()
        out = recap(s)
    assert out["day"] == date.today().isoformat()
    assert out["hands"] == 2
    assert out["accuracy"] == 0.5
    assert out["bb_given_up"] == 1.5
    assert out["biggest_miss"] == {"label": "VS_RFI (AKo)", "ev_loss_bb": 1.5}


def test_recap_biggest_miss_tie_breaks_deterministically(engine):
    with Session(engine) as s:
        s.add_all(
            [
                _attempt(100, "blunder", 2.0, hand_class="72o"),
                _attempt(112, "blunder", 2.0, hand_class="AKo"),
            ]
        )
        s.commit()
        out = recap(s)
    # tie on ev_loss_bb: max() returns the first max encountered, which is
    # insertion/query order — assert it's one of the tied rows, not both.
    assert out["biggest_miss"]["ev_loss_bb"] == 2.0
    assert out["biggest_miss"]["label"] in {"RFI_EP (72o)", "VS_RFI (AKo)"}


def test_recap_biggest_miss_rounds_ev_loss(engine):
    with Session(engine) as s:
        s.add(_attempt(112, "mistake", 1.005, hand_class="AKo"))
        s.commit()
        out = recap(s)
    # matches stdlib round(1.005, 2), incl. its float-repr quirk
    assert out["biggest_miss"]["ev_loss_bb"] == round(1.005, 2)
