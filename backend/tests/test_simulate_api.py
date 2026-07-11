"""API tests for the S9 simulate endpoints.

Exercises the wire contract, not the service internals (those are
`test_sim_session.py`, owned by T1). Depends on T1's DB-backed
`app.services.sim_session` + `app.db.models.SimSession/SimSeat/SimHand` +
migration `0009_sim_tables` — if those aren't committed yet, these tests will
fail at collection/import time (expected mid-wave; see the wave-4 ticket).
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app.db.migrate import run_migrations
from app.db.session import get_session
from app.domain.spot import ActionType, validate_card
from app.main import app


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


def _assert_no_leaked_hole_cards(body: dict) -> None:
    """No non-hero, non-showdown hole cards; no state_json/full_board, ever."""
    hand = body["hand"]
    assert "state_json" not in hand
    assert "full_board" not in hand
    hero_cards = set(hand["hero"]["hole_cards"])

    showdown_cards: set[str] = set()
    for sd in hand["showdown"]:
        showdown_cards.update(sd["hole_cards"])

    def _walk(obj):
        if isinstance(obj, dict):
            assert "state_json" not in obj
            assert "full_board" not in obj
            if "hole_cards" in obj and obj is not hand["hero"] and obj not in hand["showdown"]:
                raise AssertionError(f"unexpected hole_cards field: {obj}")
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(body)

    # seats never carry a hole_cards field at all (SeatView has none).
    for seat in hand["seats"]:
        assert "hole_cards" not in seat

    for c in hero_cards:
        validate_card(c)
    for c in showdown_cards:
        validate_card(c)


def _play_hand_to_completion(client: TestClient, session_id: str) -> dict:
    """Drive hero actions (fold when it's hero's turn) until hand_over."""
    body = client.get(f"/api/v1/simulate/session/{session_id}").json()
    for _ in range(500):
        hand = body["hand"]
        _assert_no_leaked_hole_cards(body)
        if hand["hand_over"]:
            return body
        assert hand["is_hero_turn"]
        # Prefer check/fold to end the hand quickly.
        kinds = {la["action"] for la in hand["legal_actions"]}
        action = "check" if "check" in kinds else "fold"
        resp = client.post(
            f"/api/v1/simulate/session/{session_id}/action",
            json={"action": action},
        )
        assert resp.status_code == 200
        body = resp.json()
    raise AssertionError("hand did not complete within 500 hero actions")


def test_create_returns_valid_session(client):
    resp = client.post("/api/v1/simulate/session")
    assert resp.status_code == 200
    body = resp.json()
    assert "session_id" in body
    hand = body["hand"]
    assert hand["hand_no"] == 1
    assert len(hand["seats"]) == 9
    hero_seats = [s for s in hand["seats"] if s["is_hero"]]
    assert len(hero_seats) == 1
    assert hero_seats[0]["persona_type"] is None
    assert len(hand["hero"]["hole_cards"]) == 2
    _assert_no_leaked_hole_cards(body)


def test_create_act_showdown_happy_path(client):
    create = client.post("/api/v1/simulate/session").json()
    session_id = create["session_id"]
    final = _play_hand_to_completion(client, session_id)
    assert final["hand"]["hand_over"] is True
    _assert_no_leaked_hole_cards(final)


def test_restore_returns_live_decision_point(client):
    create = client.post("/api/v1/simulate/session").json()
    session_id = create["session_id"]

    restored = client.get(f"/api/v1/simulate/session/{session_id}")
    assert restored.status_code == 200
    body = restored.json()
    assert body["session_id"] == session_id
    assert body["hand"]["hand_no"] == create["hand"]["hand_no"]
    assert body["hand"]["to_act_seat"] == create["hand"]["to_act_seat"]
    assert body["hand"]["is_hero_turn"] == create["hand"]["is_hero_turn"]
    _assert_no_leaked_hole_cards(body)


def test_404_on_missing_session(client):
    resp = client.get("/api/v1/simulate/session/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "session not found"


def test_404_on_ended_session(client):
    create = client.post("/api/v1/simulate/session").json()
    session_id = create["session_id"]

    leave_resp = client.post(f"/api/v1/simulate/session/{session_id}/leave")
    assert leave_resp.status_code == 204

    resp = client.get(f"/api/v1/simulate/session/{session_id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "session not found"


def test_illegal_hero_action_returns_400(client):
    create = client.post("/api/v1/simulate/session").json()
    session_id = create["session_id"]
    hand = create["hand"]
    assert hand["is_hero_turn"]
    legal_kinds = {la["action"] for la in hand["legal_actions"]}
    # RAISE is never legal preflop for the first-to-act hero without a size,
    # and if it happens to be legal, an absurd out-of-range size is illegal.
    if ActionType.RAISE.value in legal_kinds:
        payload = {"action": "raise", "size_bb": 100000.0}
    else:
        payload = {"action": "raise", "size_bb": 4.0}

    resp = client.post(
        f"/api/v1/simulate/session/{session_id}/action",
        json=payload,
    )
    assert resp.status_code == 400


def test_next_hand_carries_over_stacks_and_advances_button(client):
    create = client.post("/api/v1/simulate/session").json()
    session_id = create["session_id"]
    btn1 = create["hand"]["button_seat"]

    _play_hand_to_completion(client, session_id)

    resp = client.post(f"/api/v1/simulate/session/{session_id}/hand")
    assert resp.status_code == 200
    body = resp.json()
    hand2 = body["hand"]
    assert hand2["hand_no"] == 2
    assert hand2["button_seat"] == (btn1 + 1) % 9
    # Carry-over: no seat resets to a fresh 100bb unless it busted+rebought.
    for seat in hand2["seats"]:
        assert seat["stack_bb"] <= 100.0 + 1e-6
    _assert_no_leaked_hole_cards(body)
