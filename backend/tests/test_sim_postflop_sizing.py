"""N4a — postflop barrel sizing: e2e persistence + display==grade parity.

Two claims:
  1. A hero turn barrel driven through `apply_hero_action` persists a
     `sizing_correctness` verdict (OPTIMAL for the higher-merit size, ACCEPTABLE
     for the other), alongside the (unchanged) action correctness.
  2. Display parity: the barrel two-size hero offer (`_hero_legal_actions`)
     is built from the SAME `POSTFLOP_BET_FRACS` + pot + non-None grading gate as
     the graded `_barrel_spot`, so a short-stack spot where grading collapses/bails
     to one offers exactly ONE bet size on the display side too — never two-vs-one.
"""

from __future__ import annotations

import asyncio
import random

import pytest
from sqlmodel import Session, create_engine, select

from app.db.migrate import run_migrations
from app.db.models import SimDecision, SimHand, SimSeat, SimSession
from app.domain.action import Decision
from app.domain.scenarios import _OPEN_SIZE, _SEAT_ORDER
from app.domain.spot import ActionType, Position, Street
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, apply, start_hand
from app.domain.table.grade_map_postflop import map_turn_barrel
from app.services.sim_session import _hero_legal_actions, apply_hero_action

HERO_SEAT = 0
_BLINDS = {Position.SB, Position.BB}
_BUTTON_FOR_HERO = {
    Position.BTN: 0, Position.SB: 8, Position.BB: 7,
    Position.UTG: 6, Position.UTG1: 5, Position.UTG2: 4,
    Position.LJ: 3, Position.HJ: 2, Position.CO: 1,
}


def _state(hero_pos: Position, stacks: float = 100.0, seed: int = 1) -> HandState:
    dealt = deal_hand(random.Random(seed))
    return start_hand(
        dealt, button_seat=_BUTTON_FOR_HERO[hero_pos], stacks_bb=[stacks] * 9
    )


def _play(state: HandState, moves) -> HandState:
    for pos, dec in moves:
        seat = next(s.seat for s in state.seats if s.position is pos)
        assert state.to_act_seat == seat, f"expected {pos} to act"
        state = apply(state, dec)
    return state


def _fold(pos):
    return (pos, Decision(action=ActionType.FOLD))


def _check(pos):
    return (pos, Decision(action=ActionType.CHECK))


def _call(pos):
    return (pos, Decision(action=ActionType.CALL))


def _bet(pos, size):
    return (pos, Decision(action=ActionType.BET, size_bb=size))


def _before(pos):
    return _SEAT_ORDER[: _SEAT_ORDER.index(pos)]


def _turn_barrel_state(
    hero_pos: Position, stacks: float = 100.0, seed: int = 1
) -> HandState:
    """Hero opens canonically, c-bets the flop 0.33 (called); BB checks turn."""
    osize = _OPEN_SIZE[hero_pos]
    state = _state(hero_pos, stacks=stacks, seed=seed)
    moves = [_fold(p) for p in _before(hero_pos) if p not in _BLINDS]
    moves.append((hero_pos, Decision(action=ActionType.RAISE, size_bb=osize)))
    moves += [
        _fold(p)
        for p in _SEAT_ORDER[_SEAT_ORDER.index(hero_pos) + 1 :]
        if p not in _BLINDS
    ]
    moves += [_fold(Position.SB), _call(Position.BB)]
    state = _play(state, moves)
    fp = round(2 * osize + 0.5, 2)
    cbet = round(0.33 * fp, 1)
    return _play(
        state,
        [
            _check(Position.BB),
            _bet(hero_pos, cbet),
            _call(Position.BB),
            _check(Position.BB),  # turn
        ],
    )


@pytest.fixture
def db(tmp_path):
    url = f"sqlite:///{tmp_path / 'sps.db'}"
    run_migrations(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with Session(engine) as s:
        yield s


def _persist_hand(db: Session, state: HandState, sid: str = "sess-sps") -> str:
    session = SimSession(id=sid, button_seat=state.button_seat, hand_no=1)
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


# ------------------------------------------------------- e2e sizing persist


def test_turn_barrel_bet_persists_sizing_correctness(db):
    # Play a real turn barrel; the displayed two sizes ARE the graded sizes.
    # Betting the higher-merit size persists OPTIMAL; the other ACCEPTABLE.
    state = _turn_barrel_state(Position.BTN)
    spot = map_turn_barrel(state, HERO_SEAT)
    assert spot is not None
    bet_evals = [la.min_bb for la in spot.legal_actions if la.action is ActionType.BET]
    assert len(bet_evals) == 2  # two RES-B turn sizes offered/graded
    # Grade both sizes ungraded to learn which is higher-merit.
    from app.domain.postflop import grade_turn_barrel

    ungraded = grade_turn_barrel(spot, spot.hero_range, spot.villain_range, None)
    bet_freqs = {
        e.size_bb: e.frequency for e in ungraded.per_action if e.action == ActionType.BET
    }
    top_size = max(bet_freqs, key=lambda s: bet_freqs[s])
    assert bet_freqs[top_size] > 0.0, "seed 1 has a positive-merit turn barrel size"
    other_size = min(bet_freqs, key=lambda s: bet_freqs[s])
    assert top_size != other_size

    # Hand A: bet the higher-merit size -> OPTIMAL.
    sid_a = _persist_hand(db, _turn_barrel_state(Position.BTN), sid="sps-a")
    asyncio.run(
        apply_hero_action(db, sid_a, Decision(action=ActionType.BET, size_bb=top_size))
    )
    row_a = db.exec(select(SimDecision).where(SimDecision.session_id == sid_a)).all()[-1]
    assert row_a.street == "turn"
    assert row_a.sizing_correctness == "optimal"

    # Hand B (identical hand): bet the lower-merit size -> ACCEPTABLE.
    sid_b = _persist_hand(db, _turn_barrel_state(Position.BTN), sid="sps-b")
    asyncio.run(
        apply_hero_action(db, sid_b, Decision(action=ActionType.BET, size_bb=other_size))
    )
    row_b = db.exec(select(SimDecision).where(SimDecision.session_id == sid_b)).all()[-1]
    assert row_b.sizing_correctness == "acceptable"


# ------------------------------------------------- short-stack display==grade


def test_short_stack_barrel_offers_one_size_matching_grade_collapse():
    # Deep stack: grading maps (two sizes) AND display offers two.
    deep = _turn_barrel_state(Position.BTN, stacks=100.0)
    assert map_turn_barrel(deep, HERO_SEAT) is not None
    deep_bets = [la for la in _hero_legal_actions(deep) if la.action is ActionType.BET]
    assert len(deep_bets) == 2

    # Short stack: hero is too shallow for the big (0.75-pot) turn bucket, so the
    # mapper BAILS to None. Display must then NOT offer two sizes — exactly one
    # bet option, matching the grading collapse (no two-vs-one divergence).
    short = _turn_barrel_state(Position.BTN, stacks=10.0)
    assert short.street is Street.TURN and short.to_act_seat == HERO_SEAT
    assert map_turn_barrel(short, HERO_SEAT) is None  # grading bailed to one/none
    short_bets = [la for la in _hero_legal_actions(short) if la.action is ActionType.BET]
    assert len(short_bets) == 1  # display offers exactly one — parity holds
