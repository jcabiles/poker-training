"""Villain range estimator (villain-range V1) — posterior math, replay
equivalence, NO-PEEK, dead-card granularity, through_action, perf.

Spec: docs/ai-dlc/specs/simulate-villain-range.md.
"""

from __future__ import annotations

import random
import time

import pytest

from app.domain.action import Decision
from app.domain.archetypes import VillainType
from app.domain.content.notation import parse_range
from app.domain.personas import load_persona_packs
from app.domain.spot import RANKS, SUITS, ActionType, PlayerStatus, Position, Street
from app.domain.table.deck import DealtHand, deal_hand, positions_for_button
from app.domain.table.engine import HandState, apply, legal_actions, start_hand
from app.domain.table.play import _preflop_facing, assign_lineup, bot_decision
from app.domain.table.range_estimate import (
    PublicAction,
    PublicActionHistory,
    _replay_contexts,
    estimate_range,
)

_DECK = [r + s for r in RANKS for s in SUITS]
_STACKS = (100.0,) * 9
_RAISE_NAMES = ("raise", "3bet", "4bet", "5bet_shove")


@pytest.fixture(scope="module")
def packs():
    return load_persona_packs()


# ------------------------------------------------------------- helpers


def _project(state: HandState, starting_stacks=_STACKS) -> PublicActionHistory:
    """Test-side projection of a real HandState — reads ONLY public fields."""
    pos2seat = {s.position: s.seat for s in state.seats}
    return PublicActionHistory(
        button_seat=state.button_seat,
        starting_stacks_bb=tuple(starting_stacks),
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


def _hand_history(button: int, actions, board=()) -> PublicActionHistory:
    """Hand-built projection: blinds posted, then (seat, street, action, amount
    INCREMENT) tuples."""
    pos = positions_for_button(button)
    sb, bb = (button + 1) % 9, (button + 2) % 9
    acts = [
        PublicAction(
            seat=sb, position=pos[sb], street=Street.PREFLOP, action=ActionType.POST, amount_bb=0.5
        ),
        PublicAction(
            seat=bb, position=pos[bb], street=Street.PREFLOP, action=ActionType.POST, amount_bb=1.0
        ),
    ]
    for seat, street, action, amt in actions:
        acts.append(
            PublicAction(seat=seat, position=pos[seat], street=street, action=action, amount_bb=amt)
        )
    return PublicActionHistory(
        button_seat=button, starting_stacks_bb=_STACKS, board=tuple(board), actions=tuple(acts)
    )


def _dealt_fixed(villain_cards, board, villain_seat=3) -> DealtHand:
    """Deterministic deal: every non-villain seat gets the SAME cards across
    calls (pool excludes both villain variants + the board)."""
    reserved = set(board) | {"As", "Ad", "7c", "2d"}
    pool = [c for c in _DECK if c not in reserved]
    hole, k = [], 0
    for seat in range(9):
        if seat == villain_seat:
            hole.append(tuple(villain_cards))
        else:
            hole.append((pool[k], pool[k + 1]))
            k += 2
    return DealtHand(hole_cards=hole, board=list(board))


def _script(state: HandState, moves) -> HandState:
    """Apply (expected_seat, Decision) moves, asserting turn order."""
    for seat, decision in moves:
        assert state.to_act_seat == seat, f"expected seat {seat}, got {state.to_act_seat}"
        state = apply(state, decision)
    return state


def _raise_classes(pack, facing: str, position: Position) -> set[str]:
    """Classes with positive raise-family mass at the node — hand-computed
    from the pack json (first-match-wins mix semantics)."""
    for node in pack.preflop:
        if node.facing != facing:
            continue
        if node.positions is not None and position not in node.positions:
            continue
        covered: set[str] = set()
        out: set[str] = set()
        for mix in node.mixes:
            combos = parse_range(mix.combos) - covered
            covered |= combos
            if any(n in _RAISE_NAMES and w > 0 for n, w in mix.weights.items()):
                out |= combos
        return out
    raise AssertionError(f"no node for {facing}/{position}")


def _positive(res) -> set[str]:
    return {c for c, w in res.class_weights.items() if w > 0}


_FOLD = Decision(action=ActionType.FOLD)
_CALL = Decision(action=ActionType.CALL)
_CHECK = Decision(action=ActionType.CHECK)


def _raise_to(size: float) -> Decision:
    return Decision(action=ActionType.RAISE, size_bb=size)


def _bet(size: float) -> Decision:
    return Decision(action=ActionType.BET, size_bb=size)


# ------------------------------------------------ preflop pack posterior


def test_btn_open_matches_rfi_mix(packs):
    tag = packs[VillainType.TAG]
    # button=0: SB=1, BB=2, UTG=3 acts first; folds to the BTN who opens.
    hist = _hand_history(
        0,
        [(s, Street.PREFLOP, ActionType.FOLD, 0.0) for s in range(3, 9)]
        + [(0, Street.PREFLOP, ActionType.RAISE, 3.0)],
    )
    res = estimate_range(tag, hist, seat=0)
    assert res.exact is True
    assert _positive(res) == _raise_classes(tag, "unopened", Position.BTN)
    assert sum(res.class_weights.values()) == pytest.approx(1.0)


def _four_bet_history():
    # button=0: UTG (seat 3) opens 3bb, BTN 3-bets to 9, UTG 4-bets to 21.
    # Amounts are INCREMENTS: UTG's 4-bet adds 18 on top of the 3 invested.
    return _hand_history(
        0,
        [(3, Street.PREFLOP, ActionType.RAISE, 3.0)]
        + [(s, Street.PREFLOP, ActionType.FOLD, 0.0) for s in range(4, 9)]
        + [
            (0, Street.PREFLOP, ActionType.RAISE, 9.0),
            (1, Street.PREFLOP, ActionType.FOLD, 0.0),
            (2, Street.PREFLOP, ActionType.FOLD, 0.0),
            (3, Street.PREFLOP, ActionType.RAISE, 18.0),
        ],
    )


def test_four_bet_line_strict_subset_and_hand_computed_posterior(packs):
    tag = packs[VillainType.TAG]
    hist = _four_bet_history()
    open_res = estimate_range(tag, hist, seat=3, through_action=3)  # posts + open only
    four_res = estimate_range(tag, hist, seat=3)
    assert open_res.exact is True and four_res.exact is True
    open_set, four_set = _positive(open_res), _positive(four_res)
    assert four_set < open_set  # strict subset
    # tag.json: UTG open ∩ vs_3bet raise-mass = {KK+, AKs @1.0} ∪ {AQo @0.4}
    # (A5s 4-bets but is outside the UTG open range).
    assert four_set == {"AA", "KK", "AKs", "AQo"}
    # Hand-computed posterior ratio: AA = 6 combos × (1.0 × 1.0);
    # AQo = 12 combos × (1.0 × 0.4) → AA/AQo = 6/4.8 = 1.25.
    assert four_res.class_weights["AA"] / four_res.class_weights["AQo"] == pytest.approx(1.25)


# ------------------------------------------------------------- NO-PEEK


def _no_peek_state(villain_cards) -> HandState:
    dealt = _dealt_fixed(villain_cards, ["Kh", "7d", "2c", "9s", "3h"])
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)
    moves = [(3, _raise_to(3.0))]
    moves += [(s, _FOLD) for s in (4, 5, 6, 7, 8, 0, 1)]
    moves += [(2, _CALL)]
    moves += [(2, _CHECK), (3, _bet(3.0)), (2, _CALL)]  # flop
    moves += [(2, _CHECK), (3, _bet(6.0))]  # turn (mid-street stop)
    return _script(state, moves)


