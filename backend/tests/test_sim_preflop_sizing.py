"""N3 end-to-end: the two preflop sizes reach the GRADED spot (refuter HIGH).

Plays a real RFI open hand through `apply_hero_action` and asserts the persisted
`sim_decision.sizing_correctness` — proving the feature engages beyond unit
grade() tests. Also asserts the preflop chart + a single-RAISE (VS_3BET) spot are
NOT rewritten (the two-size injection is scoped to apply_hero_action).
"""

from __future__ import annotations

import asyncio
import random

import pytest
from factories import make_rfi_spot
from sqlmodel import Session, create_engine, select

from app.db.migrate import run_migrations
from app.db.models import SimDecision, SimHand, SimSeat, SimSession
from app.domain.action import Decision
from app.domain.spot import ActionType, LegalAction, NodeContext, Position
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, start_hand
from app.services.sim_session import (
    _hero_legal_actions,
    _inject_two_sizes,
    _preflop_two_sizes,
    apply_hero_action,
)

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture
def engine(tmp_path):
    url = f"sqlite:///{tmp_path / 's.db'}"
    run_migrations(url)
    return create_engine(url, connect_args={"check_same_thread": False})


def _rfi_hero_session(s: Session) -> tuple[str, int]:
    """SimSession + SimHand where hero (seat 0) is UTG first-to-act preflop
    (button_seat 6 ⇒ to_act = seat 0) — an unopened pot = RFI node."""
    dealt = deal_hand(random.Random(7))
    state = start_hand(dealt, button_seat=6, stacks_bb=[100.0] * 9)
    assert state.to_act_seat == 0  # hero acts first = RFI
    session = SimSession(id="sess1", button_seat=6, hand_no=1)
    s.add(session)
    for i in range(9):
        s.add(
            SimSeat(
                session_id="sess1",
                seat_index=i,
                is_hero=i == 0,
                persona_type=None if i == 0 else "tag",
                stack_bb=100.0,
                buyins_bb=100.0,
            )
        )
    hand = SimHand(
        session_id="sess1",
        hand_no=1,
        button_seat=6,
        rng_seed="7",
        state_json=state.model_dump_json(),
    )
    s.add(hand)
    s.commit()
    s.refresh(hand)
    return session.id, hand.id


def _two_raise_sizes(s: Session, hand_id: int) -> list[float]:
    """The two RFI raise sizes the display path offers hero on this hand."""
    hand = s.get(SimHand, hand_id)
    state = HandState.model_validate_json(hand.state_json)
    legal = _hero_legal_actions(state)
    return sorted(la.size_bb for la in legal if la.action is ActionType.RAISE)


def test_rfi_open_smaller_size_grades_optimal(engine):
    with Session(engine) as s:
        session_id, hand_id = _rfi_hero_session(s)
        sizes = _two_raise_sizes(s, hand_id)
        assert len(sizes) == 2  # two distinct RFI sizes offered
        small, big = sizes
        asyncio.run(
            apply_hero_action(
                s, session_id, Decision(action=ActionType.RAISE, size_bb=small)
            )
        )
        row = s.exec(
            select(SimDecision).where(SimDecision.session_id == session_id)
        ).first()
        assert row is not None
        assert row.chosen_action == "raise"
        assert row.sizing_correctness == "optimal"  # smaller = recommended


def test_rfi_open_bigger_size_grades_acceptable(engine):
    with Session(engine) as s:
        session_id, hand_id = _rfi_hero_session(s)
        _small, big = _two_raise_sizes(s, hand_id)
        asyncio.run(
            apply_hero_action(
                s, session_id, Decision(action=ActionType.RAISE, size_bb=big)
            )
        )
        row = s.exec(
            select(SimDecision).where(SimDecision.session_id == session_id)
        ).first()
        assert row is not None
        assert row.sizing_correctness == "acceptable"  # bigger alt


def test_synthesis_open_vs_3bet_and_fallback():
    # open: +1.0bb, distinct
    assert _preflop_two_sizes(2.5, 2.0, 100.0, NodeContext.RFI) == [2.5, 3.5]
    # 3-bet: round(rec*1.25, 1)
    assert _preflop_two_sizes(8.0, 6.0, 100.0, NodeContext.VS_RFI) == [8.0, 10.0]
    # short-stack collapse: both clamp to the max ceiling ⇒ single size
    assert _preflop_two_sizes(4.5, 4.0, 4.5, NodeContext.RFI) == [4.5]
    # rec already at max ⇒ alt can't exceed it ⇒ single size
    assert _preflop_two_sizes(4.0, 2.0, 4.0, NodeContext.RFI) == [4.0]


def _vs3bet_spot():
    """A VS_3BET (hero 4-bet, the cap) spot with one RAISE legal action."""
    return make_rfi_spot(hole_cards=("Ah", "Ad"), position=Position.CO).model_copy(
        update={
            "node_context": [NodeContext.VS_3BET],
            "facing": Position.BTN,
            "legal_actions": [
                LegalAction(action=ActionType.FOLD),
                LegalAction(action=ActionType.CALL, min_bb=10.0),
                LegalAction(action=ActionType.RAISE, min_bb=22.0, max_bb=100.0),
            ],
        }
    )


def test_vs3bet_spot_stays_single_raise_after_injection():
    """The cap: VS_3BET (hero 4-bet) must NOT gain a second size — the two-size
    injection gates strictly on RFI/VS_RFI/BLIND_DEFENSE."""
    spot = _vs3bet_spot()
    out = _inject_two_sizes(spot)
    raises = [la for la in out.legal_actions if la.action is ActionType.RAISE]
    assert len(raises) == 1
    assert out.legal_actions == spot.legal_actions  # untouched
