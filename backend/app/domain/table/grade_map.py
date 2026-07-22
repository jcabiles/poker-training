"""Dispatch a live Simulate decision point to the right street mapper (S10).

Pure domain: no web/DB imports (enforced by test_domain_purity). The mappers are
deliberately conservative — they classify ONLY HU-canonical shapes that match
existing strategy content and return None for anything they cannot build with
full confidence. None ⇒ the caller records the decision as 'unmappable'
("no baseline yet") and writes NO drill_attempt. Never fabricate ranges,
facing, or villain context.

Street ownership (decoupled 2026-07-16 so R4/R5 own disjoint modules):
  - preflop shapes  → `grade_map_preflop.map_preflop`
  - postflop shapes → `grade_map_postflop` (flop c-bet + R5 turn/river line)
  - shared helpers  → `grade_map_common`
This module is just the dispatcher; street-specific logic lives in those
modules. `_find_limp_entry` is re-exported for existing test imports.
"""

from __future__ import annotations

from app.domain.spot import Spot, Street
from app.domain.table.engine import HandState
from app.domain.table.grade_map_postflop import (
    map_flop_cbet,
    map_flop_vs_caller_raise,
    map_flop_vs_cbet,
    map_flop_vs_check_raise,
    map_mw_flop_vs_cbet,
    map_mw_vs_river_bet,
    map_mw_vs_turn_bet,
    map_river_barrel,
    map_turn_barrel,
    map_vs_river_bet,
    map_vs_turn_bet,
)
from app.domain.table.grade_map_preflop import _find_limp_entry, map_preflop

__all__ = ["map_decision_point", "_find_limp_entry"]


def map_decision_point(state: HandState, hero_seat: int) -> Spot | None:
    """Return the canonical Spot for the hero's CURRENT decision point.

    `state` must be the pre-decision state (before apply() mutates it).
    Returns None when no canonical Spot can be built with full confidence.
    """
    if state.hand_over or state.to_act_seat != hero_seat:
        return None
    if state.street is Street.PREFLOP:
        return map_preflop(state, hero_seat)
    if state.street is Street.FLOP:
        # N4b: three HU flop shapes, disjoint by hero role + street action
        # shape; N5 adds the 3-way BB-defense shape, disjoint from all HU
        # mappers by preflop entrant count (two callers vs one) — so `or`
        # never masks one with the other.
        return (
            map_flop_cbet(state, hero_seat)
            or map_flop_vs_cbet(state, hero_seat)
            or map_flop_vs_check_raise(state, hero_seat)
            or map_flop_vs_caller_raise(state, hero_seat)
            or map_mw_flop_vs_cbet(state, hero_seat)
        )
    # R5: turn/river continuation-line shapes, disjoint by hero position
    # (opener barrels vs BB defends) + entrant count (N5 3-way). Everything
    # else stays None ("no baseline yet").
    if state.street is Street.TURN:
        return (
            map_turn_barrel(state, hero_seat)
            or map_vs_turn_bet(state, hero_seat)
            or map_mw_vs_turn_bet(state, hero_seat)
        )
    if state.street is Street.RIVER:
        return (
            map_river_barrel(state, hero_seat)
            or map_vs_river_bet(state, hero_seat)
            or map_mw_vs_river_bet(state, hero_seat)
        )
    return None
