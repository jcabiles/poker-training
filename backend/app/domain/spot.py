"""Spot — the normalized, solver-ready game-state contract.

Designed to carry FULL granularity (exact stacks, full action history, exact
board/cards) even when the heuristic provider ignores some fields, so a solver
provider can key off it later with no schema migration.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.domain.archetypes import VillainType

RANKS = "23456789TJQKA"
SUITS = "cdhs"

# A card is a 2-char string: rank + suit, e.g. "Ah", "Td", "2c".
Card = str


def validate_card(c: str) -> str:
    if not isinstance(c, str) or len(c) != 2 or c[0] not in RANKS or c[1] not in SUITS:
        raise ValueError(f"invalid card: {c!r} (expected rank in {RANKS} + suit in {SUITS})")
    return c


class Position(StrEnum):
    UTG = "UTG"
    UTG1 = "UTG1"
    UTG2 = "UTG2"
    LJ = "LJ"
    HJ = "HJ"
    CO = "CO"
    BTN = "BTN"
    SB = "SB"
    BB = "BB"


class Street(StrEnum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class ActionType(StrEnum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    POST = "post"  # blind/straddle posting in action history


class PlayerStatus(StrEnum):
    IN = "in"
    FOLDED = "folded"
    ALLIN = "allin"


class NodeContext(StrEnum):
    """Strategic node tags — drive provider lookup and leak mapping.

    CBET is the Phase 2a postflop node (flop c-bet, HU SRP). VS_CBET and later
    postflop contexts are reserved for 2b+.
    """

    RFI = "RFI"
    VS_RFI = "vs_RFI"
    VS_3BET = "vs_3bet"
    VS_4BET = "vs_4bet"
    BLIND_DEFENSE = "blind_defense"
    SQUEEZE = "squeeze"
    VS_LIMPERS = "vs_limpers"
    CBET = "cbet"  # flop c-bet decision (Phase 2a)
    VS_CBET = "vs_cbet"  # facing a flop c-bet — defense (Phase 2b)
    VS_CHECK_RAISE = "vs_check_raise"  # facing a flop check-raise, as the c-bettor (2e-1)
    TURN_BARREL = "turn_barrel"  # flop aggressor deciding whether to bet the turn (S6)
    VS_TURN_BET = "vs_turn_bet"  # facing a turn bet after calling flop (S6)
    RIVER_BARREL = "river_barrel"  # aggressor who bet flop+turn deciding the river (S7)
    VS_RIVER_BET = "vs_river_bet"  # caller of flop+turn bets facing a river bet (S7)


class Stakes(BaseModel):
    sb: float
    bb: float
    ante: float = 0.0
    straddle: float | None = None
    currency: str = "USD"


class GameConfig(BaseModel):
    variant: str = "NLHE"
    format: str = "cash"
    table_size: int = 9
    stakes: Stakes
    max_buyin_bb: float | None = None
    rake: dict | None = None  # nullable stub; solver EV in Phase 3 may use it


class PlayerState(BaseModel):
    position: Position
    stack_bb: float
    status: PlayerStatus = PlayerStatus.IN
    is_hero: bool = False


class HistoryAction(BaseModel):
    street: Street
    position: Position
    action: ActionType
    amount_bb: float = 0.0


class LegalAction(BaseModel):
    action: ActionType
    min_bb: float | None = None
    max_bb: float | None = None


class Hero(BaseModel):
    position: Position
    hole_cards: tuple[Card, Card]
    stack_bb: float

    @field_validator("hole_cards")
    @classmethod
    def _validate_hole_cards(cls, v):
        return tuple(validate_card(c) for c in v)


class Spot(BaseModel):
    game: GameConfig
    street: Street = Street.PREFLOP
    board: list[Card] = Field(default_factory=list)
    pot_bb: float
    hero: Hero
    players: list[PlayerState]
    effective_stack_bb: float
    spr: float | None = None
    action_history: list[HistoryAction] = Field(default_factory=list)
    to_act: Position
    legal_actions: list[LegalAction] = Field(default_factory=list)
    node_context: list[NodeContext] = Field(default_factory=list)
    facing: Position | None = None  # opener position for vs_rfi / blind_defense
    limper_count: int = 0  # number of limpers for vs_limpers
    villain_type: VillainType | None = None  # set for exploit drills
    hero_range: str | None = None  # range-notation string (postflop grading)
    villain_range: str | None = None  # range-notation string (postflop grading)
    # SRS-key override for review spots (metadata; NOT in spot_signature)
    srs_signature: str | None = None

    @field_validator("board")
    @classmethod
    def _validate_board(cls, v):
        return [validate_card(c) for c in v]
