"""M4 (RES-H H1) — caller-re-raises-c-bet: mapper + grader pass/fail suite.

Covers the RES-H §5-H1 verbatim pass/fail items:
  1. belt-test: the mapper fires non-zero and in-band on organic seeded bot play;
  2. grader shape: freq+EV over {fold,call,raise} + sizing_correctness, never a
     boolean, `is_mixed` correct;
  3. range asymmetry: fixed marginal weak_made hand -> caller-raise FOLD freq
     strictly above `grade_vs_check_raise`'s; a strong hand continues in both;
  4. α NOT applied: no `_calibrate_catcher_fold` in the grader, and a marginal
     hand folds ABOVE the α ceiling for the faced size;
  5. `_apply_multiway` composes on the facing side when the spot is 3-live;
  7. every off-shape line (donk-raise, limped, delayed c-bet, hero-not-opener,
     BB 3-bet of the raise, off-grid c-bet) returns None.
(Item 6 — existing HU/3-way grader outputs byte-identical — is pinned by the
existing suite: tests/test_signature.py hash pins + tests/test_postflop.py.)
"""

from __future__ import annotations

import inspect
import random

from app.domain.action import Decision
from app.domain.leaks import LeakCategory
from app.domain.personas import load_persona_packs
from app.domain.postflop import (
    _hand_category,
    _merits_vs_caller_raise,
    grade_vs_caller_raise,
    grade_vs_check_raise,
)
from app.domain.scenarios import _OPEN_SIZE, _SEAT_ORDER
from app.domain.spot import (
    ActionType,
    GameConfig,
    Hero,
    HistoryAction,
    LegalAction,
    NodeContext,
    PlayerState,
    Position,
    Spot,
    Stakes,
    Street,
    players_in_pot,
)
from app.domain.table.deck import deal_hand
from app.domain.table.engine import HandState, apply, start_hand
from app.domain.table.grade_map import map_decision_point
from app.domain.table.grade_map_postflop import map_flop_vs_caller_raise
from app.domain.table.play import assign_lineup, bot_decision

HERO_SEAT = 0
_BLINDS = {Position.SB, Position.BB}
_BUTTON_FOR_HERO = {
    Position.BTN: 0, Position.SB: 8, Position.BB: 7,
    Position.UTG: 6, Position.UTG1: 5, Position.UTG2: 4,
    Position.LJ: 3, Position.HJ: 2, Position.CO: 1,
}


# ------------------------------------------------------------ state helpers


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


def _raise_to(pos, size):
    return (pos, Decision(action=ActionType.RAISE, size_bb=size))


def _srp_preflop(opener=Position.CO, caller=Position.BTN, bb_in=True):
    """Hero = the opener: opener raises canonical, `caller` cold-calls, SB
    folds, BB calls (bb_in) or folds."""
    state = _state(opener)
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        if p is opener:
            moves.append(_raise_to(p, _OPEN_SIZE[opener]))
        elif p is caller:
            moves.append(_call(p))
        else:
            moves.append(_fold(p))
    moves += [_fold(Position.SB), _call(Position.BB) if bb_in else _fold(Position.BB)]
    return _play(state, moves)


def _flop_pot(opener, bb_in=True):
    return round(
        (3 * _OPEN_SIZE[opener] + 0.5) if bb_in else (2 * _OPEN_SIZE[opener] + 1.5), 2
    )


def _caller_raise_state(
    opener=Position.CO, caller=Position.BTN, bb_in=True, bb_resp="fold",
    cbet_frac=0.33, raise_mult=3.0,
):
    """Full line to hero's caller-raise decision point. Returns
    (state, cbet, raise_to)."""
    state = _srp_preflop(opener, caller, bb_in)
    fp = _flop_pot(opener, bb_in)
    cbet = round(cbet_frac * fp, 1)
    raise_to = round(raise_mult * cbet, 1)
    moves = []
    if bb_in:
        moves.append(_check(Position.BB))
    moves += [_bet(opener, cbet), _raise_to(caller, raise_to)]
    if bb_in:
        moves.append(_call(Position.BB) if bb_resp == "call" else _fold(Position.BB))
    return _play(state, moves), cbet, raise_to