def test_no_peek_identical_weights_across_villain_cards(packs):
    tag = packs[VillainType.TAG]
    res_a = estimate_range(tag, _project(_no_peek_state(("As", "Ad"))), seat=3)
    res_b = estimate_range(tag, _project(_no_peek_state(("7c", "2d"))), seat=3)
    assert res_a.exact is False
    assert res_a.class_weights == res_b.class_weights
    assert res_a.combo_weights == res_b.combo_weights


# --------------------------------------------- replay reconstruction


def _true_ctx(state: HandState, seat: int):
    """Ground-truth decision context, read the way play.bot_decision reads it."""
    kinds = frozenset(la.action for la in legal_actions(state))
    facing = _preflop_facing(state) if state.street is Street.PREFLOP else None
    return (
        state.street,
        tuple(state.board),
        state.seats[seat].position,
        facing,
        kinds,
        sum(s.invested_total_bb for s in state.seats),
        state.seats[seat].stack_bb,
        sum(
            1
            for s in state.seats
            if s.seat != seat and s.status in (PlayerStatus.IN, PlayerStatus.ALLIN)
        ),
        state.current_bet_bb,
    )


def _assert_ctx_equal(ctx, truth, observed):
    street, board, position, facing, kinds, pot, stack, opp, cur = truth
    assert ctx.street is street
    assert ctx.board == board
    assert ctx.position is position
    assert ctx.facing == facing
    assert ctx.kinds == kinds
    assert ctx.pot_bb == pytest.approx(pot, abs=1e-9)
    assert ctx.stack_bb == pytest.approx(stack, abs=1e-9)
    assert ctx.opponents == opp
    assert ctx.current_bet_to == pytest.approx(cur, abs=1e-9)
    assert ctx.observed is observed


