import pytest
from factories import make_rfi_spot
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app.db.migrate import run_migrations
from app.db.models import DrillAttempt, SRSItemRow
from app.db.session import get_session
from app.domain.archetypes import VillainType
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


@pytest.mark.parametrize(
    "mode,ctx",
    [
        ("rfi", "RFI"),
        ("vs_rfi", "vs_RFI"),
        ("blind_defense", "blind_defense"),
        ("vs_limpers", "vs_limpers"),
        ("vs_3bet", "vs_3bet"),
    ],
)
def test_preflop_family_mode_deals_matching_node_context(client, mode, ctx):
    # Each home-hub path node deals its own family, not a generic random spot.
    for _ in range(20):
        spot = client.get(f"/api/v1/drill/next?mode={mode}").json()["spot"]
        assert spot["villain_type"] is None
        assert ctx in spot["node_context"]


def test_random_mode_never_returns_exploit_spot(client):
    for _ in range(40):
        spot = client.get("/api/v1/drill/next?mode=random").json()["spot"]
        assert spot["villain_type"] is None


def test_exploit_mode_sets_villain_type(client):
    spot = client.get("/api/v1/drill/next?mode=exploit").json()["spot"]
    assert spot["villain_type"] in {v.value for v in VillainType}
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


def test_postflop_due_row_graduates_via_review(client, temp_engine):
    from datetime import date, timedelta

    from factories import make_cbet_spot

    # 1. grade a postflop spot (strong hand, check is acceptable) -> one SRS row
    spot = make_cbet_spot(hole_cards=("Kh", "Kd")).model_dump(mode="json")
    client.post("/api/v1/drill/grade", json={"spot": spot, "action": {"action": "check"}})
    with Session(temp_engine) as s:
        rows = list(s.exec(select(SRSItemRow)))
        assert len(rows) == 1
        row = rows[0]
        sig = row.signature
        row.due_date = date.today() - timedelta(days=1)  # backdate so it's due
        s.add(row)
        s.commit()

    # 2. review serves a postflop spot carrying the SRS-key override
    review = client.get("/api/v1/drill/next?mode=review").json()["spot"]
    assert review["street"] == "flop"
    assert review["srs_signature"] == sig

    # 3. re-grade the review spot -> the SAME row graduates; NO new row is created
    #    (even though the reconstructed board's own signature may differ)
    client.post("/api/v1/drill/grade", json={"spot": review, "action": {"action": "check"}})
    with Session(temp_engine) as s:
        rows = list(s.exec(select(SRSItemRow)))
        assert len(rows) == 1
        assert rows[0].signature == sig
        assert rows[0].repetitions >= 1


def test_vs_cbet_mode_grades_and_persists(client, temp_engine):
    body = client.get("/api/v1/drill/next?mode=vs_cbet").json()
    spot = Spot.model_validate(body["spot"])
    assert spot.street.value == "flop"
    assert "vs_cbet" in spot.node_context
    assert body["grid"] == {}
    resp = client.post(
        "/api/v1/drill/grade",
        json={"spot": body["spot"], "action": {"action": "call"}},
    )
    assert resp.status_code == 200
    assert resp.json()["leak_category"] == 201  # VS_CBET
    with Session(temp_engine) as s:
        assert len(list(s.exec(select(DrillAttempt)))) == 1


def test_vs_check_raise_mode_returns_flop_spot(client):
    body = client.get("/api/v1/drill/next?mode=vs_check_raise").json()
    spot = Spot.model_validate(body["spot"])
    assert spot.street.value == "flop"
    assert len(spot.board) == 3
    assert "vs_check_raise" in spot.node_context
    assert body["grid"] == {}  # grid is preflop-only
    # hero (the original aggressor) faces a fold/call/raise decision
    legal = {la.action.value for la in spot.legal_actions}
    assert {"fold", "call", "raise"} <= legal


