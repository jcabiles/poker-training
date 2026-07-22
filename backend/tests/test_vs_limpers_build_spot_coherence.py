"""M2 refuter fix (HIGH): `build_spot` coherence for EVERY `vs_limpers` entry.

`sample_spot` (drill.py) and the "vs Limpers" leak category (Home.tsx) serve
vs_limpers entries via `scenarios.build_spot` directly — bypassing
`map_preflop`'s organic engine gating. `build_spot`'s VS_LIMPERS branch seats
limpers by iterating `_before(entry.position)` (scenarios.py:206-222); if a
position has no seats before it (e.g. UTG, the first-to-act seat), that loop
never runs and the built Spot is incoherent (phantom pot_bb, no limp actions
in history, CALL/RAISE offered with no logical limpers). This test would have
caught the UTG mistake (content authored "UTG", corrected to "UTG2" — RES-G
§1d itself measured the EP faces-1 shape at UTG2, and UTG2 has UTG/UTG1 before
it so `_before` is non-empty).

For every vs_limpers entry in the pack, assert build_spot produces exactly
`limper_count` CALL actions in the preflop history and a pot_bb consistent
with blinds (1.5) + limps (1.0 each).
"""

from __future__ import annotations

import random

from app.domain.scenarios import _entries, build_spot
from app.domain.spot import ActionType, NodeContext, Street


def _vs_limpers_entries():
    return [e for e in _entries() if e.node_context == NodeContext.VS_LIMPERS]


def test_every_vs_limpers_entry_builds_a_coherent_spot():
    entries = _vs_limpers_entries()
    assert entries, "no vs_limpers entries found — pack failed to load"
    for entry in entries:
        spot = build_spot(entry, random.Random(0), eff_bb=100.0)
        limper_count = entry.limper_count or 0
        limp_actions = [
            a
            for a in spot.action_history
            if a.street is Street.PREFLOP and a.action is ActionType.CALL
        ]
        assert len(limp_actions) == limper_count, (
            f"{entry.position} x{limper_count}: expected {limper_count} limp "
            f"CALL actions in history, got {len(limp_actions)} "
            f"({spot.action_history})"
        )
        expected_pot = round(1.5 + limper_count * 1.0, 2)
        assert spot.pot_bb == expected_pot, (
            f"{entry.position} x{limper_count}: pot_bb {spot.pot_bb} != "
            f"expected {expected_pot} (blinds 1.5 + {limper_count} limps)"
        )
