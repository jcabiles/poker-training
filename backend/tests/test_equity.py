import random
import time

from app.domain.equity import (
    class_to_combos,
    combos_for_range,
    equity_vs_range,
)


def test_aa_vs_kk_preflop():
    hero = ("As", "Ah")
    villain = combos_for_range("KK", frozenset(hero))
    eq = equity_vs_range(hero, [], villain, iters=4000, rng=random.Random(1))
    assert 0.79 <= eq <= 0.85  # ~0.82


def test_nut_straight_is_one():
    # A-K-Q-J-T broadway straight, no flush possible; villain pairs all lose.
    hero = ("Ah", "Ks")
    board = ["Qc", "Jd", "Th", "7s", "2d"]  # complete board, no runout
    villain = combos_for_range("99-22", frozenset(hero) | set(board))
    eq = equity_vs_range(hero, board, villain, iters=500, rng=random.Random(2))
    assert eq == 1.0


def test_crushed_is_near_zero():
    hero = ("2c", "7d")
    board = ["As", "Ah", "Kd"]
    villain = combos_for_range("AA,KK,AK", frozenset(hero) | set(board))
    eq = equity_vs_range(hero, board, villain, iters=2000, rng=random.Random(3))
    assert eq < 0.15


def test_deterministic_with_seed():
    hero = ("As", "Ah")
    villain = combos_for_range("QQ", frozenset(hero))
    a = equity_vs_range(hero, [], villain, iters=800, rng=random.Random(42))
    b = equity_vs_range(hero, [], villain, iters=800, rng=random.Random(42))
    assert a == b


def test_blocked_combos_excluded():
    # All four aces are dead -> villain "AA" has zero valid combos -> 0.0.
    hero = ("As", "Ad")
    board = ["Ah", "Ac", "Kd"]
    villain = combos_for_range("AA", frozenset(hero) | set(board))
    assert villain == []
    assert equity_vs_range(hero, board, villain, iters=100, rng=random.Random(4)) == 0.0


def test_class_to_combos_counts():
    assert len(class_to_combos("AA")) == 6
    assert len(class_to_combos("AKs")) == 4
    assert len(class_to_combos("AKo")) == 12


def test_perf_guard():
    hero = ("Ah", "Kh")
    board = ["Qh", "7d", "2c"]
    villain = combos_for_range("22+,A2s+,KTs+,QJs", frozenset(hero) | set(board))
    t0 = time.perf_counter()
    equity_vs_range(hero, board, villain, iters=1000, rng=random.Random(5))
    assert time.perf_counter() - t0 < 0.6
