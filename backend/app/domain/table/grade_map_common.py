"""Shared helpers for the Simulate decision-point mappers.

Split out of `grade_map` so the preflop mapper (`grade_map_preflop`) and the
postflop mapper (`grade_map_postflop`) can own disjoint modules without a
circular import through the dispatcher. Pure domain: no web/DB imports
(enforced by test_domain_purity).
"""

from __future__ import annotations

from app.domain.spot import ActionType, Position, Street
from app.domain.table.engine import HandState

_EPS = 1e-6
_BLIND_POSITIONS = (Position.SB, Position.BB)


def _street_actions(state: HandState, street: Street) -> list:
    """This street's history minus blind POSTs (posting is not acting)."""
    return [
        h
        for h in state.action_history
        if h.street is street and h.action is not ActionType.POST
    ]
