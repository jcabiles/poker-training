"""M6 (RES-H H2) — 4-way merit extension: opponent-count-scaled `_apply_multiway`
+ the 4-way `map_mw_*` widening. Covers the RES-H §5-H2 verbatim pass/fail items:

  1. HU byte-identical (`opp=1` ⇒ every scalar 1.0) AND 3-way byte-identical
     (`base**1` == the pre-M6 flat constants, pinned as LITERALS here so a
     base retune breaks this file; the full-output pins live in
     tests/test_signature.py + the existing postflop/multiway suites);
  2. monotone-in-opponents: air/draw aggressive merit non-increasing
     HU→3-way→4-way; weak_made facing FOLD merit non-decreasing;
  3. direction-only: removing the multiplier (opp=1) recovers the input
     merits EXACTLY; no MDF / per-opponent pot-odds constant in the source;
  4. a 4-way SRP spot where hero CLOSES maps and grades; a 4-way spot with a
     live player still behind hero returns None — both from engine-driven
     states;
  5. 5+-way is never a calibrated tier (the preflop gate returns None).
"""

from __future__ import annotations

import inspect
import random

from app.domain.action import Decision
from app.domain.postflop import _apply_multiway, grade_vs_cbet
from app.domain.scenarios import _OPEN_SIZE, _SEAT_ORDER, build_cbet_spot
from app.domain.spot import (
    ActionType,
    Position,
    Street,
    opponent_count,
    players_in_pot,
)
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, apply, start_hand
from app.domain.table.grade_map_postflop import (
    map_mw_flop_vs_cbet,
    map_mw_vs_turn_bet,
)

# Pre-M6 flat constants, pinned as LITERALS (never import the module bases —
# the whole point is to catch a silent base retune breaking 3-way identity).
_FLAT_BLUFF_DAMPEN = 0.6
_FLAT_VALUE_LEAN = 1.15
_FLAT_CATCH_TIGHTEN = 1.3
_FLAT_THIN_VALUE_DAMPEN = 0.7

_AGG = {"check": 1.0, "small": 2.0, "big": 1.5}
_FACE = {"fold": 0.6, "call": 1.2, "raise": 0.4}


# ------------------------- 1. HU + 3-way byte-identical (unit-level pins)


def test_opp1_is_identity_every_category_and_side():
    """Direction-only + HU byte-identity: opp=1 ⇒ exponent 0 ⇒ every scalar
    1.0 — the multiplier removed recovers the HU merits EXACTLY."""
    for cat in ("air", "draw", "weak_made", "strong"):
        assert _apply_multiway(_AGG, cat_effective=cat, facing_side=False, opp=1) == _AGG
        assert _apply_multiway(_FACE, cat_effective=cat, facing_side=True, opp=1) == _FACE


def test_opp2_equals_pre_m6_flat_constants():
    """3-way byte-identical: base**1 == today's flat constant, per category."""
    out = _apply_multiway(_AGG, cat_effective="air", facing_side=False, opp=2)
    assert out["small"] == 2.0 * _FLAT_BLUFF_DAMPEN
    assert out["big"] == 1.5 * _FLAT_BLUFF_DAMPEN
    assert out["check"] == 1.0
    out = _apply_multiway(_AGG, cat_effective="weak_made", facing_side=False, opp=2)
    assert out["small"] == 2.0 * _FLAT_THIN_VALUE_DAMPEN
    out = _apply_multiway(_AGG, cat_effective="strong", facing_side=False, opp=2)
    assert out["small"] == 2.0 * _FLAT_VALUE_LEAN
    out = _apply_multiway(_FACE, cat_effective="weak_made", facing_side=True, opp=2)
    assert out["fold"] == 0.6 * _FLAT_CATCH_TIGHTEN
    assert out["call"] == 1.2 * _FLAT_BLUFF_DAMPEN
    assert out["raise"] == 0.4 * _FLAT_BLUFF_DAMPEN


# ------------------------------------- 2. monotone-in-opponents invariant


def test_bluff_merit_non_increasing_hu_3way_4way():
    for cat in ("air", "draw"):
        prev = None
        for opp in (1, 2, 3):
            out = _apply_multiway(_AGG, cat_effective=cat, facing_side=False, opp=opp)
            agg = out["small"] + out["big"]
            if prev is not None:
                assert agg < prev  # strictly harder push per added opponent
            prev = agg


def test_weak_made_catcher_fold_non_decreasing_hu_3way_4way():
    prev = None
    for opp in (1, 2, 3):
        out = _apply_multiway(_FACE, cat_effective="weak_made", facing_side=True, opp=opp)
        if prev is not None:
            assert out["fold"] > prev["fold"]
            assert out["call"] < prev["call"]  # continue-merit dampens harder
        prev = out


# ---------------------------------------- 3. direction-only (source-level)


def test_apply_multiway_reads_only_merits_cat_side_opp():
    """No MDF / per-opponent pot-odds constant; no spot/pot access — the
    change is purely a geometric scalar on existing merits."""
    src = inspect.getsource(_apply_multiway)
    assert "max(opp - 1, 0)" in src
    # identifier-level: no defense-frequency helper, no Spot/pot access
    for forbidden in ("pot_odds", "players_in_pot", "_calibrate_catcher_fold", "pot_bb", "spot."):
        assert forbidden not in src, f"_apply_multiway must not read {forbidden}"


def test_opponent_count_off_by_one_pin():
    """HU ⇒ players_in_pot == 2 ⇒ opp == 1 (the M6 off-by-one guard)."""
    hu = build_cbet_spot(random.Random(3))
    assert players_in_pot(hu) == 2 and opponent_count(hu) == 1
    mw = build_cbet_spot(random.Random(3), players_in_pot=3)
    assert players_in_pot(mw) == 3 and opponent_count(mw) == 2


