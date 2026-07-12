"""S10 T1 — spot-mapper tests (`app.domain.table.grade_map`) + grade-wire tests.

Property test (ticket refuter low-3): for every mapped canonical shape, the
produced Spot's hero_range / villain_range / facing match the equivalent
`scenarios.py` builder output for that shape (preflop spots must be the
builder's Spot verbatim). Plus None-return tests: multiway, limped pot, turn
street, off-size raise, 3-bet pot, off-pack positions.

Wire tests: coverage gate (graded ⇒ SimDecision + tagged DrillAttempt;
unmappable ⇒ SimDecision only), zero graded rows when apply() rejects the
action, and the per-street report aggregate.
"""

from __future__ import annotations

import asyncio
import random

import pytest
from sqlmodel import Session, create_engine, select

from app.db.migrate import run_migrations
from app.db.models import DrillAttempt, SimDecision, SimHand, SimSeat, SimSession
from app.domain.action import Decision
from app.domain.scenarios import (
    _OPEN_SIZE,
    _SEAT_ORDER,
    _combos_for,
    _find_entry,
    build_cbet_spot,
    build_spot,
)
from app.domain.spot import ActionType, NodeContext, Position, Street
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, apply, start_hand
from app.domain.table.grade_map import map_decision_point
from app.services.sim_session import apply_hero_action, street_report

HERO_SEAT = 0
_BLINDS = {Position.SB, Position.BB}
# button_seat that puts seat 0 (the hero) at each position (deck._ROTATION).
_BUTTON_FOR_HERO = {
    Position.BTN: 0, Position.SB: 8, Position.BB: 7,
    Position.UTG: 6, Position.UTG1: 5, Position.UTG2: 4,
    Position.LJ: 3, Position.HJ: 2, Position.CO: 1,
}


def _state(hero_pos: Position, seed: int = 7) -> HandState:
    dealt = deal_hand(random.Random(seed))
    return start_hand(
        dealt, button_seat=_BUTTON_FOR_HERO[hero_pos], stacks_bb=[100.0] * 9
    )


def _play(state: HandState, moves: list[tuple[Position, Decision]]) -> HandState:
    """Apply scripted decisions, asserting the engine's action order matches."""
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


def _folded_to(hero_pos: Position, seed: int = 7) -> HandState:
    state = _state(hero_pos, seed)
    return _play(state, [_fold(p) for p in _before(hero_pos) if p not in _BLINDS])


def _facing_open(hero_pos: Position, opener: Position, size: float, seed: int = 7) -> HandState:
    state = _state(hero_pos, seed)
    moves = [_fold(p) for p in _before(opener) if p not in _BLINDS]
    moves.append((opener, Decision(action=ActionType.RAISE, size_bb=size)))
    moves += [_fold(p) for p in _between(opener, hero_pos)]
    return _play(state, moves)


def _cbet_state(hero_pos: Position, seed: int = 7) -> HandState:
    """Hero opens at the canonical size, only the BB calls, BB checks the flop."""
    osize = _OPEN_SIZE[hero_pos]
    state = _state(hero_pos, seed)
    moves = [_fold(p) for p in _before(hero_pos) if p not in _BLINDS]
    moves.append((hero_pos, Decision(action=ActionType.RAISE, size_bb=osize)))
    moves += [_fold(p) for p in _between(hero_pos, Position.SB) if p not in _BLINDS]
    moves += [
        _fold(Position.SB),
        (Position.BB, Decision(action=ActionType.CALL)),
        (Position.BB, Decision(action=ActionType.CHECK)),  # flop
    ]
    return _play(state, moves)


# ------------------------------------------------------ property: preflop


@pytest.mark.parametrize(
    "hero_pos",
    [Position.UTG, Position.LJ, Position.HJ, Position.CO, Position.BTN, Position.SB],
)
def test_rfi_maps_to_builder_spot_verbatim(hero_pos):
    state = _folded_to(hero_pos)
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    entry = _find_entry(NodeContext.RFI, hero_pos, None)
    expected = build_spot(
        entry, random.Random(0), eff_bb=100.0,
        hole_cards=state.seats[HERO_SEAT].hole_cards,
    )
    assert spot == expected  # incl. hero_range/villain_range/facing parity