# ------------------------------------------------------------- spot helpers


def _facing_spot(hole, board, ctx, villain, faced=5.0, pot=16.5):
    """A directly-built flop facing-a-raise spot (mirrors test_postflop's
    `_vscr_spot` inline-builder style): hero = the CO opener/c-bettor, now
    facing `villain`'s raise. `faced` is the incremental CALL amount; the
    RAISE legs give `_raise_sizing_verdict` two sizes to grade."""
    return Spot(
        game=GameConfig(stakes=Stakes(sb=0.5, bb=1.0), table_size=9),
        street=Street.FLOP,
        board=board,
        pot_bb=pot,
        hero=Hero(position=Position.CO, hole_cards=hole, stack_bb=100),
        players=[
            PlayerState(position=Position.CO, stack_bb=100, is_hero=True),
            PlayerState(position=villain, stack_bb=100),
        ],
        effective_stack_bb=100,
        spr=round(100 / pot, 1),
        to_act=Position.CO,
        node_context=[ctx],
        facing=villain,
        action_history=[
            HistoryAction(
                street=Street.FLOP, position=Position.CO,
                action=ActionType.BET, amount_bb=2.5,
            ),
            HistoryAction(
                street=Street.FLOP, position=villain,
                action=ActionType.RAISE, amount_bb=round(2.5 + faced, 2),
            ),
        ],
        legal_actions=[
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=faced),
            LegalAction(action=ActionType.RAISE, min_bb=round(2.5 * (2.5 + faced), 1), max_bb=100),
            LegalAction(action=ActionType.RAISE, min_bb=round(3.0 * (2.5 + faced), 1), max_bb=100),
        ],
        hero_range="22+, A2s+, KTs+, ATo+, KQo",
        villain_range="22-99, ATs+, KTs+, QJs, JTs",
    )


def _caller_spot(hole, board, **kw):
    return _facing_spot(hole, board, NodeContext.VS_CALLER_RAISE, Position.BTN, **kw)


def _cr_spot(hole, board, **kw):
    return _facing_spot(hole, board, NodeContext.VS_CHECK_RAISE, Position.BB, **kw)


def _freq(res, action):
    return next(e.frequency for e in res.per_action if e.action == action)


# ----------------------------------------------------- 1. belt-test firing


def test_mapper_fires_in_band_on_organic_play():
    """H1 pass/fail 1: on seeded organic bot play the mapper fires non-zero
    and in-band. RES-H §1.3 measured 16.8/1000 hands with ANY seat as the
    opener (an upper bound: it includes 4-way fields, oversize opens and
    off-grid c-bets this mapper deliberately rejects); measured post-M4 at
    this seed: 11 fires in 2000 hands. Band, not exact: floor 3 proves the
    funnel is open (the existing HU check-raise family fires ~0.17/1000);
    ceiling 60 (=30/1000, above the 16.8 upper bound) catches a gate gone
    vacuous."""
    packs = load_persona_packs()
    rng = random.Random(20260722)
    fires = 0
    for hand_no in range(2000):
        lineup = assign_lineup(rng)
        seat_packs = {s: packs[t.value] for s, t in lineup.items()}
        seat_packs.setdefault(HERO_SEAT, packs["tag"])
        state = start_hand(
            deal_hand(rng), button_seat=hand_no % 9, stacks_bb=[100.0] * 9
        )
        guard = 0
        while not state.hand_over and state.to_act_seat is not None:
            guard += 1
            assert guard <= 500, "bot playout did not terminate"
            seat = state.to_act_seat
            if map_flop_vs_caller_raise(state, seat) is not None:
                fires += 1
            state = apply(state, bot_decision(state, seat, seat_packs[seat], rng))
    assert 3 <= fires <= 60, f"caller-raise fires out of band: {fires} in 2000 hands"


# ------------------------------------------------- canonical shapes map


def test_three_way_bb_folds_maps_as_two_live():
    state, cbet, raise_to = _caller_raise_state(bb_resp="fold")
    assert state.to_act_seat == HERO_SEAT
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_CALLER_RAISE]
    assert players_in_pot(spot) == 2  # degrade-to-2-live, dead money stays
    assert spot.facing == Position.BTN
    fp = _flop_pot(Position.CO)
    assert spot.pot_bb == round(fp + cbet + raise_to, 2)
    call = next(la for la in spot.legal_actions if la.action is ActionType.CALL)
    assert call.min_bb == round(raise_to - cbet, 2)  # INCREMENTAL call


