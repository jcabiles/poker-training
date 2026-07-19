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
from app.domain.postflop import _hand_category, _river_cat_effective
from app.domain.scenarios import _find_entry
from app.domain.spot import (
    ActionType,
    Hero,
    LegalAction,
    NodeContext,
    PlayerStatus,
    Spot,
    Street,
    players_in_pot,
)
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
from app.domain.table.grade_map_postflop import (
    map_flop_vs_cbet,
    map_flop_vs_check_raise,
    map_mw_flop_vs_cbet,
    map_mw_vs_river_bet,
    map_mw_vs_turn_bet,
    map_river_barrel,
    map_turn_barrel,
    map_vs_river_bet,
    map_vs_turn_bet,
)
from app.domain.table.play import ActionEvent, advance_to_hero, assign_lineup
from app.domain.table.range_estimate import (
    PublicAction,
    PublicActionHistory,
    estimate_range,
)
from app.domain.table.sizing import (
    HERO_NODE_SIZE,
    POSTFLOP_BET_FRACS,
    last_aggressor_position,
    postflop_node_key,
    pot_fraction_to_bb,
)
from app.schemas.simulate import (
    EventView,
    ExploitNoteView,
    GradeView,
    PostflopChartAction,
    PostflopChartView,
    PreflopChartView,
    RevealedSeatView,
    RevealView,
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

# R1 capability seam: gates the on-demand villain reveal after a hero fold. A
# future hidden-persona mode can flip this off to withhold reveals without a
# rewrite. Global (not per-session) by design — v1 has no per-session hiding.
REVEAL_ENABLED = True
_REVEAL_SCOPES = ("last-in", "all")


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
        sizing_correctness=row.sizing_correctness,
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
    spot: Spot | None = None,
    hero_position: str | None = None,
) -> SimDecision:
    """The SimDecision row for a hero decision. result=None ⇒ the mapper found
    no canonical Spot ('unmappable'); a NOT_FOUND result ⇒ mapped but off-pack
    ('not_found'). Both mean "no baseline yet" (correctness None).

    N5 spot dims: `position` (hero's seat) is ALWAYS written — the caller
    passes it from live state, so it survives unmappable decisions; the
    spot-derived dims (facing/players_in_pot/node_context) stay None unless
    a canonical Spot was built."""
    dims = {
        "position": hero_position,
        "facing_position": spot.facing.value if spot is not None and spot.facing else None,
        "players_in_pot": players_in_pot(spot) if spot is not None else None,
        "node_context": (
            spot.node_context[0].value if spot is not None and spot.node_context else None
        ),
    }
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
            **dims,
        )
    return SimDecision(
        owner_id=session.owner_id,
        session_id=session.id,
        sim_hand_id=hand.id,
        street=street,
        ordinal=ordinal,
        chosen_action=decision.action.value,
        correctness=result.correctness.value if result.correctness else None,
        sizing_correctness=(
            result.sizing_correctness.value if result.sizing_correctness else None
        ),
        ev_loss_bb=result.ev_loss_bb,
        leak_category=result.leak_category,
        coverage=result.coverage.value,
        **dims,
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


def _hero_preflop_size_bb(state) -> float | None:
    """Hero's realistic predetermined preflop raise size = the content
    `sizing_bb` for hero's current spot (the SAME baseline grading uses).
    Returns None for any spot the mapper/content can't cover ⇒ FE falls back to
    the engine min-raise."""
    spot = map_decision_point(state, HERO_SEAT)
    if spot is None or not spot.node_context:
        return None
    raises = [
        h
        for h in state.action_history
        if h.street is Street.PREFLOP and h.action is ActionType.RAISE
    ]
    facing = raises[-1].position if raises else None
    entry = _find_entry(spot.node_context[0], spot.hero.position, facing)
    return entry.sizing_bb if entry else None


def _hero_postflop_size_bb(state, la, legal) -> float | None:
    """Hero's single predetermined postflop size = the RES-B node baseline
    (HERO_NODE_SIZE) for the current node, as a pot-fraction → bb. None for a
    node without a baseline (donk/lead) ⇒ FE falls back to min-raise."""
    hero_pos = state.seats[HERO_SEAT].position
    is_aggr = last_aggressor_position(state.action_history) == hero_pos
    frac = HERO_NODE_SIZE.get(postflop_node_key(state.board, legal, is_aggressor=is_aggr))
    if frac is None:
        return None
    call = next((x for x in legal if x.action is ActionType.CALL), None)
    to_call = (call.min_bb or 0.0) if call is not None else 0.0
    pot_bb = sum(s.invested_total_bb for s in state.seats)
    return pot_fraction_to_bb(
        frac, pot_bb, action=la.action, current_bet_to=state.current_bet_bb, to_call=to_call
    )


def _is_flop_cbet_node(state, legal: list[LegalAction]) -> bool:
    """True when hero's BET here is the flop c-bet (aggressor betting the flop
    for the first time) — the ONE node R3 offers two sizes for."""
    hero_pos = state.seats[HERO_SEAT].position
    is_aggr = last_aggressor_position(state.action_history) == hero_pos
    node = postflop_node_key(state.board, legal, is_aggressor=is_aggr)
    return state.street is Street.FLOP and node.startswith("cbet_")


def _hero_cbet_legal_actions(la: LegalAction, state) -> list[LegalAction]:
    """Two FIXED-pair BET options (0.33/0.75 pot, 1dp) for the flop c-bet —
    NOT `HERO_NODE_SIZE[node]`, which collapses small==big on wet/mono boards
    (`cbet_wet`==0.75). Mirrors `map_flop_cbet`'s unconditional small/big split
    (`grade_map_postflop.py`) so the displayed size equals the graded size."""
    pot_bb = sum(s.invested_total_bb for s in state.seats)
    _fsmall, _fbig = POSTFLOP_BET_FRACS["flop"]  # single source (shared w/ graded sizes + gate)
    small = round(_fsmall * pot_bb, 1)
    big = round(_fbig * pot_bb, 1)
    lo = la.min_bb if la.min_bb is not None else small
    hi = la.max_bb if la.max_bb is not None else big
    return [
        la.model_copy(update={"min_bb": min(max(small, lo), hi), "size_bb": None}),
        la.model_copy(update={"min_bb": min(max(big, lo), hi), "size_bb": None}),
    ]


def _is_turn_barrel_node(state) -> bool:
    """True when hero's BET here is a gradeable turn barrel — the node
    `map_turn_barrel` recognizes (aggressor, HU SRP line, BB checked the turn).
    Gating on the mapper (not just the street) keeps the displayed two-size
    offer in lockstep with the graded spot — no display-vs-grade divergence."""
    return (
        state.street is Street.TURN
        and map_turn_barrel(state, HERO_SEAT) is not None
    )


def _is_river_barrel_node(state) -> bool:
    """True when hero's BET here is a gradeable river barrel (mapper non-None)."""
    return (
        state.street is Street.RIVER
        and map_river_barrel(state, HERO_SEAT) is not None
    )


def _barrel_two_sizes(la: LegalAction, state, street: str) -> list[LegalAction]:
    """Two FIXED-pair BET options for a turn/river barrel from the SAME
    `POSTFLOP_BET_FRACS[street]` fractions + current pot the graded `_barrel_spot`
    uses — displayed == graded by construction. Distinctness fallback: when the
    two clamped sizes collapse to one value (short stack), offer ONE size only
    (mirrors `_preflop_two_sizes`) — no two-vs-one display/grade divergence."""
    small_frac, big_frac = POSTFLOP_BET_FRACS[street]
    pot_bb = sum(s.invested_total_bb for s in state.seats)
    small = round(small_frac * pot_bb, 1)
    big = round(big_frac * pot_bb, 1)
    lo = la.min_bb if la.min_bb is not None else small
    hi = la.max_bb if la.max_bb is not None else big
    small_c = round(min(max(small, lo), hi), 1)
    big_c = round(min(max(big, lo), hi), 1)
    if big_c <= small_c:  # short-stack collapse → one size only
        return [la.model_copy(update={"min_bb": small_c, "size_bb": None})]
    return [
        la.model_copy(update={"min_bb": small_c, "size_bb": None}),
        la.model_copy(update={"min_bb": big_c, "size_bb": None}),
    ]


def _facing_raise_spot(state) -> Spot | None:
    """The mapped facing-node spot for hero's CURRENT decision, or None (N4b).
    Gates the two-size RAISE offer on the mapper being non-None — the same
    display==grade discipline as `_is_turn_barrel_node` — and doubles as the
    source of the offered sizes (see `_facing_raise_legal_actions`)."""
    if state.street is Street.FLOP:
        return (
            map_flop_vs_cbet(state, HERO_SEAT)
            or map_flop_vs_check_raise(state, HERO_SEAT)
            or map_mw_flop_vs_cbet(state, HERO_SEAT)
        )
    if state.street is Street.TURN:
        return map_vs_turn_bet(state, HERO_SEAT) or map_mw_vs_turn_bet(state, HERO_SEAT)
    if state.street is Street.RIVER:
        return map_vs_river_bet(state, HERO_SEAT) or map_mw_vs_river_bet(
            state, HERO_SEAT
        )
    return None


def _facing_raise_legal_actions(la: LegalAction, spot: Spot) -> list[LegalAction]:
    """Hero's RAISE options at a facing node, read DIRECTLY off the mapped
    spot's RAISE legs — the exact values the grader will see, so displayed ==
    graded by construction (the mapper already applied `FACING_RAISE_MULTS` +
    clamp + short-stack collapse; a collapsed spot yields ONE option here).
    `size_bb` carries the offer (the N3 preflop two-raise FE convention).
    Defensive fallback: if a leg somehow falls outside the engine's legal
    bracket (never in practice — mapper legs are proven within it), keep the
    single engine option rather than offer an illegal size."""
    legs = [
        x.min_bb for x in spot.legal_actions if x.action is ActionType.RAISE and x.min_bb
    ]
    lo = la.min_bb if la.min_bb is not None else 0.0
    hi = la.max_bb if la.max_bb is not None else float("inf")
    if not legs or any(leg < lo - 0.01 or leg > hi + 0.01 for leg in legs):
        return [la]
    return [la.model_copy(update={"size_bb": leg}) for leg in legs]


# Preflop nodes that get a two-size (open / 3-bet) offer. VS_3BET (hero 4-bet)
# and beyond stay single-size shove/call/fold — the cap.
_TWO_SIZE_PREFLOP_NODES = frozenset(
    {NodeContext.RFI, NodeContext.VS_RFI, NodeContext.BLIND_DEFENSE}
)


def _preflop_two_sizes(
    recommended: float, min_bb: float, max_bb: float, node: NodeContext
) -> list[float]:
    """Two distinct preflop raise sizes: the authored `recommended` (smaller)
    plus a synthesized bigger alternative. Open (RFI) adds +1.0bb; a 3-bet
    (VS_RFI/BLIND_DEFENSE) uses round(rec*1.25, 1). Both clamped into
    [min_bb, max_bb], 1-dp. Distinctness fallback: if the alt collapses
    (<= recommended after clamp+round, or > max_bb), return ONE size only —
    no two-size offer, no sizing grade for that spot (short-stack collapse)."""
    rec = round(min(max(recommended, min_bb), max_bb), 1)
    if node is NodeContext.RFI:
        alt = rec + 1.0
    else:
        alt = round(rec * 1.25, 1)
    alt = round(min(max(alt, min_bb), max_bb), 1)
    if alt <= rec or alt > max_bb:
        return [rec]
    return [rec, alt]


def _inject_two_sizes(spot: Spot) -> Spot:
    """Graded-spot rewrite (N3, the refuter-HIGH fix): for a preflop open/3-bet
    node, replace the single RAISE LegalAction with the two sizes from
    `_preflop_two_sizes` so grade() can classify the size. Scoped to this call
    site (apply_hero_action) ONLY — the chart/hero-size map_decision_point calls
    stay single-RAISE, and Practice's build_spot path is untouched. Leaves the
    spot unchanged for VS_3BET+/non-preflop/unmapped, and for the short-stack
    single-fallback case (helper returns one size)."""
    if spot.street is not Street.PREFLOP or not spot.node_context:
        return spot
    node = spot.node_context[0]
    if node not in _TWO_SIZE_PREFLOP_NODES:
        return spot
    raise_la = next((la for la in spot.legal_actions if la.action is ActionType.RAISE), None)
    if raise_la is None or raise_la.min_bb is None or raise_la.max_bb is None:
        return spot
    entry = _find_entry(node, spot.hero.position, spot.facing)
    if entry is None or entry.sizing_bb is None:
        return spot
    sizes = _preflop_two_sizes(entry.sizing_bb, raise_la.min_bb, raise_la.max_bb, node)
    if len(sizes) < 2:
        return spot
    raises = [raise_la.model_copy(update={"min_bb": s, "size_bb": s}) for s in sizes]
    # Preserve original ordering: the two raises take the single RAISE's slot.
    rebuilt: list[LegalAction] = []
    inserted = False
    for la in spot.legal_actions:
        if la.action is ActionType.RAISE:
            if not inserted:
                rebuilt.extend(raises)
                inserted = True
            continue
        rebuilt.append(la)
    return spot.model_copy(update={"legal_actions": rebuilt})


def _hero_open_or_3bet_legal_actions(la: LegalAction, state) -> list[LegalAction]:
    """Two RAISE options (recommended + bigger alt) for an open/3-bet node, via
    the SAME `_preflop_two_sizes` helper the graded-spot rewrite uses — so the
    displayed sizes equal the graded sizes. Falls back to one RAISE (single-size)
    when the pair can't be made distinct. `size_bb` carries the offered size."""
    recommended = _hero_preflop_size_bb(state)
    if recommended is None or la.min_bb is None or la.max_bb is None:
        return [la]
    node = _hero_preflop_node(state)
    if node is None:
        return [la]
    sizes = _preflop_two_sizes(recommended, la.min_bb, la.max_bb, node)
    return [la.model_copy(update={"size_bb": s}) for s in sizes]


def _hero_preflop_node(state) -> NodeContext | None:
    """The two-size preflop node for hero's turn, or None when this isn't one of
    RFI/VS_RFI/BLIND_DEFENSE (VS_3BET+/unmapped ⇒ single size)."""
    spot = map_decision_point(state, HERO_SEAT)
    if spot is None or not spot.node_context:
        return None
    node = spot.node_context[0]
    return node if node in _TWO_SIZE_PREFLOP_NODES else None


def _hero_legal_actions(state) -> list[LegalAction]:
    """Legal actions for hero's turn, with a realistic `size_bb` suggestion set
    on each BET/RAISE (R2). Clamped legal; None (unmapped) ⇒ FE uses min_bb.

    R3: the flop c-bet is special-cased to TWO BET `LegalAction`s (fixed
    0.33/0.75 pot pair) instead of one — see `_hero_cbet_legal_actions`.
    N4a: turn/river barrels likewise offer TWO BET sizes (RES-B 0.5/0.75,
    0.5/1.0 pot), gated on the barrel mapper being non-None so display == grade.
    """
    legal = legal_actions(state)
    out: list[LegalAction] = []
    for la in legal:
        if la.action is ActionType.BET and _is_flop_cbet_node(state, legal):
            out.extend(_hero_cbet_legal_actions(la, state))
            continue
        if la.action is ActionType.BET and _is_turn_barrel_node(state):
            out.extend(_barrel_two_sizes(la, state, "turn"))
            continue
        if la.action is ActionType.BET and _is_river_barrel_node(state):
            out.extend(_barrel_two_sizes(la, state, "river"))
            continue
        if la.action is ActionType.RAISE and state.street is not Street.PREFLOP:
            # N4b: facing a bet/check-raise at a mapped node → the graded spot's
            # own RAISE legs become the offered sizes (display == grade).
            fspot = _facing_raise_spot(state)
            if fspot is not None:
                out.extend(_facing_raise_legal_actions(la, fspot))
                continue
        if (
            la.action is ActionType.RAISE
            and state.street is Street.PREFLOP
            and _hero_preflop_node(state) is not None
        ):
            out.extend(_hero_open_or_3bet_legal_actions(la, state))
            continue
        if la.action in (ActionType.BET, ActionType.RAISE):
            raw = (
                _hero_preflop_size_bb(state)
                if state.street is Street.PREFLOP
                else _hero_postflop_size_bb(state, la, legal)
            )
            if raw is not None and la.min_bb is not None and la.max_bb is not None:
                size = round(min(max(raw, la.min_bb), la.max_bb), 2)
                out.append(la.model_copy(update={"size_bb": size}))
                continue
        out.append(la)
    return out


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
    # R1: when the hero folded this hand, villains stay FACE-DOWN — no auto-reveal,
    # even if the villains ran a genuine showdown among themselves. The hero reveals
    # them on demand via the reveal endpoint. A hero-in showdown (hero IN/ALLIN)
    # auto-reveals exactly as before; `settle()` is untouched.
    if state.hand_over and hero_state.status is not PlayerStatus.FOLDED:
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
            legal_actions=_hero_legal_actions(state) if is_hero_turn else [],
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
    if spot is not None:
        spot = _inject_two_sizes(spot)
    result = None
    if spot is not None:
        result = await _grading_provider().evaluate(spot, decision)
    sim_row = _sim_decision_row(
        session, hand, state.street.value, len(prior), decision, result,
        spot=spot, hero_position=state.seats[HERO_SEAT].position.value,
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


_POSTFLOP_STREETS = (Street.FLOP, Street.TURN, Street.RIVER)


def _postflop_node_label(spot: Spot) -> str:
    ctx = spot.node_context[0]
    pos = spot.hero.position.value
    facing = spot.facing.value if spot.facing is not None else "?"
    if ctx is NodeContext.CBET:
        return f"{pos} flop c-bet vs {facing}"
    if ctx is NodeContext.TURN_BARREL:
        return f"{pos} turn barrel vs {facing}"
    if ctx is NodeContext.RIVER_BARREL:
        return f"{pos} river barrel vs {facing}"
    if ctx is NodeContext.VS_TURN_BET:
        return f"{pos} vs {facing} turn bet"
    if ctx is NodeContext.VS_RIVER_BET:
        return f"{pos} vs {facing} river bet"
    return f"{pos} {ctx.value}"  # future postflop contexts: honest fallback


async def postflop_chart(
    db: Session, session_id: str, owner_id: str = ""
) -> PostflopChartView:
    """Read-only: the grader's action mix for the hero's CURRENT postflop
    decision (R5). available=false when it is not the hero's postflop turn,
    the hand is over, or the decision point is unmappable — chart availability
    ≡ gradeability (same map_decision_point gate), never a fabricated mix.

    The actions are the SHARED provider singleton's `optimal(spot).per_action`
    — the exact output `apply_hero_action`'s evaluate() grades with (chart ==
    grader by construction; frequencies are never re-derived here). Writes
    NOTHING: no sim_decision, no DrillAttempt."""
    session = _get_session(db, session_id, owner_id)
    if session is None:
        raise SessionNotFound(session_id)
    hand = _current_hand(db, session)
    if hand is None or hand.state_json is None:
        return PostflopChartView(available=False)
    state = HandState.model_validate_json(hand.state_json)
    if (
        state.hand_over
        or state.street not in _POSTFLOP_STREETS
        or state.to_act_seat != HERO_SEAT
    ):
        return PostflopChartView(available=False)
    spot = map_decision_point(state, HERO_SEAT)
    if spot is None:
        return PostflopChartView(available=False)
    result = await _grading_provider().optimal(spot)
    if result.coverage is Coverage.NOT_FOUND:
        return PostflopChartView(available=False)  # never render a fabricated mix
    cat = _hand_category(spot.hero.hole_cards, spot.board)
    if spot.street is Street.RIVER:
        # Busted-draw demotion (S7): the river graders never emit a "draw" row.
        cat = _river_cat_effective(cat)
    return PostflopChartView(
        available=True,
        node_label=_postflop_node_label(spot),
        hand_category=cat,
        actions=[
            PostflopChartAction(
                action=a.action.value,
                size_bb=a.size_bb,
                frequency=a.frequency,
                ev_bb=a.ev_bb,
            )
            for a in result.per_action
        ],
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


def reveal(
    db: Session,
    session_id: str,
    scope: str,
    owner_id: str = "",
) -> RevealView:
    """On-demand reveal of the just-completed hand's villain cards after a hero
    fold (R1). Sourced from the completed hand's `state_json` (all 9 seats' hole
    cards); the hero is always excluded (hero folded, hero cards already ship on
    `Hero`). Reveal buttons fire BEFORE `deal_next_hand` advances `hand_no`, so
    the session's current hand IS the just-completed one.

    available=false (200 body, no seats) when: the reveal capability is off, the
    scope is unknown, no completed hand exists, or the hero did NOT fold this
    hand (a genuine showdown auto-reveals via `_view`, so there is nothing to
    reveal here). 404 stays reserved for SessionNotFound.

    scope 'last-in' = non-hero seats still IN/ALLIN at hand end (the lone winner
    on a fold-out, or the villain-vs-villain showdown participants);
    'all' = every non-hero seat dealt into the hand.
    """
    session = _get_session(db, session_id, owner_id)
    if session is None:
        raise SessionNotFound(session_id)
    if not REVEAL_ENABLED or scope not in _REVEAL_SCOPES:
        return RevealView(available=False, scope=scope)
    hand = _current_hand(db, session)
    if hand is None or hand.state_json is None or hand.status != "complete":
        return RevealView(available=False, scope=scope)
    state = HandState.model_validate_json(hand.state_json)
    if state.seats[HERO_SEAT].status is not PlayerStatus.FOLDED:
        # Hero reached showdown / won — auto-reveal already handled it.
        return RevealView(available=False, scope=scope)
    seats = [
        RevealedSeatView(seat_index=i, hole_cards=eng.hole_cards)
        for i, eng in enumerate(state.seats)
        if i != HERO_SEAT
        and (
            scope == "all"
            or eng.status in (PlayerStatus.IN, PlayerStatus.ALLIN)
        )
    ]
    return RevealView(available=True, scope=scope, seats=seats)


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
