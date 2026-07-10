"""RNG statistical suite for the table deck (deferred from S1, added in S2).

Spec: docs/ai-dlc/specs/simulate-s2.md "RNG statistical suite". Unmarked
(no pytest markers per repo convention); seeded `random.Random(20260710)`;
whole-file runtime budget < 10s.

Two layers:
- 200k raw shuffles of the exact deck.py deck (bypasses DealtHand/Pydantic
  construction — contract-mapper note 13: 200k full deal_hand calls would
  run Pydantic validation on 23 cards each and blow the time budget).
  Feeds a card x slot chi-square goodness-of-fit AND pocket-pair/suited
  rates derived from the same shuffles (first 18 slots == 9 hole-card pairs
  in deck.py's deal order).
- 5k full deal_hand(rng) calls proving the wrapper preserves the same
  distribution and produces no duplicate cards within a single deal.
"""

from __future__ import annotations

import random
import time

from app.domain.table.deck import deal_hand

RANKS = "23456789TJQKA"
SUITS = "cdhs"
_DECK = [r + s for r in RANKS for s in SUITS]  # same construction as deck.py

SEED = 20260710
N_SHUFFLES = 200_000
SLOTS = 18  # first 18 dealt slots == 9 seats x 2 hole cards (deck.py deal order)

# chi-square critical value, d.f. = 18 slots x 52 cards - ... treated as a
# 918-cell goodness-of-fit sum (52 cards x 18 slots), p = 0.001 upper tail.
# Wilson-Hilferty cube-root approximation: chi2 ~= df*(1 - 2/(9df) + z*sqrt(2/(9df)))^3
# with z = norm_ppf(0.999) = 3.09023230... gives chi2_0.999,918 ~= 1056.15.
# Hardcoded here (generous) per ticket instruction; stdlib only, no scipy/numpy.
CHI2_CRITICAL_918_P001 = 1057.0


def _raw_shuffle_batch(rng: random.Random, n: int) -> tuple[list[list[int]], int, int, int]:
    """Run `n` raw shuffles of the deck.py-equivalent deck.

    Returns (counts[slot][card_idx], pair_count, suited_count, hand_count)
    over the first SLOTS dealt cards, treating consecutive pairs as 9 hole
    hands per shuffle (matching deck.py's deal order: 2 consecutive cards
    per seat, seats 0-8).
    """
    card_idx = {c: i for i, c in enumerate(_DECK)}
    counts = [[0] * 52 for _ in range(SLOTS)]
    deck = list(_DECK)
    pair = 0
    suited = 0
    hands = 0
    for _ in range(n):
        rng.shuffle(deck)
        for slot in range(SLOTS):
            counts[slot][card_idx[deck[slot]]] += 1
        for seat in range(SLOTS // 2):
            a, b = deck[seat * 2], deck[seat * 2 + 1]
            hands += 1
            if a[0] == b[0]:
                pair += 1
            if a[1] == b[1]:
                suited += 1
    return counts, pair, suited, hands


def test_rng_suite_raw_shuffle_chi_square_and_deal_hand_distribution():
    """Single seeded pass covering: chi-square uniformity, raw-shuffle
    pair/suited rates, and 5k deal_hand pair/suited + no-duplicate checks.
    Combined into one test so the measured runtime is reported once.
    """
    t0 = time.perf_counter()
    rng = random.Random(SEED)

    counts, pair, suited, hands = _raw_shuffle_batch(rng, N_SHUFFLES)

    # --- chi-square goodness-of-fit: card x slot, summed over 18 slots x 52 cards ---
    expected = N_SHUFFLES / 52
    chi2 = 0.0
    for slot in range(SLOTS):
        for c in range(52):
            o = counts[slot][c]
            chi2 += (o - expected) ** 2 / expected
    assert chi2 < CHI2_CRITICAL_918_P001, (
        f"chi2={chi2} exceeds critical value {CHI2_CRITICAL_918_P001} (d.f.=918, p=0.001)"
    )

    # --- pocket-pair / suited rates from the raw shuffles (9 hands/shuffle) ---
    pair_rate = pair / hands * 100
    suited_rate = suited / hands * 100
    assert abs(pair_rate - 5.882) <= 0.3, f"raw-shuffle pair rate {pair_rate} out of tolerance"
    assert abs(suited_rate - 23.529) <= 0.3, (
        f"raw-shuffle suited rate {suited_rate} out of tolerance"
    )

    # --- 5k full deal_hand(rng) calls: distribution + no duplicate cards ---
    deal_pair = 0
    deal_suited = 0
    deal_hands = 0
    n_deals = 5_000
    for _ in range(n_deals):
        dealt = deal_hand(rng)
        all_cards = [c for hole in dealt.hole_cards for c in hole] + dealt.board
        assert len(set(all_cards)) == 23, "duplicate card within a single deal_hand deal"
        for a, b in dealt.hole_cards:
            deal_hands += 1
            if a[0] == b[0]:
                deal_pair += 1
            if a[1] == b[1]:
                deal_suited += 1

    deal_pair_rate = deal_pair / deal_hands * 100
    deal_suited_rate = deal_suited / deal_hands * 100
    assert abs(deal_pair_rate - 5.882) <= 1.5, (
        f"deal_hand pair rate {deal_pair_rate} out of tolerance"
    )
    assert abs(deal_suited_rate - 23.529) <= 1.5, (
        f"deal_hand suited rate {deal_suited_rate} out of tolerance"
    )

    elapsed = time.perf_counter() - t0
    print(f"\ntest_rng_suite runtime: {elapsed:.2f}s")
    assert elapsed < 10.0, f"RNG suite runtime {elapsed:.2f}s exceeds 10s budget"
