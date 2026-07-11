"""Simulate session service (S9) — playable, persistent 9-max sessions.

Lives in the service layer (not pure domain) because it owns persistence:
`SimSession`/`SimSeat`/`SimHand` rows, carry-over stacks, auto-rebuy, and the
serialized live `HandState` (`state_json`, server-side only). All returned
views are privacy-scrubbed field-by-field — the only hole cards that ever
leave this module are the hero's plus, at showdown, the settlement's
`showdown_seats`. `full_board`, `state_json`, and folded villains' cards are
never exposed.

RNG lifecycle (spec §RNG lifecycle): the DEAL uses `random.Random(int(rng_seed))`
with `rng_seed` persisted (reproducible). Bot ACTIONS use a fresh
`random.Random(secrets.randbits(256))` per `advance_to_hero` call — re-seeding
from `rng_seed` each request would replay identical draw sequences per street.
Bot actions are therefore intentionally NOT replayable from `rng_seed`; restore
never re-runs bots (their results are baked into `state_json`).

Spec: docs/ai-dlc/specs/simulate-s9.md.
"""

from __future__ import annotations

import random
import secrets
import uuid
from functools import cache

from sqlmodel import Session, select

from app.db.models import SimHand, SimSeat, SimSession
from app.domain.action import Decision
from app.domain.content.models import PersonaPack
from app.domain.personas import load_persona_packs
from app.domain.spot import Hero
from app.domain.table.deck import deal_hand
from app.domain.table.engine import (
    HandState,
    Settlement,
    apply,
    legal_actions,
    settle,
    start_hand,
)
from app.domain.table.play import ActionEvent, advance_to_hero, assign_lineup
from app.schemas.simulate import (
    EventView,
    SeatView,
    SessionView,
    ShowdownSeatView,
    SimulateHandView,
)

HERO_SEAT = 0
_STARTING_STACK_BB = 100.0
_REBUY_FLOOR_BB = 1.0


@cache
def _packs() -> dict:
    return load_persona_packs()


def _load_seats(db: Session, session_id: str) -> list[SimSeat]:
    rows = db.exec(select(SimSeat).where(SimSeat.session_id == session_id)).all()
    return sorted(rows, key=lambda r: r.seat_index)


def _seat_personas(seats: list[SimSeat]) -> dict[int, PersonaPack]:
    packs = _packs()
    return {
        row.seat_index: packs[row.persona_type]
        for row in seats
        if row.persona_type is not None
    }


def _fresh_rng() -> random.Random:
    return random.Random(secrets.randbits(256))


def _apply_settlement(seats: list[SimSeat], settlement: Settlement) -> None:
    """Apply per-seat deltas to carry-over stacks; auto-rebuy busted seats.

    Rounds stack_bb/buyins_bb to 2dp on every write (engine convention) so
    net_bb stays free of IEEE-754 display noise.
    """
    for row in seats:
        delta = settlement.deltas[row.seat_index].delta_bb
        stack = round(row.stack_bb + delta, 2)
        if stack < _REBUY_FLOOR_BB:
            row.buyins_bb = round(row.buyins_bb + (_STARTING_STACK_BB - stack), 2)
            stack = _STARTING_STACK_BB
        row.stack_bb = round(stack, 2)


def _deal_and_advance(
    db: Session, session: SimSession, seats: list[SimSeat]
) -> tuple[SimHand, HandState, list[ActionEvent]]:
    """Deal the session's current hand_no, advance bots to the hero (or hand
    end), settle if already over, and persist the SimHand row."""
    seed = secrets.randbits(256)
    dealt = deal_hand(random.Random(seed))
    state = start_hand(
        dealt,
        button_seat=session.button_seat,
        stacks_bb=[row.stack_bb for row in seats],
    )
    state, events = advance_to_hero(state, _seat_personas(seats), HERO_SEAT, _fresh_rng())
    hand = SimHand(
        session_id=session.id,
        hand_no=session.hand_no,
        button_seat=session.button_seat,
        rng_seed=str(seed),
        status="in_progress",
        state_json=state.model_dump_json(),
    )
    if state.hand_over:  # e.g. everyone folds to the hero's big blind
        _apply_settlement(seats, settle(state))
        hand.status = "complete"
    db.add(hand)
    for row in seats:
        db.add(row)
    db.commit()
    db.refresh(hand)
    return hand, state, events


def _current_hand(db: Session, session: SimSession) -> SimHand | None:
    return db.exec(
        select(SimHand)
        .where(SimHand.session_id == session.id)
        .where(SimHand.hand_no == session.hand_no)
    ).first()


def _get_session(db: Session, session_id: str, owner_id: str) -> SimSession | None:
    session = db.get(SimSession, session_id)
    if session is None or session.owner_id != owner_id or session.status != "active":
        return None
    return session


