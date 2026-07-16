"""R5 — `sim_session.postflop_chart` + the endpoint.

The whole point (spec §5): the chart's action mix == the grader's `per_action`
for the same spot, by construction — both come from the ONE provider
singleton's `optimal(spot)` on the SAME mapped Spot. Plus: availability gates
(preflop / not hero's turn / unmappable / hand over → available=false), the
river busted-draw category demotion (never a "draw" caption the grader would
not emit), and READ-ONLY proof (a chart fetch creates zero sim_decision /
DrillAttempt rows).
"""

from __future__ import annotations

import asyncio
import random
import uuid

import pytest
from sqlmodel import Session, create_engine, select

from app.db.migrate import run_migrations
from app.db.models import DrillAttempt, SimDecision, SimHand, SimSeat, SimSession
from app.domain.action import Decision
from app.domain.postflop import _hand_category
from app.domain.scenarios import _OPEN_SIZE, _SEAT_ORDER
from app.domain.spot import ActionType, Position, Street
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, apply, start_hand
from app.domain.table.grade_map import map_decision_point
from app.services.sim_session import (
    HERO_SEAT,
    SessionNotFound,
    _grading_provider,
    postflop_chart,
)

_BLINDS = {Position.SB, Position.BB}
_BUTTON_FOR_HERO = {
    Position.BTN: 0, Position.SB: 8, Position.BB: 7,
    Position.UTG: 6, Position.UTG1: 5, Position.UTG2: 4,
    Position.LJ: 3, Position.HJ: 2, Position.CO: 1,
}
_SEAT_BEFORE = {p: _SEAT_ORDER[: _SEAT_ORDER.index(p)] for p in _SEAT_ORDER}
_SEAT_AFTER = {p: _SEAT_ORDER[_SEAT_ORDER.index(p) + 1 :] for p in _SEAT_ORDER}


def _state(hero_pos: Position, seed: int = 7) -> HandState:
    dealt = deal_hand(random.Random(seed))
    return start_hand(
        dealt, button_seat=_BUTTON_FOR_HERO[hero_pos], stacks_bb=[100.0] * 9
    )


def _play(state: HandState, moves: list[tuple[Position, Decision]]) -> HandState:
    for pos, dec in moves:
        seat = next(s.seat for s in state.seats if s.position is pos)
        assert state.to_act_seat == seat, f"expected {pos} to act"
        state = apply(state, dec)
    return state


def _fold(pos: Position) -> tuple[Position, Decision]:
    return (pos, Decision(action=ActionType.FOLD))


def _cbet_flop_state(hero_pos: Position = Position.BTN, seed: int = 7) -> HandState:
    """Hero opens canonically, only the BB calls, BB checks the flop."""
    state = _state(hero_pos, seed)
    moves = [_fold(p) for p in _SEAT_BEFORE[hero_pos] if p not in _BLINDS]
    moves += [
        (hero_pos, Decision(action=ActionType.RAISE, size_bb=_OPEN_SIZE[hero_pos])),
        *[_fold(p) for p in _SEAT_AFTER[hero_pos] if p not in _BLINDS],
        _fold(Position.SB),
        (Position.BB, Decision(action=ActionType.CALL)),
        (Position.BB, Decision(action=ActionType.CHECK)),
    ]
    return _play(state, moves)


def _turn_barrel_state(hero_pos: Position = Position.BTN, seed: int = 7) -> HandState:
    state = _cbet_flop_state(hero_pos, seed)
    fp = round(2 * _OPEN_SIZE[hero_pos] + 0.5, 2)
    cbet = round(0.33 * fp, 1)
    return _play(
        state,
        [
            (hero_pos, Decision(action=ActionType.BET, size_bb=cbet)),
            (Position.BB, Decision(action=ActionType.CALL)),
            (Position.BB, Decision(action=ActionType.CHECK)),  # turn
        ],
    )


def _river_barrel_state(hero_pos: Position = Position.BTN, seed: int = 7) -> HandState:
    state = _turn_barrel_state(hero_pos, seed)
    fp = round(2 * _OPEN_SIZE[hero_pos] + 0.5, 2)
    cbet = round(0.33 * fp, 1)
    turn_pot = round(fp + 2 * cbet, 2)
    tbet = round(0.33 * turn_pot, 1)
    return _play(
        state,
        [
            (hero_pos, Decision(action=ActionType.BET, size_bb=tbet)),
            (Position.BB, Decision(action=ActionType.CALL)),
            (Position.BB, Decision(action=ActionType.CHECK)),  # river
        ],
    )


