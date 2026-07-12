"""Villain-range V2 — `sim_session.villain_range` + the endpoint.

Fixture parity: the endpoint's weights equal a direct V1 `estimate_range`
call on the SAME projection. Availability: hero seat / server-truth-folded
seat / hand-over / no-persona seat -> available=false; missing session ->
404 (never availability). NO-PEEK at the service layer: identical response
for two state_json blobs that differ ONLY in the villain's actual hole
cards (same persona, same public line). through_action: the narrated-count
translation (domain_index = 2 POST rows + narrated_count) changes weights
for a mid-street prefix vs the full history. No hole cards / state_json
ever serialize onto the response.
"""

from __future__ import annotations

import random

import pytest
from sqlmodel import Session, create_engine, select

from app.db.migrate import run_migrations
from app.db.models import SimHand, SimSeat, SimSession
from app.domain.action import Decision
from app.domain.personas import load_persona_packs
from app.domain.scenarios import _SEAT_ORDER
from app.domain.spot import ActionType, Position
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, apply, start_hand
from app.domain.table.range_estimate import PublicAction, PublicActionHistory, estimate_range
from app.services.sim_session import HERO_SEAT, SessionNotFound, villain_range

_BLINDS = {Position.SB, Position.BB}
_BUTTON_FOR_HERO = {
    Position.BTN: 0, Position.SB: 8, Position.BB: 7,
    Position.UTG: 6, Position.UTG1: 5, Position.UTG2: 4,
    Position.LJ: 3, Position.HJ: 2, Position.CO: 1,
}


def _state(hero_pos: Position, seed: int = 7) -> HandState:
    dealt = deal_hand(random.Random(seed))
    return start_hand(dealt, button_seat=_BUTTON_FOR_HERO[hero_pos], stacks_bb=[100.0] * 9)


def _play(state: HandState, moves: list[tuple[Position, Decision]]) -> HandState:
    for pos, dec in moves:
        seat = next(s.seat for s in state.seats if s.position is pos)
        assert state.to_act_seat == seat, f"expected {pos} to act"
        state = apply(state, dec)
    return state


def _fold(pos: Position) -> tuple[Position, Decision]:
    return (pos, Decision(action=ActionType.FOLD))


def _before(pos: Position) -> list[Position]:
    return _SEAT_ORDER[: _SEAT_ORDER.index(pos)]


def _between(a: Position, b: Position) -> list[Position]:
    return _SEAT_ORDER[_SEAT_ORDER.index(a) + 1 : _SEAT_ORDER.index(b)]


def _facing_open(hero_pos: Position, opener: Position, size: float, seed: int = 7) -> HandState:
    state = _state(hero_pos, seed)
    moves = [_fold(p) for p in _before(opener) if p not in _BLINDS]
    moves.append((opener, Decision(action=ActionType.RAISE, size_bb=size)))
    moves += [_fold(p) for p in _between(opener, hero_pos)]
    return _play(state, moves)


