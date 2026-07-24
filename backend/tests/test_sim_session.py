"""S9 session-service tests: play/fold/restore/rebuy/ledger/reproducibility +
per-decision parity between `app.domain.table.play` and the S4 harness
(`tests/test_personas_postflop.py`). Spec: docs/ai-dlc/specs/simulate-s9.md.
"""

from __future__ import annotations

import asyncio
import random

import pytest
import test_grade_map  # _cbet_state helper reference (flop c-bet HandState builder)
import test_personas_postflop as harness  # per-decision parity reference
from sqlmodel import Session, create_engine, select

from app.db.migrate import run_migrations
from app.db.models import SimHand, SimSeat
from app.domain.action import Decision
from app.domain.archetypes import VillainType
from app.domain.personas import load_persona_packs
from app.domain.scenarios import _find_entry
from app.domain.spot import ActionType, NodeContext, Position, Street
from app.domain.table import play
from app.domain.table.deck import deal_hand
from app.domain.table.engine import (
    HandState,
    PlayerStatus,
    SeatDelta,
    Settlement,
    apply,
    start_hand,
)
from app.domain.table.engine import legal_actions as engine_legal_actions
from app.domain.table.grade_map import map_decision_point
from app.services import sim_session
from app.services.sim_session import (
    SessionNotFound,
    create_session,
    deal_next_hand,
    leave_session,
    restore_session,
    reveal,
)


def apply_hero_action(*args, **kwargs):
    """Sync driver: S10 made the service async (it awaits the grading
    provider); these S9 tests still exercise it synchronously."""
    return asyncio.run(sim_session.apply_hero_action(*args, **kwargs))


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
            # Settlement must award the pot to at least one showdown seat, so
            # some seat comes out non-negative. `>= 0`, not `> 0`: a legitimate
            # board-plays chop (equal investment, no dead money) settles every
            # showdown seat to exactly 0.0 — a real outcome, not a bug. Using
            # `> 0` made this rarely flake on chopped-pot draws.
            assert any(d >= 0 for d in deltas.values())
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
            # R2: play.bot_decision now sizes bets from the persona levers /
            # node-aware distribution, while the harness mirror stays on the
            # min-raise / flat sizing that anchors the statistical bands — so
            # the two INTENTIONALLY diverge on bet SIZE. The decision LOGIC
            # (which action is chosen) must still match exactly; size
            # correctness is covered by test_bet_sizing.py.
            assert got.action == expected.action, (
                f"action parity break: hand_seed={hand_seed} guard={guard} seat={seat}"
            )
            checked += 1
            state = apply(state, got)
    assert checked > 50  # enough decisions across preflop + postflop streets


def test_hero_open_size_is_content_sizing_not_min_raise():
    # R2: hero's predetermined open size = the content rfi `sizing_bb` for its
    # seat (the baseline grading uses), NOT the engine min-raise.
    state = None
    for btn in range(9):  # find the button that makes hero (seat 0) UTG opener
        s = start_hand(deal_hand(random.Random(7)), button_seat=btn, stacks_bb=[100.0] * 9)
        if s.to_act_seat == 0 and s.street is Street.PREFLOP:
            state = s
            break
    assert state is not None
    hero_pos = state.seats[0].position
    legal = sim_session._hero_legal_actions(state)
    raise_la = next(la for la in legal if la.action is ActionType.RAISE)
    entry = _find_entry(NodeContext.RFI, hero_pos, None)
    expected = round(min(max(entry.sizing_bb, raise_la.min_bb), raise_la.max_bb), 2)
    assert raise_la.size_bb == expected
    assert raise_la.size_bb != raise_la.min_bb  # realistic, not the min-raise
    assert raise_la.min_bb <= raise_la.size_bb <= raise_la.max_bb  # legal


# --------------------------------------- R3: flop c-bet two bet sizes


def _flop_cbet_bets(state) -> list:
    legal = sim_session._hero_legal_actions(state)
    return [la for la in legal if la.action is ActionType.BET]


def test_flop_cbet_offers_two_distinct_bet_sizes():
    state = test_grade_map._cbet_state(Position.BTN)
    bets = _flop_cbet_bets(state)
    assert len(bets) == 2
    pot_bb = sum(s.invested_total_bb for s in state.seats)
    assert bets[0].min_bb == round(0.33 * pot_bb, 1)
    assert bets[1].min_bb == round(0.75 * pot_bb, 1)
    assert bets[0].min_bb != bets[1].min_bb