def test_replay_matches_real_handstate_contexts(packs):
    """Full persona playouts: every seat's replayed contexts equal the real
    HandState contexts at each decision (facing, kinds, pot, stack, SPR inputs)."""
    rng = random.Random(20260712)
    for trial in range(6):
        personas = assign_lineup(rng)
        seat_packs = {s: packs[personas.get(s, VillainType.TAG)] for s in range(9)}
        dealt = deal_hand(random.Random(rng.randrange(1_000_000_000)))
        state = start_hand(dealt, button_seat=trial % 9, stacks_bb=[100.0] * 9)
        truth: dict[int, list] = {s: [] for s in range(9)}
        guard = 0
        while not state.hand_over and state.to_act_seat is not None:
            guard += 1
            assert guard < 500
            seat = state.to_act_seat
            snapshot = _true_ctx(state, seat)
            decision = bot_decision(state, seat, seat_packs[seat], rng)
            truth[seat].append((snapshot, decision.action))
            state = apply(state, decision)
        hist = _project(state)
        for seat in range(9):
            ctxs = _replay_contexts(hist, seat, len(hist.actions))
            assert len(ctxs) == len(truth[seat])
            for ctx, (snapshot, observed) in zip(ctxs, truth[seat], strict=True):
                _assert_ctx_equal(ctx, snapshot, observed)


def test_multiway_limp_raise_facing_reconstruction():
    """Scripted limps + raise + cold-calls: replayed preflop facing equals
    play._preflop_facing on the real state at every decision index."""
    dealt = _dealt_fixed(("As", "Ad"), ["Kh", "7d", "2c", "9s", "3h"])
    state = start_hand(dealt, button_seat=8, stacks_bb=[100.0] * 9)  # SB=0 BB=1 UTG=2
    moves = [
        (2, _CALL),  # limp -> unopened
        (3, _CALL),  # limp -> vs_limpers
        (4, _raise_to(4.0)),  # iso-raise -> vs_limpers
        (5, _CALL),  # -> vs_rfi
        (6, _FOLD),
        (7, _FOLD),
        (8, _FOLD),
        (0, _FOLD),
        (1, _CALL),
        (2, _CALL),
        (3, _raise_to(12.0)),  # limp-raise -> vs_rfi
    ]
    truth: dict[int, list[str]] = {}
    expected_facings = []
    for seat, decision in moves:
        assert state.to_act_seat == seat
        facing = _preflop_facing(state)
        expected_facings.append(facing)
        truth.setdefault(seat, []).append(facing)
        state = apply(state, decision)
    assert expected_facings[:5] == ["unopened", "vs_limpers", "vs_limpers", "vs_rfi", "vs_rfi"]
    hist = _project(state)
    for seat, facings in truth.items():
        ctxs = _replay_contexts(hist, seat, len(hist.actions))
        assert [c.facing for c in ctxs] == facings


# ------------------------------------------------- postflop narrowing


