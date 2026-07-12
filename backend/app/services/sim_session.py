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

from app.db.models import DrillAttempt, SimDecision, SimHand, SimSeat, SimSession
from app.domain.action import Decision
from app.domain.content.models import PersonaPack
from app.domain.content.notation import hole_cards_to_class
from app.domain.evaluation import Coverage, EvaluationResult, FeedbackTiers
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
from app.domain.table.grade_map import map_decision_point
from app.domain.table.play import ActionEvent, advance_to_hero, assign_lineup
from app.schemas.simulate import (
    EventView,
    GradeView,
    SeatView,
    SessionView,
    ShowdownSeatView,
    SimulateHandView,
    StreetReportRow,
    StreetReportView,
)

HERO_SEAT = 0
_STARTING_STACK_BB = 100.0
_REBUY_FLOOR_BB = 1.0


class SessionNotFound(Exception):
    """Session missing/ended/not-owned — the API maps this to 404.

    ValueError stays reserved for illegal / not-hero-turn actions (=> 400)."""


@cache
def _packs() -> dict:
    return load_persona_packs()


def _grading_provider():
    """The ONE provider singleton Practice grades with — never a second
    instance (contracts/simulate-s10-s11.md §1). Imported lazily: a module-level
    import would be circular (api.v1's package __init__ imports simulate.py,
    which imports this module)."""
    from app.api.v1.drill import _provider

    return _provider


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


def _grade_view(row: SimDecision, tiers: FeedbackTiers | None = None) -> GradeView:
    """GradeView from a persisted SimDecision. verdict/reasoning come from the
    in-memory evaluation tiers of the decision graded THIS request; persisted
    rows carry no tier text (frozen S10 schema), so recap rows for earlier
    decisions surface freq/EV fields only."""
    return GradeView(
        street=row.street,
        ordinal=row.ordinal,
        chosen_action=row.chosen_action,
        correctness=row.correctness,
        ev_loss_bb=row.ev_loss_bb,
        coverage=row.coverage,
        verdict=tiers.verdict if tiers is not None else None,
        reasoning=tiers.reasoning if tiers is not None else None,
    )


def _hand_decisions(db: Session, sim_hand_id: int) -> list[SimDecision]:
    rows = db.exec(
        select(SimDecision).where(SimDecision.sim_hand_id == sim_hand_id)
    ).all()
    return sorted(rows, key=lambda r: r.ordinal)


def _sim_decision_row(
    session: SimSession,
    hand: SimHand,
    street: str,
    ordinal: int,
    decision: Decision,
    result: EvaluationResult | None,
) -> SimDecision:
    """The SimDecision row for a hero decision. result=None ⇒ the mapper found
    no canonical Spot ('unmappable'); a NOT_FOUND result ⇒ mapped but off-pack
    ('not_found'). Both mean "no baseline yet" (correctness None)."""
    if result is None or result.coverage == Coverage.NOT_FOUND:
        return SimDecision(
            owner_id=session.owner_id,
            session_id=session.id,
            sim_hand_id=hand.id,
            street=street,
            ordinal=ordinal,
            chosen_action=decision.action.value,
            correctness=None,
            ev_loss_bb=0.0,
            leak_category=None,
            coverage="unmappable" if result is None else Coverage.NOT_FOUND.value,
        )
    return SimDecision(
        owner_id=session.owner_id,
        session_id=session.id,
        sim_hand_id=hand.id,
        street=street,
        ordinal=ordinal,
        chosen_action=decision.action.value,
        correctness=result.correctness.value if result.correctness else None,
        ev_loss_bb=result.ev_loss_bb,
        leak_category=result.leak_category,
        coverage=result.coverage.value,
    )


