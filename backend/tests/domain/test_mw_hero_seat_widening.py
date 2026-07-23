"""M7 (RES-I L5) — hero-seat widening: opener + cold-caller MW mappers.

Covers the spec verify-by items:
  1. the new mappers fire on engine-driven MW states (hero-as-opener /
     hero-as-caller) that returned None before — incl. an organic belt test;
  2. the closing invariant holds: the earlier caller (someone live behind
     hero) stays None, and a cold-caller inside the BB-in MW shape stays None
     through the dispatcher (structural: the BB always holds a live action
     behind every caller postflop — the documented skip);
  3. existing BB-path outputs untouched (the BB family suites stay green;
     nothing here monkeypatches or re-tunes them);
  4. grading is freq+EV (never boolean) via the existing graders + M6's
     opp-aware `_apply_multiway`.
"""

from __future__ import annotations

import random

from app.domain.action import Decision
from app.domain.personas import load_persona_packs
from app.domain.postflop import grade_cbet, grade_vs_cbet
from app.domain.scenarios import _OPEN_SIZE, _SEAT_ORDER
from app.domain.spot import (
    ActionType,
    NodeContext,
    Position,
    Street,
    players_in_pot,
)
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, apply, start_hand
from app.domain.table.grade_map import map_decision_point
from app.domain.table.grade_map_postflop import (
    map_mw_caller_vs_cbet,
    map_mw_caller_vs_river_bet,
    map_mw_caller_vs_turn_bet,
    map_mw_flop_cbet,
    map_mw_river_barrel,
    map_mw_turn_barrel,
)
from app.domain.table.play import assign_lineup, bot_decision

HERO_SEAT = 0
_BLINDS = {Position.SB, Position.BB}
_BUTTON_FOR_HERO = {
    Position.BTN: 0, Position.SB: 8, Position.BB: 7,
    Position.UTG: 6, Position.UTG1: 5, Position.UTG2: 4,
    Position.LJ: 3, Position.HJ: 2, Position.CO: 1,
}


def _state(hero_pos: Position, seed: int = 7, stacks: float = 100.0) -> HandState:
    dealt = deal_hand(random.Random(seed))
    return start_hand(
        dealt, button_seat=_BUTTON_FOR_HERO[hero_pos], stacks_bb=[stacks] * 9
    )


def _seat(state: HandState, pos: Position) -> int:
    return next(s.seat for s in state.seats if s.position is pos)


def _play(state: HandState, moves) -> HandState:
    for pos, dec in moves:
        assert state.to_act_seat == _seat(state, pos), f"expected {pos} to act"
        state = apply(state, dec)
    return state


def _fold(pos):
    return (pos, Decision(action=ActionType.FOLD))


def _check(pos):
    return (pos, Decision(action=ActionType.CHECK))


def _call(pos):
    return (pos, Decision(action=ActionType.CALL))


def _bet(pos, size):
    return (pos, Decision(action=ActionType.BET, size_bb=size))


def _raise_to(pos, size):
    return (pos, Decision(action=ActionType.RAISE, size_bb=size))


# --------------------------------------------- hero as OPENER (BB-in shape)


def _opener_preflop(
    callers=(Position.LJ,), open_to: float | None = None
) -> HandState:
    """Hero (UTG, seat 0) opens; `callers` cold-call; SB folds, BB calls."""
    state = _state(Position.UTG)
    osize = open_to if open_to is not None else _OPEN_SIZE[Position.UTG]
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        if p is Position.UTG:
            moves.append(_raise_to(p, osize))
        elif p in callers:
            moves.append(_call(p))
        else:
            moves.append(_fold(p))
    moves += [_fold(Position.SB), _call(Position.BB)]
    return _play(state, moves)