@pytest.mark.parametrize(
    ("hero_pos", "opener", "ctx"),
    [
        (Position.HJ, Position.UTG, NodeContext.VS_RFI),
        (Position.CO, Position.UTG, NodeContext.VS_RFI),
        (Position.CO, Position.HJ, NodeContext.VS_RFI),
        (Position.BTN, Position.CO, NodeContext.VS_RFI),
        (Position.BTN, Position.HJ, NodeContext.VS_RFI),
        (Position.BTN, Position.UTG, NodeContext.VS_RFI),
        (Position.SB, Position.CO, NodeContext.BLIND_DEFENSE),
        (Position.SB, Position.BTN, NodeContext.BLIND_DEFENSE),
        (Position.BB, Position.UTG, NodeContext.BLIND_DEFENSE),
        (Position.BB, Position.CO, NodeContext.BLIND_DEFENSE),
        (Position.BB, Position.BTN, NodeContext.BLIND_DEFENSE),
    ],
)
def test_vs_rfi_and_blind_defense_map_to_builder_spot_verbatim(hero_pos, opener, ctx):
    state = _facing_open(hero_pos, opener, _OPEN_SIZE[opener])
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    entry = _find_entry(ctx, hero_pos, opener)
    assert entry is not None
    expected = build_spot(
        entry, random.Random(0), eff_bb=100.0,
        hole_cards=state.seats[HERO_SEAT].hole_cards,
    )
    assert spot == expected
    assert spot.facing is opener


# ----------------------------------------------------- property: flop c-bet


@pytest.mark.parametrize("hero_pos", [Position.UTG, Position.CO, Position.BTN])
def test_flop_cbet_maps_with_builder_ranges(hero_pos):
    state = _cbet_state(hero_pos)
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    built = build_cbet_spot(
        random.Random(0), pairing=(hero_pos, Position.BB), eff_bb=100.0
    )
    # The ticket's property: ranges + facing match the equivalent builder spot.
    assert spot.hero_range == built.hero_range
    assert spot.villain_range == built.villain_range
    assert spot.facing == built.facing == Position.BB
    assert spot.node_context == [NodeContext.CBET]
    # Live-state truthfulness: real board/cards/pot, builder sizing buckets.
    assert spot.street is Street.FLOP
    assert spot.board == state.board
    assert spot.hero.hole_cards == state.seats[HERO_SEAT].hole_cards
    assert spot.pot_bb == built.pot_bb
    assert [
        (la.action, la.min_bb) for la in spot.legal_actions
    ] == [(la.action, la.min_bb) for la in built.legal_actions]
    assert spot.spr == built.spr


# --------------------------------------------------------- None returns


def test_multiway_flop_returns_none():
    # Hero UTG opens, LJ AND BB call: three-way flop is not HU-canonical.
    state = _state(Position.UTG)
    state = _play(
        state,
        [
            (Position.UTG, Decision(action=ActionType.RAISE, size_bb=3.0)),
            _fold(Position.UTG1),
            _fold(Position.UTG2),
            (Position.LJ, Decision(action=ActionType.CALL)),
            _fold(Position.HJ),
            _fold(Position.CO),
            _fold(Position.BTN),
            _fold(Position.SB),
            (Position.BB, Decision(action=ActionType.CALL)),
            (Position.BB, Decision(action=ActionType.CHECK)),  # flop
        ],
    )
    assert state.street is Street.FLOP
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_limped_pot_returns_none():
    state = _state(Position.BTN)
    state = _play(
        state,
        [
            _fold(Position.UTG),
            _fold(Position.UTG1),
            _fold(Position.UTG2),
            (Position.LJ, Decision(action=ActionType.CALL)),  # limp
            _fold(Position.HJ),
            _fold(Position.CO),
        ],
    )
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_off_size_open_returns_none():
    # A bot-style min-raise to 2.0 is not the canonical 2.5bb CO open.
    state = _facing_open(Position.BTN, Position.CO, 2.0)
    assert map_decision_point(state, HERO_SEAT) is None


def test_three_bet_pot_returns_none():
    state = _state(Position.BTN)
    state = _play(
        state,
        [
            (Position.UTG, Decision(action=ActionType.RAISE, size_bb=3.0)),
            _fold(Position.UTG1),
            _fold(Position.UTG2),
            _fold(Position.LJ),
            _fold(Position.HJ),
            (Position.CO, Decision(action=ActionType.RAISE, size_bb=9.0)),
        ],
    )
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_turn_street_returns_none():
    state = _cbet_state(Position.BTN)
    state = _play(
        state,
        [
            (Position.BTN, Decision(action=ActionType.CHECK)),  # hero checks back
            (Position.BB, Decision(action=ActionType.CHECK)),  # turn
        ],
    )
    assert state.street is Street.TURN
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_off_pack_rfi_position_returns_none():
    # Folded to UTG1: canonical RFI shape, but no UTG1 content entry exists.
    state = _folded_to(Position.UTG1)
    assert map_decision_point(state, HERO_SEAT) is None


def test_off_pack_vs_rfi_pairing_returns_none():
    # HJ facing an LJ open (canonical size): no vs_RFI HJ-vs-LJ entry exists.
    assert _find_entry(NodeContext.VS_RFI, Position.HJ, Position.LJ) is None
    state = _facing_open(Position.HJ, Position.LJ, _OPEN_SIZE[Position.LJ])
    assert map_decision_point(state, HERO_SEAT) is None


def test_not_hero_turn_or_hand_over_returns_none():
    state = _state(Position.BTN)  # UTG to act, not the hero
    assert map_decision_point(state, HERO_SEAT) is None


