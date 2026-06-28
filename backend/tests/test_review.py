from datetime import date, timedelta

import pytest
from factories import make_rfi_spot
from sqlmodel import Session, create_engine

from app.db.migrate import run_migrations
from app.domain.spot import Position
from app.services.review import due_items, record_attempt


@pytest.fixture
def engine(tmp_path):
    url = f"sqlite:///{tmp_path / 'r.db'}"
    run_migrations(url)
    return create_engine(url, connect_args={"check_same_thread": False})


def test_record_creates_srs_row(engine):
    spot = make_rfi_spot(position=Position.CO)
    with Session(engine) as s:
        row = record_attempt(s, spot, "blunder", leak_category=102)
    assert row.repetitions == 0  # failed -> reset
    assert row.interval_days == 1
    assert row.leak_category == 102


def test_due_queue_respects_interval(engine):
    spot = make_rfi_spot(position=Position.CO)
    with Session(engine) as s:
        record_attempt(s, spot, "blunder", leak_category=102)
    with Session(engine) as s:
        assert due_items(s, date.today()) == []  # due tomorrow, not today
        future = due_items(s, date.today() + timedelta(days=2))
        assert len(future) == 1
        assert future[0].leak_category == 102


def test_repeat_attempt_updates_same_row(engine):
    spot = make_rfi_spot(position=Position.CO)
    with Session(engine) as s:
        record_attempt(s, spot, "optimal")
        record_attempt(s, spot, "optimal")
        rows = due_items(s, date.today() + timedelta(days=999))
    assert len(rows) == 1  # same signature -> one row
    assert rows[0].repetitions == 2


def test_exploit_attempt_persists_villain_type(engine):
    from app.domain.archetypes import VillainType

    spot = make_rfi_spot(position=Position.CO).model_copy(update={"villain_type": VillainType.NIT})
    with Session(engine) as s:
        row = record_attempt(s, spot, "optimal", leak_category=301)
    assert row.villain_type == "nit"
