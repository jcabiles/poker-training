"""Engine test battery for S2 — betting, side pots, showdown, chip conservation.

Authored against the frozen interface in docs/ai-dlc/specs/simulate-s2.md
(the engine, backend/app/domain/table/engine.py, is implemented by a parallel
maker to this exact spec). Tests are the executable contract: scripted
side-pot settlements assert EXACT amounts, legal-action shapes are asserted
structurally, and a random-policy playout property proves chip conservation.
"""

from __future__ import annotations

import random

import pytest

from app.domain.action import Decision
from app.domain.spot import ActionType, PlayerStatus, Street
from app.domain.table import DealtHand, deal_hand
from app.domain.table.engine import apply, legal_actions, settle, start_hand

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

RANKS = "23456789TJQKA"
SUITS = "cdhs"
_FULL_DECK = [r + s for r in RANKS for s in SUITS]


def _filler_deal(seed: int) -> DealtHand:
    """A deal_hand()-sourced DealtHand for scenarios where showdown strength
    doesn't matter (fold-out / walk / limp / illegal-action / legal-shape
    cases never reach an uncontrolled showdown in these tests).
    """
    return deal_hand(random.Random(seed))


def _crafted_deal(hole_by_seat: dict[int, tuple[str, str]], board: list[str]) -> DealtHand:
    """Build a DealtHand with explicit hole cards for named seats (showdown
    strength matters) and filler disjoint cards for the rest, so scripted
    side-pot scenarios can pin exact winners.
    """
    used = set(board)
    for a, b in hole_by_seat.values():
        used.add(a)
        used.add(b)
    filler = [c for c in _FULL_DECK if c not in used]
    hole_cards: list[tuple[str, str]] = []
    fi = 0
    for seat in range(9):
        if seat in hole_by_seat:
            hole_cards.append(hole_by_seat[seat])
        else:
            hole_cards.append((filler[fi], filler[fi + 1]))
            fi += 2
    return DealtHand(hole_cards=hole_cards, board=board)


def _act(state, seat: int, action: ActionType, size_bb: float | None = None):
    """Assert it's `seat`'s turn, then apply the decision. Returns new state."""
    assert state.to_act_seat == seat, (
        f"expected seat {seat} to act, got {state.to_act_seat}"
    )
    return apply(state, Decision(action=action, size_bb=size_bb))


def _fold_all(state, seats: list[int]):
    for s in seats:
        state = _act(state, s, ActionType.FOLD)
    return state


def _legal_shapes(state) -> list[tuple[ActionType, float | None, float | None]]:
    return [(la.action, la.min_bb, la.max_bb) for la in legal_actions(state)]


# ---------------------------------------------------------------------------
# (a) 3-way, two all-ins at different amounts + a folded seat's dead money
# ---------------------------------------------------------------------------


def test_side_pots_two_allins_different_amounts_plus_folded_dead_money():
    board = ["2c", "7d", "9h", "Jc", "4s"]
    hole = {
        0: ("As", "Ah"),  # BTN — best hand, wins both pots
        3: ("3c", "3d"),  # UTG — short all-in at 5bb, pair of 3s (worst)
        6: ("Kd", "Qd"),  # LJ — mid all-in at 15bb, king-high (loses both)
    }
    dealt = _crafted_deal(hole, board)
    stacks = [100.0, 100.0, 100.0, 5.0, 100.0, 100.0, 15.0, 100.0, 100.0]
    state = start_hand(dealt, button_seat=0, stacks_bb=stacks)

    # preflop action order: UTG(3), UTG1(4), UTG2(5), LJ(6), HJ(7), CO(8), BTN(0), SB(1), BB(2)
    state = _act(state, 3, ActionType.RAISE, 5.0)  # all-in to 5.0 (complete raise)
    state = _act(state, 4, ActionType.FOLD)
    state = _act(state, 5, ActionType.FOLD)
    state = _act(state, 6, ActionType.RAISE, 15.0)  # all-in to 15.0 (complete raise)
    state = _act(state, 7, ActionType.FOLD)
    state = _act(state, 8, ActionType.FOLD)
    state = _act(state, 0, ActionType.CALL, None)  # calls 15.0
    state = _act(state, 1, ActionType.FOLD)  # SB dead money: 0.5
    state = _act(state, 2, ActionType.FOLD)  # BB dead money: 1.0

    assert state.hand_over is True
    settlement = settle(state)

    # main pot [0,5]: everyone's contribution capped at 5 -> 0.5+1.0+5+5+5 = 16.5
    # side pot (5,15]: only seat0/seat6 contribute beyond 5 -> 10+10 = 20.0
    pot_amounts = sorted(p.amount_bb for p in settlement.pots)
    assert pot_amounts == pytest.approx([16.5, 20.0])

    by_seat = {d.seat: d.delta_bb for d in settlement.deltas}
    assert by_seat[0] == pytest.approx(21.5)  # won 36.5, invested 15.0
    assert by_seat[3] == pytest.approx(-5.0)
    assert by_seat[6] == pytest.approx(-15.0)
    assert by_seat[1] == pytest.approx(-0.5)
    assert by_seat[2] == pytest.approx(-1.0)
    for seat in (4, 5, 7, 8):
        assert by_seat[seat] == pytest.approx(0.0)
    assert sum(by_seat.values()) == pytest.approx(0.0, abs=1e-9)

    for winners in settlement.winners_by_pot:
        assert winners == [0]  # seat0 wins both pots outright


