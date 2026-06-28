import pytest
from factories import make_rfi_spot
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app.db.migrate import run_migrations
from app.db.models import DrillAttempt, SRSItemRow
from app.db.session import get_session
from app.domain.spot import Spot
from app.main import app


@pytest.fixture
def temp_engine(tmp_path):
    url = f"sqlite:///{tmp_path / 'api.db'}"
    run_migrations(url)
    return create_engine(url, connect_args={"check_same_thread": False})


@pytest.fixture
def client(temp_engine):
    def _override():
        with Session(temp_engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.parametrize("mode", ["random", "review", "leak_focus", "exploit"])
def test_next_returns_valid_spot_for_each_mode(client, mode):
    resp = client.get(f"/api/v1/drill/next?mode={mode}")
    assert resp.status_code == 200
    spot = Spot.model_validate(resp.json()["spot"])
    assert spot.street.value == "preflop"
    assert spot.node_context  # has at least one node tag


def test_random_mode_never_returns_exploit_spot(client):
    for _ in range(40):
        spot = client.get("/api/v1/drill/next?mode=random").json()["spot"]
        assert spot["villain_type"] is None


def test_exploit_mode_sets_villain_type(client):
    spot = client.get("/api/v1/drill/next?mode=exploit").json()["spot"]
    assert spot["villain_type"] in {"calling_station", "nit", "lag", "passive_fish"}
    assert spot["node_context"]


def test_grade_persists_attempt_and_updates_srs(client, temp_engine):
    spot = make_rfi_spot().model_dump(mode="json")  # AKo from CO -> opens
    resp = client.post(
        "/api/v1/drill/grade",
        json={"spot": spot, "action": {"action": "raise", "size_bb": 2.5}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "heuristic"
    assert body["coverage"] == "full"
    assert body["correctness"] == "optimal"
    assert "is_mixed" in body

    with Session(temp_engine) as s:
        assert len(list(s.exec(select(DrillAttempt)))) == 1
        srs = list(s.exec(select(SRSItemRow)))
        assert len(srs) == 1 and srs[0].repetitions == 1  # one correct rep


def test_openapi_lists_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in [
        "/api/v1/drill/next",
        "/api/v1/drill/grade",
        "/api/v1/drill/quiz/next",
        "/api/v1/drill/quiz/grade",
        "/api/v1/health",
        "/api/v1/stats/leaks",
        "/api/v1/stats/summary",
    ]:
        assert p in paths


# --- Phase 2a: postflop mode + foundational quizzes ---
def test_postflop_mode_returns_flop_spot_no_grid(client):
    body = client.get("/api/v1/drill/next?mode=postflop").json()
    spot = Spot.model_validate(body["spot"])
    assert spot.street.value == "flop"
    assert len(spot.board) == 3
    assert body["grid"] == {}  # grid is preflop-only
    assert spot.hero_range and spot.villain_range


def test_postflop_grade_persists_and_grades(client, temp_engine):
    spot = client.get("/api/v1/drill/next?mode=postflop").json()["spot"]
    resp = client.post(
        "/api/v1/drill/grade",
        json={"spot": spot, "action": {"action": "check"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["leak_category"] == 200  # FLOP_CBET
    assert body["correctness"] is not None
    with Session(temp_engine) as s:
        assert len(list(s.exec(select(DrillAttempt)))) == 1


def test_texture_quiz_round_trips(client, temp_engine):
    item = client.get("/api/v1/drill/quiz/next?kind=texture").json()
    assert item["kind"] == "texture"
    assert len(item["board"]) == 3
    res = client.post(
        "/api/v1/drill/quiz/grade",
        json={"kind": "texture", "board": item["board"], "choice": "wet"},
    ).json()
    assert res["correctness"] in ("optimal", "acceptable", "blunder")
    assert res["expected"] in ("dry", "medium", "wet")
    with Session(temp_engine) as s:
        rows = list(s.exec(select(DrillAttempt)))
        assert len(rows) == 1 and rows[0].provider == "quiz"


def test_equity_quiz_round_trips_and_grades_bands(client, temp_engine):
    item = client.get("/api/v1/drill/quiz/next?kind=equity").json()
    assert item["kind"] == "equity"
    assert item["hero_cards"] and item["villain_range"]
    res = client.post(
        "/api/v1/drill/quiz/grade",
        json={
            "kind": "equity",
            "board": item["board"],
            "hero_cards": item["hero_cards"],
            "villain_range": item["villain_range"],
            "estimate_pct": 50.0,
        },
    ).json()
    assert res["correctness"] in ("optimal", "acceptable", "mistake", "blunder")
    assert res["delta"] is not None
    assert res["expected"].endswith("%")
    with Session(temp_engine) as s:
        rows = list(s.exec(select(DrillAttempt)))
        assert len(rows) == 1 and rows[0].provider == "quiz"
