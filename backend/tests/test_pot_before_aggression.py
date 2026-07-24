"""W0-a — `pot_before_current_aggression` unit tests (persona-realism foundation).

The helper reconstructs "the pot before the current aggression" + the latest
aggressor's chip contribution from `action_history` — the shared denominator
the commit gate, the faced_frac fix, and the semi-bluff EV math need
(theory contract §7). These tests drive the REAL engine (`start_hand`/`apply`),
never hand-authored `amount_bb` values, so they pin the true encoding:
`HistoryAction.amount_bb` is the per-action chip INCREMENT (contribution), not
the bet-TO. The self-re-raise and blind-raiser cases assert
independently-hand-computed numbers — the non-circular checks that catch a
bet-TO/increment confusion (which coincide only when prior street investment is
zero).
"""

from __future__ import annotations

import random

from app.domain.action import Decision
from app.domain.spot import ActionType, Street
from app.domain.table import deal_hand
from app.domain.table.engine import apply, start_hand
from app.domain.table.sizing import pot_before_current_aggression

# button=0 -> SB=1, BB=2, UTG=3; preflop order 3,4,5,6,7,8,0,1,2.
_BUTTON = 0


def _deal(seed: int = 1):
    return deal_hand(random.Random(seed))


def _start():
    return start_hand(_deal(), button_seat=_BUTTON, stacks_bb=[100.0] * 9)


def _start_stacks(stacks: list[float]):
    return start_hand(_deal(), button_seat=_BUTTON, stacks_bb=stacks)


def _act(state, seat: int, action: ActionType, size_bb: float | None = None):
    assert state.to_act_seat == seat, f"expected seat {seat}, got {state.to_act_seat}"
    return apply(state, Decision(action=action, size_bb=size_bb))


def _fold_until(state, target: int):
    while state.to_act_seat is not None and state.to_act_seat != target:
        state = _act(state, state.to_act_seat, ActionType.FOLD)
    return state


def _live_pot(state) -> float:
    return round(sum(s.invested_total_bb for s in state.seats), 2)


# --------------------------------------------------------------------------
# 1. Fresh single bet — increment == the bet, pot_before == the prior pot.
# --------------------------------------------------------------------------
def test_fresh_flop_bet():
    state = _start()
    # Fold everyone to the blinds; SB completes, BB checks -> flop pot 2.0.
    state = _fold_until(state, 1)  # folds UTG..button, stops at SB
    state = _act(state, 1, ActionType.CALL)  # SB completes to 1.0
    state = _act(state, 2, ActionType.CHECK)  # BB checks option
    assert state.street is Street.FLOP
    # SB (first live postflop) bets 1.0 into the 2.0 pot.
    state = _act(state, 1, ActionType.BET, 1.0)
    res = pot_before_current_aggression(state.action_history, state.street)
    assert res.latest_aggressor_contribution_bb == 1.0
    assert res.pot_before_bb == 2.0  # == the pre-bet pot
    assert res.pot_before_bb == round(_live_pot(state) - 1.0, 2)


# --------------------------------------------------------------------------
# 2. Self-re-raise — THE key case: increment != raise-TO.
#    UTG opens to 3, seat4 3bets to 9, UTG 4bets to 21.
#    UTG's 4bet contribution = 21 - 3 (its own open) = 18, NOT 21.
#    pot_before = SB .5 + BB 1 + UTG open 3 + seat4 3bet 9 = 13.5.
# --------------------------------------------------------------------------
def test_self_reraise_uses_increment_not_bet_to():
    state = _start()
    state = _act(state, 3, ActionType.RAISE, 3.0)  # UTG open
    state = _act(state, 4, ActionType.RAISE, 9.0)  # seat4 3bet
    state = _fold_until(state, 3)  # fold 5..2 back to UTG
    state = _act(state, 3, ActionType.RAISE, 21.0)  # UTG 4bet (self-re-raise)
    assert state.to_act_seat == 4  # seat4 now faces the 4bet
    res = pot_before_current_aggression(state.action_history, Street.PREFLOP)
    assert res.latest_aggressor_contribution_bb == 18.0  # 21 - 3, NOT 21
    assert res.pot_before_bb == 13.5  # hand-computed, non-circular
    assert res.pot_before_bb == round(_live_pot(state) - 18.0, 2)


# --------------------------------------------------------------------------
# 3. Blind-raiser — POST then RAISE by the same seat.
#    UTG opens to 3, BB raises to 8. BB posted 1, so its raise contribution
#    = 8 - 1 = 7, NOT 8. pot_before = SB .5 + BB posted 1 + UTG 3 = 4.5.
# --------------------------------------------------------------------------
def test_blind_raiser_subtracts_posted_blind():
    state = _start()
    state = _act(state, 3, ActionType.RAISE, 3.0)  # UTG open
    state = _fold_until(state, 2)  # fold 4..8,0,SB back to BB
    state = _act(state, 2, ActionType.RAISE, 8.0)  # BB raises over its own post
    res = pot_before_current_aggression(state.action_history, Street.PREFLOP)
    assert res.latest_aggressor_contribution_bb == 7.0  # 8 - 1 posted, NOT 8
    assert res.pot_before_bb == 4.5  # hand-computed, non-circular
    assert res.pot_before_bb == round(_live_pot(state) - 7.0, 2)


