"""Map a live Simulate decision point to a canonical gradeable Spot (S10).

Pure domain: no web/DB imports (enforced by test_domain_purity). The mapper is
deliberately conservative — it classifies ONLY HU-canonical shapes that match
existing strategy content (preflop RFI / vs-RFI HU; HU flop c-bet) and returns
None for anything it cannot build with full confidence (multiway, off-size,
off-pack, turn/river). None ⇒ the caller records the decision as 'unmappable'
("no baseline yet") and writes NO drill_attempt. Never fabricate ranges,
facing, or villain context.

T0 freezes this interface; T1 supplies the classification logic.
"""

from __future__ import annotations

from app.domain.spot import Spot
from app.domain.table.engine import HandState


def map_decision_point(state: HandState, hero_seat: int) -> Spot | None:
    """Return the canonical Spot for the hero's CURRENT decision point.

    `state` must be the pre-decision state (before apply() mutates it).
    Returns None when no canonical Spot can be built with full confidence.
    """
    # T0 contract stub — T1 implements. Returning None keeps behavior
    # unchanged (every decision reads "no baseline yet") until T1 lands.
    _ = (state, hero_seat)
    return None
