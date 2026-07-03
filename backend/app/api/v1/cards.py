"""Concept-card lookup endpoint (N8).

GET /cards/match?leak_category=<int>&tags=<comma-separated> -> the best
matching card, or {"card": null} when nothing covers this leak_category.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.domain.content.models import ConceptCard
from app.services.concept_cards import match_card

router = APIRouter(prefix="/cards", tags=["cards"])


class CardMatchResponse(BaseModel):
    card: ConceptCard | None = None


@router.get("/match", response_model=CardMatchResponse)
async def match(
    leak_category: int = Query(...),
    tags: str = Query(""),
) -> CardMatchResponse:
    tag_list = [t for t in tags.split(",") if t] if tags else []
    return CardMatchResponse(card=match_card(leak_category, tag_list))
