import pytest
from sqlmodel import Session, create_engine

from app.db.migrate import run_migrations
from app.db.models import DrillAttempt
from app.services.stats import leak_stats, summary


@pytest.fixture
def engine(tmp_path):
    url = f"sqlite:///{tmp_path / 's.db'}"
    run_migrations(url)
    return create_engine(url, connect_args={"check_same_thread": False})


def _attempt(cat, correctness, loss=0.0):
    return DrillAttempt(
        spot_signature="sig",
        leak_category=cat,
        chosen_action="raise",
        correctness=correctness,
        ev_loss_bb=loss,
        provider="heuristic",
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