# ------------------------------------------------------------- grade wire


@pytest.fixture
def db(tmp_path):
    url = f"sqlite:///{tmp_path / 'gm.db'}"
    run_migrations(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with Session(engine) as s:
        yield s


def _persist_hand(db: Session, state: HandState) -> str:
    """SimSession + seats + an in-progress SimHand holding `state`."""
    session = SimSession(id="sess-gm", button_seat=state.button_seat, hand_no=1)
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


def test_graded_decision_writes_sim_decision_and_tagged_attempt(db):
    session_id = _persist_hand(db, _folded_to(Position.BTN))  # canonical RFI
    view = asyncio.run(
        apply_hero_action(db, session_id, Decision(action=ActionType.FOLD))
    )
    rows = db.exec(select(SimDecision)).all()
    assert len(rows) == 1
    assert rows[0].street == "preflop" and rows[0].ordinal == 0
    assert rows[0].coverage == "full"
    assert rows[0].correctness in ("optimal", "acceptable", "mistake", "blunder")
    attempts = db.exec(select(DrillAttempt)).all()
    assert len(attempts) == 1
    assert attempts[0].source == "simulate"
    assert attempts[0].spot_signature.startswith("sim:")
    grade = view.hand.last_grade
    assert grade is not None and grade.correctness == rows[0].correctness
    assert grade.verdict and grade.reasoning  # non-empty feedback tiers
    # Hero folded ⇒ the hand resolves; the recap lists the hand's decisions.
    assert view.hand.hand_over
    assert [g.ordinal for g in view.hand.recap] == [0]


def test_unmappable_decision_writes_no_baseline_row_and_no_attempt(db):
    # Off-size (min-raise) open: unmappable ⇒ SimDecision only, no attempt.
    session_id = _persist_hand(db, _facing_open(Position.BTN, Position.CO, 2.0))
    view = asyncio.run(
        apply_hero_action(db, session_id, Decision(action=ActionType.FOLD))
    )
    rows = db.exec(select(SimDecision)).all()
    assert len(rows) == 1
    assert rows[0].coverage == "unmappable"
    assert rows[0].correctness is None and rows[0].ev_loss_bb == 0.0
    assert db.exec(select(DrillAttempt)).all() == []
    grade = view.hand.last_grade
    assert grade is not None
    assert grade.correctness is None and grade.verdict is None


def test_illegal_action_leaves_zero_graded_rows(db):
    session_id = _persist_hand(db, _folded_to(Position.BTN))
    with pytest.raises(ValueError):
        asyncio.run(
            apply_hero_action(
                db, session_id, Decision(action=ActionType.RAISE, size_bb=1.5)
            )
        )
    db.rollback()
    assert db.exec(select(SimDecision)).all() == []
    assert db.exec(select(DrillAttempt)).all() == []


# ---------------------------------------------------------- street report


def test_street_report_buckets_by_street_and_excludes_no_baseline(db):
    session_id = _persist_hand(db, _folded_to(Position.BTN))
    hand_id = db.exec(select(SimHand)).one().id
    common = {"session_id": session_id, "sim_hand_id": hand_id}
    db.add_all(
        [
            SimDecision(street="preflop", ordinal=0, chosen_action="raise",
                        correctness="optimal", ev_loss_bb=0.0, coverage="full", **common),
            SimDecision(street="preflop", ordinal=1, chosen_action="call",
                        correctness="blunder", ev_loss_bb=4.0, coverage="full", **common),
            SimDecision(street="preflop", ordinal=2, chosen_action="fold",
                        correctness=None, ev_loss_bb=0.0, coverage="not_found", **common),
            SimDecision(street="flop", ordinal=3, chosen_action="bet",
                        correctness=None, ev_loss_bb=0.0, coverage="unmappable", **common),
        ]
    )
    db.commit()
    report = street_report(db)
    assert [r.street for r in report.rows] == ["preflop", "flop", "turn", "river"]
    pre, flop, turn, river = report.rows
    assert (pre.graded, pre.optimal, pre.blunder, pre.no_baseline) == (2, 1, 1, 1)
    assert pre.ev_loss_bb == 4.0  # graded rows only
    assert (flop.graded, flop.no_baseline) == (0, 1)
    assert turn.graded == turn.no_baseline == river.graded == river.no_baseline == 0
    assert report.total_decisions == 4


def test_range_helpers_never_fabricate():
    # The mapper's c-bet ranges come from real content entries — assert the
    # entries it depends on exist and are non-empty (guards silent fallback).
    for opener in (Position.UTG, Position.CO, Position.BTN):
        rfi = _find_entry(NodeContext.RFI, opener, None)
        bd = _find_entry(NodeContext.BLIND_DEFENSE, Position.BB, opener)
        assert _combos_for(rfi, ActionType.RAISE)
        assert _combos_for(bd, ActionType.CALL)
