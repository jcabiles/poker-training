"""M5 (Epic 5, RES-G Slice C) — HU limped-pot flop grader.

RES-G §6-C pass/fail:
  (a) a bot-driven belt fires the new mappers on organic HU limped flops
      (hero leads / hero faces a lead), and a 0-raise HU flop that returned
      None before grades freq+EV;
  (b) any multiway (3+) limped flop still returns None — explicitly INCLUDING
      a 3-preflop-entrant pot that degraded to 2-live by hero's turn (the
      entrant gate reads PREFLOP actions, never current statuses);
  (c) raised-pot postflop graders are byte-unchanged (the existing suite pins
      them; here we assert the raised-pot shapes still map to their own
      nodes, never a limped one);
  (d) EVs approximate (freq+EV, never boolean), `spot_signature()` unchanged.
"""

from __future__ import annotations

import random

import pytest

from app.domain.action import Decision
from app.domain.evaluation import Correctness
from app.domain.postflop import grade_limped_lead, grade_limped_vs_lead
from app.domain.scenarios import _SEAT_ORDER
from app.domain.spot import ActionType, NodeContext, Position, Street, players_in_pot
from app.domain.srs import spot_signature
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, apply, start_hand
from app.domain.table.grade_map import map_decision_point

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


def _play(state: HandState, moves) -> HandState:
    for pos, dec in moves:
        seat = next(s.seat for s in state.seats if s.position is pos)
        assert state.to_act_seat == seat, f"expected {pos} to act"
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


def _limped_hu_preflop(hero_pos: Position, limper: Position | None = None, seed: int = 7):
    """0-raise HU pot: `limper` open-limps (or the SB completes when limper is
    None with hero/villain in the blinds), everyone else folds, BB checks."""
    state = _state(hero_pos, seed=seed)
    entrants = {limper, Position.BB} - {None}
    if limper is None:
        entrants = {Position.SB, Position.BB}
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        moves.append(_call(p) if p in entrants else _fold(p))
    moves.append(_call(Position.SB) if Position.SB in entrants else _fold(Position.SB))
    moves.append(_check(Position.BB))
    return _play(state, moves)


# ------------------------------------------------- (a) canonical HU shapes map


def test_hero_bb_lead_maps_and_grades():
    # BTN open-limps, folds around, hero = BB checks; flop: hero acts first
    # with no bet yet — a 0-raise HU flop that was None before M5.
    state = _limped_hu_preflop(Position.BB, limper=Position.BTN)
    assert state.street is Street.FLOP and state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.LIMPED_LEAD]
    assert players_in_pot(spot) == 2
    assert spot.pot_bb == 2.5  # limp 1.0 + BB 1.0 + dead SB 0.5
    assert spot.facing is Position.BTN
    # grades freq+EV, never boolean
    res = grade_limped_lead(spot, spot.hero_range, spot.villain_range, None)
    assert len(res.per_action) == 3
    assert abs(sum(e.frequency for e in res.per_action) - 1.0) < 1e-6
    assert all(isinstance(e.ev_bb, float) for e in res.per_action)
    graded = grade_limped_lead(
        spot, None, None, Decision(action=ActionType.CHECK)
    )
    assert graded.correctness in tuple(Correctness)
    assert graded.chosen_eval is not None
    assert graded.leak_category == 208


def test_hero_ip_limper_lead_maps_after_bb_check():
    # Hero = BTN open-limped; BB checked the flop to hero.
    state = _limped_hu_preflop(Position.BTN, limper=Position.BTN)
    state = _play(state, [_check(Position.BB)])
    assert state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.LIMPED_LEAD]
    assert spot.facing is Position.BB


def test_sb_complete_vs_bb_maps():
    # Hero = SB completed vs the BB: pot 2.0, hero first to act on the flop.
    state = _limped_hu_preflop(Position.SB, limper=None)
    assert state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.LIMPED_LEAD]
    assert spot.pot_bb == 2.0
    assert spot.facing is Position.BB


def test_hero_bb_vs_lead_maps_and_grades():
    # Hero = BB checked the flop; the BTN limper stabs 0.5 pot (1.25 on 2.5:
    # the engine min bet is 1BB, so a 0.33-pot stab is illegal here) — hero
    # faces a lead (hero's raise is a check-raise here).
    state = _limped_hu_preflop(Position.BB, limper=Position.BTN)
    state = _play(state, [_check(Position.BB), _bet(Position.BTN, 1.25)])
    assert state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.LIMPED_VS_LEAD]
    assert spot.pot_bb == 3.75
    call = next(la for la in spot.legal_actions if la.action is ActionType.CALL)
    assert call.min_bb == 1.25  # the ACTUAL bet — true price preserved
    res = grade_limped_vs_lead(
        spot, None, None, Decision(action=ActionType.FOLD)
    )
    assert res.correctness in tuple(Correctness)
    assert res.chosen_eval is not None
    assert res.leak_category == 209
    assert abs(sum(e.frequency for e in res.per_action) - 1.0) < 1e-6