@pytest.fixture
def db(tmp_path):
    url = f"sqlite:///{tmp_path / 'pfchart.db'}"
    run_migrations(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with Session(engine) as s:
        yield s


def _persist(db: Session, state: HandState) -> str:
    session = SimSession(
        id=uuid.uuid4().hex, button_seat=state.button_seat, hand_no=1
    )
    db.add(session)
    for i in range(9):
        db.add(
            SimSeat(
                session_id=session.id, seat_index=i, is_hero=i == HERO_SEAT,
                persona_type=None if i == HERO_SEAT else "tag",
                stack_bb=100.0, buyins_bb=100.0,
            )
        )
    db.add(
        SimHand(
            session_id=session.id, hand_no=1, button_seat=state.button_seat,
            rng_seed="1", status="in_progress", state_json=state.model_dump_json(),
        )
    )
    db.commit()
    return session.id


# --------------------------------------------------- chart == grader


@pytest.mark.parametrize(
    ("state_fn", "street", "label"),
    [
        (_cbet_flop_state, Street.FLOP, "BTN flop c-bet vs BB"),
        (_turn_barrel_state, Street.TURN, "BTN turn barrel vs BB"),
        (_river_barrel_state, Street.RIVER, "BTN river barrel vs BB"),
    ],
)
def test_chart_actions_equal_grader_per_action(db, state_fn, street, label):
    state = state_fn()
    assert state.street is street and state.to_act_seat == HERO_SEAT
    session_id = _persist(db, state)
    view = asyncio.run(postflop_chart(db, session_id))
    assert view.available is True
    assert view.node_label == label
    assert view.approx is True
    # The grader's own mix for the SAME spot, via the SAME singleton — and
    # evaluate() (what apply_hero_action grades with) yields the identical
    # per_action, so chart == grader for the live verdict too.
    spot = map_decision_point(state, HERO_SEAT)
    optimal = asyncio.run(_grading_provider().optimal(spot))
    graded = asyncio.run(
        _grading_provider().evaluate(spot, Decision(action=ActionType.CHECK))
    )
    expected = [
        (a.action.value, a.size_bb, a.frequency, a.ev_bb) for a in optimal.per_action
    ]
    assert [
        (a.action, a.size_bb, a.frequency, a.ev_bb) for a in view.actions
    ] == expected
    assert [
        (a.action.value, a.size_bb, a.frequency, a.ev_bb) for a in graded.per_action
    ] == expected
    # Frequencies are the grader's own (already normalized) — never re-derived.
    assert abs(sum(a.frequency for a in view.actions) - 1.0) < 1e-6


def test_hand_category_matches_grader_taxonomy(db):
    state = _turn_barrel_state()
    session_id = _persist(db, state)
    view = asyncio.run(postflop_chart(db, session_id))
    spot = map_decision_point(state, HERO_SEAT)
    assert view.hand_category == _hand_category(spot.hero.hole_cards, spot.board)
    assert view.hand_category in ("strong", "weak_made", "draw", "air")


def test_river_category_never_says_draw(db):
    # Busted-draw demotion (S7): scan seeds for a hero holding a river "draw"
    # per raw _hand_category; the chart must caption it "air" — a "draw" row
    # would be a category the river graders never emit.
    for seed in range(80):
        state = _river_barrel_state(seed=seed)
        spot = map_decision_point(state, HERO_SEAT)
        assert spot is not None  # scripted line is always canonical
        raw = _hand_category(spot.hero.hole_cards, spot.board)
        if raw != "draw":
            continue
        session_id = _persist(db, state)
        view = asyncio.run(postflop_chart(db, session_id))
        assert view.available is True
        assert view.hand_category == "air"  # demoted, never "draw"
        return
    raise AssertionError("no busted-draw river hero found in 80 seeds")


# --------------------------------------------------------- read-only


def test_chart_fetch_writes_nothing(db):
    session_id = _persist(db, _turn_barrel_state())
    view = asyncio.run(postflop_chart(db, session_id))
    assert view.available is True
    db.rollback()  # a read-only service has nothing pending to roll back
    assert db.exec(select(SimDecision)).all() == []
    assert db.exec(select(DrillAttempt)).all() == []


# ------------------------------------------------------------ unavailable


def test_preflop_turn_is_unavailable(db):
    state = _state(Position.BTN)
    state = _play(
        state, [_fold(p) for p in _SEAT_BEFORE[Position.BTN] if p not in _BLINDS]
    )
    assert state.street is Street.PREFLOP and state.to_act_seat == HERO_SEAT
    session_id = _persist(db, state)
    view = asyncio.run(postflop_chart(db, session_id))
    assert view.available is False
    assert view.actions == [] and view.node_label is None and view.hand_category is None


def test_unmappable_postflop_spot_is_unavailable(db):
    # Off-size flop c-bet line reaching the turn: unmappable ⇒ "no baseline
    # yet", never a fabricated mix.
    state = _cbet_flop_state()
    state = _play(
        state,
        [
            (Position.BTN, Decision(action=ActionType.BET, size_bb=2.5)),  # off-size
            (Position.BB, Decision(action=ActionType.CALL)),
            (Position.BB, Decision(action=ActionType.CHECK)),  # turn
        ],
    )
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    session_id = _persist(db, state)
    assert asyncio.run(postflop_chart(db, session_id)).available is False


def test_not_hero_turn_is_unavailable(db):
    state = _state(Position.BTN)  # UTG to act preflop — not even postflop
    session_id = _persist(db, state)
    assert asyncio.run(postflop_chart(db, session_id)).available is False


def test_missing_session_raises_session_not_found(db):
    with pytest.raises(SessionNotFound):
        asyncio.run(postflop_chart(db, "nope"))


# ------------------------------------------------------------ HTTP shape


def test_endpoint_http_shape_and_404(db):
    from fastapi.testclient import TestClient

    from app.db.session import get_session
    from app.main import app

    def _override():
        yield db

    app.dependency_overrides[get_session] = _override
    try:
        client = TestClient(app)
        session_id = _persist(db, _turn_barrel_state())
        resp = client.get(f"/api/v1/simulate/{session_id}/postflop-chart")
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is True
        assert body["node_label"] == "BTN turn barrel vs BB"
        assert body["approx"] is True
        assert len(body["actions"]) == 3
        for a in body["actions"]:
            assert set(a) == {"action", "size_bb", "frequency", "ev_bb"}
        # Endpoint fetch is read-only too.
        assert db.exec(select(SimDecision)).all() == []
        assert db.exec(select(DrillAttempt)).all() == []
        assert client.get("/api/v1/simulate/nope/postflop-chart").status_code == 404
    finally:
        app.dependency_overrides.clear()
