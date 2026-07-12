"""S9 session-service tests: play/fold/restore/rebuy/ledger/reproducibility +
per-decision parity between `app.domain.table.play` and the S4 harness
(`tests/test_personas_postflop.py`). Spec: docs/ai-dlc/specs/simulate-s9.md.
"""

from __future__ import annotations

import random

import pytest
import test_personas_postflop as harness  # per-decision parity reference
from sqlmodel import Session, create_engine, select

from app.db.migrate import run_migrations
from app.db.models import SimHand, SimSeat
from app.domain.action import Decision
from app.domain.archetypes import VillainType
from app.domain.personas import load_persona_packs
from app.domain.spot import ActionType, Street
from app.domain.table import play
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, SeatDelta, Settlement, apply, start_hand
from app.domain.table.engine import legal_actions as engine_legal_actions
from app.services import sim_session
from app.services.sim_session import (
    SessionNotFound,
    apply_hero_action,
    create_session,
    deal_next_hand,
    leave_session,
    restore_session,
)


@pytest.fixture
def db(tmp_path):
    url = f"sqlite:///{tmp_path / 'sim.db'}"
    run_migrations(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with Session(engine) as s:
        yield s


def _hero_decision(view, fold_if_possible: bool = False) -> Decision:
    kinds = {la.action for la in view.hand.legal_actions}
    if fold_if_possible and ActionType.FOLD in kinds:
        return Decision(action=ActionType.FOLD)
    if ActionType.CHECK in kinds:
        return Decision(action=ActionType.CHECK)
    if ActionType.CALL in kinds:
        return Decision(action=ActionType.CALL)
    return Decision(action=ActionType.FOLD)


def _play_current_hand(db, view, fold_if_possible: bool = False):
    """Drive the hero (check/call, or fold-when-facing-chips) to hand end."""
    guard = 0
    while not view.hand.hand_over:
        guard += 1
        assert guard < 100, "hand did not terminate"
        # Persisted state is always at a hero decision boundary or hand-over.
        assert view.hand.is_hero_turn
        assert view.hand.legal_actions, "hero turn must carry legal actions"
        view = apply_hero_action(
            db, view.session_id, _hero_decision(view, fold_if_possible)
        )
    return view


# ------------------------------------------------------------- lifecycle


def test_create_session_seats_and_lineup(db):
    view = create_session(db)
    seats = db.exec(select(SimSeat).where(SimSeat.session_id == view.session_id)).all()
    assert len(seats) == 9
    by_index = {s.seat_index: s for s in seats}
    assert by_index[0].is_hero and by_index[0].persona_type is None
    bots = sorted(by_index[i].persona_type for i in range(1, 9))
    assert bots == sorted(v.value for v in play.LINEUP)
    assert all(s.stack_bb == 100.0 and s.buyins_bb == 100.0 for s in seats)
    assert len(view.hand.seats) == 9
    assert view.hand.hero.hole_cards is not None


def test_play_hand_to_showdown(db):
    view = create_session(db)
    for _ in range(30):  # hero check/calls: a multiway showdown shows up fast
        final = _play_current_hand(db, view)
        if final.hand.showdown:
            assert final.hand.hand_over
            assert final.hand.street == Street.RIVER.value
            for sd in final.hand.showdown:
                assert len(sd.hole_cards) == 2
            deltas = {sd.seat_index: sd.delta_bb for sd in final.hand.showdown}
            assert any(d > 0 for d in deltas.values())
            return
        view = deal_next_hand(db, final.session_id)
    pytest.fail("no showdown reached in 30 hands")


def test_hero_fold_ends_hero_participation(db):
    view = create_session(db)
    for _ in range(30):
        if view.hand.hand_over:
            view = deal_next_hand(db, view.session_id)
            continue
        kinds = {la.action for la in view.hand.legal_actions}
        if ActionType.FOLD in kinds:
            after = apply_hero_action(db, view.session_id, Decision(action=ActionType.FOLD))
            # Bots resolve synchronously: with the hero out, the hand runs to
            # completion inside this one request.
            assert after.hand.hand_over
            assert after.hand.seats[0].status == "folded"
            assert all(sd.seat_index != 0 for sd in after.hand.showdown)
            return
        view = apply_hero_action(db, view.session_id, _hero_decision(view))
    pytest.fail("hero never faced a bet in 30 decisions")


def test_restore_mid_hand_exact_decision_point(db):
    view = create_session(db)
    for _ in range(20):
        if view.hand.is_hero_turn:
            break
        view = deal_next_hand(db, view.session_id)  # hand 1 can end pre-hero
    assert view.hand.is_hero_turn
    restored = restore_session(db, view.session_id)
    assert restored is not None
    assert restored.hand.to_act_seat == view.hand.to_act_seat == 0
    assert restored.hand.is_hero_turn
    assert restored.hand.legal_actions == view.hand.legal_actions
    assert restored.hand.hero.hole_cards == view.hand.hero.hole_cards
    assert restored.hand.board == view.hand.board
    assert restored.hand.pot_bb == view.hand.pot_bb
    assert restored.hand.events == []  # events are per-request, not persisted


def test_apply_and_deal_raise_session_not_found_on_missing_or_ended(db):
    fold = Decision(action=ActionType.FOLD)
    with pytest.raises(SessionNotFound):
        apply_hero_action(db, "missing", fold)
    with pytest.raises(SessionNotFound):
        deal_next_hand(db, "missing")
    view = create_session(db)
    leave_session(db, view.session_id)
    with pytest.raises(SessionNotFound):
        apply_hero_action(db, view.session_id, fold)
    with pytest.raises(SessionNotFound):
        deal_next_hand(db, view.session_id)


def test_restore_missing_or_ended_session_is_none(db):
    assert restore_session(db, "nope") is None
    view = create_session(db)
    leave_session(db, view.session_id)
    assert restore_session(db, view.session_id) is None


# ----------------------------------------------------- ledger / rebuy / chips


def test_bust_triggers_rebuy_and_2dp_ledger():
    seats = [
        SimSeat(
            session_id="s", seat_index=i, is_hero=i == 0,
            persona_type=None if i == 0 else "tag",
            stack_bb=100.0, buyins_bb=100.0,
        )
        for i in range(9)
    ]
    deltas = [0.0] * 9
    deltas[0], deltas[1] = -99.55, 99.55
    settlement = Settlement(
        pots=[], winners_by_pot=[],
        deltas=[SeatDelta(seat=i, delta_bb=deltas[i]) for i in range(9)],
        showdown_seats=[0, 1],
    )
    sim_session._apply_settlement(seats, settlement)
    # Seat 0 busted (0.45 < 1.0): rebuy to 100, buyins grow by 99.55.
    assert seats[0].stack_bb == 100.0
    assert seats[0].buyins_bb == 199.55
    assert seats[1].stack_bb == 199.55 and seats[1].buyins_bb == 100.0
    for s in seats:
        assert s.stack_bb == round(s.stack_bb, 2)
        assert s.buyins_bb == round(s.buyins_bb, 2)
    net = sum(s.stack_bb - s.buyins_bb for s in seats)
    assert round(net, 2) == 0.0


def test_chip_conservation_across_hands(db):
    view = create_session(db)
    for _ in range(5):
        view = _play_current_hand(db, view)
        seats = db.exec(select(SimSeat).where(SimSeat.session_id == view.session_id)).all()
        assert round(sum(s.stack_bb - s.buyins_bb for s in seats), 2) == 0.0
        for s in seats:
            assert s.stack_bb == round(s.stack_bb, 2)
            assert s.buyins_bb == round(s.buyins_bb, 2)
        view = deal_next_hand(db, view.session_id)


# -------------------------------------------------------- reproducibility


def test_deal_reproducible_from_rng_seed(db):
    view = create_session(db)
    row = db.exec(select(SimHand).where(SimHand.session_id == view.session_id)).first()
    state = HandState.model_validate_json(row.state_json)
    dealt = deal_hand(random.Random(int(row.rng_seed)))
    assert [tuple(s.hole_cards) for s in state.seats] == dealt.hole_cards
    assert state.full_board == dealt.board
    # NOT full-hand replay: bot actions use a separate, unseeded-from-rng_seed
    # stream by design — only the deal is pinned to rng_seed.


# ---------------------------------------------------- per-decision parity


def test_bot_decision_parity_with_harness():
    packs = load_persona_packs()
    if set(VillainType) - set(packs):
        pytest.skip("not all persona packs authored yet")
    personas = sorted(v for v in VillainType)
    persona_by_seat = {i: personas[i % len(personas)] for i in range(9)}
    checked = 0
    for hand_seed in (11, 22, 33, 44, 55):
        dealt = deal_hand(random.Random(hand_seed))
        state = start_hand(dealt, button_seat=hand_seed % 9, stacks_bb=[100.0] * 9)
        guard = 0
        while not state.hand_over:
            guard += 1
            assert guard < 500
            seat = state.to_act_seat
            legal = engine_legal_actions(state)
            pack = packs[persona_by_seat[seat]]
            seat_state = state.seats[seat]
            decision_seed = hand_seed * 1000 + guard
            got = play.bot_decision(state, seat, pack, random.Random(decision_seed))
            if state.street is Street.PREFLOP:
                facing = harness._preflop_facing(state)
                expected = harness._preflop_decision(
                    pack, seat_state.position, facing, seat_state.hole_cards,
                    legal, random.Random(decision_seed),
                )
            else:
                pot_bb = sum(s.invested_total_bb for s in state.seats)
                opponents = harness._live_opponents(state, seat)
                expected = harness._postflop_decision(
                    pack, seat_state.hole_cards, state.board, legal, pot_bb,
                    seat_state.stack_bb, opponents, random.Random(decision_seed),
                    state.current_bet_bb,
                )
            assert got == expected, (
                f"parity break: hand_seed={hand_seed} guard={guard} seat={seat}"
            )
            checked += 1
            state = apply(state, got)
    assert checked > 50  # enough decisions across preflop + postflop streets
