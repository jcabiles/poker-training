"""Map a live Simulate PREFLOP decision point to a canonical gradeable Spot.

Split out of `grade_map` (S10) so preflop coverage work (R4: UTG+1/UTG+2 and
their node contexts) owns this module cleanly. Pure domain: no web/DB imports
(enforced by test_domain_purity). Classifies ONLY HU-canonical preflop shapes
that match existing strategy content (RFI / vs-RFI / blind defense / vs-3-bet /
vs-4-bet / vs-limpers) and returns None for anything it cannot build with full
confidence (multiway, off-size, off-pack, cold-call and limp-raise lines,
5-bet+ pots). None ⇒ the caller records the decision as 'unmappable'
("no baseline yet") and writes NO drill_attempt. Never fabricate ranges,
facing, or villain context.

Canonical-shape parity: preflop spots are built by the SAME
`scenarios.build_spot` the Practice drills use (with the hero's real hole cards)
— so a mapped Spot is always one the existing graders were built for.
"""

from __future__ import annotations

import random

from app.domain.scenarios import (
    _OPEN_SIZE,
    _entries,
    _find_entry,
    _posted,
    build_spot,
)
from app.domain.spot import (
    ActionType,
    HistoryAction,
    NodeContext,
    PlayerStatus,
    Position,
    Spot,
    Street,
)
from app.domain.table.engine import HandState
from app.domain.table.grade_map_common import _BLIND_POSITIONS, _EPS, _street_actions

# R2: bots now size realistically (open 3bb+, 3-bet 3.5x, 4-bet 2.4x) instead of
# the engine min-raise the old bands were tuned for, so the preflop grading bands
# widen from the min-raise-era caps to the STANDARD live sizes. Genuine oversizes
# (maniac 5.5x, fish 4bb opens, jam-adjacent) still return None — defense ranges
# shift materially. Grading a standard 3bb open against the canonical (2.5) entry
# stays within the ≈-approximate EV labels (same W1 rationale as the 2.0 relax).
_STD_OPEN_CAP = max(_OPEN_SIZE.values())  # 3.0bb universal standard open
# Coverage widen (2026-07-19): FACING a villain open, accept up to the largest
# persona open (maniac 4.5bb) so station (3.5) / fish (4.0) / maniac (4.5) opens
# map to the standard defense chart instead of showing "no baseline yet" — half
# the persona pool opens above 3.0, which was leaving most facing-a-raise spots
# ungradeable in live play. The chart lookup keys on node/position, never bet
# size, so this reuses the same defense entry; the EV stays ≈-approximate, and
# the approximation is wider vs an oversize (defense really does tighten) — an
# accepted tradeoff for coverage. Opens ABOVE 4.5 (jams, off-the-charts sizes)
# still return None. Applies ONLY to the facing-open gate — the hero's own open
# in a 3-bet/4-bet pot stays capped at the standard _STD_OPEN_CAP.
_OVERSIZE_OPEN_CAP = 4.5
_THREEBET_MULT_CAP = 3.5  # standard 3-bet = 3.5x the open
_FOURBET_MULT_CAP = 2.4  # standard 4-bet = 2.4x the 3-bet


def _preflop_spot(entry, state: HandState, hero_seat: int) -> Spot:
    """Canonical preflop Spot via the SAME builder Practice uses, with the
    hero's real hole cards. The rng is never drawn from (hole_cards given);
    eff_bb is the hero's available chips — the preflop grader is chart-based
    and stack-agnostic, so depth is informational only."""
    hero = state.seats[hero_seat]
    eff = round(hero.stack_bb + hero.invested_street_bb, 2)
    return build_spot(entry, random.Random(0), eff_bb=eff, hole_cards=hero.hole_cards)


def map_preflop(state: HandState, hero_seat: int) -> Spot | None:
    hero = state.seats[hero_seat]
    acts = _street_actions(state, Street.PREFLOP)
    # CHECK/BET never appear in a well-formed preflop line before the hero acts.
    if any(
        h.action not in (ActionType.FOLD, ActionType.RAISE, ActionType.CALL)
        for h in acts
    ):
        return None
    # A live all-in villain (short blind, jammed open/3-bet/4-bet) is
    # off-script for every preflop family.
    if any(
        s.seat != hero_seat and s.status is PlayerStatus.ALLIN for s in state.seats
    ):
        return None
    raises = [h for h in acts if h.action is ActionType.RAISE]
    calls = [h for h in acts if h.action is ActionType.CALL]

    if calls:
        # Calls + raises = limp-raise or cold-call lines — no content entry
        # describes those pots (extra live callers change every range). Only
        # pure limped pots (calls, zero raises) route to VS_LIMPERS.
        if raises:
            return None
        return _map_vs_limpers(state, hero_seat, calls)

    if not raises:
        # Folded to the hero: RFI (the BB never has an RFI decision).
        entry = _find_entry(NodeContext.RFI, hero.position, None)
        if entry is None:
            return None
        return _preflop_spot(entry, state, hero_seat)
    if len(raises) == 1:
        return _map_vs_open(state, hero_seat, raises)
    if len(raises) == 2:
        return _map_vs_3bet(state, hero_seat, raises)
    if len(raises) == 3:
        return _map_vs_4bet(state, hero_seat, raises)
    return None  # 5-bet+ pots are out of scope