def test_three_way_bb_calls_maps_as_three_live():
    state, cbet, raise_to = _caller_raise_state(bb_resp="call")
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_CALLER_RAISE]
    assert players_in_pot(spot) == 3
    fp = _flop_pot(Position.CO)
    assert spot.pot_bb == round(fp + cbet + 2 * raise_to, 2)


def test_bb_folded_preflop_two_way_maps():
    state, cbet, raise_to = _caller_raise_state(bb_in=False)
    spot = map_decision_point(state, HERO_SEAT)
    assert spot is not None
    assert spot.node_context == [NodeContext.VS_CALLER_RAISE]
    assert players_in_pot(spot) == 2
    fp = _flop_pot(Position.CO, bb_in=False)
    assert spot.pot_bb == round(fp + cbet + raise_to, 2)


# ------------------------------------- 2. grader shape: freq+EV, never bool


def test_grader_freq_ev_shape_and_is_mixed():
    state, _cbet, _raise_to = _caller_raise_state()
    spot = map_decision_point(state, HERO_SEAT)
    res = grade_vs_caller_raise(spot, spot.hero_range, spot.villain_range, None)
    assert [e.action for e in res.per_action] == [
        ActionType.FOLD, ActionType.CALL, ActionType.RAISE,
    ]
    assert abs(sum(e.frequency for e in res.per_action) - 1.0) < 1e-6
    for e in res.per_action:
        assert isinstance(e.frequency, float) and not isinstance(e.frequency, bool)
        assert isinstance(e.ev_bb, float) and not isinstance(e.ev_bb, bool)
    assert res.is_mixed == (sum(1 for e in res.per_action if e.frequency > 0.20) >= 2)
    assert res.leak_category == int(LeakCategory.VS_CALLER_RAISE) == 207
    # A graded decision carries chosen_eval/correctness (freq+EV ladder).
    graded = grade_vs_caller_raise(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.FOLD)
    )
    assert graded.correctness is not None
    assert graded.chosen_eval is not None


def test_sizing_correctness_on_two_leg_raise():
    # A strong hand raising on a dry board: small leg = the RES-B teach.
    spot = _caller_spot(("As", "Ac"), ["Ah", "7d", "2c"])
    small_leg = min(
        la.min_bb for la in spot.legal_actions if la.action is ActionType.RAISE
    )
    res = grade_vs_caller_raise(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.RAISE, size_bb=small_leg),
    )
    assert res.sizing_correctness is not None


# --------------------------------------------------- 3. range asymmetry


def test_marginal_hand_folds_more_than_vs_check_raise():
    """H1 pass/fail 3: fixed marginal weak_made hand + texture + faced size —
    the caller-raise FOLD freq is strictly above grade_vs_check_raise's. The
    low/connected/wet board is the bluff-friendliest texture (bluffy maximal),
    exactly where the halved bluff credit must still out-fold the check-raise
    node. Positions chosen so `range_advantage` labels both spots identically
    ('villain' on 8h7h6c from CO vs either BB or BTN) — the freq gap is the
    §3.2 merit asymmetry alone, not a positional confound."""
    hole, board = ("As", "8d"), ["8h", "7h", "6c"]  # top pair -> weak_made
    assert _hand_category(hole, board) == "weak_made"
    car = grade_vs_caller_raise(_caller_spot(hole, board), None, None, None)
    cr = grade_vs_check_raise(_cr_spot(hole, board), None, None, None)
    assert _freq(car, ActionType.FOLD) > _freq(cr, ActionType.FOLD)
    # Also on a dry board (bluffy <= 0): the 1.9 baseline alone must out-fold.
    hole2, board2 = ("Kh", "Qc"), ["Ks", "7d", "2c"]
    assert _hand_category(hole2, board2) == "weak_made"
    car2 = grade_vs_caller_raise(_caller_spot(hole2, board2), None, None, None)
    cr2 = grade_vs_check_raise(_cr_spot(hole2, board2), None, None, None)
    assert _freq(car2, ActionType.FOLD) > _freq(cr2, ActionType.FOLD)


