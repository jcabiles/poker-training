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


def build_spot(entry: Entry, rng: random.Random, eff_bb: float = 100.0) -> Spot:
    c1, c2 = rng.sample(_DECK, 2)
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