def test_hero_ip_faces_outright_lead():
    # Hero = BTN limper; the BB leads into hero without a check.
    state = _limped_hu_preflop(Position.BTN, limper=Position.BTN)
    state = _play(state, [_bet(Position.BB, 1.25)])
    assert state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.LIMPED_VS_LEAD]
    assert spot.facing is Position.BB


def test_off_grid_lead_size_stays_none():
    # A lead off the recognition grid (0.42-pot ≈ 1.05 on a 2.5 pot) gates.
    state = _limped_hu_preflop(Position.BB, limper=Position.BTN)
    state = _play(state, [_check(Position.BB), _bet(Position.BTN, 1.05)])
    assert map_decision_point(state, HERO_SEAT) is None


# ------------------- (b) multiway limped stays None (explicit entrant gate)


def _three_way_limped(hero_pos=Position.BB, seed: int = 7) -> HandState:
    state = _state(hero_pos, seed=seed)
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        moves.append(_call(p) if p in (Position.CO, Position.BTN) else _fold(p))
    moves += [_fold(Position.SB), _check(Position.BB)]
    return _play(state, moves)


def test_three_entrant_limped_flop_stays_none():
    # 3 preflop entrants (CO + BTN limped, hero = BB): the lead-shaped flop
    # node (hero first to act, no bet yet) must NOT HU-grade.
    state = _three_way_limped()
    assert state.street is Street.FLOP and state.to_act_seat == HERO_SEAT
    assert map_decision_point(state, HERO_SEAT) is None


def test_degraded_to_two_live_limped_flop_stays_none():
    # 3 preflop entrants; CO bets the flop, BTN folds — hero faces the bet
    # with only 2 LIVE players. The entrant gate reads PREFLOP actions, so
    # this must STILL be None (multiway limped = "no baseline yet"), never a
    # silently HU-graded pot.
    state = _three_way_limped()
    pot = round(sum(s.invested_total_bb for s in state.seats), 2)
    cbet = round(0.33 * pot, 1)
    state = _play(state, [_check(Position.BB), _bet(Position.CO, cbet), _fold(Position.BTN)])
    assert state.to_act_seat == HERO_SEAT
    live = sum(1 for s in state.seats if s.status.value != "folded")
    assert live == 2  # degraded to 2-live — and still None:
    assert map_decision_point(state, HERO_SEAT) is None


# ----------------------- (c) raised pots never route to the limped mappers


def test_raised_pot_still_maps_to_its_own_node():
    # HU SRP vs-cbet line: the raised-pot mapper owns it; the limped mappers
    # (zero-raise gate) can never fire here.
    from app.domain.scenarios import _OPEN_SIZE
    from app.domain.table.grade_map_postflop import (
        map_limped_flop_lead,
        map_limped_flop_vs_lead,
    )

    state = _state(Position.BB)
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        if p is Position.CO:
            moves.append((p, Decision(action=ActionType.RAISE, size_bb=_OPEN_SIZE[Position.CO])))
        else:
            moves.append(_fold(p))
    moves += [_fold(Position.SB), _call(Position.BB)]
    state = _play(state, moves)
    pot = round(2 * _OPEN_SIZE[Position.CO] + 0.5, 2)
    state = _play(state, [_check(Position.BB), _bet(Position.CO, round(0.33 * pot, 1))])
    assert map_limped_flop_lead(state, HERO_SEAT) is None
    assert map_limped_flop_vs_lead(state, HERO_SEAT) is None
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None and spot.node_context == [NodeContext.VS_CBET]


# --------------------------------- (d) signature + direction sanity checks


def test_signatures_stable_and_distinct_per_node():
    state = _limped_hu_preflop(Position.BB, limper=Position.BTN)
    lead = map_decision_point(state, HERO_SEAT)
    state = _play(state, [_check(Position.BB), _bet(Position.BTN, 1.25)])
    faced = map_decision_point(state, HERO_SEAT)
    assert lead is not None and faced is not None
    assert spot_signature(lead) == spot_signature(lead)  # stable
    assert spot_signature(lead) != spot_signature(faced)  # node-distinct


@pytest.mark.parametrize("board", [["Kh", "7d", "2s"]])
def test_directions_middle_checks_and_big_lead_folds_more(board):
    # §4b-4: OOP medium made hand mostly checks (never bloats a limped pot);
    # §4b-2: the marginal catcher folds MORE vs a big lead than a small one.
    state = _limped_hu_preflop(Position.BB, limper=Position.BTN)
    lead = map_decision_point(state, HERO_SEAT)
    assert lead is not None
    lead = lead.model_copy(
        update={
            "board": board,
            "hero": lead.hero.model_copy(update={"hole_cards": ("Kc", "5c")}),
        }
    )
    res = grade_limped_lead(lead, None, None, None)
    check_eval = next(e for e in res.per_action if e.action is ActionType.CHECK)
    assert res.best_action.action is ActionType.CHECK
    assert check_eval.frequency == max(e.frequency for e in res.per_action)

    def _faced(bet: float):
        s = _limped_hu_preflop(Position.BB, limper=Position.BTN)
        s = _play(s, [_check(Position.BB), _bet(Position.BTN, bet)])
        spot = map_decision_point(s, HERO_SEAT)
        assert spot is not None
        return spot.model_copy(
            update={
                "board": board,
                "hero": spot.hero.model_copy(update={"hole_cards": ("Kc", "5c")}),
            }
        )

    small = grade_limped_vs_lead(_faced(1.25), None, None, None)  # 0.5 pot
    big = grade_limped_vs_lead(_faced(2.5), None, None, None)  # 1.0 pot
    f_small = next(e for e in small.per_action if e.action is ActionType.FOLD).frequency
    f_big = next(e for e in big.per_action if e.action is ActionType.FOLD).frequency
    assert f_big > f_small