def test_postflop_barrel_narrows_toward_strength(packs):
    """After a TAG c-bet on dry Kh7d2c, aggregate weight shifts toward strong
    classes vs the preflop-only posterior (fails under a no-op reweight)."""
    tag = packs[VillainType.TAG]
    dealt = _dealt_fixed(("As", "Ad"), ["Kh", "7d", "2c", "Qs", "3d"])
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)
    moves = [(3, _raise_to(3.0))]
    moves += [(s, _FOLD) for s in (4, 5, 6, 7, 8, 0, 1)]
    moves += [(2, _CALL), (2, _CHECK), (3, _bet(4.5))]
    state = _script(state, moves)
    hist = _project(state)
    prior = estimate_range(tag, hist, seat=3, through_action=len(hist.actions) - 1)
    posterior = estimate_range(tag, hist, seat=3)
    assert prior.exact is True  # no villain postflop action in the prefix
    assert posterior.exact is False
    strong = {"AA", "KK", "77", "AKs", "AKo"}
    prior_share = sum(prior.class_weights[c] for c in strong)
    post_share = sum(posterior.class_weights[c] for c in strong)
    assert post_share > prior_share + 0.02


# ------------------------------------------- dead cards / through_action


def test_dead_cards_reduce_ako_zero_only_blocked_akss(packs):
    tag = packs[VillainType.TAG]
    hist = _hand_history(
        0,
        [(s, Street.PREFLOP, ActionType.FOLD, 0.0) for s in range(3, 9)]
        + [(0, Street.PREFLOP, ActionType.RAISE, 3.0)],
    )
    free = estimate_range(tag, hist, seat=0)
    dead = estimate_range(tag, hist, seat=0, dead_cards=("Ah", "Ks"))
    # Every combo containing a dead card is zero.
    for (c1, c2), w in dead.combo_weights.items():
        if "Ah" in (c1, c2) or "Ks" in (c1, c2):
            assert w == 0.0
    # AKo: reduced, not zeroed — 7 of 12 combos survive.
    ako_live = [
        c
        for c, w in dead.combo_weights.items()
        if w > 0 and {c[0][0], c[1][0]} == {"A", "K"} and c[0][1] != c[1][1]
    ]
    assert len(ako_live) == 7
    assert 0 < dead.class_weights["AKo"] < free.class_weights["AKo"]
    # AKs: drops ONLY the blocked combos (AhKh, AsKs); clubs/diamonds survive.
    assert dead.combo_weights[("Kh", "Ah")] == 0.0
    assert dead.combo_weights[("Ks", "As")] == 0.0
    assert dead.combo_weights[("Kc", "Ac")] > 0.0
    assert dead.combo_weights[("Kd", "Ad")] > 0.0


def test_through_action_prefix(packs):
    tag = packs[VillainType.TAG]
    hist = _four_bet_history()
    open_only = estimate_range(tag, hist, seat=3, through_action=3)
    assert _positive(open_only) == _raise_classes(tag, "unopened", Position.UTG)
    full = estimate_range(tag, hist, seat=3)
    assert _positive(open_only) != _positive(full)
    clamped = estimate_range(tag, hist, seat=3, through_action=len(hist.actions))
    assert clamped == full


# ---------------------------------------------------------------- perf


def test_river_depth_estimate_under_150ms(packs):
    tag = packs[VillainType.TAG]
    dealt = _dealt_fixed(("As", "Ad"), ["Kh", "7d", "2c", "Qs", "3d"])
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)
    moves = [(3, _raise_to(3.0))]
    moves += [(s, _FOLD) for s in (4, 5, 6, 7, 8, 0, 1)]
    moves += [(2, _CALL)]
    moves += [(2, _CHECK), (3, _bet(3.0)), (2, _CALL)]  # flop
    moves += [(2, _CHECK), (3, _bet(7.0)), (2, _CALL)]  # turn
    moves += [(2, _CHECK), (3, _bet(15.0))]  # river
    state = _script(state, moves)
    hist = _project(state)
    t0 = time.perf_counter()
    res = estimate_range(tag, hist, seat=3, dead_cards=("Tc", "Td"))
    elapsed = time.perf_counter() - t0
    assert res.exact is False
    assert elapsed < 0.15, f"river-depth estimate took {elapsed * 1000:.1f}ms"
