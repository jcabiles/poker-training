"""Shared test factories for building domain objects."""

from __future__ import annotations

from app.domain.spot import (
    ActionType,
    GameConfig,
    Hero,
    LegalAction,
    NodeContext,
    PlayerState,
    Position,
    Spot,
    Stakes,
    Street,
)


def make_rfi_spot(
    hole_cards=("Ah", "Ks"),
    position: Position = Position.CO,
    eff_bb: float = 100.0,
    pot_bb: float = 1.5,
) -> Spot:
    """A canonical preflop RFI spot ($1/$2, 9-handed)."""
    game = GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0)
    return Spot(
        game=game,
        street=Street.PREFLOP,
        board=[],
        pot_bb=pot_bb,
        hero=Hero(position=position, hole_cards=hole_cards, stack_bb=eff_bb),
        players=[
            PlayerState(position=position, stack_bb=eff_bb, is_hero=True),
            PlayerState(position=Position.BB, stack_bb=eff_bb),
        ],
        effective_stack_bb=eff_bb,
        to_act=position,
        legal_actions=[
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.RAISE, min_bb=2.0, max_bb=eff_bb),
        ],
        node_context=[NodeContext.RFI],
    )
