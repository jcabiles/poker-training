"""GET /api/v1/review/plan — read-only "today's plan" surfacing (N7)."""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app.db.migrate import run_migrations
from app.db.models import SRSItemRow
from app.db.session import get_session
from app.main import app


def _client(engine):
    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    return TestClient(app)


def test_plan_empty_db_returns_zero_due(tmp_path):
    url = f"sqlite:///{tmp_path / 'plan_empty.db'}"
    run_migrations(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    client = _client(engine)
    try:
        resp = client.get("/api/v1/review/plan")
        assert resp.status_code == 200
        body = resp.json()
        assert body["due_count"] == 0
        assert body["items"] == []
    finally:
        app.dependency_overrides.clear()


def test_plan_lists_due_item_with_label(tmp_path):
    url = f"sqlite:///{tmp_path / 'plan_due.db'}"
    run_migrations(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with Session(engine) as s:
        s.add(
            SRSItemRow(
                owner_id="",
                signature="sig-due-1",
                node_context="RFI",
                position="CO",
                due_date=date.today() - timedelta(days=1),
                last_grade=2,
            )
        )
        s.commit()
    client = _client(engine)
    try:
        resp = client.get("/api/v1/review/plan")
        assert resp.status_code == 200
        body = resp.json()
        assert body["due_count"] >= 1
        assert body["items"][0]["label"] == "RFI (CO)"
        assert body["items"][0]["last_grade"] == 2
    finally:
        app.dependency_overrides.clear()
