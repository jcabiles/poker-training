"""N5 — blind-defense content fills: the 9 new entries exist, resolve through
`_find_entry`, and the defend sets nest monotonically (an earlier/tighter
opener's defend range is always contained in a later/looser opener's).

Chain (tightest -> widest opener):
  BB: vs-UTG <= vs-UTG1 <= vs-UTG2 <= vs-LJ <= vs-HJ <= vs-CO <= vs-BTN
  SB: vs-UTG <= vs-UTG1 <= vs-UTG2 <= vs-LJ <= vs-HJ <= vs-CO <= vs-BTN

Frequency fields are advisory-only (pre-existing `_combos_for` behavior) —
sets here are the union of all combos across actions, which is exactly what
range consumers see.
"""

from __future__ import annotations

import pytest

from app.domain.equity import combos_for_range
from app.domain.scenarios import _find_entry
from app.domain.spot import ActionType, NodeContext, Position

_CHAIN = [
    Position.UTG,
    Position.UTG1,
    Position.UTG2,
    Position.LJ,
    Position.HJ,
    Position.CO,
    Position.BTN,
]


def _defend_set(blind: Position, opener: Position) -> set:
    entry = _find_entry(NodeContext.BLIND_DEFENSE, blind, opener)
    assert entry is not None, f"missing blind_defense entry: {blind} vs {opener}"
    combos: set = set()
    for a in entry.actions:
        combos.update(combos_for_range(a.combos))
    assert combos, f"empty defend set: {blind} vs {opener}"
    return combos


@pytest.mark.parametrize("blind", [Position.BB, Position.SB])
def test_all_seven_opener_entries_resolve(blind):
    for opener in _CHAIN:
        _defend_set(blind, opener)


@pytest.mark.parametrize("blind", [Position.BB, Position.SB])
def test_defend_sets_nest_monotonically(blind):
    prev_opener = _CHAIN[0]
    prev = _defend_set(blind, prev_opener)
    for opener in _CHAIN[1:]:
        cur = _defend_set(blind, opener)
        extra = prev - cur
        assert not extra, (
            f"{blind.value} defend vs {prev_opener.value} is not contained in "
            f"vs {opener.value}; violating combos: {sorted(extra)[:10]}"
        )
        prev, prev_opener = cur, opener


def test_sb_entries_are_three_bet_or_fold():
    # SB never flats — every SB entry has raise actions only (matches the two
    # v1 anchors; a call action appearing later would be a philosophy break).
    for opener in _CHAIN:
        entry = _find_entry(NodeContext.BLIND_DEFENSE, Position.SB, opener)
        assert all(a.action == ActionType.RAISE for a in entry.actions), (
            f"SB vs {opener.value} contains a non-raise action"
        )