def test_vs_check_raise_mode_grades_and_persists(client, temp_engine):
    body = client.get("/api/v1/drill/next?mode=vs_check_raise").json()
    spot = Spot.model_validate(body["spot"])
    assert spot.street.value == "flop"
    assert "vs_check_raise" in spot.node_context
    assert body["grid"] == {}
    resp = client.post(
        "/api/v1/drill/grade",
        json={"spot": body["spot"], "action": {"action": "call"}},
    )
    assert resp.status_code == 200
    assert resp.json()["leak_category"] == 202  # VS_CHECK_RAISE
    with Session(temp_engine) as s:
        assert len(list(s.exec(select(DrillAttempt)))) == 1


def test_challenge_mode_returns_rfi_spot_and_grades(client, temp_engine):
    body = client.get("/api/v1/drill/next?mode=challenge").json()
    spot = Spot.model_validate(body["spot"])
    assert spot.street.value == "preflop"
    assert "RFI" in spot.node_context
    assert body["grid"]  # preflop -> non-empty grid
    resp = client.post(
        "/api/v1/drill/grade",
        json={"spot": body["spot"], "action": {"action": "fold"}},
    )
    assert resp.status_code == 200
    with Session(temp_engine) as s:
        rows = list(s.exec(select(DrillAttempt)))
        assert len(rows) == 1
        assert rows[0].hand_class  # persisted on every grade, per T1


def test_vs_check_raise_due_row_graduates_via_review(client, temp_engine):
    from datetime import date, timedelta

    from factories import make_check_raise_spot

    # 1. grade a check-raise spot (top two pair -> a natural call) -> exactly one SRS row
    spot = make_check_raise_spot().model_dump(mode="json")
    graded = client.post("/api/v1/drill/grade", json={"spot": spot, "action": {"action": "call"}})
    assert graded.status_code == 200
    assert graded.json()["leak_category"] == 202
    with Session(temp_engine) as s:
        rows = list(s.exec(select(SRSItemRow)))
        assert len(rows) == 1
        row = rows[0]
        assert row.node_context == "vs_check_raise"
        sig = row.signature
        row.due_date = date.today() - timedelta(days=1)  # backdate so it's due
        s.add(row)
        s.commit()

    # 2. review serves a RECONSTRUCTED check-raise spot carrying the SRS-key override
    review = client.get("/api/v1/drill/next?mode=review").json()["spot"]
    assert review["street"] == "flop"
    assert "vs_check_raise" in review["node_context"]
    assert review["srs_signature"] == sig

    # 3. re-grade the review spot -> the SAME row graduates; NO new row is created
    #    (even though the reconstructed board's own signature may differ). We assert
    #    the backdated (due-yesterday) row was rescheduled FORWARD rather than
    #    repetitions>=1: the reconstructed spot has a random board+hand, so "call"
    #    vs a check-raise may score as a failed recall (SM-2 resets reps to 0). The
    #    real graduation guarantee is that re-grading routed to the SAME row.
    client.post("/api/v1/drill/grade", json={"spot": review, "action": {"action": "call"}})
    with Session(temp_engine) as s:
        rows = list(s.exec(select(SRSItemRow)))
        assert len(rows) == 1  # no new row from the reconstructed board's own signature
        assert rows[0].signature == sig
        assert rows[0].due_date >= date.today()  # re-graded -> rescheduled off yesterday


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


# --- S6: coverage gate + turn SRS rebuild ---


def test_not_found_grade_persists_nothing(client, temp_engine):
    """Tripwire: a NOT_FOUND grade returns 200 but writes NOTHING — no
    DrillAttempt row, no SRSItemRow (pre-S6 both were written unconditionally,
    seeding junk rows into the due queue)."""
    from factories import make_cbet_spot

    from app.domain.spot import Street

    # A river spot with a flop (CBET) node context: the S7 river provider only
    # accepts the river node contexts, so this still grades NOT_FOUND.
    spot = make_cbet_spot().model_copy(
        update={"street": Street.RIVER, "board": ["Ac", "Kd", "Qh", "7s", "2h"]}
    )
    resp = client.post(
        "/api/v1/drill/grade",
        json={"spot": spot.model_dump(mode="json"), "action": {"action": "check"}},
    )
    assert resp.status_code == 200
    assert resp.json()["coverage"] == "not_found"
    with Session(temp_engine) as s:
        assert list(s.exec(select(DrillAttempt))) == []
        assert list(s.exec(select(SRSItemRow))) == []