def test_opener_mw_flop_cbet_maps_3way():
    state = _play(_opener_preflop(), [_check(Position.BB)])
    assert state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.CBET]
    assert players_in_pot(spot) == 3
    pot = round(3 * _OPEN_SIZE[Position.UTG] + 0.5, 2)
    assert spot.pot_bb == pot
    bets = [la.min_bb for la in spot.legal_actions if la.action is ActionType.BET]
    assert bets == [round(0.33 * pot, 1), round(0.75 * pot, 1)]


def test_opener_mw_4way_cbet_maps_and_grades_freq_ev():
    state = _play(
        _opener_preflop(callers=(Position.LJ, Position.CO)), [_check(Position.BB)]
    )
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None and spot.node_context == [NodeContext.CBET]
    assert players_in_pot(spot) == 4
    res = grade_cbet(spot, spot.hero_range, spot.villain_range, None)
    freqs = [a.frequency for a in res.per_action]
    assert abs(sum(freqs) - 1.0) < 0.01  # freq+EV, never boolean
    assert all(a.ev_bb is not None for a in res.per_action)


def _opener_turn_state() -> tuple[HandState, float, float]:
    """Intact MW flop line (hero c-bets 0.33, both respond call), BB checks
    the turn. Returns (state, flop_pot, cbet)."""
    state = _opener_preflop()
    fp = round(3 * _OPEN_SIZE[Position.UTG] + 0.5, 2)
    cbet = round(0.33 * fp, 1)
    state = _play(state, [
        _check(Position.BB), _bet(Position.UTG, cbet),
        _call(Position.LJ), _call(Position.BB),
        _check(Position.BB),  # turn
    ])
    return state, fp, cbet


def test_opener_mw_turn_and_river_barrel_map():
    state, fp, cbet = _opener_turn_state()
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.TURN_BARREL]
    tp = round(fp + 3 * cbet, 2)
    assert spot.pot_bb == tp
    # continue: hero barrels 0.5 pot, both call; BB checks the river
    tbet = round(0.5 * tp, 1)
    state = _play(state, [
        _bet(Position.UTG, tbet), _call(Position.LJ), _call(Position.BB),
        _check(Position.BB),  # river
    ])
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.RIVER_BARREL]
    assert spot.pot_bb == round(tp + 3 * tbet, 2)
    assert players_in_pot(spot) == 3


def test_opener_mw_turn_none_after_off_grid_flop_cbet():
    # 0.42-pot flop c-bet is off the recognition grid: the flop street of the
    # line is off-shape, so the TURN barrel must not map.
    state = _opener_preflop()
    fp = round(3 * _OPEN_SIZE[Position.UTG] + 0.5, 2)
    off = round(0.42 * fp, 2)
    state = _play(state, [
        _check(Position.BB), _bet(Position.UTG, off),
        _call(Position.LJ), _call(Position.BB),
        _check(Position.BB),
    ])
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_opener_mw_delayed_cbet_stays_none():
    # Flop checks through — a delayed turn c-bet is a different node.
    state = _opener_preflop()
    state = _play(state, [
        _check(Position.BB), _check(Position.UTG), _check(Position.LJ),
        _check(Position.BB),  # turn
    ])
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_opener_mw_bb_donk_lead_stays_none():
    # BB leads into hero: the flop is not checked-to-hero — no barrel node.
    state = _opener_preflop()
    fp = round(3 * _OPEN_SIZE[Position.UTG] + 0.5, 2)
    state = _play(state, [_bet(Position.BB, round(0.33 * fp, 1))])
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_opener_mw_off_band_open_stays_none():
    state = _play(_opener_preflop(open_to=5.0), [_check(Position.BB)])
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


# ----------------------------------- hero as COLD-CALLER (no-BB 3-way shape)


def _caller_preflop(open_to: float | None = None) -> HandState:
    """UTG opens, CO cold-calls, hero (BTN, seat 0) cold-calls, blinds fold."""
    state = _state(Position.BTN)
    osize = open_to if open_to is not None else _OPEN_SIZE[Position.UTG]
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        if p is Position.UTG:
            moves.append(_raise_to(p, osize))
        elif p in (Position.CO, Position.BTN):
            moves.append(_call(p))
        else:
            moves.append(_fold(p))
    moves += [_fold(Position.SB), _fold(Position.BB)]
    return _play(state, moves)