def test_strong_hand_continues_in_both_graders():
    hole, board = ("6s", "6d"), ["8h", "7h", "6c"]  # set -> strong
    assert _hand_category(hole, board) == "strong"
    car = grade_vs_caller_raise(_caller_spot(hole, board), None, None, None)
    cr = grade_vs_check_raise(_cr_spot(hole, board), None, None, None)
    for res in (car, cr):
        assert res.best_action.action in (ActionType.CALL, ActionType.RAISE)
        assert res.best_action.action != ActionType.FOLD


# --------------------------------------------------- 4. α is NOT applied


def test_alpha_clamp_not_called():
    """H1 pass/fail 4 (grep-level): neither the grader nor its merit function
    references `_calibrate_catcher_fold` in CODE (RES-H §3.4 — α is the
    flat-call form and must not clamp a raise-response). AST-walk, so the
    grader's own explanatory comment doesn't false-positive."""
    import ast
    import textwrap

    for fn in (grade_vs_caller_raise, _merits_vs_caller_raise):
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        assert "_calibrate_catcher_fold" not in names


def test_marginal_hand_may_fold_above_alpha_ceiling():
    """H1 pass/fail 4 (behavioral): the marginal catcher's fold share is NOT
    clamped to the α band. faced=5 into pot=16.5 -> α = 5/16.5 ≈ 0.303; the
    flat-call grader would cap the weak_made fold share there, this grader
    folds well above it."""
    hole, board = ("Kh", "Qc"), ["Ks", "7d", "2c"]
    assert _hand_category(hole, board) == "weak_made"
    spot = _caller_spot(hole, board, faced=5.0, pot=16.5)
    res = grade_vs_caller_raise(spot, spot.hero_range, spot.villain_range, None)
    alpha = 5.0 / 16.5
    assert _freq(res, ActionType.FOLD) > alpha


# --------------------------------------- 5. `_apply_multiway` composes


def test_multiway_composes_on_three_live_spot():
    """Same spot shape, 3-live vs BB-folded copy: the facing-side multiway
    tighten (fold up, call dampened) must move the weak_made frequencies.
    (That the MAPPER builds a 3-live spot when the BB calls the raise is
    pinned by test_three_way_bb_calls_maps_as_three_live.)"""
    spot = _caller_spot(("Kh", "Qc"), ["Ks", "7d", "2c"])  # weak_made
    spot = spot.model_copy(
        update={"players": [*spot.players, PlayerState(position=Position.BB, stack_bb=100)]}
    )
    assert players_in_pot(spot) == 3
    hu_like = spot.model_copy(
        update={
            "players": [
                p if p.is_hero or p.position == spot.facing
                else p.model_copy(update={"status": "folded"})
                for p in spot.players
            ]
        }
    )
    assert players_in_pot(hu_like) == 2
    mw_res = grade_vs_caller_raise(spot, spot.hero_range, spot.villain_range, None)
    hu_res = grade_vs_caller_raise(hu_like, hu_like.hero_range, hu_like.villain_range, None)
    assert _freq(mw_res, ActionType.FOLD) > _freq(hu_res, ActionType.FOLD)


# --------------------------------------------------- 7. off-shape -> None


def test_donk_raise_stays_none():
    # BB donk-leads, hero raises, caller re-raises: hero faces a raise but
    # never c-bet a checked-to flop — off-shape.
    state = _srp_preflop()
    fp = _flop_pot(Position.CO)
    donk = round(0.33 * fp, 1)
    state = _play(state, [
        _bet(Position.BB, donk),
        _raise_to(Position.CO, round(3 * donk, 1)),
        _raise_to(Position.BTN, round(9 * donk, 1)),
        _fold(Position.BB),
    ])
    assert state.to_act_seat == HERO_SEAT
    assert map_flop_vs_caller_raise(state, HERO_SEAT) is None
    assert map_decision_point(state, HERO_SEAT) is None