def _map_vs_open(
    state: HandState, hero_seat: int, raises: list[HistoryAction]
) -> Spot | None:
    hero = state.seats[hero_seat]
    opener_pos = raises[0].position
    canonical_open = _OPEN_SIZE.get(opener_pos)
    # Open-size band [min-raise 2.0 .. _OVERSIZE_OPEN_CAP 4.5]: bots open at the
    # persona open_bb, and half the pool opens above the 3.0 standard (station
    # 3.5 / fish 4.0 / maniac 4.5). Those now map to the standard defense entry
    # instead of "no baseline yet" — the registry keys by node/position, never
    # bet size, so the same chart is reused; EV stays ≈-approximate (wider vs an
    # oversize, an accepted coverage tradeoff — 2026-07-19). Opens above 4.5
    # (jams, off-the-charts) still return None.
    if canonical_open is None or not (
        2.0 - _EPS <= state.current_bet_bb <= _OVERSIZE_OPEN_CAP + _EPS
    ):
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


def _map_vs_3bet(
    state: HandState, hero_seat: int, raises: list[HistoryAction]
) -> Spot | None:
    """Hero opened, exactly one villain 3-bet, everyone else folded (no calls
    reach here). Content covers only non-blind hero openers (UTG/CO/BTN), so a
    blind-opener shape can never look up an entry; the explicit blind gate also
    keeps `raises[0].amount_bb` (the history INCREMENT) equal to the raise-TO
    size — a blind opener's increment excludes the post."""
    hero = state.seats[hero_seat]
    if raises[0].position is not hero.position or hero.position in _BLIND_POSITIONS:
        return None  # cold-facing someone else's 3-bet has no content entry
    entry = _find_entry(NodeContext.VS_3BET, hero.position, raises[1].position)
    if entry is None:
        return None
    osize = _OPEN_SIZE[hero.position]
    # Hero's own open must sit in the same [min-raise 2.0 .. standard 3.0] band
    # as VS_RFI (R2) — vs an oversized open the villain's 3-bet range (and
    # hero's defend range) shifts materially, so oversize ⇒ None.
    if not (2.0 - _EPS <= raises[0].amount_bb <= _STD_OPEN_CAP + _EPS):
        return None
    # 3-bet band (engine legality supplies the lower bound — a bot's 3-bet
    # already passed apply()): cap at the standard 3.5x-the-open (R2 bots 3-bet
    # threebet_mult×open; tag/nit/lag 3.5x). Same justification as the open
    # band: the registry keys by node/position/facing, never bet size; grading
    # a standard 3-bet against the canonical entry stays within the ≈
    # approximation. Bigger 3-bets (maniac 5.5x) tighten hero's continue range
    # materially ⇒ None.
    if state.current_bet_bb > _THREEBET_MULT_CAP * osize + _EPS:
        return None
    return _preflop_spot(entry, state, hero_seat)


def _map_vs_4bet(
    state: HandState, hero_seat: int, raises: list[HistoryAction]
) -> Spot | None:
    """Villain opened, hero 3-bet, the SAME villain 4-bet (a cold 4-bet from a
    third seat is a different node with no content), everyone else folded.
    Content openers are all non-blind (UTG/CO/BTN), so the opener's history
    increment equals the raise-TO size; the hero (who may be the BB) gets the
    post added back to recover the 3-bet-TO size."""
    hero = state.seats[hero_seat]
    opener_pos = raises[0].position
    if (
        raises[1].position is not hero.position
        or raises[2].position is not opener_pos
        or opener_pos in _BLIND_POSITIONS
    ):
        return None
    entry = _find_entry(NodeContext.VS_4BET, hero.position, opener_pos)
    if entry is None:
        return None
    osize = _OPEN_SIZE[opener_pos]
    tbet = _THREEBET_MULT_CAP * osize  # standard 3-bet: 3.5x the open (R2)
    fbet = tbet * _FOURBET_MULT_CAP  # standard 4-bet: 2.4x the 3-bet (R2)
    # Same tolerant [engine-min .. standard] band per raise, same rationale as
    # the open/3-bet bands (R2 bots size realistically every street of the raise
    # war; the registry never keys on size). Anything ABOVE the standard size ⇒
    # None — jam-adjacent oversizes change hero's continue range materially
    # (true all-in 4-bets are already rejected by the ALLIN gate above).
    if not (2.0 - _EPS <= raises[0].amount_bb <= _STD_OPEN_CAP + _EPS):
        return None
    if raises[1].amount_bb + _posted(hero.position) > tbet + _EPS:
        return None
    if state.current_bet_bb > fbet + _EPS:
        return None
    return _preflop_spot(entry, state, hero_seat)


def _find_limp_entry(pos: Position, limper_count: int):
    """`_find_entry` ignores limper_count (BTN has vs_limpers entries for BOTH
    1 and 2 limpers) — match it explicitly here."""
    for e in _entries():
        if (
            e.villain_type is None
            and e.node_context == NodeContext.VS_LIMPERS
            and e.position == pos
            and (e.limper_count or 0) == limper_count
        ):
            return e
    return None


def _map_vs_limpers(
    state: HandState, hero_seat: int, calls: list[HistoryAction]
) -> Spot | None:
    """Unraised pot with only limps in front of the hero. The content keys the
    node by (hero position, limper COUNT) alone — build_spot canonically seats
    the limpers at _LIMP_SEATS[:count] — so WHICH non-blind seats limped is
    canonicalized away, exactly like the canonical sizes/stacks the other
    preflop families substitute. An SB complete is NOT a canonical limp
    (_LIMP_SEATS is non-blind only; it also means the hero is the BB, a
    position with no vs_limpers entry) ⇒ None."""
    hero = state.seats[hero_seat]
    if any(h.position in _BLIND_POSITIONS for h in calls):
        return None
    entry = _find_limp_entry(hero.position, len(calls))
    if entry is None:
        return None  # off-pack position or limper count — never fabricate
    return _preflop_spot(entry, state, hero_seat)