def _caller_flop_pot() -> float:
    return round(3 * _OPEN_SIZE[Position.UTG] + 1.5, 2)  # both blinds dead


def test_caller_mw_flop_vs_cbet_maps_and_closes():
    state = _caller_preflop()
    fp = _caller_flop_pot()
    cbet = round(0.33 * fp, 1)
    state = _play(state, [_bet(Position.UTG, cbet), _call(Position.CO)])
    assert state.to_act_seat == HERO_SEAT  # hero (BTN) genuinely closes
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_CBET]
    assert players_in_pot(spot) == 3
    assert spot.facing == Position.UTG
    assert spot.pot_bb == round(fp + 2 * cbet, 2)
    # plain in-position facing-bet raise legs (hero never checked): 2.5x/3.0x
    legs = [la.min_bb for la in spot.legal_actions if la.action is ActionType.RAISE]
    assert legs == [round(2.5 * cbet, 1), round(3.0 * cbet, 1)]
    res = grade_vs_cbet(spot, spot.hero_range, spot.villain_range, None)
    freqs = [a.frequency for a in res.per_action]
    assert abs(sum(freqs) - 1.0) < 0.01  # freq+EV, never boolean
    assert all(a.ev_bb is not None for a in res.per_action)


def test_caller_mw_earlier_caller_not_closing_stays_none():
    # Same shape, hero = CO (the EARLIER caller): BTN is live behind hero at
    # his decision — hero-not-closing multiway stays "no baseline yet".
    state = _state(Position.CO)
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        if p is Position.UTG:
            moves.append(_raise_to(p, _OPEN_SIZE[Position.UTG]))
        elif p in (Position.CO, Position.BTN):
            moves.append(_call(p))
        else:
            moves.append(_fold(p))
    moves += [_fold(Position.SB), _fold(Position.BB)]
    state = _play(state, moves)
    fp = _caller_flop_pot()
    state = _play(state, [_bet(Position.UTG, round(0.33 * fp, 1))])
    assert state.to_act_seat == HERO_SEAT  # hero (CO) faces the bet first
    assert map_decision_point(state, HERO_SEAT) is None


def test_caller_inside_bb_in_mw_shape_stays_none():
    # The documented structural skip: inside the BB-in `_mw_srp_preflop`
    # shape a cold-caller can NEVER close (postflop the BB acts first, so
    # after the opener's bet the BB always holds a live action behind every
    # caller). Hero = BTN cold-caller, BB in the pot: None through the
    # dispatcher even though every prior caller responded.
    state = _state(Position.BTN)
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        if p is Position.UTG:
            moves.append(_raise_to(p, _OPEN_SIZE[Position.UTG]))
        elif p in (Position.CO, Position.BTN):
            moves.append(_call(p))
        else:
            moves.append(_fold(p))
    moves += [_fold(Position.SB), _call(Position.BB)]
    state = _play(state, moves)
    fp = round(4 * _OPEN_SIZE[Position.UTG] + 0.5, 2)
    cbet = round(0.33 * fp, 1)
    state = _play(state, [_check(Position.BB), _bet(Position.UTG, cbet), _call(Position.CO)])
    assert state.to_act_seat == HERO_SEAT  # BB still live BEHIND hero
    assert map_decision_point(state, HERO_SEAT) is None


