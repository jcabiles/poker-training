import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app.db.migrate import run_migrations
from app.db.session import get_session
from app.domain.spot import Position, validate_card
from app.main import app

_RING_ORDER = [
    Position.UTG,
    Position.UTG1,
    Position.UTG2,
    Position.LJ,
    Position.HJ,
    Position.CO,
    Position.BTN,
    Position.SB,
    Position.BB,
]


@pytest.fixture
def temp_engine(tmp_path):
    url = f"sqlite:///{tmp_path / 'simulate_api.db'}"
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


def _seat_of_btn(players: list[dict]) -> int:
    btn = [i for i, p in enumerate(players) if p["position"] == "BTN"]
    assert len(btn) == 1
    return btn[0]


def test_session_create_returns_valid_hand(client):
    resp = client.post("/api/v1/simulate/session")
    assert resp.status_code == 200
    body = resp.json()
    assert "session_id" in body
    hand = body["hand"]
    assert hand["hand_no"] == 1

    players = hand["players"]
    assert len(players) == 9

    btn_positions = [p for p in players if p["position"] == "BTN"]
    assert len(btn_positions) == 1

    hero_players = [p for p in players if p["is_hero"]]
    assert len(hero_players) == 1
    assert hero_players[0]["position"] == hand["hero"]["position"]

    for p in players:
        assert p["stack_bb"] == 100

    hero_cards = hand["hero"]["hole_cards"]
    assert len(hero_cards) == 2
    for c in hero_cards:
        validate_card(c)  # raises ValueError if invalid
    assert hand["hero"]["stack_bb"] == 100


def test_next_hand_advances_button_one_seat_and_increments_hand_no(client):
    create = client.post("/api/v1/simulate/session").json()
    session_id = create["session_id"]
    hand1_players = create["hand"]["players"]
    btn_seat_1 = _seat_of_btn(hand1_players)

    resp = client.post(f"/api/v1/simulate/session/{session_id}/hand")
    assert resp.status_code == 200
    hand2 = resp.json()
    assert hand2["hand_no"] == 2
    btn_seat_2 = _seat_of_btn(hand2["players"])

    assert btn_seat_2 == (btn_seat_1 + 1) % 9

    # Every emitted position is a valid RING member, exactly one BTN.
    positions = [p["position"] for p in hand2["players"]]
    assert all(pos in {p.value for p in _RING_ORDER} for pos in positions)
    assert positions.count("BTN") == 1


def test_next_hand_deals_different_hero_cards_across_hands(client):
    session_id = client.post("/api/v1/simulate/session").json()["session_id"]
    hero_hands = set()
    for _ in range(3):
        resp = client.post(f"/api/v1/simulate/session/{session_id}/hand")
        hero_hands.add(tuple(resp.json()["hero"]["hole_cards"]))
    # Overwhelmingly unlikely all 3 draws collide if seeded independently.
    assert len(hero_hands) > 1


def test_response_has_no_board_or_villain_cards(client):
    resp = client.post("/api/v1/simulate/session")
    body = resp.json()

    def _walk(obj):
        if isinstance(obj, dict):
            assert "board" not in obj
            assert "hole_cards" not in obj or obj is body["hand"]["hero"]
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(body)

    # players carry no hole-card field at all (PlayerState has none).
    for p in body["hand"]["players"]:
        assert "hole_cards" not in p


def test_unknown_session_id_returns_404(client):
    resp = client.post("/api/v1/simulate/session/does-not-exist/hand")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "session not found"
