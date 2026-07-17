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
    # N3 preflop sizing verdict; None unless hero raised at a two-size node.
    sizing_correctness: str | None = None
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


class PostflopChartAction(BaseModel):
    """One action of the grader's postflop mix (the grader's OWN ActionEval,
    re-shaped for the wire — never re-derived frequencies)."""

    action: str  # check / bet / fold / call / raise
    size_bb: float | None = None  # bet/raise sizing bucket; None for check/fold/call
    frequency: float  # 0-1, ≈ baseline
    ev_bb: float  # ≈ approximate (heuristic provider)


class PostflopChartView(BaseModel):
    """Point-of-need action-mix chart for the hero's current POSTFLOP decision
    (R5). Renders the grading provider's own per_action output — chart==grader
    by construction. available=false (no actions) when it is not the hero's
    postflop turn, the hand is over, or the spot is unmappable ("no baseline
    yet" — never fabricated). Availability is a 200-body concern; 404 stays
    reserved for a missing/ended session. Distinct from PreflopChartView: an
    action mix, not a 169-combo grid."""

    available: bool
    node_label: str | None = None
    hand_category: str | None = None  # strong / weak_made / draw / air (river: draw→air)
    actions: list[PostflopChartAction] = []
    approx: bool = True  # heuristic EVs — always labeled approximate


class RevealedSeatView(BaseModel):
    """One villain's hole cards, revealed on demand after a hero fold (R1).

    Distinct from ShowdownSeatView: no delta_bb (reveal is a card lookup, not a
    settlement). The ONLY other wire shape that carries villain hole cards."""

    seat_index: int
    hole_cards: tuple[str, str]


class RevealView(BaseModel):
    """On-demand reveal of the just-completed hand's villain cards (R1).

    Sourced server-side from SimHand.state_json; hero is never included (hero
    folded, and hero cards already ship on Hero). available=false (empty seats)
    when the reveal capability is off, the hand isn't complete, or the hero did
    not fold this hand (a genuine showdown auto-reveals instead) — never a
    fabricated reveal. Availability is a 200-body concern; 404 stays reserved
    for a missing/ended session.

    scope: 'last-in' = non-hero seats still IN/ALLIN at hand end;
    'all' = every non-hero seat dealt into the hand."""

    available: bool
    scope: str
    seats: list[RevealedSeatView] = []


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