def test_flop_cbet_wet_and_mono_boards_stay_distinct():
    # Regression (refuter HIGH): sizing off `HERO_NODE_SIZE[node]` alone would
    # collapse small==big on these textures (both node baselines are 0.75/0.33
    # single fractions) — the fixed 0.33/0.75 PAIR must stay distinct regardless.
    from app.domain.texture import classify

    wet = ["Jh", "Th", "9d"]  # two-tone, connected -> wet, not monotone
    mono = ["Kh", "7h", "2h"]  # monotone
    assert classify(wet).wetness == "wet" and classify(wet).suitedness != "monotone"
    assert classify(mono).suitedness == "monotone"
    for board in (wet, mono):
        state = test_grade_map._cbet_state(Position.BTN)
        state.board = board
        state.full_board = board + state.full_board[3:]
        bets = _flop_cbet_bets(state)
        assert len(bets) == 2, f"expected two BET legs for board {board}"
        assert bets[0].min_bb != bets[1].min_bb, f"sizes collapsed for board {board}"


def test_flop_cbet_displayed_sizes_match_graded_spot_sizes():
    # Parity (refuter LOW): the LIVE legal_actions sizes the FE shows must
    # equal the sizes the graded Spot (map_flop_cbet) carries, same 1dp round.
    state = test_grade_map._cbet_state(Position.BTN)
    displayed = _flop_cbet_bets(state)
    spot = map_decision_point(state, sim_session.HERO_SEAT)
    assert spot is not None
    graded = [la for la in spot.legal_actions if la.action is ActionType.BET]
    assert [la.min_bb for la in displayed] == [la.min_bb for la in graded]


def test_flop_cbet_non_cbet_node_keeps_single_bet_size():
    # A non-c-bet postflop BET (turn barrel, or a flop donk/lead where hero is
    # NOT the aggressor) is untouched — single size, as before R3.
    state = test_grade_map._cbet_state(Position.BTN)
    assert state.street is Street.FLOP and state.to_act_seat == sim_session.HERO_SEAT

    legal = engine_legal_actions(state)
    assert sim_session._is_flop_cbet_node(state, legal)  # sanity: flop IS the c-bet node

    # Flip the aggressor flag to simulate a donk/lead node on the SAME flop
    # shape (hero not the aggressor) — postflop_node_key must return "flat".
    from app.domain.table.sizing import postflop_node_key

    node = postflop_node_key(state.board, legal, is_aggressor=False)
    assert node == "flat"

    # Advance past the flop c-bet to the turn: BTN barrels, BB calls.
    bet_leg = next(a for a in legal if a.action is ActionType.BET)
    state = apply(state, Decision(action=ActionType.BET, size_bb=bet_leg.min_bb))
    state = apply(state, Decision(action=ActionType.CALL))
    assert state.street is Street.TURN
    guard = 0
    while state.to_act_seat != sim_session.HERO_SEAT and not state.hand_over:
        guard += 1
        assert guard < 10
        acts = engine_legal_actions(state)
        kinds = {a.action for a in acts}
        move = ActionType.CHECK if ActionType.CHECK in kinds else ActionType.FOLD
        state = apply(state, Decision(action=move))
    assert not state.hand_over and state.street is Street.TURN
    turn_legal = sim_session._hero_legal_actions(state)
    turn_bets = [la for la in turn_legal if la.action is ActionType.BET]
    assert len(turn_bets) <= 1  # turn_barrel keeps the single-size R2 behavior


def test_flop_cbet_size_choice_grades_freq_ev_not_boolean(db):
    # Deterministic: craft the session's live hand into the canonical flop
    # c-bet shape directly (scripted, not random-play-until-we-get-lucky).
    view = create_session(db)
    state = test_grade_map._cbet_state(Position.BTN)
    session = sim_session._get_session(db, view.session_id, "")
    hand = sim_session._current_hand(db, session)
    hand.state_json = state.model_dump_json()
    hand.status = "in_progress"
    db.add(hand)
    db.commit()

    bets = _flop_cbet_bets(state)
    assert len(bets) == 2 and bets[0].min_bb != bets[1].min_bb
    after = apply_hero_action(
        db, view.session_id, Decision(action=ActionType.BET, size_bb=bets[0].min_bb)
    )
    grade = after.hand.last_grade
    assert grade is not None
    # freq+EV verdict, never a boolean: correctness is a tier label (or None
    # for no-baseline) and ev_loss_bb is always a float.
    assert grade.correctness in (None, "optimal", "acceptable", "mistake", "blunder")
    assert isinstance(grade.ev_loss_bb, float)


