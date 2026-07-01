"""Scenario sampler — content-driven.

Picks a content-pack Entry and builds a valid Spot for it (random hole cards +
canonical action_history + legal actions). Sampling from authored entries
guarantees every spot has a matching grading node.

Call amounts (`LegalAction.call.min_bb`) are INCREMENTAL — the chips hero must
add, net of what they've already posted/invested. Effective stack varies across
{75, 100, 150}bb (1b light depth variety); the depth-bucketed spot_signature
separates SRS items by bucket.
"""

from __future__ import annotations

import random

from app.domain.content.models import Entry
from app.domain.content.registry import load_preflop_packs
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

RFI_POSITIONS = [
    Position.UTG,
    Position.LJ,
    Position.HJ,
    Position.CO,
    Position.BTN,
    Position.SB,
]

_RANKS = "23456789TJQKA"
_SUITS = "cdhs"
_DECK = [r + s for r in _RANKS for s in _SUITS]
_OPEN_SIZE = {
    Position.UTG: 3.0,
    Position.UTG1: 3.0,
    Position.UTG2: 3.0,
    Position.LJ: 3.0,
    Position.HJ: 2.5,
    Position.CO: 2.5,
    Position.BTN: 2.5,
    Position.SB: 3.0,
}
_LIMP_SEATS = [Position.UTG, Position.LJ, Position.HJ, Position.CO]
_DEPTHS = [75.0, 100.0, 150.0]

_ENTRIES: list[Entry] | None = None
_EXPLOIT_ENTRIES: list[Entry] | None = None


def _all() -> list[Entry]:
    return [e for pack in load_preflop_packs() for e in pack.entries]


def _entries() -> list[Entry]:
    """Baseline pool only (no exploit entries leak into random/leak_focus)."""
    global _ENTRIES
    if _ENTRIES is None:
        _ENTRIES = [e for e in _all() if e.villain_type is None]
    return _ENTRIES


def _exploit_entries() -> list[Entry]:
    global _EXPLOIT_ENTRIES
    if _EXPLOIT_ENTRIES is None:
        _EXPLOIT_ENTRIES = [e for e in _all() if e.villain_type is not None]
    return _EXPLOIT_ENTRIES


def _blinds() -> list[HistoryAction]:
    return [
        HistoryAction(
            street=Street.PREFLOP, position=Position.SB, action=ActionType.POST, amount_bb=0.5
        ),
        HistoryAction(
            street=Street.PREFLOP, position=Position.BB, action=ActionType.POST, amount_bb=1.0
        ),
    ]


def _posted(pos: Position) -> float:
    if pos == Position.SB:
        return 0.5
    if pos == Position.BB:
        return 1.0
    return 0.0


def _raise(pos: Position, amount: float) -> HistoryAction:
    return HistoryAction(
        street=Street.PREFLOP, position=pos, action=ActionType.RAISE, amount_bb=amount
    )