def test_caller_mw_turn_and_river_map_on_continuation_line():
    state = _caller_preflop()
    fp = _caller_flop_pot()
    fbet = round(0.33 * fp, 1)
    state = _play(state, [
        _bet(Position.UTG, fbet), _call(Position.CO), _call(Position.BTN),
    ])
    tp = round(fp + 3 * fbet, 2)
    tbet = round(0.5 * tp, 1)
    state = _play(state, [_bet(Position.UTG, tbet), _call(Position.CO)])
    assert state.street is Street.TURN and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_TURN_BET]
    assert players_in_pot(spot) == 3 and spot.facing == Position.UTG
    # continue: hero calls; river bet, CO calls — hero closes again
    state = apply(state, Decision(action=ActionType.CALL))
    rp = round(tp + 3 * tbet, 2)
    rbet = round(0.5 * rp, 1)
    state = _play(state, [_bet(Position.UTG, rbet), _call(Position.CO)])
    assert state.street is Street.RIVER and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_RIVER_BET]
    assert spot.pot_bb == round(rp + 2 * rbet, 2)


def test_caller_mw_other_caller_folds_degrades_with_dead_money():
    # CO folds to the c-bet: hero still closes; 2 live + CO's dead money.
    state = _caller_preflop()
    fp = _caller_flop_pot()
    cbet = round(0.33 * fp, 1)
    state = _play(state, [_bet(Position.UTG, cbet), _fold(Position.CO)])
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert players_in_pot(spot) == 2
    assert spot.pot_bb == round(fp + cbet, 2)


def test_caller_mw_opener_raise_war_stays_none():
    # CO raises the c-bet instead of calling: hero faces a raise, not the
    # canonical bet — different (unmapped) node.
    state = _caller_preflop()
    fp = _caller_flop_pot()
    cbet = round(0.33 * fp, 1)
    state = _play(state, [
        _bet(Position.UTG, cbet), _raise_to(Position.CO, round(3 * cbet, 1)),
    ])
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_caller_mw_off_band_open_stays_none():
    state = _caller_preflop(open_to=5.0)
    fp = round(3 * 5.0 + 1.5, 2)
    state = _play(state, [_bet(Position.UTG, round(0.33 * fp, 1)), _call(Position.CO)])
    assert state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


# ------------------------------------------------- organic belt (verify #1)


def _count_new_mapper_fires(proxy: str, seed: int, hands: int) -> int:
    """RES-I §1 method: real engine + real bot policy, hero seat 0 plays the
    proxy persona, button rotates, stacks reset, lineup shuffled per hand,
    one seeded Random. Counts non-None returns from the SIX new M7 mappers
    only (the BB family is counted by test_mw_funnel_belt)."""
    packs = load_persona_packs()
    hero_pack = packs[proxy]
    rng = random.Random(seed)
    mappers = (
        map_mw_flop_cbet, map_mw_turn_barrel, map_mw_river_barrel,
        map_mw_caller_vs_cbet, map_mw_caller_vs_turn_bet,
        map_mw_caller_vs_river_bet,
    )
    fires = 0
    for hand_no in range(hands):
        lineup = assign_lineup(rng)
        seat_packs = {s: packs[t.value] for s, t in lineup.items()}
        state = start_hand(
            deal_hand(rng), button_seat=hand_no % 9, stacks_bb=[100.0] * 9
        )
        guard = 0
        while not state.hand_over and state.to_act_seat is not None:
            guard += 1
            assert guard <= 500, "bot playout did not terminate"
            seat = state.to_act_seat
            if seat == HERO_SEAT:
                if any(m(state, HERO_SEAT) is not None for m in mappers):
                    fires += 1
                dec = bot_decision(state, seat, hero_pack, rng)
            else:
                dec = bot_decision(state, seat, seat_packs[seat], rng)
            state = apply(state, dec)
    return fires


def test_new_mappers_fire_on_organic_play():
    # Belt, not a point estimate: >=1 proves the new hero seats actually fire
    # on engine-driven states that were None before M7; the generous ceiling
    # catches a gate accidentally going vacuous. Deterministic (seeded).
    fires = _count_new_mapper_fires("tag", 20260722, 2000)
    assert 1 <= fires <= 60, f"M7 fires out of band: {fires} in 2000 hands"