def _view(
    session: SimSession,
    hand: SimHand,
    state: HandState,
    seats: list[SimSeat],
    events: list[ActionEvent],
) -> SessionView:
    """Assemble the privacy-scrubbed view field-by-field from the HandState.

    Only `hero.hole_cards` and, at showdown, the settlement's `showdown_seats`
    carry hole cards; `full_board`/`state_json` never appear.
    """
    complete = hand.status == "complete"
    seat_views = []
    for row in seats:
        eng = state.seats[row.seat_index]
        seat_views.append(
            SeatView(
                seat_index=row.seat_index,
                position=eng.position.value,
                persona_type=row.persona_type,
                is_hero=row.is_hero,
                # Mid-hand: chips behind from the live state; after settlement
                # the SimSeat row holds the post-settlement (incl. rebuy) stack.
                stack_bb=row.stack_bb if complete else eng.stack_bb,
                status=eng.status.value,
                invested_street_bb=eng.invested_street_bb,
                net_bb=round(row.stack_bb - row.buyins_bb, 2),
            )
        )
    hero_state = state.seats[HERO_SEAT]
    is_hero_turn = not state.hand_over and state.to_act_seat == HERO_SEAT
    showdown: list[ShowdownSeatView] = []
    if state.hand_over:
        settlement = settle(state)
        showdown = [
            ShowdownSeatView(
                seat_index=s,
                hole_cards=state.seats[s].hole_cards,
                delta_bb=settlement.deltas[s].delta_bb,
            )
            for s in settlement.showdown_seats
        ]
    return SessionView(
        session_id=session.id,
        hand=SimulateHandView(
            hand_no=hand.hand_no,
            button_seat=hand.button_seat,
            street=state.street.value,
            board=list(state.board),
            pot_bb=round(sum(s.invested_total_bb for s in state.seats), 2),
            seats=seat_views,
            hero=Hero(
                position=hero_state.position,
                hole_cards=hero_state.hole_cards,
                stack_bb=hero_state.stack_bb,
            ),
            to_act_seat=state.to_act_seat,
            is_hero_turn=is_hero_turn,
            legal_actions=legal_actions(state) if is_hero_turn else [],
            events=[
                EventView(
                    seat_index=e.seat,
                    position=e.position.value,
                    action=e.action.value,
                    amount_bb=e.amount_bb,
                    street=e.street.value,
                )
                for e in events
            ],
            hand_over=state.hand_over,
            showdown=showdown,
        ),
    )


# ------------------------------------------------------------- public API


def create_session(db: Session, owner_id: str = "") -> SessionView:
    session = SimSession(
        id=uuid.uuid4().hex,
        owner_id=owner_id,
        button_seat=secrets.randbelow(9),
        hand_no=1,
        status="active",
    )
    db.add(session)
    lineup = assign_lineup(_fresh_rng())
    seats = [
        SimSeat(
            session_id=session.id,
            seat_index=i,
            is_hero=i == HERO_SEAT,
            persona_type=None if i == HERO_SEAT else lineup[i].value,
            stack_bb=_STARTING_STACK_BB,
            buyins_bb=_STARTING_STACK_BB,
        )
        for i in range(9)
    ]
    for row in seats:
        db.add(row)
    hand, state, events = _deal_and_advance(db, session, seats)
    return _view(session, hand, state, seats, events)


def restore_session(db: Session, session_id: str, owner_id: str = "") -> SessionView | None:
    session = _get_session(db, session_id, owner_id)
    if session is None:
        return None  # => 404
    hand = _current_hand(db, session)
    if hand is None or hand.state_json is None:
        return None
    state = HandState.model_validate_json(hand.state_json)
    return _view(session, hand, state, _load_seats(db, session_id), events=[])


def apply_hero_action(
    db: Session, session_id: str, decision: Decision, owner_id: str = ""
) -> SessionView:
    session = _get_session(db, session_id, owner_id)
    if session is None:
        raise ValueError("session not found")
    hand = _current_hand(db, session)
    if hand is None or hand.status != "in_progress" or hand.state_json is None:
        raise ValueError("no hand in progress")
    state = HandState.model_validate_json(hand.state_json)
    if state.hand_over or state.to_act_seat != HERO_SEAT:
        raise ValueError("not the hero's turn")
    state = apply(state, decision)  # raises ValueError on illegal action/size
    seats = _load_seats(db, session_id)
    state, events = advance_to_hero(state, _seat_personas(seats), HERO_SEAT, _fresh_rng())
    hand.state_json = state.model_dump_json()
    if state.hand_over:
        _apply_settlement(seats, settle(state))
        hand.status = "complete"
        for row in seats:
            db.add(row)
    db.add(hand)
    db.commit()
    return _view(session, hand, state, seats, events)


def deal_next_hand(db: Session, session_id: str, owner_id: str = "") -> SessionView:
    session = _get_session(db, session_id, owner_id)
    if session is None:
        raise ValueError("session not found")
    hand = _current_hand(db, session)
    if hand is not None and hand.status == "in_progress":
        # Idempotent no-op: the current hand is still live — return it.
        state = HandState.model_validate_json(hand.state_json)
        return _view(session, hand, state, _load_seats(db, session_id), events=[])
    session.button_seat = (session.button_seat + 1) % 9
    session.hand_no += 1
    db.add(session)
    seats = _load_seats(db, session_id)
    hand, state, events = _deal_and_advance(db, session, seats)
    return _view(session, hand, state, seats, events)


def leave_session(db: Session, session_id: str, owner_id: str = "") -> None:
    session = _get_session(db, session_id, owner_id)
    if session is None:
        return  # idempotent: already gone/ended
    session.status = "ended"
    db.add(session)
    db.commit()