def test_limped_pot_stays_none():
    # No preflop raise: hero (BTN) over-limps... a limped pot has no opener.
    state = _state(Position.CO)
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        moves.append(_call(p) if p in (Position.CO, Position.BTN) else _fold(p))
    moves += [_fold(Position.SB), _check(Position.BB)]
    state = _play(state, moves)
    pot = round(2.0 * 2 + 2.0 + 0.5, 2)
    state = _play(state, [
        _check(Position.BB),
        _bet(Position.CO, round(0.33 * pot, 1)),
        _raise_to(Position.BTN, round(round(0.33 * pot, 1) * 3, 1)),
        _fold(Position.BB),
    ])
    assert state.to_act_seat == HERO_SEAT
    assert map_flop_vs_caller_raise(state, HERO_SEAT) is None
    assert map_decision_point(state, HERO_SEAT) is None


def test_delayed_cbet_raise_stays_none():
    # Flop checks through; hero bets the TURN and the caller raises — the
    # family is flop-only (len(board) == 3 gate).
    state = _srp_preflop()
    state = _play(state, [_check(Position.BB), _check(Position.CO), _check(Position.BTN)])
    fp = _flop_pot(Position.CO)
    tbet = round(0.5 * fp, 1)
    state = _play(state, [
        _check(Position.BB), _bet(Position.CO, tbet),
        _raise_to(Position.BTN, round(3 * tbet, 1)), _fold(Position.BB),
    ])
    assert state.to_act_seat == HERO_SEAT
    assert map_flop_vs_caller_raise(state, HERO_SEAT) is None
    assert map_decision_point(state, HERO_SEAT) is None


def test_hero_not_opener_stays_none():
    # Hero = the BB in the same 3-way caller-raise line: not this family
    # (and no other mapper claims it — RES-H: "no baseline yet").
    state = _state(Position.BB)
    opener, caller = Position.CO, Position.BTN
    moves = []
    for p in _SEAT_ORDER:
        if p in _BLINDS:
            continue
        if p is opener:
            moves.append(_raise_to(p, _OPEN_SIZE[opener]))
        elif p is caller:
            moves.append(_call(p))
        else:
            moves.append(_fold(p))
    moves += [_fold(Position.SB), _call(Position.BB)]
    state = _play(state, moves)
    fp = _flop_pot(opener)
    cbet = round(0.33 * fp, 1)
    state = _play(state, [
        _check(Position.BB), _bet(opener, cbet), _raise_to(caller, round(3 * cbet, 1)),
    ])
    assert state.to_act_seat == HERO_SEAT  # hero (BB) faces the raise
    assert map_flop_vs_caller_raise(state, HERO_SEAT) is None
    assert map_decision_point(state, HERO_SEAT) is None


def test_bb_reraise_stays_none():
    # BB 3-bets over the caller's raise instead of fold/call: hero no longer
    # closes vs the caller's raise — off-shape.
    state = _srp_preflop()
    fp = _flop_pot(Position.CO)
    cbet = round(0.33 * fp, 1)
    raise_to = round(3 * cbet, 1)
    state = _play(state, [
        _check(Position.BB), _bet(Position.CO, cbet),
        _raise_to(Position.BTN, raise_to),
        _raise_to(Position.BB, round(3 * raise_to, 1)),
    ])
    assert state.to_act_seat == HERO_SEAT
    assert map_flop_vs_caller_raise(state, HERO_SEAT) is None


def test_off_grid_cbet_stays_none():
    # A c-bet off the whole recognition grid (0.42-pot) gates the line.
    state, _cbet, _raise_to = _caller_raise_state(cbet_frac=0.42)
    assert state.to_act_seat == HERO_SEAT
    assert map_flop_vs_caller_raise(state, HERO_SEAT) is None


# ------------------------------------------- provider routing (end-to-end)


def test_provider_routes_caller_raise_spot():
    import asyncio

    from app.domain.providers.postflop import PostflopHeuristicProvider

    state, _cbet, _raise_to = _caller_raise_state()
    spot = map_decision_point(state, HERO_SEAT)
    provider = PostflopHeuristicProvider()
    assert asyncio.run(provider.supports(spot))
    res = asyncio.run(provider.evaluate(spot, Decision(action=ActionType.FOLD)))
    assert res.leak_category == int(LeakCategory.VS_CALLER_RAISE)
