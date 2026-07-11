"""API request/response schemas for the simulate endpoints.

Wire contract for S9 (hero plays / session persistence). Hero-only hole-card
privacy is structural: `SeatView` carries no hole cards; only `Hero.hole_cards`
(reused from the domain) and, at showdown, `ShowdownSeatView.hole_cards` ever
appear on the wire. No endpoint returns `state_json`, `full_board`, or a raw
`HandState`. See `docs/ai-dlc/specs/simulate-s9.md`.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.spot import Hero, LegalAction


class SeatView(BaseModel):
    seat_index: int
    position: str
    persona_type: str | None  # badge; None for hero
    is_hero: bool
    stack_bb: float
    status: str  # IN / FOLDED / ALLIN
    invested_street_bb: float  # this street's commitment (chips-in-front display)
    net_bb: float  # stack_bb - buyins_bb (ledger)


class ShowdownSeatView(BaseModel):
    seat_index: int
    hole_cards: tuple[str, str]
    delta_bb: float


class EventView(BaseModel):
    seat_index: int
    position: str
    action: str
    amount_bb: float
    street: str


class SimulateHandView(BaseModel):
    hand_no: int
    button_seat: int
    street: str
    board: list[str]  # revealed cards only (never full_board)
    pot_bb: float
    seats: list[SeatView]
    hero: Hero  # hero.hole_cards is the only in-hand hole cards
    to_act_seat: int | None
    is_hero_turn: bool
    legal_actions: list[LegalAction]  # populated only when is_hero_turn
    events: list[EventView]  # bot actions since the last hero decision
    hand_over: bool
    showdown: list[ShowdownSeatView]  # [] until hand_over; folded villains never listed


class SessionView(BaseModel):
    session_id: str
    hand: SimulateHandView