# --------------- 4./5. engine-driven 4-way mapper gates (hero closes / not)

_BLINDS = {Position.SB, Position.BB}


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


def _mw_preflop(callers: tuple[Position, ...], seed: int = 7) -> HandState:
    """Engine-driven MW SRP: UTG opens 3.0, `callers` cold-call, BB calls."""
    state = start_hand(deal_hand(random.Random(seed)), button_seat=0, stacks_bb=[100.0] * 9)
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        if p is Position.UTG:
            moves.append((p, Decision(action=ActionType.RAISE, size_bb=_OPEN_SIZE[Position.UTG])))
        elif p in callers:
            moves.append(_call(p))
        else:
            moves.append(_fold(p))
    moves += [_fold(Position.SB), _call(Position.BB)]
    return _play(state, moves)


def _four_way_flop_faced(seed: int = 7) -> tuple[HandState, float]:
    """4-way (UTG opener + HJ + BTN + BB): flop check(BB) → c-bet(UTG) →
    call(HJ) → call(BTN); hero (BB) faces the bet and CLOSES."""
    state = _mw_preflop((Position.HJ, Position.BTN), seed)
    flop_pot = 4 * _OPEN_SIZE[Position.UTG] + 0.5
    cbet = round(0.33 * flop_pot, 2)
    state = _play(state, [
        _check(Position.BB), _bet(Position.UTG, cbet),
        _call(Position.HJ), _call(Position.BTN),
    ])
    return state, cbet


def test_four_way_hero_closes_maps_and_grades():
    state, _cbet = _four_way_flop_faced()
    spot = map_mw_flop_vs_cbet(state, _seat(state, Position.BB))
    assert spot is not None, "4-way hero-closes SRP shape must map (M6)"
    assert players_in_pot(spot) == 4 and opponent_count(spot) == 3
    res = grade_vs_cbet(spot, spot.hero_range, spot.villain_range, None)
    freqs = [a.frequency for a in res.per_action]
    assert abs(sum(freqs) - 1.0) < 0.01  # freq+EV, never boolean
    assert all(a.ev_bb is not None for a in res.per_action)


def test_four_way_live_player_behind_hero_is_none():
    """Same engine line, but hero = HJ (the first caller) at HIS decision:
    BTN and BB are live BEHIND him — no baseline yet (RES-H §1.2/§2.4)."""
    state = _mw_preflop((Position.HJ, Position.BTN))
    flop_pot = 4 * _OPEN_SIZE[Position.UTG] + 0.5
    cbet = round(0.33 * flop_pot, 2)
    state = _play(state, [_check(Position.BB), _bet(Position.UTG, cbet)])
    hj = _seat(state, Position.HJ)
    assert state.to_act_seat == hj  # engine-driven: HJ genuinely faces the bet
    assert map_mw_flop_vs_cbet(state, hj) is None


def test_four_way_partial_response_never_reaches_hero_short():
    """Action-order guard: with only ONE caller responded the street act-list
    can't match, so even a direct probe of the BB seat stays None."""
    state = _mw_preflop((Position.HJ, Position.BTN))
    flop_pot = 4 * _OPEN_SIZE[Position.UTG] + 0.5
    cbet = round(0.33 * flop_pot, 2)
    state = _play(state, [
        _check(Position.BB), _bet(Position.UTG, cbet), _call(Position.HJ),
    ])
    assert map_mw_flop_vs_cbet(state, _seat(state, Position.BB)) is None


def test_five_way_is_not_a_calibrated_tier():
    state = _mw_preflop((Position.HJ, Position.CO, Position.BTN))
    flop_pot = 5 * _OPEN_SIZE[Position.UTG] + 0.5
    cbet = round(0.33 * flop_pot, 2)
    state = _play(state, [
        _check(Position.BB), _bet(Position.UTG, cbet),
        _call(Position.HJ), _call(Position.CO), _call(Position.BTN),
    ])
    assert map_mw_flop_vs_cbet(state, _seat(state, Position.BB)) is None


def test_four_way_caller_folds_degrades_with_dead_money():
    """One caller folds to the c-bet: still maps (3 live + dead money in the
    pot), same degrade pattern the 3-way mapper already handled."""
    state = _mw_preflop((Position.HJ, Position.BTN))
    flop_pot = 4 * _OPEN_SIZE[Position.UTG] + 0.5
    cbet = round(0.33 * flop_pot, 2)
    state = _play(state, [
        _check(Position.BB), _bet(Position.UTG, cbet),
        _fold(Position.HJ), _call(Position.BTN),
    ])
    spot = map_mw_flop_vs_cbet(state, _seat(state, Position.BB))
    assert spot is not None
    assert players_in_pot(spot) == 3
    assert abs(spot.pot_bb - (flop_pot + 2 * cbet)) < 0.01


def test_four_way_turn_line_maps():
    """The widened prior-street gate: 4-way flop bet-call-call-call, then the
    turn bet with both callers responded — hero (BB) closes and maps."""
    state, cbet = _four_way_flop_faced()
    state = _play(state, [_call(Position.BB)])
    flop_pot = 4 * _OPEN_SIZE[Position.UTG] + 0.5
    turn_pot = flop_pot + 4 * cbet
    tbet = round(0.5 * turn_pot, 2)
    state = _play(state, [
        _check(Position.BB), _bet(Position.UTG, tbet),
        _call(Position.HJ), _call(Position.BTN),
    ])
    assert len(state.board) == 4 and state.to_act_seat == _seat(state, Position.BB)
    spot = map_mw_vs_turn_bet(state, _seat(state, Position.BB))
    assert spot is not None
    assert spot.street is Street.TURN and players_in_pot(spot) == 4
