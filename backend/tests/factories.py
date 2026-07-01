"""Shared test factories for building domain objects."""

from __future__ import annotations

from app.domain.spot import (
    ActionType,
    GameConfig,
    Hero,
    HistoryAction,
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


def make_cbet_spot(
    hole_cards=("Ah", "Ks"),
    position: Position = Position.BTN,
    eff_bb: float = 100.0,
) -> Spot:
    """A canonical flop c-bet spot (BTN vs BB, $1/$2, 9-handed). Hero is the aggressor."""
    game = GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0)
    osize = 2.5
    pot = round(2 * osize + 0.5, 2)
    remaining = round(eff_bb - osize, 2)
    spr = round(remaining / pot, 1)
    small = round(0.33 * pot, 1)
    big = round(0.75 * pot, 1)

    return Spot(
        game=game,
        street=Street.FLOP,
        board=["Ac", "Kd", "Qh"],
        pot_bb=pot,
        hero=Hero(position=position, hole_cards=hole_cards, stack_bb=remaining),
        players=[
            PlayerState(position=position, stack_bb=remaining, is_hero=True),
            PlayerState(position=Position.BB, stack_bb=remaining),
        ],
        effective_stack_bb=remaining,
        spr=spr,
        action_history=[
            HistoryAction(street=Street.PREFLOP, position=Position.SB, action=ActionType.POST, amount_bb=1.0),
            HistoryAction(street=Street.PREFLOP, position=Position.BB, action=ActionType.POST, amount_bb=2.0),
            HistoryAction(street=Street.PREFLOP, position=position, action=ActionType.RAISE, amount_bb=osize),
            HistoryAction(street=Street.PREFLOP, position=Position.BB, action=ActionType.CALL, amount_bb=osize),
        ],
        to_act=position,
        legal_actions=[
            LegalAction(action=ActionType.CHECK),
            LegalAction(action=ActionType.BET, min_bb=small, max_bb=remaining),
            LegalAction(action=ActionType.BET, min_bb=big, max_bb=remaining),
        ],
        node_context=[NodeContext.CBET],
        facing=Position.BB,
        hero_range="22+, A2s+, KTs+, QJs, AJo+",
        villain_range="22-99, ATs+, KJs+, QJs, AJo+, KQo",
    )


def make_check_raise_spot(
    hole_cards=("Ah", "Ks"),
    position: Position = Position.BTN,
    eff_bb: float = 100.0,
) -> Spot:
    """A canonical flop check-raise spot (BTN opener c-bets, BB check-raises).

    Hero is the ORIGINAL aggressor (the flop c-bettor) now facing the raise, so
    hero.position == the opener and `facing` == the BB check-raiser — the mirror
    image of make_cbet_spot's aggressor. CALL.min_bb is the INCREMENTAL delta
    (raise_to - cbet), matching build_check_raise_spot's sizing convention.
    """
    game = GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0)
    osize = 2.5
    flop_pot = round(2 * osize + 0.5, 2)  # opener + BB call + SB dead 0.5
    cbet = round(0.75 * flop_pot, 1)  # a big c-bet
    raise_to = round(3.0 * cbet, 2)  # defender check-raises to this TOTAL
    pot = round(flop_pot + cbet + raise_to, 2)  # pot includes everything committed
    hero_remaining = round(eff_bb - osize - cbet, 2)  # preflop open + flop c-bet
    villain_remaining = round(eff_bb - osize - raise_to, 2)  # preflop call + check-raise
    effective = min(hero_remaining, villain_remaining)
    spr = round(effective / pot, 1)
    call_amt = round(raise_to - cbet, 2)  # INCREMENTAL amount hero owes, NOT raise_to
    raise_size = round(3 * raise_to, 2)  # a further 4-bet

    return Spot(
        game=game,
        street=Street.FLOP,
        board=["Ac", "Kd", "Qh"],  # hero (AhKs) flops top two pair -> a "strong" hand
        pot_bb=pot,
        hero=Hero(position=position, hole_cards=hole_cards, stack_bb=hero_remaining),
        players=[
            PlayerState(position=position, stack_bb=hero_remaining, is_hero=True),
            PlayerState(position=Position.BB, stack_bb=villain_remaining),
        ],
        effective_stack_bb=effective,
        spr=spr,
        action_history=[
            HistoryAction(street=Street.PREFLOP, position=Position.SB, action=ActionType.POST, amount_bb=1.0),
            HistoryAction(street=Street.PREFLOP, position=Position.BB, action=ActionType.POST, amount_bb=2.0),
            HistoryAction(street=Street.PREFLOP, position=position, action=ActionType.RAISE, amount_bb=osize),
            HistoryAction(street=Street.PREFLOP, position=Position.BB, action=ActionType.CALL, amount_bb=osize),
            HistoryAction(street=Street.FLOP, position=position, action=ActionType.BET, amount_bb=cbet),
            HistoryAction(street=Street.FLOP, position=Position.BB, action=ActionType.RAISE, amount_bb=raise_to),
        ],
        to_act=position,
        legal_actions=[
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=call_amt),
            LegalAction(action=ActionType.RAISE, min_bb=raise_size, max_bb=hero_remaining),
        ],
        node_context=[NodeContext.VS_CHECK_RAISE],
        facing=Position.BB,
        hero_range="22+, A2s+, KTs+, QJs, AJo+",
        villain_range="22-99, ATs+, KJs+, QJs, AJo+, KQo",
    )
