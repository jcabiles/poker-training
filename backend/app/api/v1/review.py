"""Today's-plan endpoint (N7) — read-only surfacing of the SM-2 due queue.

No new storage: reuses `due_items()` (services/review.py), which already
selects the local user's (`owner_id == ""`) due `srs_item` rows off the
existing `ix_srs_item_due_date` index. Each row already carries its own
archetype fields (node_context/position) from `record_attempt()`, so a label
is built directly from those columns — no signature re-parsing/reconstruction
needed (that heavier path in drill.py exists to rebuild a drillable Spot, not
to describe one).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.models import SRSItemRow
from app.db.session import get_session
from app.schemas.review import DuePlanItem, ReviewPlanResponse
from app.services.review import due_items

router = APIRouter(prefix="/review", tags=["review"])

# Cap on the number of due items surfaced in the plan (the queue itself may be
# larger; the UI only needs a short "what's next" preview).
PLAN_LIMIT = 10

_NODE_FAMILY_LABELS = {
    "RFI": "RFI",
    "vs_RFI": "vs RFI",
    "vs_3bet": "vs 3-bet",
    "vs_4bet": "vs 4-bet",
    "blind_defense": "Blind defense",
    "squeeze": "Squeeze",
    "vs_limpers": "vs limpers",
    "cbet": "C-bet",
    "vs_cbet": "Facing c-bet",
    "vs_check_raise": "Facing check-raise",
}


def _label(row: SRSItemRow) -> str:
    family = _NODE_FAMILY_LABELS.get(row.node_context, row.node_context)
    return f"{family} ({row.position})"


@router.get("/plan", response_model=ReviewPlanResponse)
def get_plan(session: Session = Depends(get_session)) -> ReviewPlanResponse:
    due = due_items(session)
    items = [
        DuePlanItem(
            signature=row.signature,
            due_date=row.due_date,
            last_grade=row.last_grade,
            label=_label(row),
        )
        for row in due[:PLAN_LIMIT]
    ]
    return ReviewPlanResponse(due_count=len(due), items=items)
