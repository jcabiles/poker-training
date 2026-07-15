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
from app.domain.archetypes import VillainType
from app.domain.content.models import PersonaPack
from app.domain.content.notation import hole_cards_to_class
from app.domain.content.registry import lookup
from app.domain.evaluation import Coverage, EvaluationResult, FeedbackTiers
from app.domain.grading import range_grid
from app.domain.personas import load_persona_packs
from app.domain.spot import ActionType, Hero, NodeContext, PlayerStatus, Spot, Street
from app.domain.table.deck import deal_hand
from app.domain.table.engine import (
    HandState,
    SeatState,
    Settlement,
    apply,
    legal_actions,
    settle,
    start_hand,
)
from app.domain.table.grade_map import map_decision_point
from app.domain.table.play import ActionEvent, advance_to_hero, assign_lineup
from app.domain.table.range_estimate import (
    PublicAction,
    PublicActionHistory,
    estimate_range,
)
from app.schemas.simulate import (
    EventView,
    ExploitNoteView,
    GradeView,
    PreflopChartView,
    SeatView,
    SessionView,
    ShowdownSeatView,
    SimulateHandView,
    StreetReportRow,
    StreetReportView,
    VillainRangeView,
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
    rows carry no tier text (frozen S10 schema). Scope of the gap (W1 refuter
    med-1): recap rows for earlier decisions lack tiers on the LIVE path, and
    a session reload (restore_session) rebuilds the recap with tiers=None for
    EVERY row — including the hand's final decision. correctness/ev_loss/
    coverage always survive. Reload-durable reasoning = a SimDecision
    verdict/reasoning migration (0011), tracked as a roadmap NEXT note."""
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


def _last_action(state: HandState, eng: SeatState) -> str | None:
    """The verb of a seat's last VOLUNTARY action on the CURRENT street, for the
    felt label (S-action-labels). Per-street: clears when the street advances,
    like the chips-in-front puck. A folded seat reads "fold" persistently (a fold
    is a hand-level state — its fold entry may sit on an earlier street). Forced
    blind POSTs are not a voluntary action and are skipped (the amount already
    shows in the chips puck). None ⇒ hasn't acted this street ⇒ no label.
    """
    if eng.status is PlayerStatus.FOLDED:
        return "fold"
    for h in reversed(state.action_history):
        if (
            h.position == eng.position
            and h.street == state.street
            and h.action is not ActionType.POST
        ):
            return h.action.value
    return None


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
                last_action=_last_action(state, eng),
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


def _content_index() -> dict:
    """The ONE content index singleton Practice's drill grid is built from —
    reusing it (not a second build_index) guarantees the chart grid is
    byte-identical to the Practice drill grid for the same Spot. Lazy import
    for the same circularity reason as _grading_provider."""
    from app.api.v1.drill import _INDEX

    return _INDEX


def _node_label(spot: Spot) -> str:
    ctx = spot.node_context[0]
    pos = spot.hero.position.value
    if ctx is NodeContext.RFI:
        return f"{pos} open (RFI)"
    if ctx is NodeContext.VS_LIMPERS:
        n = spot.limper_count or 0
        return f"{pos} vs {n} limper{'' if n == 1 else 's'}"
    facing = spot.facing.value if spot.facing is not None else "?"
    if ctx is NodeContext.VS_3BET:
        return f"{pos} vs {facing} 3-bet"
    if ctx is NodeContext.VS_4BET:
        return f"{pos} vs {facing} 4-bet"
    return f"{pos} vs {facing} open"  # VS_RFI / BLIND_DEFENSE


def _exploit_note(
    spot: Spot, state: HandState, seats: list[SimSeat]
) -> ExploitNoteView | None:
    """The authored exploit rationale for (mapped node, LIVE villain persona).

    Villain resolution (spec med-1): the mapped Spot carries villain_type=None;
    the villain is the seat sitting at the Spot's `facing` position in the LIVE
    hand — its persona_type keys the registry lookup. Spots without a facing
    position (RFI, vs_limpers — content keys limpers by count, not seat) carry
    no single resolvable villain seat ⇒ no note; ditto any missing authored
    pair. The note is omitted, never guessed."""
    if spot.facing is None:
        return None
    villain_seat = next(s.seat for s in state.seats if s.position is spot.facing)
    persona = seats[villain_seat].persona_type
    if persona is None:
        return None
    entry = lookup(_content_index(), spot, villain_type=VillainType(persona))
    if entry is None or entry.rationale is None:
        return None
    return ExploitNoteView(villain_label=persona, rationale=entry.rationale)


def preflop_chart(db: Session, session_id: str, owner_id: str = "") -> PreflopChartView:
    """Read-only: the baseline chart for the hero's CURRENT preflop decision.

    available=false when it is not the hero's preflop turn, the hand is over,
    or the decision point is unmappable — chart availability ≡ gradeability
    (same map_decision_point gate), never a fabricated grid."""
    session = _get_session(db, session_id, owner_id)
    if session is None:
        raise SessionNotFound(session_id)
    hand = _current_hand(db, session)
    if hand is None or hand.state_json is None:
        return PreflopChartView(available=False)
    state = HandState.model_validate_json(hand.state_json)
    if (
        state.hand_over
        or state.street is not Street.PREFLOP
        or state.to_act_seat != HERO_SEAT
    ):
        return PreflopChartView(available=False)
    spot = map_decision_point(state, HERO_SEAT)
    if spot is None:
        return PreflopChartView(available=False)
    # Exactly api/v1/drill.py's preflop-grid pattern, on the same singletons.
    grid = range_grid(lookup(_content_index(), spot))
    return PreflopChartView(
        available=True,
        node_label=_node_label(spot),
        grid=grid,
        exploit_note=_exploit_note(spot, state, _load_seats(db, session_id)),
    )


def _public_history(state: HandState) -> PublicActionHistory:
    """Card-free projection of `state` (villain-range V2, spec structural
    no-peek §high-3). Built ONLY from `state.action_history`/`state.board`/
    `state.seats[*].position`/`state.seats[*].stack_bb`+`invested_total_bb` —
    never `SeatState.hole_cards`, never passed as a `SeatState` object. Each
    seat's pre-hand starting stack is stack_bb + invested_total_bb (nothing
    resets invested_total_bb mid-hand, so the sum recovers the hand's opening
    stack without a separate persisted snapshot)."""
    pos2seat = {s.position: s.seat for s in state.seats}
    starting = [0.0] * len(state.seats)
    for s in state.seats:
        starting[s.seat] = round(s.stack_bb + s.invested_total_bb, 2)
    return PublicActionHistory(
        button_seat=state.button_seat,
        starting_stacks_bb=tuple(starting),
        board=tuple(state.board),
        actions=tuple(
            PublicAction(
                seat=pos2seat[h.position],
                position=h.position,
                street=h.street,
                action=h.action,
                amount_bb=h.amount_bb,
            )
            for h in state.action_history
        ),
    )


def villain_range(
    db: Session,
    session_id: str,
    seat_index: int,
    through_action: int | None = None,
    owner_id: str = "",
) -> VillainRangeView:
    """Read-only: the live estimated hand-range for a villain seat (spec
    `simulate-villain-range.md`). NO-PEEK is structural — `state` (which
    holds every seat's hole cards) is stripped to a `PublicActionHistory`
    projection by `_public_history` BEFORE `estimate_range` ever sees it;
    dead cards are the hero's own hole cards plus the revealed board only.

    available=false (200 body) when the seat is the hero, is FOLDED per
    SERVER truth (the FE's staged/lag gating is a display concern layered on
    top, not this), the hand is over (showdown reveals real cards), or the
    seat has no persona (should not happen for a live non-hero seat, but
    checked defensively). 404 stays reserved for SessionNotFound.

    `through_action`: the wire unit is a NARRATED action count — the number
    of non-POST public actions (hero's own + every villain's) that have
    happened so far in the hand, in chronological order — because that's
    what a client-side event log naturally tracks. `action_history` always
    opens with exactly 2 POST rows (SB, BB) before any narrated action, and
    every subsequent apply() (hero or bot) appends exactly one row, so the
    translation to V1's POST-inclusive `estimate_range(through_action=...)`
    index is a constant offset: `domain_index = 2 + narrated_count`. `None`
    means "full history so far" (no truncation). Clamped to
    `[0, len(action_history)]` so an out-of-range count degrades to the
    nearest valid prefix rather than erroring.
    """
    session = _get_session(db, session_id, owner_id)
    if session is None:
        raise SessionNotFound(session_id)
    hand = _current_hand(db, session)
    if hand is None or hand.state_json is None:
        return VillainRangeView(available=False, seat_index=seat_index)
    state = HandState.model_validate_json(hand.state_json)
    if (
        seat_index == HERO_SEAT
        or state.hand_over
        or state.seats[seat_index].status is PlayerStatus.FOLDED
    ):
        return VillainRangeView(available=False, seat_index=seat_index)
    seats = _load_seats(db, session_id)
    persona_type = seats[seat_index].persona_type
    if persona_type is None:
        return VillainRangeView(available=False, seat_index=seat_index)
    pack = _packs()[VillainType(persona_type)]

    history = _public_history(state)
    total = len(history.actions)
    domain_through: int | None = None
    if through_action is not None:
        domain_through = max(0, min(2 + through_action, total))
    dead_cards = tuple(state.seats[HERO_SEAT].hole_cards)
    estimate = estimate_range(
        pack, history, seat_index, dead_cards=dead_cards, through_action=domain_through
    )
    n = total if domain_through is None else domain_through
    street = history.actions[n - 1].street if n > 0 else Street.PREFLOP
    weights = {cls: w for cls, w in estimate.class_weights.items() if w > 0.0}
    return VillainRangeView(
        available=True,
        seat_index=seat_index,
        persona_label=pack.display_name,
        street=street.value,
        exact=estimate.exact,
        weights=weights,
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