def test_last_action_per_street_folded_override_and_post_excluded():
    """`_last_action` (felt label): current-street verb only, folded persists,
    blind POSTs excluded, clears when the street advances. Spec:
    docs/ai-dlc/specs/simulate-seat-action-labels.md."""
    la = sim_session._last_action
    dealt = deal_hand(random.Random(7))
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)

    # Preflop, before any voluntary action: SB/BB have POSTed blinds, but POST is
    # excluded, so every seat's label is None.
    for eng in state.seats:
        assert la(state, eng) is None

    # Drive preflop: first legal raiser opens, BB (seat 2) calls, everyone else
    # folds → reaches the flop heads-up (raiser vs BB).
    raiser_seat = None
    while not state.hand_over and state.street is Street.PREFLOP:
        seat = state.to_act_seat
        acts = engine_legal_actions(state)
        kinds = {a.action for a in acts}
        if raiser_seat is None and ActionType.RAISE in kinds:
            legal = next(a for a in acts if a.action is ActionType.RAISE)
            state = apply(state, Decision(action=ActionType.RAISE, size_bb=legal.min_bb))
            raiser_seat = seat
        elif seat == 2 and ActionType.CALL in kinds:
            state = apply(state, Decision(action=ActionType.CALL))
        else:
            state = apply(state, Decision(action=ActionType.FOLD))

    assert state.street is Street.FLOP
    assert raiser_seat is not None

    # Per-street clear: the preflop raise does NOT bleed onto the flop.
    assert la(state, state.seats[raiser_seat]) is None
    assert la(state, state.seats[2]) is None  # BB called preflop; cleared on flop
    # Folded override: a seat that folded PREFLOP still reads "fold" on the flop.
    folded = next(s for s in state.seats if s.status.value == "folded")
    assert la(state, folded) == "fold"

    # A current-street action shows its verb immediately.
    seat = state.to_act_seat
    acts = engine_legal_actions(state)
    kinds = {a.action for a in acts}
    if ActionType.CHECK in kinds:
        state = apply(state, Decision(action=ActionType.CHECK))
        assert la(state, state.seats[seat]) == "check"
    else:
        legal = next(a for a in acts if a.action is ActionType.BET)
        state = apply(state, Decision(action=ActionType.BET, size_bb=legal.min_bb))
        assert la(state, state.seats[seat]) == "bet"


# ------------------------------------------------------- R1: reveal hands
# Bots act via a non-seeded fresh RNG (sim_session._fresh_rng), so a hero-fold-
# then-villain-showdown line can't be reproduced deterministically through play.
# Per the R1 spec's test-determinism note, craft a completed HandState directly.


def _terminal_state(hero: str = "fold", in_seats=(1, 2), allin_seats=()) -> HandState:
    """A completed river HandState. Every seat FOLDED except: the hero (per
    `hero`: 'fold' | 'in'), the `in_seats` (left IN), and `allin_seats` (ALLIN).
    Non-folded seats carry investment so settle() forms a real (showdown) pot."""
    st = start_hand(deal_hand(random.Random(7)), 0, [100.0] * 9)
    st.street = Street.RIVER
    st.board = list(st.full_board)
    st.to_act_seat = None
    st.hand_over = True
    for s in st.seats:
        s.status = PlayerStatus.FOLDED
        s.invested_street_bb = 0.0
        s.invested_total_bb = 0.0
    st.seats[0].status = PlayerStatus.FOLDED if hero == "fold" else PlayerStatus.IN
    if hero == "in":
        st.seats[0].invested_total_bb = 5.0
    for i in in_seats:
        st.seats[i].status = PlayerStatus.IN
        st.seats[i].invested_total_bb = 5.0
    for i in allin_seats:
        st.seats[i].status = PlayerStatus.ALLIN
        st.seats[i].invested_total_bb = 5.0
    return st


