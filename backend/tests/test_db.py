from sqlalchemy import inspect
from sqlmodel import Session, create_engine, select

from app.db.migrate import run_migrations
from app.db.models import DrillAttempt


def test_migrations_create_table_and_row(tmp_path):
    db = tmp_path / "t.db"
    url = f"sqlite:///{db}"

    run_migrations(url)  # alembic upgrade head from clean state

    engine = create_engine(url)
    assert "drill_attempt" in inspect(engine).get_table_names()

    with Session(engine) as s:
        s.add(
            DrillAttempt(
                spot_signature="abc123",
                leak_category=102,
                chosen_action="raise",
                correctness="optimal",
                ev_loss_bb=0.0,
                provider="heuristic",
            )
        )
        s.commit()

    with Session(engine) as s:
        rows = s.exec(select(DrillAttempt)).all()
        assert len(rows) == 1
        assert rows[0].spot_signature == "abc123"
        assert rows[0].created_at is not None