# --------------------------------------------------------------------------
# 4. Unraised / checked street — no aggression -> contribution 0, pot intact.
# --------------------------------------------------------------------------
def test_unraised_street_has_zero_contribution():
    state = _start()
    state = _fold_until(state, 1)
    state = _act(state, 1, ActionType.CALL)  # SB completes
    state = _act(state, 2, ActionType.CHECK)  # BB checks -> flop
    assert state.street is Street.FLOP
    state = _act(state, 1, ActionType.CHECK)  # SB checks (no flop aggression yet)
    res = pot_before_current_aggression(state.action_history, Street.FLOP)
    assert res.latest_aggressor_contribution_bb == 0.0
    assert res.pot_before_bb == 2.0
    assert res.pot_before_bb == _live_pot(state)


# --------------------------------------------------------------------------
# 5. Multi-street — prior streets are fully inside pot_before; only the current
#    street's aggression is excluded.
# --------------------------------------------------------------------------
def test_multistreet_prior_streets_in_pot_before():
    state = _start()
    state = _fold_until(state, 1)
    state = _act(state, 1, ActionType.CALL)  # SB completes -> pot 2
    state = _act(state, 2, ActionType.CHECK)
    # Flop: SB bets 1, BB calls 1 -> pot 4.
    state = _act(state, 1, ActionType.BET, 1.0)
    state = _act(state, 2, ActionType.CALL)
    assert state.street is Street.TURN
    # Turn: SB bets 2 -> facing this, pot_before = 4 (all prior in).
    state = _act(state, 1, ActionType.BET, 2.0)
    res = pot_before_current_aggression(state.action_history, Street.TURN)
    assert res.latest_aggressor_contribution_bb == 2.0
    assert res.pot_before_bb == 4.0
    assert res.pot_before_bb == round(_live_pot(state) - 2.0, 2)


# --------------------------------------------------------------------------
# 6. Multiway bet/call/raise — a bet+call precede the raise; both stay inside
#    pot_before, only the raise contribution is excluded.
#    Preflop: seats 3,4 limp, others fold, SB folds, BB checks -> pot 3.5.
#    Flop: BB bets 1, seat3 calls 1, seat4 raises to 3 (contribution 3).
#    pot_before = 3.5 + 1 + 1 = 5.5.
# --------------------------------------------------------------------------
def test_multiway_bet_call_raise():
    state = _start()
    state = _act(state, 3, ActionType.CALL)  # UTG limp
    state = _act(state, 4, ActionType.CALL)  # seat4 limp
    state = _fold_until(state, 1)  # fold 5..8,0 to SB
    state = _act(state, 1, ActionType.FOLD)  # SB folds (forfeits 0.5)
    state = _act(state, 2, ActionType.CHECK)  # BB checks -> flop, pot 3.5
    assert state.street is Street.FLOP
    state = _act(state, 2, ActionType.BET, 1.0)  # BB bets
    state = _act(state, 3, ActionType.CALL)  # seat3 calls
    state = _act(state, 4, ActionType.RAISE, 3.0)  # seat4 raises
    res = pot_before_current_aggression(state.action_history, Street.FLOP)
    assert res.latest_aggressor_contribution_bb == 3.0
    assert res.pot_before_bb == 5.5  # 3.5 + BB's 1 + seat3's 1
    assert res.pot_before_bb == round(_live_pot(state) - 3.0, 2)


# --------------------------------------------------------------------------
# 7. Incomplete all-in raise — a short jam below the min-raise stores only the
#    chips paid; the helper reads that contribution unconditionally.
#    seat4 has a 4bb stack; UTG opens to 3; seat4 jams all-in to 4.
# --------------------------------------------------------------------------
def test_incomplete_all_in_raise():
    stacks = [100.0] * 9
    stacks[4] = 4.0
    state = _start_stacks(stacks)
    state = _act(state, 3, ActionType.RAISE, 3.0)  # UTG open to 3
    state = _act(state, 4, ActionType.RAISE, 4.0)  # seat4 jam all-in to 4 (< min-raise 5)
    res = pot_before_current_aggression(state.action_history, Street.PREFLOP)
    assert res.latest_aggressor_contribution_bb == 4.0  # full jam-to, seat4 had 0 in
    # pot_before = SB .5 + BB 1 + UTG 3 = 4.5 (seat4's 4 excluded).
    assert res.pot_before_bb == 4.5
    assert res.pot_before_bb == round(_live_pot(state) - 4.0, 2)


# --------------------------------------------------------------------------
# 8. W1-b wiring — POSTFLOP self-re-raise: the increment play.py threads into the
#    price-aware fold is strictly BELOW the live bet-TO, so the faced_frac
#    denominator (live_pot − contribution) is correct where current_bet_bb alone
#    over-subtracted. HU: SB bets 2, BB raises to 6, SB re-raises to 13.
# --------------------------------------------------------------------------
def test_postflop_self_reraise_contribution_below_current_bet():
    state = _start()
    state = _fold_until(state, 1)  # fold to SB
    state = _act(state, 1, ActionType.CALL)  # SB completes
    state = _act(state, 2, ActionType.CHECK)  # BB checks -> flop
    assert state.street is Street.FLOP
    state = _act(state, 1, ActionType.BET, 2.0)  # SB bets
    state = _act(state, 2, ActionType.RAISE, 6.0)  # BB raises to 6
    state = _act(state, 1, ActionType.RAISE, 13.0)  # SB re-raises (self-re-raise)
    assert state.to_act_seat == 2  # BB now faces the re-raise
    res = pot_before_current_aggression(state.action_history, state.street)
    assert res.latest_aggressor_contribution_bb == 11.0  # 13 − SB's own earlier 2
    assert res.latest_aggressor_contribution_bb < state.current_bet_bb  # 11 < 13
    assert res.pot_before_bb == round(_live_pot(state) - 11.0, 2)