def test_draw_vs_big_lead_calls_not_raises():
    # Refuter HIGH repro (end-to-end): BB Jc-Tc (OESD) on dry Qh-9d-4c faces a
    # 1.0x-pot lead (2.5 on 2.5) from the BTN limper — edge reads "villain",
    # board is dry. Pre-fix the flat draw raise merit crossed over the
    # price-decayed call/fold and RAISE graded best; §4b-2 says a big
    # limped-pot lead is value-heavy: defend the draw at a price. CALL must
    # be the best action and grade OPTIMAL; RAISE must not be best.
    state = _limped_hu_preflop(Position.BB, limper=Position.BTN)
    state = _play(state, [_check(Position.BB), _bet(Position.BTN, 2.5)])
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None and spot.node_context == [NodeContext.LIMPED_VS_LEAD]
    spot = spot.model_copy(
        update={
            "board": ["Qh", "9d", "4c"],
            "hero": spot.hero.model_copy(update={"hole_cards": ("Jc", "Tc")}),
        }
    )
    res = grade_limped_vs_lead(spot, None, None, Decision(action=ActionType.CALL))
    assert res.best_action.action is not ActionType.RAISE
    assert res.best_action.action is ActionType.CALL
    assert res.correctness is Correctness.OPTIMAL


def test_draw_raise_best_only_wet_plus_hero_edge_sweep():
    # Mechanical sweep (refuter-mandated): all 5 RECOGNIZED_BET_FRACS ×
    # edge{hero,neutral,villain} × texture{wet,dry} for the "draw" category.
    # RAISE may be the best action ONLY in wet + hero-edge cells (§4b's one
    # sanctioned semibluff-raise condition); everywhere else CALL or FOLD
    # must win — in particular RAISE is NEVER best on dry or vs villain edge.
    # "Best" = strictly-greater merit, matching the grader's tie resolution
    # (fold/call precede raise in the eval order, so a tie never picks raise).
    from app.domain.postflop import _merits_limped_vs_lead
    from app.domain.table.sizing import RECOGNIZED_BET_FRACS
    from app.domain.texture import classify

    wet = classify(["9h", "8h", "6d"])
    dry = classify(["Kh", "7d", "2s"])
    assert wet.wetness == "wet" and dry.wetness == "dry"
    raise_best_cells = set()
    for tex, tname in ((wet, "wet"), (dry, "dry")):
        for edge in ("hero", "neutral", "villain"):
            for frac in RECOGNIZED_BET_FRACS:
                price = frac / (1.0 + frac)  # bet/(pot+bet): the graders' price
                m_fold, m_call, m_raise = _merits_limped_vs_lead(edge, price, tex, "draw")
                if m_raise > max(m_fold, m_call):
                    raise_best_cells.add((tname, edge, frac))
    assert all(cell[:2] == ("wet", "hero") for cell in raise_best_cells), raise_best_cells
    # the sanctioned semibluff cells actually exist (the knob isn't dead):
    assert raise_best_cells, "semibluff-raise never best — wet+hero knob is dead"


# ------------------------------ (a) belt: organic bot-driven fires (fixed seed)


def test_limped_flop_mappers_fire_on_organic_play():
    """Same method as test_limper_coverage_belt: hero seat 0 plays a
    limp-happy persona proxy (calling_station), button rotates, lineup
    shuffled per hand, one seeded Random. Both new mappers must fire on
    organic HU limped flops (measured at this seed: lead 86, vs_lead 21
    per 1500 hands)."""
    from app.domain.personas import load_persona_packs
    from app.domain.table.play import assign_lineup, bot_decision

    packs = load_persona_packs()
    hero_pack = packs["calling_station"]
    rng = random.Random(20260722)
    fires: dict[str, int] = {}
    for hand_no in range(1500):
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
                if state.street is Street.FLOP:
                    spot = map_decision_point(state, HERO_SEAT)
                    if spot is not None and spot.node_context[0] in (
                        NodeContext.LIMPED_LEAD, NodeContext.LIMPED_VS_LEAD
                    ):
                        key = spot.node_context[0].value
                        fires[key] = fires.get(key, 0) + 1
                dec = bot_decision(state, seat, hero_pack, rng)
            else:
                dec = bot_decision(state, seat, seat_packs[seat], rng)
            state = apply(state, dec)
    assert fires.get("limped_lead", 0) >= 1, f"lead never fired: {fires}"
    assert fires.get("limped_vs_lead", 0) >= 1, f"vs_lead never fired: {fires}"
