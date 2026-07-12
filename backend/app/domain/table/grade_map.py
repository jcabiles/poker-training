"""Map a live Simulate decision point to a canonical gradeable Spot (S10).

Pure domain: no web/DB imports (enforced by test_domain_purity). The mapper is
deliberately conservative — it classifies ONLY HU-canonical shapes that match
existing strategy content (preflop RFI / vs-RFI / blind defense HU; HU flop
c-bet) and returns None for anything it cannot build with full confidence
(multiway, off-size, off-pack, limped pots, 3-bet+ pots, turn/river). None ⇒
the caller records the decision as 'unmappable' ("no baseline yet") and writes
NO drill_attempt. Never fabricate ranges, facing, or villain context.

Canonical-shape parity: preflop spots are built by the SAME
`scenarios.build_spot` the Practice drills use (with the hero's real hole
cards); the flop c-bet spot mirrors `scenarios.build_cbet_spot` field-by-field
with the live board / cards / stacks / pot substituted in and the ranges
resolved through the same content entries — so a mapped Spot is always one the
existing graders were built for.
"""

from __future__ import annotations

import random

from app.domain.scenarios import _OPEN_SIZE, _combos_for, _find_entry, build_spot
from app.domain.spot import (
    ActionType,
    GameConfig,
    Hero,
    HistoryAction,
    LegalAction,
    NodeContext,
    PlayerState,
    PlayerStatus,
    Position,
    Spot,
    Stakes,
    Street,
)
from app.domain.table.engine import HandState

_EPS = 1e-6
_BLIND_POSITIONS = (Position.SB, Position.BB)


def _street_actions(state: HandState, street: Street) -> list[HistoryAction]:
    """This street's history minus blind POSTs (posting is not acting)."""
    return [
        h
        for h in state.action_history
        if h.street is street and h.action is not ActionType.POST
    ]


def _preflop_spot(entry, state: HandState, hero_seat: int) -> Spot:
    """Canonical preflop Spot via the SAME builder Practice uses, with the
    hero's real hole cards. The rng is never drawn from (hole_cards given);
    eff_bb is the hero's available chips — the preflop grader is chart-based
    and stack-agnostic, so depth is informational only."""
    hero = state.seats[hero_seat]
    eff = round(hero.stack_bb + hero.invested_street_bb, 2)
    return build_spot(entry, random.Random(0), eff_bb=eff, hole_cards=hero.hole_cards)


def _map_preflop(state: HandState, hero_seat: int) -> Spot | None:
    hero = state.seats[hero_seat]
    acts = _street_actions(state, Street.PREFLOP)
    # Any CALL = limped or cold-called pot; any CHECK/BET is malformed here.
    if any(h.action not in (ActionType.FOLD, ActionType.RAISE) for h in acts):
        return None
    raises = [h for h in acts if h.action is ActionType.RAISE]
    if len(raises) > 1:
        return None  # 3-bet+ pots are out of v1 scope
    # A live all-in villain (short-stacked blind or all-in open) is off-script.
    if any(
        s.seat != hero_seat and s.status is PlayerStatus.ALLIN for s in state.seats
    ):
        return None

    if not raises:
        # Folded to the hero: RFI (the BB never has an RFI decision).
        entry = _find_entry(NodeContext.RFI, hero.position, None)
        if entry is None:
            return None
        return _preflop_spot(entry, state, hero_seat)

    opener_pos = raises[0].position
    canonical_open = _OPEN_SIZE.get(opener_pos)
    # Off-size open (e.g. a bot min-raise to 2.0) ⇒ not the canonical shape.
    if canonical_open is None or abs(state.current_bet_bb - canonical_open) > _EPS:
        return None
    ctx = (
        NodeContext.BLIND_DEFENSE
        if hero.position in _BLIND_POSITIONS
        else NodeContext.VS_RFI
    )
    entry = _find_entry(ctx, hero.position, opener_pos)
    if entry is None:
        return None
    return _preflop_spot(entry, state, hero_seat)