def build_spot(
    entry: Entry,
    rng: random.Random,
    eff_bb: float = 100.0,
    hole_cards: tuple[str, str] | None = None,
) -> Spot:
    """Build a Spot for `entry`.

    `hole_cards`, if given, is used as-is instead of drawing a fresh random
    combo from `rng` — for callers (e.g. Challenge mode) that already picked
    the hero's hole cards themselves and would otherwise draw-and-discard a
    combo here. Default `None` preserves today's behavior exactly (draw 2
    cards from `_DECK` via `rng`).
    """
    c1, c2 = hole_cards if hole_cards is not None else rng.sample(_DECK, 2)
    hero = Hero(position=entry.position, hole_cards=(c1, c2), stack_bb=eff_bb)
    ctx = entry.node_context
    facing = entry.facing
    limper_count = entry.limper_count or 0
    history = _blinds()

    players = [PlayerState(position=entry.position, stack_bb=eff_bb, is_hero=True)]
    seen = {entry.position}

    def add(pos: Position | None) -> None:
        if pos is not None and pos not in seen:
            players.append(PlayerState(position=pos, stack_bb=eff_bb))
            seen.add(pos)

    if ctx == NodeContext.RFI:
        pot = 1.5
        legal = [
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.RAISE, min_bb=entry.sizing_bb or 2.5, max_bb=eff_bb),
        ]
        add(Position.SB)
        add(Position.BB)
    elif ctx in (NodeContext.VS_RFI, NodeContext.BLIND_DEFENSE):
        osize = _OPEN_SIZE.get(facing, 2.5)
        history.append(_raise(facing, osize))
        pot = round(1.5 + osize, 2)
        legal = [
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=round(osize - _posted(entry.position), 2)),
            LegalAction(action=ActionType.RAISE, min_bb=entry.sizing_bb or 9.0, max_bb=eff_bb),
        ]
        add(facing)
        add(Position.SB)
        add(Position.BB)
    elif ctx == NodeContext.VS_LIMPERS:
        for lp in _LIMP_SEATS[:limper_count]:
            history.append(
                HistoryAction(
                    street=Street.PREFLOP, position=lp, action=ActionType.CALL, amount_bb=1.0
                )
            )
            add(lp)
        pot = round(1.5 + limper_count * 1.0, 2)
        legal = [
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=round(1.0 - _posted(entry.position), 2)),
            LegalAction(action=ActionType.RAISE, min_bb=entry.sizing_bb or 5.0, max_bb=eff_bb),
        ]
        add(Position.SB)
        add(Position.BB)
    elif ctx == NodeContext.VS_3BET:
        osize = _OPEN_SIZE.get(entry.position, 2.5)
        tbet = round(osize * 3, 2)
        history += [_raise(entry.position, osize), _raise(facing, tbet)]
        pot = round(1.5 + osize + tbet, 2)
        legal = [
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=round(tbet - osize, 2)),
            LegalAction(action=ActionType.RAISE, min_bb=entry.sizing_bb or 22.0, max_bb=eff_bb),
        ]
        add(facing)
        add(Position.SB)
        add(Position.BB)
    elif ctx == NodeContext.VS_4BET:
        osize = _OPEN_SIZE.get(facing, 2.5)
        tbet = round(osize * 3, 2)
        fbet = round(tbet * 2.3, 2)
        history += [_raise(facing, osize), _raise(entry.position, tbet), _raise(facing, fbet)]
        pot = round(1.5 + osize + tbet + fbet, 2)
        legal = [
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=round(fbet - tbet, 2)),
            LegalAction(action=ActionType.RAISE, min_bb=eff_bb, max_bb=eff_bb),  # jam
        ]
        add(facing)
        add(Position.SB)
        add(Position.BB)
    else:
        pot = 1.5
        legal = [LegalAction(action=ActionType.FOLD)]
        add(Position.SB)
        add(Position.BB)

    return Spot(
        game=GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0),
        street=Street.PREFLOP,
        board=[],
        pot_bb=pot,
        hero=hero,
        players=players,
        effective_stack_bb=eff_bb,
        action_history=history,
        to_act=entry.position,
        legal_actions=legal,
        node_context=[ctx],
        facing=facing,
        limper_count=limper_count,
        villain_type=entry.villain_type,
    )


def sample_spot(rng: random.Random | None = None, entries: list[Entry] | None = None) -> Spot:
    rng = rng or random.Random()
    pool = entries if entries is not None else _entries()
    eff = rng.choice(_DEPTHS)
    return build_spot(rng.choice(pool), rng, eff_bb=eff)


def sample_exploit_spot(rng: random.Random | None = None) -> Spot:
    rng = rng or random.Random()
    eff = rng.choice(_DEPTHS)
    return build_spot(rng.choice(_exploit_entries()), rng, eff_bb=eff)


def sample_rfi_spot(rng: random.Random | None = None, eff_bb: float = 100.0) -> Spot:
    """RFI-only sampler (kept for back-compat / focused drilling)."""
    rng = rng or random.Random()
    rfi = [e for e in _entries() if e.node_context == NodeContext.RFI]
    return build_spot(rng.choice(rfi), rng, eff_bb=eff_bb)


# --- Postflop: flop c-bet spot (Phase 2a) ---
# HU single-raised pots: hero is the preflop raiser (in position) and the BB
# defends by calling. Ranges are resolved from the authored preflop content:
# hero_range = opener's RFI raise range; villain_range = BB's blind-defense call
# range. All three pairings put hero in position (villain checks -> hero c-bets).
_CBET_PAIRINGS = [
    (Position.BTN, Position.BB),
    (Position.CO, Position.BB),
    (Position.UTG, Position.BB),
]


def _find_entry(ctx: NodeContext, pos: Position, facing: Position | None) -> Entry | None:
    for e in _entries():
        if (
            e.villain_type is None
            and e.node_context == ctx
            and e.position == pos
            and e.facing == facing
        ):
            return e
    return None


def _combos_for(entry: Entry | None, action: ActionType) -> str:
    if entry is None:
        return ""
    return ", ".join(a.combos for a in entry.actions if a.action == action)


