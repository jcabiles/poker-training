"""R5 — turn/river spot mappers (`grade_map_postflop`) + dispatcher + wire.

Per-mapper multi-street gate matrix (spec §4a): every off-size / not-called /
multiway / off-line branch returns None; the one canonical HU continuation
shape (canonical open + BB call, canonical flop c-bet + call, [canonical turn
barrel + call,] check to hero / bet at hero) returns a correctly-tagged Spot
whose ranges match the equivalent `scenarios.py` builder. Wire: a live
turn/river hero decision now persists a graded `sim_decision` verdict + a
sim-tagged DrillAttempt (never via record_attempt/SRS).
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
    build_river_barrel_spot,
    build_turn_barrel_spot,
    build_vs_river_bet_spot,
    build_vs_turn_bet_spot,
)
from app.domain.spot import ActionType, NodeContext, Position, Street
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, apply, start_hand
from app.domain.table.grade_map import map_decision_point
from app.services.sim_session import apply_hero_action

HERO_SEAT = 0
_BLINDS = {Position.SB, Position.BB}
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
    for pos, dec in moves:
        seat = next(s.seat for s in state.seats if s.position is pos)
        assert state.to_act_seat == seat, f"expected {pos} to act"
        state = apply(state, dec)
    return state


def _fold(pos: Position) -> tuple[Position, Decision]:
    return (pos, Decision(action=ActionType.FOLD))


def _check(pos: Position) -> tuple[Position, Decision]:
    return (pos, Decision(action=ActionType.CHECK))


def _call(pos: Position) -> tuple[Position, Decision]:
    return (pos, Decision(action=ActionType.CALL))


def _bet(pos: Position, size: float) -> tuple[Position, Decision]:
    return (pos, Decision(action=ActionType.BET, size_bb=size))


def _before(pos: Position) -> list[Position]:
    return _SEAT_ORDER[: _SEAT_ORDER.index(pos)]


# --- canonical line builders (opener = the non-BB seat, BB the lone caller) ---


def _srp_flop(opener: Position, osize: float | None = None) -> HandState:
    """Preflop: opener raises `osize` (default canonical), only the BB calls.
    Play stops at the flop with the BB to act."""
    osize = osize if osize is not None else _OPEN_SIZE[opener]
    state = _state(opener if opener is not Position.BB else Position.BB)
    # Hero seat 0 sits at `hero_pos` of _state's arg; for BB-hero lines the
    # caller passes the OPENER here and re-seats via _srp_flop_bb below.
    moves = [_fold(p) for p in _before(opener) if p not in _BLINDS]
    moves.append((opener, Decision(action=ActionType.RAISE, size_bb=osize)))
    moves += [
        _fold(p)
        for p in _SEAT_ORDER[_SEAT_ORDER.index(opener) + 1 :]
        if p not in _BLINDS
    ]
    moves += [_fold(Position.SB), _call(Position.BB)]
    return _play(state, moves)


def _srp_flop_bb(opener: Position, osize: float | None = None) -> HandState:
    """Same line but the HERO (seat 0) is the BB."""
    osize = osize if osize is not None else _OPEN_SIZE[opener]
    state = _state(Position.BB)
    moves = [_fold(p) for p in _before(opener) if p not in _BLINDS]
    moves.append((opener, Decision(action=ActionType.RAISE, size_bb=osize)))
    moves += [
        _fold(p)
        for p in _SEAT_ORDER[_SEAT_ORDER.index(opener) + 1 :]
        if p not in _BLINDS
    ]
    moves += [_fold(Position.SB), _call(Position.BB)]
    return _play(state, moves)


def _flop_pot(opener: Position) -> float:
    return round(2 * _OPEN_SIZE[opener] + 0.5, 2)


def _turn_barrel_state(
    hero_pos: Position, cbet_frac: float = 0.33, cbet_override: float | None = None
) -> HandState:
    """Hero opened, c-bet the flop (called), BB checks the turn to the hero."""
    state = _srp_flop(hero_pos)
    fp = _flop_pot(hero_pos)
    cbet = cbet_override if cbet_override is not None else round(cbet_frac * fp, 1)
    return _play(
        state,
        [
            _check(Position.BB),
            _bet(hero_pos, cbet),
            _call(Position.BB),
            _check(Position.BB),  # turn
        ],
    )


def _vs_turn_bet_state(
    opener: Position, tbet_frac: float = 0.33, tbet_override: float | None = None
) -> HandState:
    """Hero = BB defender; opener c-bet (hero called) and now bets the turn."""
    state = _srp_flop_bb(opener)
    fp = _flop_pot(opener)
    cbet = round(0.33 * fp, 1)
    turn_pot = round(fp + 2 * cbet, 2)
    tbet = tbet_override if tbet_override is not None else round(tbet_frac * turn_pot, 1)
    return _play(
        state,
        [
            _check(Position.BB),
            _bet(opener, cbet),
            _call(Position.BB),
            _check(Position.BB),  # turn
            _bet(opener, tbet),
        ],
    )


def _river_barrel_state(
    hero_pos: Position, tbet_override: float | None = None
) -> HandState:
    """Hero opened, c-bet + barreled (both called); BB checks the river."""
    state = _turn_barrel_state(hero_pos)
    fp = _flop_pot(hero_pos)
    cbet = round(0.33 * fp, 1)
    turn_pot = round(fp + 2 * cbet, 2)
    tbet = tbet_override if tbet_override is not None else round(0.33 * turn_pot, 1)
    return _play(
        state,
        [
            _bet(hero_pos, tbet),
            _call(Position.BB),
            _check(Position.BB),  # river
        ],
    )


def _vs_river_bet_state(
    opener: Position, rbet_override: float | None = None
) -> HandState:
    """Hero = BB who called flop + turn; opener now bets the river."""
    state = _vs_turn_bet_state(opener)
    fp = _flop_pot(opener)
    cbet = round(0.33 * fp, 1)
    turn_pot = round(fp + 2 * cbet, 2)
    tbet = round(0.33 * turn_pot, 1)
    river_pot = round(turn_pot + 2 * tbet, 2)
    rbet = rbet_override if rbet_override is not None else round(0.33 * river_pot, 1)
    return _play(
        state,
        [
            _call(Position.BB),  # hero calls the turn barrel
            _check(Position.BB),  # river
            _bet(opener, rbet),
        ],
    )


# --------------------------------------------------- canonical shapes map


@pytest.mark.parametrize("hero_pos", [Position.UTG, Position.CO, Position.BTN])
@pytest.mark.parametrize("frac", [0.33, 0.75])
def test_turn_barrel_maps_with_builder_ranges(hero_pos, frac):
    state = _turn_barrel_state(hero_pos, cbet_frac=frac)
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    built = build_turn_barrel_spot(
        random.Random(0), pairing=(hero_pos, Position.BB), eff_bb=100.0
    )
    assert spot.hero_range == built.hero_range
    assert spot.villain_range == built.villain_range
    assert spot.facing == built.facing == Position.BB
    assert spot.node_context == [NodeContext.TURN_BARREL]
    # Live-state truthfulness: real board/cards/pot, builder sizing buckets.
    assert spot.street is Street.TURN
    assert spot.board == state.board and len(spot.board) == 4
    assert spot.hero.hole_cards == state.seats[HERO_SEAT].hole_cards
    fp = _flop_pot(hero_pos)
    cbet = round(frac * fp, 1)
    pot = round(fp + 2 * cbet, 2)
    assert spot.pot_bb == pot
    assert [(la.action, la.min_bb) for la in spot.legal_actions] == [
        (ActionType.CHECK, None),
        (ActionType.BET, round(0.33 * pot, 1)),
        (ActionType.BET, round(0.75 * pot, 1)),
    ]


@pytest.mark.parametrize("opener", [Position.UTG, Position.CO, Position.BTN])
@pytest.mark.parametrize("frac", [0.33, 0.75])
def test_vs_turn_bet_maps_with_builder_ranges(opener, frac):
    state = _vs_turn_bet_state(opener, tbet_frac=frac)
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    built = build_vs_turn_bet_spot(
        random.Random(0), pairing=(opener, Position.BB), eff_bb=100.0
    )
    assert spot.hero_range == built.hero_range  # BB blind-defense call range
    assert spot.villain_range == built.villain_range  # opener RFI raise range
    assert spot.facing == built.facing == opener
    assert spot.node_context == [NodeContext.VS_TURN_BET]
    fp = _flop_pot(opener)
    cbet = round(0.33 * fp, 1)
    turn_pot = round(fp + 2 * cbet, 2)
    tbet = round(frac * turn_pot, 1)
    assert spot.pot_bb == round(turn_pot + tbet, 2)  # pot INCLUDES the turn bet
    assert [(la.action, la.min_bb) for la in spot.legal_actions] == [
        (ActionType.FOLD, None),
        (ActionType.CALL, tbet),
        (ActionType.RAISE, round(3 * tbet, 1)),
    ]


@pytest.mark.parametrize("hero_pos", [Position.UTG, Position.CO, Position.BTN])
def test_river_barrel_maps_with_builder_ranges(hero_pos):
    state = _river_barrel_state(hero_pos)
    assert state.street is Street.RIVER and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    built = build_river_barrel_spot(
        random.Random(0), pairing=(hero_pos, Position.BB), eff_bb=100.0
    )
    assert spot.hero_range == built.hero_range
    assert spot.villain_range == built.villain_range
    assert spot.facing == built.facing == Position.BB
    assert spot.node_context == [NodeContext.RIVER_BARREL]
    assert spot.street is Street.RIVER
    assert spot.board == state.board and len(spot.board) == 5


@pytest.mark.parametrize("opener", [Position.UTG, Position.CO, Position.BTN])
def test_vs_river_bet_maps_with_builder_ranges(opener):
    state = _vs_river_bet_state(opener)
    assert state.street is Street.RIVER and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    built = build_vs_river_bet_spot(
        random.Random(0), pairing=(opener, Position.BB), eff_bb=100.0
    )
    assert spot.hero_range == built.hero_range
    assert spot.villain_range == built.villain_range
    assert spot.facing == built.facing == opener
    assert spot.node_context == [NodeContext.VS_RIVER_BET]
    fp = _flop_pot(opener)
    cbet = round(0.33 * fp, 1)
    turn_pot = round(fp + 2 * cbet, 2)
    tbet = round(0.33 * turn_pot, 1)
    river_pot = round(turn_pot + 2 * tbet, 2)
    rbet = round(0.33 * river_pot, 1)
    assert spot.pot_bb == round(river_pot + rbet, 2)
    assert [(la.action, la.min_bb) for la in spot.legal_actions] == [
        (ActionType.FOLD, None),
        (ActionType.CALL, rbet),
        (ActionType.RAISE, round(3 * rbet, 1)),
    ]


# ------------------------------------------------ gate matrix: turn → None


def test_off_size_flop_cbet_gates_turn_barrel():
    # 2.5bb on a 5.5bb pot is neither the 1.8 (0.33) nor 4.1 (0.75) bucket:
    # the flop street of the line is off-shape, so the TURN spot must not map.
    state = _turn_barrel_state(Position.BTN, cbet_override=2.5)
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_no_flop_cbet_gates_turn_barrel():
    # Flop went check-check (no c-bet at all): a delayed-barrel turn is NOT
    # the c-bet continuation line the S6 grader was built for.
    state = _srp_flop(Position.BTN)
    state = _play(
        state,
        [_check(Position.BB), _check(Position.BTN), _check(Position.BB)],  # turn
    )
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_off_size_turn_bet_gates_vs_turn_bet():
    # Canonical flop, but the opener's turn bet (2.0bb on 9.1bb) is off-bucket.
    state = _vs_turn_bet_state(Position.BTN, tbet_override=2.0)
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def _turn_after_open(osize: float) -> HandState:
    """BTN opens `osize`, BB calls; canonical 0.33 c-bet on the ACTUAL pot,
    BB calls and checks the turn."""
    state = _srp_flop(Position.BTN, osize=osize)
    fp = round(2 * osize + 0.5, 2)
    return _play(
        state,
        [
            _check(Position.BB),
            _bet(Position.BTN, round(0.33 * fp, 1)),
            _call(Position.BB),
            _check(Position.BB),  # turn
        ],
    )


def test_std_band_open_maps_turn_barrel_oversize_still_gates():
    # Refuter HIGH fix: BTN opens 3.0 (per-seat canonical is 2.5, but 3.0 is
    # inside the [min-raise 2.0 .. standard 3.0] band grade_map_preflop already
    # accepts — and it's what tag/lag/nit bots open from EVERY seat). The turn
    # barrel must now map, with pot math on the ACTUAL open.
    state = _turn_after_open(3.0)
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.TURN_BARREL]
    fp = round(2 * 3.0 + 0.5, 2)
    assert spot.pot_bb == round(fp + 2 * round(0.33 * fp, 1), 2)  # 10.7
    # A genuine oversize (station 3.5 / fish 4.0 territory) still refuses even
    # with every postflop street canonical on the actual pot.
    state = _turn_after_open(3.5)
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_multiway_turn_returns_none():
    # Three players reach the turn: HU-only mappers refuse (no baseline yet).
    state = _state(Position.BTN)
    moves = [_fold(p) for p in [Position.UTG, Position.UTG1, Position.UTG2, Position.LJ]]
    moves += [
        (Position.HJ, Decision(action=ActionType.RAISE, size_bb=2.5)),
        _fold(Position.CO),
        (Position.BTN, Decision(action=ActionType.CALL)),
        _fold(Position.SB),
        _call(Position.BB),
    ]
    state = _play(state, moves)
    # flop: checks around; turn: checks to the hero (BTN)
    state = _play(
        state,
        [
            _check(Position.BB), _check(Position.HJ), _check(Position.BTN),
            _check(Position.BB), _check(Position.HJ),
        ],
    )
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_bb_turn_lead_returns_none():
    # BB donk-leads the turn into the aggressor: not check-to-hero (barrel) and
    # the hero isn't the BB (vs-bet) — no mapper may claim it.
    state = _srp_flop(Position.BTN)
    fp = _flop_pot(Position.BTN)
    state = _play(
        state,
        [
            _check(Position.BB),
            _bet(Position.BTN, round(0.33 * fp, 1)),
            _call(Position.BB),
            _bet(Position.BB, 3.0),  # turn lead
        ],
    )
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


# ----------------------------------------------- gate matrix: river → None


def test_off_size_turn_barrel_gates_river():
    # Flop canonical, turn barrel 2.0bb (off-bucket, called): the river spot
    # must refuse even though the river street itself looks canonical.
    state = _river_barrel_state(Position.BTN, tbet_override=2.0)
    assert state.street is Street.RIVER and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_checked_through_turn_gates_river_barrel():
    # Hero c-bet the flop but checked the turn back: two streets of the
    # three-street story exist, the third is a different (ungraded) node.
    state = _turn_barrel_state(Position.BTN)
    state = _play(
        state,
        [_check(Position.BTN), _check(Position.BB)],  # turn check-back, river
    )
    assert state.street is Street.RIVER and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_off_size_river_bet_gates_vs_river_bet():
    state = _vs_river_bet_state(Position.BTN, rbet_override=2.0)
    assert state.street is Street.RIVER and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


# ------------------------------------------------------------- grade wire


@pytest.fixture
def db(tmp_path):
    url = f"sqlite:///{tmp_path / 'gmtr.db'}"
    run_migrations(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with Session(engine) as s:
        yield s


def _persist_hand(db: Session, state: HandState) -> str:
    session = SimSession(id="sess-tr", button_seat=state.button_seat, hand_no=1)
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


def test_live_turn_decision_persists_graded_verdict(db):
    session_id = _persist_hand(db, _turn_barrel_state(Position.BTN))
    view = asyncio.run(
        apply_hero_action(db, session_id, Decision(action=ActionType.CHECK))
    )
    rows = db.exec(select(SimDecision)).all()
    assert len(rows) == 1
    assert rows[0].street == "turn"
    assert rows[0].correctness in ("optimal", "acceptable", "mistake", "blunder")
    attempts = db.exec(select(DrillAttempt)).all()
    assert len(attempts) == 1
    assert attempts[0].source == "simulate"
    # Sim namespace only — NEVER spot_signature()/SRS (frozen-pin invariant).
    assert attempts[0].spot_signature == "sim:turn_barrel:BTN:BB"
    grade = view.hand.last_grade
    assert grade is not None and grade.correctness == rows[0].correctness


def test_live_river_decision_persists_graded_verdict(db):
    session_id = _persist_hand(db, _vs_river_bet_state(Position.BTN))
    asyncio.run(apply_hero_action(db, session_id, Decision(action=ActionType.FOLD)))
    rows = db.exec(select(SimDecision)).all()
    assert len(rows) == 1
    assert rows[0].street == "river"
    assert rows[0].correctness in ("optimal", "acceptable", "mistake", "blunder")
    attempts = db.exec(select(DrillAttempt)).all()
    assert len(attempts) == 1
    assert attempts[0].spot_signature == "sim:vs_river_bet:BB:BTN"


def test_off_shape_turn_decision_stays_no_baseline(db):
    # Off-size c-bet line: the widened dispatcher must NOT silently persist a
    # fabricated-texture verdict (spec refuter risk #1).
    session_id = _persist_hand(db, _turn_barrel_state(Position.BTN, cbet_override=2.5))
    asyncio.run(apply_hero_action(db, session_id, Decision(action=ActionType.CHECK)))
    rows = db.exec(select(SimDecision)).all()
    assert len(rows) == 1
    assert rows[0].coverage == "unmappable" and rows[0].correctness is None
    assert db.exec(select(DrillAttempt)).all() == []


# ------------------------------------------------- bot-driven belt (refuter)


_LATE = (Position.HJ, Position.CO, Position.BTN)


def _belt_policy(hand) -> Decision:
    """Steer hero toward the turn-barrel line through REAL persona play: open
    3.0 (the tag/lag/nit standard, NOT the 2.5 per-seat canonical) only from
    HJ/CO/BTN in an unopened, unlimped pot, c-bet the small option of the R3
    fixed pair (its size rides in min_bb == the mapper's canonical 0.33
    bucket), check everything else, fold to aggression."""
    kinds = {la.action for la in hand.legal_actions}
    if hand.street == "preflop":
        # A limper spoils the HU-SRP shape (its preflop CALL stays in history),
        # so only open a truly untouched pot.
        touched = any(s.last_action in ("raise", "call") for s in hand.seats)
        ra = next(
            (la for la in hand.legal_actions if la.action is ActionType.RAISE), None
        )
        if (
            not touched
            and ra is not None
            and hand.hero.position in _LATE
            and (ra.min_bb or 0) <= 3.0 <= (ra.max_bb or 0)
        ):
            return Decision(action=ActionType.RAISE, size_bb=3.0)
    elif hand.street == "flop":
        bets = [
            la
            for la in hand.legal_actions
            if la.action is ActionType.BET and la.min_bb is not None
        ]
        if len(bets) == 2:  # the R3 fixed 0.33/0.75 c-bet pair — take small
            return Decision(action=ActionType.BET, size_bb=min(b.min_bb for b in bets))
    if ActionType.CHECK in kinds:
        return Decision(action=ActionType.CHECK)
    return Decision(action=ActionType.FOLD)


def test_bot_driven_turn_barrel_grades_on_standard_open(db, monkeypatch):
    # Refuter HIGH belt: end-to-end proof the turn-barrel coverage fires
    # ORGANICALLY — hero opens the 3.0 standard from a late seat (bots open a
    # fixed persona open_bb from every seat, never the 2.5 per-seat canonical,
    # so the pre-fix exact-2.5 gate zeroed HJ/CO/BTN turn/river coverage), a
    # REAL persona BB flat-calls preflop, check-calls the flop c-bet and checks
    # the turn — engine, personas, service wire all real; only the entropy is
    # pinned (same pattern as test_grade_map.py's bot-driven belt, PLUS
    # secrets.randbelow: the initial button seat is the one entropy source that
    # belt missed, which made its hand offsets drift run-to-run). Fully pinned,
    # the clean BB-flat line lands deterministically at hand ~505 of this
    # stream (BB flats of a late open are rare in this limpy lineup — most
    # opens get spoiled by cold-callers).
    from app.services import sim_session as svc
    from app.services.sim_session import create_session, deal_next_hand

    rng_seeds = iter(range(100_000))
    deal_seeds = iter(range(500_000, 600_000))
    monkeypatch.setattr(svc, "_fresh_rng", lambda: random.Random(next(rng_seeds)))
    monkeypatch.setattr(svc.secrets, "randbits", lambda _bits: next(deal_seeds))
    monkeypatch.setattr(svc.secrets, "randbelow", lambda _n: 0)

    view = create_session(db)
    for _ in range(600):
        while not view.hand.hand_over:
            view = asyncio.run(
                apply_hero_action(db, view.session_id, _belt_policy(view.hand))
            )
        hits = [
            a.spot_signature
            for a in db.exec(select(DrillAttempt)).all()
            if a.source == "simulate"
            and a.spot_signature.startswith("sim:turn_barrel:")
        ]
        if hits:
            # Hero only ever opens from HJ/CO/BTN, so any hit IS a late-seat
            # 3.0 open — the exact shape the pre-fix gate could never map.
            assert all(h.split(":")[2] in {"HJ", "CO", "BTN"} for h in hits)
            return
        view = deal_next_hand(db, view.session_id)
    raise AssertionError(
        "no bot-driven turn-barrel decision graded in 600 hands "
        "(open-size band regression in grade_map_postflop?)"
    )