@pytest.fixture
def db(tmp_path):
    url = f"sqlite:///{tmp_path / 'vrange.db'}"
    run_migrations(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with Session(engine) as s:
        yield s


def _persist(
    db: Session,
    state: HandState,
    personas_by_position: dict[Position, str] | None = None,
    session_id: str = "sess-vrange",
) -> str:
    by_pos = personas_by_position or {}
    session = SimSession(id=session_id, button_seat=state.button_seat, hand_no=1)
    db.add(session)
    for i in range(9):
        pos = state.seats[i].position
        db.add(
            SimSeat(
                session_id=session.id, seat_index=i, is_hero=i == HERO_SEAT,
                persona_type=None if i == HERO_SEAT else by_pos.get(pos, "tag"),
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


def _project(state: HandState) -> PublicActionHistory:
    """Test-side reference projection — mirrors range_estimate's own test
    helper and `sim_session._public_history`'s public-fields-only contract."""
    pos2seat = {s.position: s.seat for s in state.seats}
    starting = [0.0] * 9
    for s in state.seats:
        starting[s.seat] = round(s.stack_bb + s.invested_total_bb, 2)
    return PublicActionHistory(
        button_seat=state.button_seat,
        starting_stacks_bb=tuple(starting),
        board=tuple(state.board),
        actions=tuple(
            PublicAction(
                seat=pos2seat[h.position], position=h.position,
                street=h.street, action=h.action, amount_bb=h.amount_bb,
            )
            for h in state.action_history
        ),
    )


# --------------------------------------------------------------- parity


def test_endpoint_matches_direct_v1_estimate(db):
    # Hero BB faces a BTN open; villain seat under test = the live BTN (nit).
    state = _facing_open(Position.BB, Position.BTN, 2.5)
    btn_seat = next(s.seat for s in state.seats if s.position is Position.BTN)
    session_id = _persist(db, state, personas_by_position={Position.BTN: "nit"})
    view = villain_range(db, session_id, btn_seat)
    assert view.available is True
    packs = load_persona_packs()
    from app.domain.archetypes import VillainType

    ref = estimate_range(
        packs[VillainType.NIT],
        _project(state),
        btn_seat,
        dead_cards=tuple(state.seats[HERO_SEAT].hole_cards),
    )
    expected = {c: w for c, w in ref.class_weights.items() if w > 0.0}
    assert view.weights == pytest.approx(expected)
    assert view.exact is ref.exact
    assert view.persona_label == packs[VillainType.NIT].display_name
    assert view.street == "preflop"
    assert view.seat_index == btn_seat


# ------------------------------------------------------------ unavailable


def test_hero_seat_is_unavailable(db):
    state = _state(Position.BTN)
    session_id = _persist(db, state)
    view = villain_range(db, session_id, HERO_SEAT)
    assert view.available is False
    assert view.weights is None and view.persona_label is None and view.street is None


def test_folded_seat_is_unavailable(db):
    state = _state(Position.BTN)
    utg_seat = next(s.seat for s in state.seats if s.position is Position.UTG)
    state = _play(state, [_fold(Position.UTG)])
    session_id = _persist(db, state)
    view = villain_range(db, session_id, utg_seat)
    assert view.available is False


def test_hand_over_is_unavailable(db):
    # Everyone folds to the hero's big blind: the hand is over on arrival.
    state = _state(Position.BB)
    moves = [_fold(p) for p in _before(Position.SB) if p not in _BLINDS]
    moves.append(_fold(Position.SB))
    state = _play(state, moves)
    assert state.hand_over
    btn_seat = next(s.seat for s in state.seats if s.position is Position.BTN)
    session_id = _persist(db, state)
    view = villain_range(db, session_id, btn_seat)
    assert view.available is False


def test_no_persona_seat_is_unavailable(db):
    # Defensive: a live non-hero seat with no persona assigned.
    state = _state(Position.BTN)
    utg_seat = next(s.seat for s in state.seats if s.position is Position.UTG)
    session_id = _persist(db, state)
    row = db.exec(
        select(SimSeat).where(SimSeat.session_id == session_id, SimSeat.seat_index == utg_seat)
    ).one()
    row.persona_type = None
    db.add(row)
    db.commit()
    view = villain_range(db, session_id, utg_seat)
    assert view.available is False


def test_missing_session_raises_session_not_found(db):
    with pytest.raises(SessionNotFound):
        villain_range(db, "nope", 3)


# ---------------------------------------------------------------- no-peek


def test_no_peek_identical_across_swapped_villain_cards(db):
    """Same persona + same public line, DIFFERENT actual villain hole cards
    -> byte-identical response (spec load-bearing invariant)."""
    state_a = _facing_open(Position.BB, Position.BTN, 2.5)
    btn_seat = next(s.seat for s in state_a.seats if s.position is Position.BTN)

    # Rebuild an identical hand but swap the BTN seat's hole cards for two
    # cards untouched elsewhere in the deck (same button/positions/history).
    used = {c for s in state_a.seats for c in s.hole_cards} | set(state_a.board)
    from app.domain.spot import RANKS, SUITS

    deck = [r + s for r in RANKS for s in SUITS]
    swap = [c for c in deck if c not in used][:2]
    state_b = state_a.model_copy(deep=True)
    old = state_b.seats[btn_seat].hole_cards
    assert tuple(swap) != old
    state_b.seats[btn_seat].hole_cards = (swap[0], swap[1])

    view_a = villain_range(db, _persist(db, state_a, session_id="sess-a"), btn_seat)
    view_b = villain_range(db, _persist(db, state_b, session_id="sess-b"), btn_seat)
    assert view_a.available is True and view_b.available is True
    assert view_a.weights == view_b.weights
    assert view_a.exact == view_b.exact
    assert view_a.street == view_b.street
    assert view_a.persona_label == view_b.persona_label


# ------------------------------------------------------------ through_action


def _four_bet_state() -> HandState:
    # UTG opens 3bb, everyone folds to BTN who calls, then it's the hero's
    # (BB) forced action... instead: build a clean multiway-free HU line so
    # `through_action` truncation is unambiguous — UTG opens, folds around to
    # BTN (hero) who calls, blinds fold, flop check-through, UTG bets turn.
    state = _state(Position.BTN)
    moves = [
        (Position.UTG, Decision(action=ActionType.RAISE, size_bb=3.0)),
        _fold(Position.UTG1), _fold(Position.UTG2), _fold(Position.LJ),
        _fold(Position.HJ), _fold(Position.CO),
        (Position.BTN, Decision(action=ActionType.CALL)),
        _fold(Position.SB), _fold(Position.BB),
        (Position.UTG, Decision(action=ActionType.CHECK)),
        (Position.BTN, Decision(action=ActionType.CHECK)),
    ]
    return _play(state, moves)


def test_through_action_narrated_prefix_changes_weights(db):
    state = _four_bet_state()
    utg_seat = next(s.seat for s in state.seats if s.position is Position.UTG)
    session_id = _persist(db, state, personas_by_position={Position.UTG: "tag"})

    full = villain_range(db, session_id, utg_seat)
    assert full.available is True
    # Narrated count 1 = just UTG's own open (2 POST rows + 1 = domain index
    # 3), BEFORE UTG's flop check ever happened -> preflop-only weights,
    # differing from the full (flop-inclusive) posterior.
    prefix = villain_range(db, session_id, utg_seat, through_action=1)
    assert prefix.available is True
    assert prefix.street == "preflop"
    assert full.street == "flop"
    assert prefix.weights != full.weights

    # Narrated count clamped past the end of history == full history.
    clamped = villain_range(db, session_id, utg_seat, through_action=10_000)
    assert clamped.weights == full.weights


# ---------------------------------------------------------- no leaked cards


def test_response_never_carries_hole_cards_or_state_json(db):
    # Weight keys are 169-class notation (e.g. "AJs") which legitimately
    # contains rank/suit-like substrings, so this checks the SCHEMA never
    # carries a hole-card/state field at all, not a naive card-string grep.
    state = _facing_open(Position.BB, Position.BTN, 2.5)
    btn_seat = next(s.seat for s in state.seats if s.position is Position.BTN)
    session_id = _persist(db, state, personas_by_position={Position.BTN: "nit"})
    view = villain_range(db, session_id, btn_seat)
    assert "hole_cards" not in type(view).model_fields
    assert "state_json" not in type(view).model_fields
    assert "full_board" not in type(view).model_fields
    dumped = view.model_dump_json()
    assert '"hole_cards"' not in dumped
    assert '"state_json"' not in dumped
    assert '"full_board"' not in dumped


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
        state = _facing_open(Position.BB, Position.BTN, 2.5)
        btn_seat = next(s.seat for s in state.seats if s.position is Position.BTN)
        session_id = _persist(db, state, personas_by_position={Position.BTN: "nit"})
        resp = client.get(f"/api/v1/simulate/{session_id}/villain-range/{btn_seat}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is True
        assert body["seat_index"] == btn_seat
        assert body["persona_label"]
        assert body["street"] == "preflop"
        assert isinstance(body["weights"], dict) and body["weights"]
        assert "hole_cards" not in resp.text and "state_json" not in resp.text

        # ?through_action= param wired through.
        resp_prefix = client.get(
            f"/api/v1/simulate/{session_id}/villain-range/{btn_seat}",
            params={"through_action": 0},
        )
        assert resp_prefix.status_code == 200

        # Hero seat -> available=false, still 200.
        resp_hero = client.get(f"/api/v1/simulate/{session_id}/villain-range/{HERO_SEAT}")
        assert resp_hero.status_code == 200
        assert resp_hero.json()["available"] is False

        # 404 stays SessionNotFound-only.
        assert client.get(f"/api/v1/simulate/nope/villain-range/{btn_seat}").status_code == 404
    finally:
        app.dependency_overrides.clear()