def build_cbet_spot(
    rng: random.Random,
    pairing: tuple[Position, Position] | None = None,
    eff_bb: float = 100.0,
) -> Spot:
    from app.domain.equity import combos_for_range

    opener, caller = pairing or rng.choice(_CBET_PAIRINGS)
    rfi = _find_entry(NodeContext.RFI, opener, None)
    bd = _find_entry(NodeContext.BLIND_DEFENSE, caller, opener)
    hero_range = _combos_for(rfi, ActionType.RAISE) or "22+, A2s+, KTs+, QJs, AJo+"
    villain_range = _combos_for(bd, ActionType.CALL) or "22-99, ATs+, KJs+, QJs, AJo+, KQo"

    h1, h2 = rng.choice(combos_for_range(hero_range))
    dead = {h1, h2}
    flop = rng.sample([c for c in _DECK if c not in dead], 3)

    osize = _OPEN_SIZE.get(opener, 2.5)
    pot = round(2 * osize + 0.5, 2)  # opener + BB call + SB dead 0.5
    remaining = round(eff_bb - osize, 2)
    spr = round(remaining / pot, 1)
    small = round(0.33 * pot, 1)
    big = round(0.75 * pot, 1)

    history = _blinds() + [
        _raise(opener, osize),
        HistoryAction(
            street=Street.PREFLOP, position=caller, action=ActionType.CALL, amount_bb=osize
        ),
    ]

    return Spot(
        game=GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0),
        street=Street.FLOP,
        board=flop,
        pot_bb=pot,
        hero=Hero(position=opener, hole_cards=(h1, h2), stack_bb=remaining),
        players=[
            PlayerState(position=opener, stack_bb=remaining, is_hero=True),
            PlayerState(position=caller, stack_bb=remaining),
        ],
        effective_stack_bb=remaining,
        spr=spr,
        action_history=history,
        to_act=opener,
        legal_actions=[
            LegalAction(action=ActionType.CHECK),
            LegalAction(action=ActionType.BET, min_bb=small, max_bb=remaining),
            LegalAction(action=ActionType.BET, min_bb=big, max_bb=remaining),
        ],
        node_context=[NodeContext.CBET],
        facing=caller,
        hero_range=hero_range,
        villain_range=villain_range,
    )


def sample_cbet_spot(rng: random.Random | None = None) -> Spot:
    rng = rng or random.Random()
    return build_cbet_spot(rng, eff_bb=rng.choice(_DEPTHS))


# --- Postflop: facing a flop c-bet (Phase 2b) ---
# Same HU SRP pairing as 2a, flipped: hero = BB defender (OOP) facing the
# opener's flop c-bet. hero_range = BB defend (call) range; villain_range =
# opener RFI range (the c-bettor's range). Decision: fold / call / raise.
def build_vs_cbet_spot(
    rng: random.Random,
    pairing: tuple[Position, Position] | None = None,
    eff_bb: float = 100.0,
    cbet_frac: float | None = None,
) -> Spot:
    from app.domain.equity import combos_for_range

    opener, caller = pairing or rng.choice(_CBET_PAIRINGS)
    rfi = _find_entry(NodeContext.RFI, opener, None)
    bd = _find_entry(NodeContext.BLIND_DEFENSE, caller, opener)
    villain_range = _combos_for(rfi, ActionType.RAISE) or "22+, A2s+, KTs+, QJs, AJo+"
    hero_range = _combos_for(bd, ActionType.CALL) or "22-99, ATs+, KJs+, QJs, AJo+, KQo"

    h1, h2 = rng.choice(combos_for_range(hero_range))
    dead = {h1, h2}
    flop = rng.sample([c for c in _DECK if c not in dead], 3)

    osize = _OPEN_SIZE.get(opener, 2.5)
    flop_pot = round(2 * osize + 0.5, 2)  # opener + BB call + SB dead 0.5
    frac = cbet_frac if cbet_frac is not None else rng.choice([0.33, 0.75])
    cbet = round(frac * flop_pot, 1)
    pot = round(flop_pot + cbet, 2)  # pot hero faces INCLUDES the c-bet
    hero_remaining = round(eff_bb - osize, 2)
    villain_remaining = round(eff_bb - osize - cbet, 2)
    effective = min(hero_remaining, villain_remaining)
    spr = round(effective / pot, 1)
    raise_size = round(3 * cbet, 1)

    history = _blinds() + [
        _raise(opener, osize),
        HistoryAction(
            street=Street.PREFLOP, position=caller, action=ActionType.CALL, amount_bb=osize
        ),
        HistoryAction(street=Street.FLOP, position=opener, action=ActionType.BET, amount_bb=cbet),
    ]

    return Spot(
        game=GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0),
        street=Street.FLOP,
        board=flop,
        pot_bb=pot,
        hero=Hero(position=caller, hole_cards=(h1, h2), stack_bb=hero_remaining),
        players=[
            PlayerState(position=caller, stack_bb=hero_remaining, is_hero=True),
            PlayerState(position=opener, stack_bb=villain_remaining),
        ],
        effective_stack_bb=effective,
        spr=spr,
        action_history=history,
        to_act=caller,
        legal_actions=[
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=cbet),
            LegalAction(action=ActionType.RAISE, min_bb=raise_size, max_bb=hero_remaining),
        ],
        node_context=[NodeContext.VS_CBET],
        facing=opener,
        hero_range=hero_range,
        villain_range=villain_range,
    )


