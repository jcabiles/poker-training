"""Bot play-loop — drives persona bots through the S2 hand engine (S9).

Productionizes the per-decision logic of the closed-loop harness in
`tests/test_personas_postflop.py` (`_preflop_facing`, `_preflop_decision`,
`_postflop_decision`, `_live_opponents`, `_play_hand`) EXACTLY — preflop raise
size = `la.min_bb`, postflop threads `current_bet_to=state.current_bet_bb`.
The ONE behavioral change vs `_play_hand`: `advance_to_hero` stops when
`to_act_seat == hero_seat` (control returns to the caller) instead of sampling
the hero's persona. Parity with the harness is per-DECISION only — a full-hand
playout diverges by design because production skips the hero's RNG draws.

Pure domain: no web/DB imports; the caller owns the `random.Random`.
Spec: docs/ai-dlc/specs/simulate-s9.md.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.domain.action import Decision
from app.domain.archetypes import VillainType
from app.domain.content.models import PersonaPack
from app.domain.personas import sample_preflop_action
from app.domain.personas_postflop import sample_postflop_decision
from app.domain.spot import ActionType, PlayerStatus, Position, Street
from app.domain.table.engine import HandState, apply, legal_actions

# Fixed table composition: 8 bots shuffled across the non-hero seats.
LINEUP: tuple[VillainType, ...] = (
    VillainType.PASSIVE_FISH,
    VillainType.PASSIVE_FISH,
    VillainType.TAG,
    VillainType.TAG,
    VillainType.CALLING_STATION,
    VillainType.NIT,
    VillainType.LAG,
    VillainType.MANIAC,
)


def assign_lineup(rng: random.Random) -> dict[int, VillainType]:
    """Shuffle LINEUP across the 8 non-hero seats (1..8); seat 0 is the hero (absent)."""
    bots = list(LINEUP)
    rng.shuffle(bots)
    return {seat: bots[seat - 1] for seat in range(1, 9)}


@dataclass(frozen=True)
class ActionEvent:
    """One bot action, safe to serialize (NO hole cards).

    amount_bb: raise-TO / bet-TO for BET/RAISE (the decision's size), the call
    increment for CALL, 0.0 for FOLD/CHECK.
    """

    seat: int
    position: Position
    action: ActionType
    amount_bb: float
    street: Street


# --- Harness mirrors (tests/test_personas_postflop.py) — keep byte-equivalent ---


def _preflop_facing(state: HandState) -> str:
    raises = [
        h
        for h in state.action_history
        if h.street is Street.PREFLOP and h.action == ActionType.RAISE
    ]
    if not raises:
        limped = any(
            h.action == ActionType.CALL for h in state.action_history if h.street is Street.PREFLOP
        )
        return "vs_limpers" if limped else "unopened"
    n = len(raises)
    if n == 1:
        return "vs_rfi"
    if n == 2:
        return "vs_3bet"
    return "vs_4bet"  # n >= 3 (4bet, 5bet_shove, ...)


def _preflop_decision(pack, position, facing, hole, legal, rng) -> Decision:
    act = sample_preflop_action(pack, position, facing, hole, rng)
    kinds = {la.action for la in legal}
    if act.action not in kinds:
        # Persona wants an action the engine doesn't offer here (e.g. raise
        # not legal because the raise didn't reopen) -- fall back to call if
        # legal, else fold/check per engine's own bracket.
        if ActionType.CALL in kinds:
            act_action = ActionType.CALL
        elif ActionType.CHECK in kinds:
            act_action = ActionType.CHECK
        else:
            act_action = ActionType.FOLD
    else:
        act_action = act.action
    if act_action in (ActionType.BET, ActionType.RAISE):
        la = next(x for x in legal if x.action == act_action)
        size = la.min_bb if la.min_bb is not None else la.max_bb
        return Decision(action=act_action, size_bb=round(size, 2))
    return Decision(action=act_action)


def _postflop_decision(
    pack, hole, board, legal, pot_bb, stack_bb, opponents, rng, current_bet_to
) -> Decision:
    kinds = {la.action for la in legal}
    d = sample_postflop_decision(
        pack, hole, board, legal, pot_bb, stack_bb, opponents, rng, current_bet_to=current_bet_to
    )
    if d.action not in kinds:
        # Defensive: never happens if the sampler honors `legal`, but keep
        # the loop crash-proof against an engine/sampler mismatch.
        if ActionType.CHECK in kinds:
            return Decision(action=ActionType.CHECK)
        return Decision(action=ActionType.FOLD)
    return d


def _live_opponents(state: HandState, seat: int) -> int:
    return sum(
        1
        for s in state.seats
        if s.seat != seat and s.status in (PlayerStatus.IN, PlayerStatus.ALLIN)
    )


# ------------------------------------------------------------- public API


def bot_decision(
    state: HandState, seat: int, pack: PersonaPack, rng: random.Random
) -> Decision:
    """One bot seat's action for the current decision point."""
    legal = legal_actions(state)
    seat_state = state.seats[seat]
    if state.street is Street.PREFLOP:
        facing = _preflop_facing(state)
        return _preflop_decision(
            pack, seat_state.position, facing, seat_state.hole_cards, legal, rng
        )
    pot_bb = sum(s.invested_total_bb for s in state.seats)
    opponents = _live_opponents(state, seat)
    return _postflop_decision(
        pack,
        seat_state.hole_cards,
        state.board,
        legal,
        pot_bb,
        seat_state.stack_bb,
        opponents,
        rng,
        state.current_bet_bb,
    )


def advance_to_hero(
    state: HandState,
    seat_personas: dict[int, PersonaPack],
    hero_seat: int,
    rng: random.Random,
) -> tuple[HandState, list[ActionEvent]]:
    """Apply bot actions until to_act_seat == hero_seat OR the hand is over.

    Never applies a hero action. Returns the advanced state + ordered events.
    """
    events: list[ActionEvent] = []
    guard = 0
    while (
        not state.hand_over
        and state.to_act_seat is not None
        and state.to_act_seat != hero_seat
    ):
        guard += 1
        if guard >= 500:
            raise RuntimeError("bot playout did not terminate")
        seat = state.to_act_seat
        street = state.street
        position = state.seats[seat].position
        decision = bot_decision(state, seat, seat_personas[seat], rng)
        state = apply(state, decision)
        if decision.action in (ActionType.BET, ActionType.RAISE):
            amount = decision.size_bb or 0.0
        elif decision.action is ActionType.CALL:
            amount = state.action_history[-1].amount_bb  # the call increment
        else:
            amount = 0.0
        events.append(
            ActionEvent(
                seat=seat,
                position=position,
                action=decision.action,
                amount_bb=round(amount, 2),
                street=street,
            )
        )
    return state, events
