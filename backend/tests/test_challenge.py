"""Tests for the Challenge-mode difficulty scorer + sampler (domain.challenge).

See docs/ai-dlc/specs/challenge-preflop-rfi.md ("Difficulty model") and the
T2 ticket's acceptance criteria — this file covers the spec's Verify-by tests
2 (cold-start distribution), 2b (position flip), 2c (edge score robustness),
and 2d (determinism).
"""

from __future__ import annotations

import random
from collections import Counter

from app.domain.challenge import (
    _rfi_grids,
    edge_score,
    sample_challenge_spot,
)
from app.domain.content.notation import hole_cards_to_class
from app.domain.scenarios import RFI_POSITIONS
from app.domain.spot import NodeContext, Position


def _sample_hand_classes(n: int, seed: int, **kw) -> list[tuple[Position, str]]:
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        spot = sample_challenge_spot(rng, **kw)
        out.append((spot.hero.position, hole_cards_to_class(*spot.hero.hole_cards)))
    return out


def test_sample_challenge_spot_is_a_valid_rfi_spot():
    spot = sample_challenge_spot(random.Random(0))
    assert spot.hero.position in RFI_POSITIONS
    assert NodeContext.RFI in spot.node_context
    assert spot.hero.hole_cards[0] != spot.hero.hole_cards[1]


# --- 2: seeded cold-start distribution ---
def test_cold_start_favors_boundary_hands_over_premiums_and_trash():
    """Boundary hands (position-flippy, near a range edge) must be sampled
    markedly more often than premiums (raise-everywhere) and trash
    (fold-everywhere) under pure objective difficulty (no personal history
    injected). Assert weight/frequency ORDERING, not exact counts.
    """
    samples = _sample_hand_classes(3000, seed=1)
    counts = Counter(hand for _, hand in samples)

    boundary = ["A9o", "KTo", "66", "54s"]
    premiums = ["AA", "AKs"]
    trash = ["72o"]

    boundary_total = sum(counts.get(h, 0) for h in boundary)
    premium_total = sum(counts.get(h, 0) for h in premiums)
    trash_total = sum(counts.get(h, 0) for h in trash)

    # Markedly more: an order-of-magnitude margin, not a hair's-breadth one.
    assert boundary_total > 10 * max(premium_total, trash_total, 1)

    for h in boundary:
        assert counts.get(h, 0) > counts.get("AA", 0)
        assert counts.get(h, 0) > counts.get("72o", 0)


# --- 2b: position-flip is exercised ---
def test_same_hand_is_sampled_at_both_a_raise_seat_and_a_fold_seat():
    """A9o is raised at CO/BTN/SB and folded at UTG/LJ/HJ in the RFI charts.
    Over enough draws, the sampler should hit both sides of that flip.
    """
    samples = _sample_hand_classes(3000, seed=2)
    grids = _rfi_grids()
    sampled_positions = {pos for pos, hand in samples if hand == "A9o"}
    assert len(sampled_positions) >= 2, "need at least 2 distinct seats to exercise the flip"

    actions = {grids[pos]["A9o"] for pos in sampled_positions}
    assert "raise" in actions
    assert "fold" in actions


# --- 2c: edge score is not fooled by trash that ranks near a loose floor ---
def test_edge_score_low_for_trash_near_rank_floor_high_for_transition_hand():
    """(refuter HIGH-1) 74o/82o/93o are unambiguous BTN folds that happen to
    rank close to BTN's loose floor under the coarse hand_rank strength
    PROXY. A naive "distance to nearest rank-order neighbor with a different
    action" would score them spuriously high, because a lone suited-connector
    "raise" can sit rank-order-adjacent to a sea of offsuit "fold" trash (the
    proxy isn't monotonic in playability). The local-disagreement-density
    edge score must not be fooled: these three should score LOW (they're
    each the local MAJORITY action in their own rank-order neighborhood).

    54s is the weakest suited connector BTN still opens — a hand genuinely at
    the edge of a raise/fold transition — and should score HIGH.
    """
    for trash in ("74o", "82o", "93o"):
        e = edge_score(Position.BTN, trash)
        assert e < 0.3, f"expected LOW edge score for {trash}, got {e}"

    e_transition = edge_score(Position.BTN, "54s")
    assert e_transition > 0.7, f"expected HIGH edge score for 54s, got {e_transition}"

    # Directly comparative, in case the absolute thresholds ever drift.
    for trash in ("74o", "82o", "93o"):
        assert edge_score(Position.BTN, trash) < e_transition


# --- 2d: determinism ---
def test_seeded_run_reproduces_the_same_hand_sequence():
    seq1 = _sample_hand_classes(200, seed=99)
    seq2 = _sample_hand_classes(200, seed=99)
    assert seq1 == seq2

    # A different seed should (almost certainly) diverge -- guards against a
    # sampler that silently ignores the injected rng.
    seq3 = _sample_hand_classes(200, seed=1234)
    assert seq1 != seq3
