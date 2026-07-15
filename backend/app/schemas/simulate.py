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
    last_action: str | None  # verb of last VOLUNTARY action this street (felt label);
    # "fold" persists for folded seats; None ⇒ hasn't acted this street. Blinds excluded.
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


class ExploitNoteView(BaseModel):
    """Persona-keyed exploit line for the chart's LIVE villain (preflop chart).

    villain_label is the actual opponent seat's persona_type — resolved from
    the mapped Spot's facing position, never guessed (spec med-1)."""

    villain_label: str
    rationale: str


class PreflopChartView(BaseModel):
    """Point-of-need baseline range chart for the hero's current preflop
    decision (simulate-preflop-chart C1). available=false (no grid) when it is
    not the hero's preflop turn, the hand is over, or the spot is unmappable —
    never a fabricated chart. Availability is a 200-body concern; 404 stays
    reserved for a missing/ended session."""

    available: bool
    node_label: str | None = None
    grid: dict[str, dict[str, float]] | None = None  # hand -> {action: freq}, ≈ baseline
    exploit_note: ExploitNoteView | None = None  # None when no authored pair exists


class VillainRangeView(BaseModel):
    """Live per-villain range estimate (villain-range V2). available=false
    (no weights) for the hero's own seat, a folded seat (staged-fold gating
    is a FE concern; this is the SERVER-truth fold state), a finished hand
    (showdown reveals real cards), or a seat with no persona — never a
    fabricated chart. Availability is a 200-body concern; 404 stays reserved
    for a missing/ended session (spec refuter low-1)."""

    available: bool
    seat_index: int
    persona_label: str | None = None
    street: str | None = None
    exact: bool = False
    weights: dict[str, float] | None = None  # hand class -> weight; zero-weight omitted
