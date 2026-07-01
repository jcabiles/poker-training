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


# --- Phase 2c: postflop archetype persistence + override ---
import random  # noqa: E402

from sqlmodel import select  # noqa: E402

from app.db.models import SRSItemRow  # noqa: E402
from app.domain.scenarios import build_cbet_spot, build_vs_cbet_spot  # noqa: E402
from app.domain.srs import spot_signature  # noqa: E402


def test_cbet_attempt_persists_archetype(engine):
    spot = build_cbet_spot(random.Random(1), eff_bb=100.0)
    with Session(engine) as s:
        row = record_attempt(s, spot, "optimal", 200)
    assert row.street == "flop"
    assert row.texture_class and row.spr_bucket
    assert row.faced_bet_bucket == "none"  # hero is the bettor


def test_vs_cbet_attempt_persists_faced_bucket(engine):
    spot = build_vs_cbet_spot(random.Random(2), eff_bb=100.0, cbet_frac=0.75)
    with Session(engine) as s:
        row = record_attempt(s, spot, "mistake", 201)
    assert row.street == "flop"
    assert row.faced_bet_bucket in ("small", "big")


def test_preflop_attempt_has_null_buckets(engine):
    spot = make_rfi_spot(position=Position.CO)
    with Session(engine) as s:
        row = record_attempt(s, spot, "optimal", 102)
    assert row.street == "preflop"
    assert row.texture_class is None and row.faced_bet_bucket is None


def test_legacy_null_row_backfills(engine):
    spot = build_cbet_spot(random.Random(4), eff_bb=100.0)
    sig = spot_signature(spot)
    with Session(engine) as s:
        s.add(
            SRSItemRow(
                signature=sig,
                node_context="cbet",
                position=spot.hero.position.value,
                facing=spot.facing.value if spot.facing else None,
            )
        )
        s.commit()
        row = record_attempt(s, spot, "optimal", 200)
    assert row.street == "flop"
    assert row.texture_class is not None  # backfilled on next attempt


def test_srs_signature_override_routes_to_named_row(engine):
    spot = build_cbet_spot(random.Random(6), eff_bb=100.0)
    with Session(engine) as s:
        first = record_attempt(s, spot, "optimal", 200)
        n1 = len(list(s.exec(select(SRSItemRow))))
        other = build_vs_cbet_spot(random.Random(7), eff_bb=100.0)
        other.srs_signature = first.signature
        assert spot_signature(other) != first.signature
        second = record_attempt(s, other, "optimal", 201)
        assert second.signature == first.signature
        assert len(list(s.exec(select(SRSItemRow)))) == n1  # no new row created