def sample_vs_cbet_spot(rng: random.Random | None = None) -> Spot:
    rng = rng or random.Random()
    return build_vs_cbet_spot(rng, eff_bb=rng.choice(_DEPTHS))


# --- Postflop: facing a flop check-raise (Phase 2e-1) ---
# Same HU SRP pairing as 2a/2b: hero = opener/aggressor (the flop c-bettor),
# villain = caller = BB defender who check-raises. Extends build_cbet_spot's
# flow one step further: hero c-bets, the defender check-raises to a total of
# `raise_to`, and hero (still the original aggressor) must fold / call / 4-bet.
#
# CALL sizing is the INCREMENTAL amount hero still owes: hero already has `cbet`
# invested this street, so hero only adds `raise_to - cbet` to call (mirrors the
# preflop VS_3BET/VS_4BET precedent `CALL.min_bb = tbet - osize`, NOT
# build_vs_cbet_spot's `CALL.min_bb = cbet` zero-prior-investment shortcut).
def build_check_raise_spot(
    rng: random.Random,
    pairing: tuple[Position, Position] | None = None,
    eff_bb: float = 100.0,
    raise_mult: float | None = None,
) -> Spot:
    from app.domain.equity import combos_for_range

    opener, caller = pairing or rng.choice(_CBET_PAIRINGS)
    rfi = _find_entry(NodeContext.RFI, opener, None)
    bd = _find_entry(NodeContext.BLIND_DEFENSE, caller, opener)
    hero_range = _combos_for(rfi, ActionType.RAISE) or "22+, A2s+, KTs+, QJs, AJo+"
    villain_range = _combos_for(bd, ActionType.CALL) or "22-99, ATs+, KJs+, QJs, AJo+, KQo"

    h1, h2 = rng.choice(combos_for_range(hero_range))
    dead = {h1, h2}
    flop = rng.sample([c for c in _DECK if c not in dead], 3)

    osize = _OPEN_SIZE.get(opener, 2.5)
    flop_pot = round(2 * osize + 0.5, 2)  # opener + BB call + SB dead 0.5
    frac = rng.choice([0.33, 0.75])  # same small/big c-bet convention as 2a
    cbet = round(frac * flop_pot, 1)
    mult = raise_mult if raise_mult is not None else rng.choice([2.5, 3.0])  # §4.4
    raise_to = round(mult * cbet, 2)  # defender check-raises to this TOTAL

    pot = round(flop_pot + cbet + raise_to, 2)  # pot includes everything committed so far
    hero_remaining = round(eff_bb - osize - cbet, 2)  # hero: preflop open + flop c-bet
    villain_remaining = round(eff_bb - osize - raise_to, 2)  # villain: preflop call + check-raise
    effective = min(hero_remaining, villain_remaining)
    spr = round(effective / pot, 1)
    call_amt = round(raise_to - cbet, 2)  # INCREMENTAL amount hero owes, NOT raise_to
    raise_size = round(3 * raise_to, 2)  # a further 4-bet

    history = _blinds() + [
        _raise(opener, osize),
        HistoryAction(
            street=Street.PREFLOP, position=caller, action=ActionType.CALL, amount_bb=osize
        ),
        HistoryAction(street=Street.FLOP, position=opener, action=ActionType.BET, amount_bb=cbet),
        HistoryAction(
            street=Street.FLOP, position=caller, action=ActionType.RAISE, amount_bb=raise_to
        ),
    ]

    return Spot(
        game=GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0),
        street=Street.FLOP,
        board=flop,
        pot_bb=pot,
        hero=Hero(position=opener, hole_cards=(h1, h2), stack_bb=hero_remaining),
        players=[
            PlayerState(position=opener, stack_bb=hero_remaining, is_hero=True),
            PlayerState(position=caller, stack_bb=villain_remaining),
        ],
        effective_stack_bb=effective,
        spr=spr,
        action_history=history,
        to_act=opener,
        legal_actions=[
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=call_amt),
            LegalAction(action=ActionType.RAISE, min_bb=raise_size, max_bb=hero_remaining),
        ],
        node_context=[NodeContext.VS_CHECK_RAISE],
        facing=caller,
        hero_range=hero_range,
        villain_range=villain_range,
    )


def sample_check_raise_spot(rng: random.Random | None = None) -> Spot:
    rng = rng or random.Random()
    return build_check_raise_spot(rng, eff_bb=rng.choice(_DEPTHS))
