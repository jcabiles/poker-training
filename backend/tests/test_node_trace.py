"""W0-c — the seeded node-trace pack produces a structurally valid trace.

This asserts the pack RUNS and logs the required fields for the full seed set;
it does NOT assert realism thresholds (that is each behavior slice's job). The
value is that the trace exists for later "right stat, wrong node" review.
"""

from __future__ import annotations

from app.domain.action import ActionType
from app.domain.archetypes import VillainType
from tests.node_trace import SPOTS, build_trace

_ACTION_VALUES = {a.value for a in ActionType}


def test_node_trace_pack_runs_and_is_well_formed():
    rows = build_trace()
    # One row per persona x spot.
    assert len(rows) == len(list(VillainType)) * len(SPOTS)
    for r in rows:
        assert r.persona and r.spot_id and r.bucket and r.draw_class and r.prescription
        # Chosen action is a real seeded sample from the ActionType space
        # (never a forced population[0]).
        assert r.chosen_action in _ACTION_VALUES
        probs = r.action_probabilities
        tag = f"{r.persona}/{r.spot_id}"
        assert probs, f"{tag}: empty probabilities"
        # Captured population is the ACTION draw (ActionType values), never the
        # sizing draw (Sol #8).
        assert set(probs) <= _ACTION_VALUES, f"{tag}: non-action keys {set(probs)}"
        # Normalized distribution: sums to 1 (or the deterministic fallback 1.0).
        assert abs(sum(probs.values()) - 1.0) < 1e-6, f"{tag}: sum {sum(probs.values())}"
        # The seeded chosen action is one the sampler actually weighed.
        assert r.chosen_action in probs, f"{tag}: chose {r.chosen_action} not in {set(probs)}"


def test_node_trace_no_degenerate_zero_merit_fallback():
    """Every chosen spot must exercise a real candidate set (>=2 weighted
    actions) — none may collapse to the single-action zero-total-merit fallback
    (`range_estimate`-style capture would yield len 1). Guards Sol #9 / the
    theory-reviewer's fixture-degeneracy nit."""
    for r in build_trace():
        assert len(r.action_probabilities) >= 2, (
            f"{r.persona}/{r.spot_id}: degenerate fallback {r.action_probabilities}"
        )


def test_node_trace_is_deterministic():
    """Same seed -> identical trace (seeded replay must be reproducible for the
    fit loop)."""
    assert build_trace(seed=123) == build_trace(seed=123)
