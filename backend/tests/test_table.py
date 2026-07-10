import random

from app.domain.spot import RANKS, SUITS, Position
from app.domain.table import DealtHand, deal_hand, positions_for_button


def test_fixed_seed_deals_exact_expected_cards():
    """Known seed ⇒ exact expected 18 hole + 5 board cards (deterministic deal order)."""
    dealt = deal_hand(random.Random(42))
    assert dealt.hole_cards == [
        ("4d", "7s"),
        ("8d", "2s"),
        ("7d", "Jh"),
        ("6c", "Js"),
        ("6s", "4s"),
        ("Kh", "8c"),
        ("Td", "9d"),
        ("9s", "Qs"),
        ("3c", "9c"),
    ]
    assert dealt.board == ["4h", "8h", "Jc", "2c", "Kc"]


def test_deal_hand_returns_dealt_hand_model():
    dealt = deal_hand(random.Random(1))
    assert isinstance(dealt, DealtHand)
    assert len(dealt.hole_cards) == 9
    assert len(dealt.board) == 5


def test_deal_hand_uses_52_distinct_cards_no_repeats():
    dealt = deal_hand(random.Random(7))
    full_deck = {r + s for r in RANKS for s in SUITS}
    consumed = [c for pair in dealt.hole_cards for c in pair] + dealt.board
    assert len(consumed) == 23  # 18 hole + 5 board
    assert len(set(consumed)) == 23  # no repeats
    assert set(consumed).issubset(full_deck)


def test_deal_hand_is_reproducible_for_same_seed():
    a = deal_hand(random.Random(99))
    b = deal_hand(random.Random(99))
    assert a == b


def test_deal_hand_varies_across_seeds():
    a = deal_hand(random.Random(1))
    b = deal_hand(random.Random(2))
    assert a != b


def test_positions_for_button_zero_matches_worked_example():
    assert positions_for_button(0) == [
        Position.BTN,
        Position.SB,
        Position.BB,
        Position.UTG,
        Position.UTG1,
        Position.UTG2,
        Position.LJ,
        Position.HJ,
        Position.CO,
    ]


def test_positions_for_button_two_puts_btn_at_seat_two():
    result = positions_for_button(2)
    assert result[2] == Position.BTN
    assert result[3] == Position.SB  # clockwise = ascending seat index mod 9
    assert result[1] == Position.CO  # wraps around


def test_positions_for_button_every_seat_valid_and_exactly_one_btn():
    for button_seat in range(9):
        result = positions_for_button(button_seat)
        assert len(result) == 9
        assert all(isinstance(p, Position) for p in result)
        assert sum(1 for p in result if p == Position.BTN) == 1
        assert set(result) == set(Position)  # all 9 positions present exactly once