def _write_terminal(db, session_id: str, state: HandState):
    """Overwrite the session's current hand with a crafted completed state."""
    session = sim_session._get_session(db, session_id, "")
    hand = sim_session._current_hand(db, session)
    hand.state_json = state.model_dump_json()
    hand.status = "complete"
    db.add(hand)
    db.commit()


def test_hero_fold_villain_showdown_autoreveals_compared_hands(db):
    # Hero folded; villains 1 & 2 ran a genuine showdown among themselves.
    state = _terminal_state(hero="fold", in_seats=(1, 2))
    view = create_session(db)
    _write_terminal(db, view.session_id, state)
    restored = restore_session(db, view.session_id)

    seats = {sd.seat_index for sd in restored.hand.showdown}
    assert seats == {1, 2}
    shown_cards = {
        card
        for sd in restored.hand.showdown
        for card in sd.hole_cards
    }
    for i in (1, 2):
        assert set(state.seats[i].hole_cards).issubset(shown_cards)
    assert all(sd.seat_index != 0 for sd in restored.hand.showdown)

    # Privacy sweep: folded villains that did not reach showdown still do not
    # leak through the normal hand view's only villain-card field.
    for i in range(3, 9):
        for card in state.seats[i].hole_cards:
            assert card not in shown_cards, f"seat {i} card {card} leaked to showdown"
    # Hero's own cards still ship (allowed).
    assert restored.hand.hero.hole_cards == state.seats[0].hole_cards


def test_hero_in_showdown_still_autoreveals(db):
    # Regression: a genuine hero-in showdown auto-reveals exactly as before.
    state = _terminal_state(hero="in", in_seats=(2,))
    view = create_session(db)
    _write_terminal(db, view.session_id, state)
    restored = restore_session(db, view.session_id)
    seats = {sd.seat_index for sd in restored.hand.showdown}
    assert seats == {0, 2}  # hero + the villain compared


def test_reveal_last_in_returns_only_live_seats(db):
    # Hero folded; seats 1,2 IN and seat 3 ALLIN at end; 4-8 folded.
    state = _terminal_state(hero="fold", in_seats=(1, 2), allin_seats=(3,))
    view = create_session(db)
    _write_terminal(db, view.session_id, state)
    result = reveal(db, view.session_id, "last-in")
    assert result.available
    assert {s.seat_index for s in result.seats} == {1, 2, 3}
    assert all(len(s.hole_cards) == 2 for s in result.seats)


def test_reveal_all_returns_every_nonhero_seat(db):
    state = _terminal_state(hero="fold", in_seats=(1, 2), allin_seats=(3,))
    view = create_session(db)
    _write_terminal(db, view.session_id, state)
    result = reveal(db, view.session_id, "all")
    assert result.available
    assert {s.seat_index for s in result.seats} == set(range(1, 9))  # hero excluded


def test_reveal_available_when_hero_not_folded(db):
    # Debug reveal works on ANY completed hand, hero fold or not; the hero is
    # always excluded and last-in still means non-hero IN/ALLIN seats.
    state = _terminal_state(hero="in", in_seats=(2,))
    view = create_session(db)
    _write_terminal(db, view.session_id, state)
    last_in = reveal(db, view.session_id, "last-in")
    assert last_in.available
    assert {s.seat_index for s in last_in.seats} == {2}  # hero (seat 0) excluded
    all_seats = reveal(db, view.session_id, "all")
    assert all_seats.available
    assert {s.seat_index for s in all_seats.seats} == set(range(1, 9))


def test_reveal_unavailable_on_live_hand_and_unknown_scope(db):
    view = create_session(db)  # hand 1 is in_progress, not complete
    assert not reveal(db, view.session_id, "last-in").available
    # Unknown scope is a 200-body availability concern, never an error.
    state = _terminal_state(hero="fold", in_seats=(1, 2))
    _write_terminal(db, view.session_id, state)
    assert not reveal(db, view.session_id, "sideways").available


def test_reveal_unavailable_when_capability_off(db, monkeypatch):
    state = _terminal_state(hero="fold", in_seats=(1, 2))
    view = create_session(db)
    _write_terminal(db, view.session_id, state)
    monkeypatch.setattr(sim_session, "REVEAL_ENABLED", False)
    assert not reveal(db, view.session_id, "all").available


def test_reveal_missing_session_raises(db):
    with pytest.raises(SessionNotFound):
        reveal(db, "no-such-session", "all")