# ---------------------------------------------------------------------------
# (b) split main pot + sole side-pot winner
# ---------------------------------------------------------------------------


def test_split_main_pot_and_sole_side_pot_winner():
    board = ["9h", "4c", "2s", "Kd", "7c"]
    hole = {
        0: ("9c", "4d"),  # BTN — two pair 9s&4s, ties seat3 on main; sole side-pot winner
        3: ("9s", "4h"),  # UTG — ties seat0 on main pot (identical two pair ranks)
        6: ("Qh", "Jd"),  # LJ — king-high, loses main and side
    }
    dealt = _crafted_deal(hole, board)
    stacks = [100.0, 100.0, 100.0, 10.0, 100.0, 100.0, 100.0, 100.0, 100.0]
    state = start_hand(dealt, button_seat=0, stacks_bb=stacks)

    state = _act(state, 3, ActionType.RAISE, 10.0)  # all-in to 10.0
    state = _act(state, 4, ActionType.FOLD)
    state = _act(state, 5, ActionType.FOLD)
    state = _act(state, 6, ActionType.CALL, None)  # calls 10.0
    state = _act(state, 7, ActionType.FOLD)
    state = _act(state, 8, ActionType.FOLD)
    state = _act(state, 0, ActionType.CALL, None)  # calls 10.0
    state = _act(state, 1, ActionType.FOLD)
    state = _act(state, 2, ActionType.FOLD)

    assert state.street == Street.FLOP
    assert state.board == board[:3]

    # flop: first IN seat clockwise from SB — seat1/2 folded, seat3 is ALLIN
    # (not IN), seat4/5 folded, so seat6 acts first; seat0 (BTN) acts next.
    state = _act(state, 6, ActionType.BET, 10.0)
    state = _act(state, 0, ActionType.CALL, None)

    # seat3 is ALLIN; seat0/seat6 are still IN with chips behind, so betting
    # continues — check the turn and river down to a legitimate showdown
    # (rule 5: street only auto-advances to hand_over when <=1 IN seat can act).
    for _ in range(2):
        state = _act(state, 6, ActionType.CHECK, None)
        state = _act(state, 0, ActionType.CHECK, None)

    assert state.hand_over is True
    settlement = settle(state)

    # main pot: 3x10 preflop/flop-call layer + 1.5 dead money (SB 0.5 + BB 1.0
    # folded preflop) = 31.5, eligible seats 0/3/6 (rule 7). side pot: seat0 and
    # seat6's flop bet/call beyond seat3's 10bb cap = 2x10 = 20.0.
    pot_amounts = sorted(p.amount_bb for p in settlement.pots)
    assert pot_amounts == pytest.approx([20.0, 31.5])  # side pot, then main pot

    by_seat = {d.seat: d.delta_bb for d in settlement.deltas}
    assert by_seat[0] == pytest.approx(15.75)  # 15.75 (split main) + 20 (side) - 20 invested
    assert by_seat[3] == pytest.approx(5.75)  # 15.75 (split main) - 10 invested
    assert by_seat[6] == pytest.approx(-20.0)  # 0 won - 20 invested
    assert by_seat[1] == pytest.approx(-0.5)  # SB dead money
    assert by_seat[2] == pytest.approx(-1.0)  # BB dead money
    assert sum(by_seat.values()) == pytest.approx(0.0, abs=1e-9)

    main_pot = next(p for p in settlement.pots if p.amount_bb == pytest.approx(31.5))
    side_pot = next(p for p in settlement.pots if p.amount_bb == pytest.approx(20.0))
    main_idx = settlement.pots.index(main_pot)
    side_idx = settlement.pots.index(side_pot)
    assert sorted(settlement.winners_by_pot[main_idx]) == [0, 3]  # split
    assert settlement.winners_by_pot[side_idx] == [0]  # sole winner
    assert sorted(main_pot.eligible_seats) == [0, 3, 6]
    assert sorted(side_pot.eligible_seats) == [0, 6]


# ---------------------------------------------------------------------------
# (c) incomplete-raise: no-reopen seat gets [FOLD, CALL], never RAISE
# ---------------------------------------------------------------------------