def _view(
    session: SimSession,
    hand: SimHand,
    state: HandState,
    seats: list[SimSeat],
    events: list[ActionEvent],
    last_grade: GradeView | None = None,
    recap: list[GradeView] | None = None,
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
            last_grade=last_grade,
            recap=recap or [],
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
    recap = (
        [_grade_view(r) for r in _hand_decisions(db, hand.id)]
        if state.hand_over
        else None
    )
    return _view(session, hand, state, _load_seats(db, session_id), events=[], recap=recap)


async def apply_hero_action(
    db: Session, session_id: str, decision: Decision, owner_id: str = ""
) -> SessionView:
    session = _get_session(db, session_id, owner_id)
    if session is None:
        raise SessionNotFound(session_id)
    hand = _current_hand(db, session)
    if hand is None or hand.status != "in_progress" or hand.state_json is None:
        raise ValueError("no hand in progress")
    state = HandState.model_validate_json(hand.state_json)
    if state.hand_over or state.to_act_seat != HERO_SEAT:
        raise ValueError("not the hero's turn")
    # Validate/apply FIRST (raises ValueError on illegal action/size) so a
    # rejected decision leaves ZERO graded rows, then grade from the
    # PRE-apply() state (mutation-ordering hazard, contract §3). apply() is
    # pure — `state` is still the pre-decision snapshot here.
    new_state = apply(state, decision)

    # --- S10 grading (baseline only, behind the one StrategyProvider) ---
    prior = _hand_decisions(db, hand.id)
    spot = map_decision_point(state, HERO_SEAT)
    result = None
    if spot is not None:
        result = await _grading_provider().evaluate(spot, decision)
    sim_row = _sim_decision_row(
        session, hand, state.street.value, len(prior), decision, result
    )
    db.add(sim_row)
    graded = result is not None and result.coverage != Coverage.NOT_FOUND
    if graded:
        # Tagged attempt so sim leaks flow into by-source stats. NEVER via
        # record_attempt()/spot_signature() (no SRS writes; frozen hash).
        db.add(
            DrillAttempt(
                owner_id=owner_id,
                spot_signature=_sim_signature(spot),
                leak_category=result.leak_category,
                chosen_action=decision.action.value,
                correctness=result.correctness.value if result.correctness else None,
                ev_loss_bb=result.ev_loss_bb,
                provider=result.provider.value,
                hand_class=hole_cards_to_class(*spot.hero.hole_cards),
                source="simulate",
            )
        )

    state = new_state
    seats = _load_seats(db, session_id)
    state, events = advance_to_hero(state, _seat_personas(seats), HERO_SEAT, _fresh_rng())
    hand.state_json = state.model_dump_json()
    if state.hand_over:
        _apply_settlement(seats, settle(state))
        hand.status = "complete"
        for row in seats:
            db.add(row)
    db.add(hand)
    # Single commit: the SimDecision/DrillAttempt rows ride the same
    # transaction as the hand-state advance (refuter med-1).
    db.commit()
    last_grade = _grade_view(sim_row, result.tiers if graded else None)
    recap = [*(_grade_view(r) for r in prior), last_grade] if state.hand_over else None
    return _view(session, hand, state, seats, events, last_grade=last_grade, recap=recap)


def _sim_signature(spot) -> str:
    """Namespaced marker for sim-tagged attempts. Deliberately NOT
    spot_signature() (frozen hash, SRS-keyed) — sim rows never enter SRS and
    only need to be queryable/groupable by source + archetype."""
    parts = ["sim", spot.node_context[0].value, spot.hero.position.value]
    if spot.facing is not None:
        parts.append(spot.facing.value)
    return ":".join(parts)


_STREET_ORDER = ("preflop", "flop", "turn", "river")


def street_report(db: Session, owner_id: str = "") -> StreetReportView:
    """All-time per-street aggregate over sim_decision (S10 report, Gate-1).

    Always returns all four streets (include-with-zeros: stable shape). Rates
    derived from these figures exclude no-baseline rows by construction —
    graded/tier counts and ev_loss_bb cover baseline-graded rows only;
    no_baseline (not_found + unmappable) is its own honest count.
    """
    rows = db.exec(select(SimDecision).where(SimDecision.owner_id == owner_id)).all()
    by_street: dict[str, dict] = {
        s: {
            "graded": 0,
            "optimal": 0,
            "acceptable": 0,
            "mistake": 0,
            "blunder": 0,
            "ev_loss_bb": 0.0,
            "no_baseline": 0,
        }
        for s in _STREET_ORDER
    }
    for r in rows:
        agg = by_street.get(r.street)
        if agg is None:  # unknown street value: never happens, but never crash a report
            continue
        if r.correctness is None:
            agg["no_baseline"] += 1
            continue
        agg["graded"] += 1
        agg["ev_loss_bb"] = round(agg["ev_loss_bb"] + r.ev_loss_bb, 2)
        if r.correctness in ("optimal", "acceptable", "mistake", "blunder"):
            agg[r.correctness] += 1
    return StreetReportView(
        rows=[StreetReportRow(street=s, **by_street[s]) for s in _STREET_ORDER],
        total_decisions=sum(a["graded"] + a["no_baseline"] for a in by_street.values()),
    )


def deal_next_hand(db: Session, session_id: str, owner_id: str = "") -> SessionView:
    session = _get_session(db, session_id, owner_id)
    if session is None:
        raise SessionNotFound(session_id)
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