def _map_flop_cbet(state: HandState, hero_seat: int) -> Spot | None:
    """HU flop c-bet: hero opened preflop at the canonical size, the BB (and
    only the BB) called, and the BB has checked the flop to the hero."""
    hero = state.seats[hero_seat]
    if len(state.board) != 3 or hero.position in _BLIND_POSITIONS:
        return None
    live = [s for s in state.seats if s.status is not PlayerStatus.FOLDED]
    if len(live) != 2:
        return None  # multiway (or hero alone — impossible at a decision point)
    villain = next(s for s in live if s.seat != hero_seat)
    if villain.status is not PlayerStatus.IN or villain.position is not Position.BB:
        return None

    pre = _street_actions(state, Street.PREFLOP)
    raises = [h for h in pre if h.action is ActionType.RAISE]
    calls = [h for h in pre if h.action is ActionType.CALL]
    if any(
        h.action not in (ActionType.FOLD, ActionType.RAISE, ActionType.CALL)
        for h in pre
    ):
        return None
    if len(raises) != 1 or raises[0].position is not hero.position:
        return None  # hero must be the single preflop raiser
    if len(calls) != 1 or calls[0].position is not Position.BB:
        return None
    osize = _OPEN_SIZE.get(hero.position)
    # Engine history stores the raise INCREMENT; a non-blind opener's increment
    # equals the raise-TO size. Off-size opens ⇒ None.
    if osize is None or abs(raises[0].amount_bb - osize) > _EPS:
        return None

    flop_acts = _street_actions(state, Street.FLOP)
    if (
        len(flop_acts) != 1
        or flop_acts[0].action is not ActionType.CHECK
        or flop_acts[0].position is not Position.BB
    ):
        return None

    # Ranges come from the SAME content entries build_cbet_spot resolves —
    # never the builder's literal fallback strings (that would fabricate).
    rfi_entry = _find_entry(NodeContext.RFI, hero.position, None)
    bd_entry = _find_entry(NodeContext.BLIND_DEFENSE, Position.BB, hero.position)
    hero_range = _combos_for(rfi_entry, ActionType.RAISE)
    villain_range = _combos_for(bd_entry, ActionType.CALL)
    if not hero_range or not villain_range:
        return None

    pot = round(sum(s.invested_total_bb for s in state.seats), 2)
    if abs(pot - (2 * osize + 0.5)) > _EPS:
        return None  # anything but open + BB call + dead SB is off-shape
    small = round(0.33 * pot, 1)
    big = round(0.75 * pot, 1)
    hero_remaining = hero.stack_bb
    villain_remaining = villain.stack_bb
    if hero_remaining < big or villain_remaining <= 0:
        return None  # too shallow for the canonical small/big bet buckets
    effective = round(min(hero_remaining, villain_remaining), 2)
    spr = round(effective / pot, 1)

    players = [
        PlayerState(
            position=s.position,
            stack_bb=s.stack_bb,
            status=s.status,
            is_hero=s.seat == hero_seat,
        )
        for s in state.seats
    ]
    return Spot(
        game=GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0),
        street=Street.FLOP,
        board=list(state.board),
        pot_bb=pot,
        hero=Hero(
            position=hero.position,
            hole_cards=hero.hole_cards,
            stack_bb=hero_remaining,
        ),
        players=players,
        effective_stack_bb=effective,
        spr=spr,
        action_history=list(state.action_history),
        to_act=hero.position,
        legal_actions=[
            LegalAction(action=ActionType.CHECK),
            LegalAction(action=ActionType.BET, min_bb=small, max_bb=hero_remaining),
            LegalAction(action=ActionType.BET, min_bb=big, max_bb=hero_remaining),
        ],
        node_context=[NodeContext.CBET],
        facing=Position.BB,
        hero_range=hero_range,
        villain_range=villain_range,
    )


def map_decision_point(state: HandState, hero_seat: int) -> Spot | None:
    """Return the canonical Spot for the hero's CURRENT decision point.

    `state` must be the pre-decision state (before apply() mutates it).
    Returns None when no canonical Spot can be built with full confidence.
    """
    if state.hand_over or state.to_act_seat != hero_seat:
        return None
    if state.street is Street.PREFLOP:
        return _map_preflop(state, hero_seat)
    if state.street is Street.FLOP:
        return _map_flop_cbet(state, hero_seat)
    return None  # turn/river grading is out of v1 scope