def test_incomplete_raise_no_reopen_legal_action_shape():
    dealt = _filler_deal(seed=101)
    stacks = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 4.0, 100.0, 100.0]
    state = start_hand(dealt, button_seat=0, stacks_bb=stacks)

    state = _act(state, 3, ActionType.RAISE, 3.0)  # UTG opens to 3.0 (complete: +2.0 >= 1.0)
    assert state.min_raise_to_bb == pytest.approx(5.0)
    assert state.last_full_raise_bb == pytest.approx(2.0)

    state = _act(state, 4, ActionType.FOLD)
    state = _act(state, 5, ActionType.FOLD)
    # LJ all-in to 4.0: increment 1.0 < last_full_raise_bb 2.0 -> incomplete raise
    state = _act(state, 6, ActionType.RAISE, 4.0)
    assert state.current_bet_bb == pytest.approx(4.0)
    assert state.min_raise_to_bb == pytest.approx(5.0)  # unchanged
    assert state.last_full_raise_bb == pytest.approx(2.0)  # unchanged
    assert state.seats[6].status == PlayerStatus.ALLIN

    state = _act(state, 7, ActionType.FOLD)
    state = _act(state, 8, ActionType.FOLD)
    state = _act(state, 0, ActionType.FOLD)
    state = _act(state, 1, ActionType.FOLD)
    state = _act(state, 2, ActionType.FOLD)

    # action returns to seat3 (UTG), who already acted this street (the raise)
    # and now faces only an incomplete raise -> no RAISE offered.
    assert state.to_act_seat == 3
    shapes = _legal_shapes(state)
    actions_offered = {a for a, _, _ in shapes}
    assert actions_offered == {ActionType.FOLD, ActionType.CALL}
    call = next(la for la in legal_actions(state) if la.action == ActionType.CALL)
    assert call.min_bb == pytest.approx(1.0)  # incremental: 4.0 - 3.0

    with pytest.raises(ValueError):
        apply(state, Decision(action=ActionType.RAISE, size_bb=6.0))


# ---------------------------------------------------------------------------
# (d) fold-out: last seat wins uncalled, showdown_seats == []
# ---------------------------------------------------------------------------


def test_fold_out_last_seat_wins_uncalled_no_showdown():
    dealt = _filler_deal(seed=202)
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)

    state = _act(state, 3, ActionType.RAISE, 3.0)
    state = _fold_all(state, [4, 5, 6, 7, 8, 0, 1, 2])

    assert state.hand_over is True
    settlement = settle(state)
    assert settlement.showdown_seats == []

    by_seat = {d.seat: d.delta_bb for d in settlement.deltas}
    # seat3 wins own 3.0 back + SB 0.5 + BB 1.0 dead money = net +1.5
    assert by_seat[3] == pytest.approx(1.5)
    assert by_seat[1] == pytest.approx(-0.5)
    assert by_seat[2] == pytest.approx(-1.0)
    for seat in (0, 4, 5, 6, 7, 8):
        assert by_seat[seat] == pytest.approx(0.0)
    assert sum(by_seat.values()) == pytest.approx(0.0, abs=1e-9)
    assert settlement.winners_by_pot == [[3]]


# ---------------------------------------------------------------------------
# (e) BB walk: everyone folds to BB
# ---------------------------------------------------------------------------


def test_bb_walk_everyone_folds():
    dealt = _filler_deal(seed=303)
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)

    state = _fold_all(state, [3, 4, 5, 6, 7, 8, 0, 1])

    assert state.hand_over is True
    settlement = settle(state)
    assert settlement.showdown_seats == []
    by_seat = {d.seat: d.delta_bb for d in settlement.deltas}
    assert by_seat[2] == pytest.approx(0.5)  # wins SB's dead 0.5
    assert by_seat[1] == pytest.approx(-0.5)
    for seat in (0, 3, 4, 5, 6, 7, 8):
        assert by_seat[seat] == pytest.approx(0.0)
    assert sum(by_seat.values()) == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# (f) limped-pot BB option: [CHECK, RAISE] only — never CALL(min_bb=0), never BET
# ---------------------------------------------------------------------------


def test_limped_pot_bb_option_shape():
    dealt = _filler_deal(seed=404)
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)

    for seat in [3, 4, 5, 6, 7, 8, 0]:
        state = _act(state, seat, ActionType.CALL, None)  # limp in for 1.0
    state = _act(state, 1, ActionType.CALL, None)  # SB completes to 1.0

    assert state.to_act_seat == 2  # BB
    assert state.seats[2].invested_street_bb == pytest.approx(state.current_bet_bb)

    shapes = _legal_shapes(state)
    actions_offered = {a for a, _, _ in shapes}
    assert actions_offered == {ActionType.CHECK, ActionType.RAISE}

    raise_la = next(la for la in legal_actions(state) if la.action == ActionType.RAISE)
    assert raise_la.min_bb == pytest.approx(state.min_raise_to_bb)
    assert raise_la.min_bb <= raise_la.max_bb

    # BB checks to see the flop.
    state = _act(state, 2, ActionType.CHECK, None)
    assert state.street == Street.FLOP


