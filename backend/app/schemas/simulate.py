"""API request/response schemas for the simulate endpoints.

Domain models (PlayerState, Hero) are Pydantic and are reused directly as the
wire contract — no parallel DTOs to drift. Villain hole cards and the board
are dealt server-side but never serialized here (see
`docs/ai-dlc/specs/simulate-s1.md`).
"""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.spot import Hero, PlayerState


class SimulateHandView(BaseModel):
    hand_no: int  # 1-based, increments per hand
    players: list[PlayerState]  # exactly 9, one per Position, stack_bb=100
    hero: Hero  # position + hole_cards (the ONLY hole cards on the wire) + stack_bb=100


class SimulateSessionResponse(BaseModel):
    session_id: str  # uuid4 hex
    hand: SimulateHandView
