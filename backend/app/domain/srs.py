"""SRS item + the locked spot_signature.

spot_signature is a deterministic, version-stable id computed from a CANONICAL
subset of the Spot. It deliberately excludes hole cards (same strategic
archetype) and bet amounts / pot size (sizes vary), so the same conceptual spot
maps to one SRS item across content-pack version bumps. Changing this function
is a breaking change to persisted SRS history.

No datetime here — scheduling stays date-free in the pure domain; the DB/service
layer resolves due dates from interval_days (Phase 1).
"""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field

from app.domain.spot import Spot, Street

DEFAULT_EASE = 2.5

# Coarse effective-stack buckets (bb). Stable boundaries — appending a deeper
# bucket is safe; renaming/reordering existing ones breaks signatures.
_STACK_BUCKETS = [(40, "<=40"), (75, "40-75"), (125, "75-125"), (200, "125-200")]


def stack_bucket(eff_bb: float) -> str:
    for hi, label in _STACK_BUCKETS:
        if eff_bb <= hi:
            return label
    return ">200"


# Stable SPR buckets for the postflop signature. Boundaries are locked.
def spr_bucket(spr: float | None) -> str:
    if spr is None:
        return "na"
    if spr <= 3:
        return "<=3"
    if spr <= 6:
        return "3-6"
    if spr <= 13:
        return "6-13"
    return ">13"


def spot_signature(spot: Spot) -> str:
    if spot.street != Street.PREFLOP:
        return _postflop_signature(spot)
    # --- Preflop path: UNCHANGED (preserves existing persisted hashes) ---
    ctx = ",".join(sorted(c.value for c in spot.node_context))
    facing = spot.facing.value if spot.facing else "-"
    villain = spot.villain_type.value if spot.villain_type else "-"
    parts = [
        spot.game.variant,
        spot.game.format,
        spot.street.value,
        ctx,
        spot.hero.position.value,
        facing,
        str(spot.limper_count),
        str(spot.game.table_size),
        stack_bucket(spot.effective_stack_bb),
        villain,  # last (locked position)
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _postflop_signature(spot: Spot) -> str:
    """Postflop signature — keyed on texture CLASS + SPR bucket, not the exact
    board or hole cards, so same-archetype flops collapse to one SRS item."""
    from app.domain.texture import classify

    ctx = ",".join(sorted(c.value for c in spot.node_context))
    facing = spot.facing.value if spot.facing else "-"
    tex = classify(spot.board).texture_class if len(spot.board) >= 3 else "-"
    parts = [
        spot.game.variant,
        spot.game.format,
        spot.street.value,
        ctx,
        spot.hero.position.value,
        facing,
        tex,
        spr_bucket(spot.spr),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class SRSItem(BaseModel):
    id: str  # == spot_signature(spot)
    leak_category: int
    ease_factor: float = DEFAULT_EASE
    interval_days: int = 0
    repetitions: int = 0
    due_offset_days: int = 0  # days from "today"; resolved to a date in the service layer
    last_grade: int | None = None
    history: list[int] = Field(default_factory=list)


_QUALITY = {"optimal": 5, "acceptable": 4, "mistake": 2, "blunder": 0}


def quality_from_correctness(correctness: str | None) -> int:
    return _QUALITY.get(correctness or "", 0)


def sm2(ease: float, interval: int, repetitions: int, quality: int) -> tuple[float, int, int]:
    """SM-2 step. Returns (ease, interval_days, repetitions). Pure — no dates."""
    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = max(1, round(interval * ease))
        repetitions += 1
    ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return max(1.3, ease), interval, repetitions