# ---------------------------------------------------------------------------
# illegal-action ValueErrors
# ---------------------------------------------------------------------------


def test_illegal_action_wrong_type_for_shape_raises():
    dealt = _filler_deal(seed=505)
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)
    # UTG faces an unopened-to-them betting round with chips already in (facing
    # the BB) -> CHECK is not a legal action type here.
    with pytest.raises(ValueError):
        apply(state, Decision(action=ActionType.CHECK, size_bb=None))


def test_illegal_action_size_outside_bounds_raises():
    dealt = _filler_deal(seed=606)
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)
    raise_la = next(la for la in legal_actions(state) if la.action == ActionType.RAISE)
    with pytest.raises(ValueError):
        apply(state, Decision(action=ActionType.RAISE, size_bb=raise_la.min_bb - 0.5))
    with pytest.raises(ValueError):
        apply(state, Decision(action=ActionType.RAISE, size_bb=raise_la.max_bb + 1.0))


def test_illegal_action_size_none_on_bet_raises():
    dealt = _filler_deal(seed=707)
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)
    state = _fold_all(state, [3, 4, 5, 6, 7, 8])
    state = _act(state, 0, ActionType.CALL, None)
    state = _act(state, 1, ActionType.CALL, None)
    state = _act(state, 2, ActionType.CHECK, None)
    assert state.street == Street.FLOP
    with pytest.raises(ValueError):
        apply(
            state,
            Decision.model_construct(action=ActionType.BET, size_bb=None, size_fraction=None),
        )


def test_illegal_action_raise_by_no_reopen_seat_raises():
    dealt = _filler_deal(seed=808)
    stacks = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 4.0, 100.0, 100.0]
    state = start_hand(dealt, button_seat=0, stacks_bb=stacks)
    state = _act(state, 3, ActionType.RAISE, 3.0)
    state = _fold_all(state, [4, 5])
    state = _act(state, 6, ActionType.RAISE, 4.0)  # incomplete raise
    state = _fold_all(state, [7, 8, 0, 1, 2])
    assert state.to_act_seat == 3
    with pytest.raises(ValueError):
        apply(state, Decision(action=ActionType.RAISE, size_bb=6.0))


def test_illegal_action_act_on_finished_hand_raises():
    dealt = _filler_deal(seed=909)
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)
    state = _act(state, 3, ActionType.RAISE, 3.0)
    state = _fold_all(state, [4, 5, 6, 7, 8, 0, 1, 2])
    assert state.hand_over is True
    with pytest.raises(ValueError):
        apply(state, Decision(action=ActionType.CHECK, size_bb=None))


# ---------------------------------------------------------------------------
# chip-conservation property: >=2k random-policy playouts
# ---------------------------------------------------------------------------


def _play_random_hand(rng: random.Random, hand_seed: int, button_seat: int):
    dealt = deal_hand(random.Random(hand_seed))
    state = start_hand(dealt, button_seat=button_seat, stacks_bb=[100.0] * 9)
    guard = 0
    while not state.hand_over:
        guard += 1
        assert guard < 500, "playout did not terminate"
        actions = legal_actions(state)
        assert actions, "no legal actions offered for a seat to act"
        chosen = actions[rng.randrange(len(actions))]
        size = None
        if chosen.action in (ActionType.BET, ActionType.RAISE):
            lo, hi = chosen.min_bb, chosen.max_bb
            size = lo if lo >= hi else round(rng.uniform(lo, hi), 2)
        state = apply(state, Decision(action=chosen.action, size_bb=size))
    return state


def test_chip_conservation_random_policy_playouts():
    rng = random.Random(20260710)
    n_hands = 2000
    for i in range(n_hands):
        hand_seed = rng.randrange(1_000_000_000)
        button_seat = rng.randrange(9)
        final_state = _play_random_hand(rng, hand_seed, button_seat)
        settlement = settle(final_state)

        total = sum(d.delta_bb for d in settlement.deltas)
        assert total == pytest.approx(0.0, abs=1e-9), f"hand {i} delta sum={total}"

        invested = {s.seat: s.invested_total_bb for s in final_state.seats}
        by_seat = {d.seat: d.delta_bb for d in settlement.deltas}
        starting_stack_bb = 100.0
        for seat_state in final_state.seats:
            seat = seat_state.seat
            # no negative resulting stacks (delta_bb is net vs. the hand's starting stack)
            assert starting_stack_bb + by_seat[seat] >= -1e-9
            if seat_state.status == PlayerStatus.ALLIN:
                assert by_seat[seat] >= -invested[seat] - 1e-9
