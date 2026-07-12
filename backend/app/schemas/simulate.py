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
    status: str  # in / folded / allin
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


class GradeView(BaseModel):
    """One graded hero decision (S10). correctness None = 'no baseline yet'."""

    street: str
    ordinal: int
    chosen_action: str
    correctness: str | None
    ev_loss_bb: float  # ≈ approximate (heuristic provider)
    coverage: str  # full / partial / not_found / unmappable
    verdict: str | None  # FeedbackTiers.verdict; None when no baseline
    reasoning: str | None  # FeedbackTiers.reasoning; recap expands for mistakes+


class StreetReportRow(BaseModel):
    """All-time per-street aggregate over sim_decision (S10 report).

    Rates derived client-side EXCLUDE no_baseline rows (they carry no
    correctness); no_baseline is surfaced as its own count so sparse v1
    coverage reads honestly.
    """

    street: str
    graded: int  # decisions with a baseline verdict
    optimal: int
    acceptable: int
    mistake: int
    blunder: int
    ev_loss_bb: float  # ≈ sum over graded rows
    no_baseline: int  # not_found + unmappable rows


class StreetReportView(BaseModel):
    rows: list[StreetReportRow]  # street order: preflop, flop, turn, river
    total_decisions: int  # graded + no_baseline across all streets


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
    # S10 grading: verdict for the decision just taken (None when the last
    # request wasn't a graded hero action), and the full per-decision recap for
    # the finished hand ([] until hand_over).
    last_grade: GradeView | None = None
    recap: list[GradeView] = []


class SessionView(BaseModel):
    session_id: str
    hand: SimulateHandView