def test_turn_due_row_rebuilds_matching_archetype(client, temp_engine):
    """A due TURN row rebuilds a spot whose node_context, street, flop texture
    AND turn-card class all match the row — non-tautological: we assert the
    rebuilt spot's own properties, not just the srs_signature override."""
    import random
    from datetime import date, timedelta

    from app.api.v1 import drill
    from app.domain.scenarios import build_turn_barrel_spot
    from app.domain.spot import Position
    from app.domain.texture import classify, turn_card_class
    from app.services.review import record_attempt

    spot = build_turn_barrel_spot(
        random.Random(7), pairing=(Position.BTN, Position.BB), eff_bb=100.0
    )
    with Session(temp_engine) as s:
        row = record_attempt(s, spot, "optimal", 203)
        sig, tex, tclass = row.signature, row.texture_class, row.turn_class
        assert row.street == "turn"
        assert tclass is not None  # S6 dimension persisted, not write-only
        row.due_date = date.today() - timedelta(days=1)  # backdate so it's due
        s.add(row)
        s.commit()

    # Seed the router's RNG so rejection sampling is deterministic (this seed
    # yields a tier-a exact archetype match among the 150 candidates).
    drill._RNG.seed(20260710)
    body = client.get("/api/v1/drill/next?mode=review").json()["spot"]
    rebuilt = Spot.model_validate(body)
    assert rebuilt.street.value == "turn"
    assert len(rebuilt.board) == 4
    assert "turn_barrel" in body["node_context"]
    assert body["srs_signature"] == sig
    assert classify(rebuilt.board[:3]).texture_class == tex  # flop texture matches
    assert turn_card_class(rebuilt.board) == tclass  # turn-card class matches


def test_river_due_row_rebuilds_matching_archetype(client, temp_engine):
    """A due RIVER row rebuilds a spot whose node_context, street, flop texture,
    turn-card class AND river-card class all match the row — non-tautological:
    we assert the rebuilt spot's own properties, not just the srs_signature
    override."""
    import random
    from datetime import date, timedelta

    from app.api.v1 import drill
    from app.domain.scenarios import build_river_barrel_spot
    from app.domain.spot import Position
    from app.domain.texture import classify, river_card_class, turn_card_class
    from app.services.review import record_attempt

    spot = build_river_barrel_spot(
        random.Random(7), pairing=(Position.BTN, Position.BB), eff_bb=100.0
    )
    with Session(temp_engine) as s:
        row = record_attempt(s, spot, "optimal", 205)
        sig, tex, tclass, rclass = row.signature, row.texture_class, row.turn_class, row.river_class
        assert row.street == "river"
        assert tclass is not None  # S6 dimension persisted on river rows too
        assert rclass is not None  # S7 dimension persisted, not write-only
        row.due_date = date.today() - timedelta(days=1)  # backdate so it's due
        s.add(row)
        s.commit()

    # Seed the router's RNG so rejection sampling is deterministic (this seed
    # yields a tier-a exact archetype match among the 150 candidates).
    drill._RNG.seed(20260710)
    body = client.get("/api/v1/drill/next?mode=review").json()["spot"]
    rebuilt = Spot.model_validate(body)
    assert rebuilt.street.value == "river"
    assert len(rebuilt.board) == 5
    assert "river_barrel" in body["node_context"]
    assert body["srs_signature"] == sig
    assert classify(rebuilt.board[:3]).texture_class == tex  # flop texture matches
    assert turn_card_class(rebuilt.board) == tclass  # turn-card class matches
    assert river_card_class(rebuilt.board) == rclass  # river-card class matches


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
