"""Map a live Simulate POSTFLOP decision point to a canonical gradeable Spot.

Split out of `grade_map` (S10) so postflop range/coverage work (R5: the
openable call/fold/raise chart + widened postflop grading) owns this module
cleanly. Pure domain: no web/DB imports (enforced by test_domain_purity).
Today it classifies ONLY the HU flop c-bet shape; anything else returns None
("no baseline yet") — never a fabricated or flop-truncated postflop spot.

Canonical-shape parity: the flop c-bet spot mirrors `scenarios.build_cbet_spot`
field-by-field with the live board / cards / stacks / pot substituted in and the
ranges resolved through the same content entries — so a mapped Spot is always
one the existing graders were built for.
"""

from __future__ import annotations

from app.domain.scenarios import _OPEN_SIZE, _combos_for, _find_entry
from app.domain.spot import (
    ActionType,
    GameConfig,
    Hero,
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
from app.domain.table.grade_map_common import _BLIND_POSITIONS, _EPS, _street_actions


def map_flop_cbet(state: HandState, hero_seat: int) -> Spot | None:
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
