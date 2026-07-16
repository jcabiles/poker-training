"""Map a live Simulate POSTFLOP decision point to a canonical gradeable Spot.

Split out of `grade_map` (S10) so postflop range/coverage work (R5: the
openable call/fold/raise chart + widened postflop grading) owns this module
cleanly. Pure domain: no web/DB imports (enforced by test_domain_purity).
It classifies ONLY the HU single-raised-pot continuation line — flop c-bet
(S10), plus the four turn/river shapes (R5): turn barrel, facing a turn bet,
river barrel, facing a river bet. Anything else returns None ("no baseline
yet") — never a fabricated or truncated postflop spot.

Canonical-shape parity: each mapper mirrors its `scenarios.py` builder
(`build_cbet_spot` / `build_turn_barrel_spot` / `build_vs_turn_bet_spot` /
`build_river_barrel_spot` / `build_vs_river_bet_spot`) field-by-field with the
live board / cards / stacks / pot substituted in and the ranges resolved
through the same content entries — so a mapped Spot is always one the existing
graders were built for. The turn/river mappers gate 2–3 SEQUENTIAL streets of
exact bet sizing (in-band open, 0.33/0.75-pot c-bet AND called, 0.33/0.75-pot
turn barrel AND called for river) and return None on ANY doubt.
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
from app.domain.table.grade_map_preflop import _STD_OPEN_CAP


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


# --- R5: turn/river mappers (HU SRP continuation line only) -----------------
# Each mapper re-verifies the FULL prior line street by street. The canonical
# bet buckets are the builders' 0.33/0.75-of-pot sizes rounded to 1dp — any
# other size (or an uncalled bet, a raise, a lead, a check-back) ⇒ None.

_BET_FRACS = (0.33, 0.75)


def _is_canonical_bet(amount_bb: float, pot_before: float) -> bool:
    return any(abs(amount_bb - round(f * pot_before, 1)) <= _EPS for f in _BET_FRACS)


def _hu_srp_preflop(state: HandState) -> tuple | None:
    """Gate: HU single-raised pot. One non-blind opener raised to a size in
    the standard open band [min-raise 2.0 .. 3.0], the BB (and only the BB)
    called, everyone else folded. Returns (opener_seat_state, bb_seat_state,
    open_to) — open_to is the ACTUAL open size (downstream pot math depends on
    it: the BB called that amount) — or None."""
    live = [s for s in state.seats if s.status is not PlayerStatus.FOLDED]
    if len(live) != 2:
        return None  # multiway (or fold-out) — never HU-canonical
    bb = next((s for s in live if s.position is Position.BB), None)
    opener = next((s for s in live if s.position is not Position.BB), None)
    if bb is None or opener is None or opener.position in _BLIND_POSITIONS:
        return None
    if bb.status is not PlayerStatus.IN or opener.status is not PlayerStatus.IN:
        return None  # an all-in anywhere in the line is off-shape
    pre = _street_actions(state, Street.PREFLOP)
    if any(
        h.action not in (ActionType.FOLD, ActionType.RAISE, ActionType.CALL)
        for h in pre
    ):
        return None
    raises = [h for h in pre if h.action is ActionType.RAISE]
    calls = [h for h in pre if h.action is ActionType.CALL]
    if len(raises) != 1 or raises[0].position is not opener.position:
        return None
    if len(calls) != 1 or calls[0].position is not Position.BB:
        return None
    open_to = raises[0].amount_bb
    # Engine history stores the raise INCREMENT; a non-blind opener's increment
    # equals the raise-TO size. Same [min-raise 2.0 .. standard 3.0] band as
    # grade_map_preflop._map_vs_open (R2): bot personas open a FIXED open_bb
    # from EVERY seat (tag/lag/nit 3.0), so an exact per-seat canonical gate
    # (2.5 for HJ/CO/BTN) would silently zero those seats' turn/river coverage.
    # Oversized persona opens (station 3.5 / fish 4.0 / maniac 4.5) still
    # return None — defense ranges tighten materially vs oversizes.
    if not (2.0 - _EPS <= open_to <= _STD_OPEN_CAP + _EPS):
        return None
    return opener, bb, open_to


def _check_bet_call(
    state: HandState, street: Street, opener_pos: Position, pot_before: float
) -> float | None:
    """Gate: this street went EXACTLY check(BB) → bet(opener, canonical size)
    → call(BB). Returns the bet size or None."""
    acts = _street_actions(state, street)
    if len(acts) != 3:
        return None
    chk, bet, call = acts
    if chk.action is not ActionType.CHECK or chk.position is not Position.BB:
        return None
    if bet.action is not ActionType.BET or bet.position is not opener_pos:
        return None
    if call.action is not ActionType.CALL or call.position is not Position.BB:
        return None
    if not _is_canonical_bet(bet.amount_bb, pot_before):
        return None
    if abs(call.amount_bb - bet.amount_bb) > _EPS:
        return None  # short call = someone is all-in — off-shape
    return bet.amount_bb


def _check_bet(
    state: HandState, street: Street, opener_pos: Position, pot_before: float
) -> float | None:
    """Gate: this street went EXACTLY check(BB) → bet(opener, canonical size),
    hero (the BB) now facing it. Returns the bet size or None."""
    acts = _street_actions(state, street)
    if len(acts) != 2:
        return None
    chk, bet = acts
    if chk.action is not ActionType.CHECK or chk.position is not Position.BB:
        return None
    if bet.action is not ActionType.BET or bet.position is not opener_pos:
        return None
    if not _is_canonical_bet(bet.amount_bb, pot_before):
        return None
    return bet.amount_bb


def _bb_checked_only(state: HandState, street: Street) -> bool:
    """Gate: this street's only action so far is the BB's check to the hero."""
    acts = _street_actions(state, street)
    return (
        len(acts) == 1
        and acts[0].action is ActionType.CHECK
        and acts[0].position is Position.BB
    )


def _srp_ranges(opener_pos: Position) -> tuple[str, str] | None:
    """(opener RFI raise range, BB blind-defense call range) from the SAME
    content entries the builders resolve — never their literal fallbacks."""
    rfi_entry = _find_entry(NodeContext.RFI, opener_pos, None)
    bd_entry = _find_entry(NodeContext.BLIND_DEFENSE, Position.BB, opener_pos)
    opener_range = _combos_for(rfi_entry, ActionType.RAISE)
    bb_range = _combos_for(bd_entry, ActionType.CALL)
    if not opener_range or not bb_range:
        return None
    return opener_range, bb_range


def _players(state: HandState, hero_seat: int) -> list[PlayerState]:
    return [
        PlayerState(
            position=s.position,
            stack_bb=s.stack_bb,
            status=s.status,
            is_hero=s.seat == hero_seat,
        )
        for s in state.seats
    ]


def _live_pot(state: HandState) -> float:
    return round(sum(s.invested_total_bb for s in state.seats), 2)


def _barrel_spot(
    state: HandState,
    hero_seat: int,
    villain,
    pot: float,
    street: Street,
    ctx: NodeContext,
    hero_range: str,
    villain_range: str,
) -> Spot | None:
    """Hero = aggressor deciding check / bet small / bet big (mirrors
    build_turn_barrel_spot / build_river_barrel_spot legal-action shape)."""
    hero = state.seats[hero_seat]
    small = round(0.33 * pot, 1)
    big = round(0.75 * pot, 1)
    hero_remaining = hero.stack_bb
    villain_remaining = villain.stack_bb
    if hero_remaining < big or villain_remaining <= 0:
        return None  # too shallow for the canonical small/big bet buckets
    effective = round(min(hero_remaining, villain_remaining), 2)
    return Spot(
        game=GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0),
        street=street,
        board=list(state.board),
        pot_bb=pot,
        hero=Hero(
            position=hero.position, hole_cards=hero.hole_cards, stack_bb=hero_remaining
        ),
        players=_players(state, hero_seat),
        effective_stack_bb=effective,
        spr=round(effective / pot, 1),
        action_history=list(state.action_history),
        to_act=hero.position,
        legal_actions=[
            LegalAction(action=ActionType.CHECK),
            LegalAction(action=ActionType.BET, min_bb=small, max_bb=hero_remaining),
            LegalAction(action=ActionType.BET, min_bb=big, max_bb=hero_remaining),
        ],
        node_context=[ctx],
        facing=Position.BB,
        hero_range=hero_range,
        villain_range=villain_range,
    )


def _faced_bet_spot(
    state: HandState,
    hero_seat: int,
    villain,
    pot: float,
    bet: float,
    street: Street,
    ctx: NodeContext,
    hero_range: str,
    villain_range: str,
) -> Spot | None:
    """Hero = BB defender facing the opener's bet: fold / call / raise
    (mirrors build_vs_turn_bet_spot / build_vs_river_bet_spot; CALL.min_bb is
    the INCREMENTAL bet — hero has nothing invested this street yet)."""
    hero = state.seats[hero_seat]
    raise_size = round(3 * bet, 1)
    hero_remaining = hero.stack_bb
    villain_remaining = villain.stack_bb
    if hero_remaining < raise_size or villain_remaining <= 0:
        return None  # too shallow for the canonical raise bucket
    effective = round(min(hero_remaining, villain_remaining), 2)
    return Spot(
        game=GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0),
        street=street,
        board=list(state.board),
        pot_bb=pot,
        hero=Hero(
            position=hero.position, hole_cards=hero.hole_cards, stack_bb=hero_remaining
        ),
        players=_players(state, hero_seat),
        effective_stack_bb=effective,
        spr=round(effective / pot, 1),
        action_history=list(state.action_history),
        to_act=hero.position,
        legal_actions=[
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=bet),
            LegalAction(action=ActionType.RAISE, min_bb=raise_size, max_bb=hero_remaining),
        ],
        node_context=[ctx],
        facing=villain.position,
        hero_range=hero_range,
        villain_range=villain_range,
    )


def map_turn_barrel(state: HandState, hero_seat: int) -> Spot | None:
    """HU turn barrel: hero opened canonically, c-bet the flop at a canonical
    size and got called, and the BB has checked the turn to the hero."""
    hero = state.seats[hero_seat]
    if len(state.board) != 4 or hero.position in _BLIND_POSITIONS:
        return None
    gate = _hu_srp_preflop(state)
    if gate is None:
        return None
    opener, bb, osize = gate
    if opener.seat != hero_seat:
        return None  # hero must be the opener; BB shapes go to map_vs_turn_bet
    flop_pot = round(2 * osize + 0.5, 2)
    cbet = _check_bet_call(state, Street.FLOP, hero.position, flop_pot)
    if cbet is None:
        return None
    if not _bb_checked_only(state, Street.TURN):
        return None
    pot = _live_pot(state)
    if abs(pot - (flop_pot + 2 * cbet)) > _EPS:
        return None
    ranges = _srp_ranges(hero.position)
    if ranges is None:
        return None
    return _barrel_spot(
        state, hero_seat, bb, pot, Street.TURN, NodeContext.TURN_BARREL, *ranges
    )


def map_vs_turn_bet(state: HandState, hero_seat: int) -> Spot | None:
    """HU vs turn bet: hero = BB who called a canonical open and a canonical
    flop c-bet, checked the turn, and now faces the opener's canonical bet."""
    hero = state.seats[hero_seat]
    if len(state.board) != 4 or hero.position is not Position.BB:
        return None
    gate = _hu_srp_preflop(state)
    if gate is None:
        return None
    opener, bb, osize = gate
    if bb.seat != hero_seat:
        return None
    flop_pot = round(2 * osize + 0.5, 2)
    cbet = _check_bet_call(state, Street.FLOP, opener.position, flop_pot)
    if cbet is None:
        return None
    turn_pot = round(flop_pot + 2 * cbet, 2)
    tbet = _check_bet(state, Street.TURN, opener.position, turn_pot)
    if tbet is None:
        return None
    pot = _live_pot(state)
    if abs(pot - (turn_pot + tbet)) > _EPS:
        return None
    ranges = _srp_ranges(opener.position)
    if ranges is None:
        return None
    opener_range, bb_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, tbet,
        Street.TURN, NodeContext.VS_TURN_BET, bb_range, opener_range,
    )


def map_river_barrel(state: HandState, hero_seat: int) -> Spot | None:
    """HU river barrel: hero opened, c-bet the flop AND barreled the turn at
    canonical sizes, called both times; the BB has checked the river."""
    hero = state.seats[hero_seat]
    if len(state.board) != 5 or hero.position in _BLIND_POSITIONS:
        return None
    gate = _hu_srp_preflop(state)
    if gate is None:
        return None
    opener, bb, osize = gate
    if opener.seat != hero_seat:
        return None
    flop_pot = round(2 * osize + 0.5, 2)
    cbet = _check_bet_call(state, Street.FLOP, hero.position, flop_pot)
    if cbet is None:
        return None
    turn_pot = round(flop_pot + 2 * cbet, 2)
    tbet = _check_bet_call(state, Street.TURN, hero.position, turn_pot)
    if tbet is None:
        return None
    if not _bb_checked_only(state, Street.RIVER):
        return None
    pot = _live_pot(state)
    if abs(pot - (turn_pot + 2 * tbet)) > _EPS:
        return None
    ranges = _srp_ranges(hero.position)
    if ranges is None:
        return None
    return _barrel_spot(
        state, hero_seat, bb, pot, Street.RIVER, NodeContext.RIVER_BARREL, *ranges
    )


def map_vs_river_bet(state: HandState, hero_seat: int) -> Spot | None:
    """HU vs river bet: hero = BB who called the open, the flop c-bet AND the
    turn barrel (all canonical), checked the river, and now faces the opener's
    canonical river bet."""
    hero = state.seats[hero_seat]
    if len(state.board) != 5 or hero.position is not Position.BB:
        return None
    gate = _hu_srp_preflop(state)
    if gate is None:
        return None
    opener, bb, osize = gate
    if bb.seat != hero_seat:
        return None
    flop_pot = round(2 * osize + 0.5, 2)
    cbet = _check_bet_call(state, Street.FLOP, opener.position, flop_pot)
    if cbet is None:
        return None
    turn_pot = round(flop_pot + 2 * cbet, 2)
    tbet = _check_bet_call(state, Street.TURN, opener.position, turn_pot)
    if tbet is None:
        return None
    river_pot = round(turn_pot + 2 * tbet, 2)
    rbet = _check_bet(state, Street.RIVER, opener.position, river_pot)
    if rbet is None:
        return None
    pot = _live_pot(state)
    if abs(pot - (river_pot + rbet)) > _EPS:
        return None
    ranges = _srp_ranges(opener.position)
    if ranges is None:
        return None
    opener_range, bb_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, rbet,
        Street.RIVER, NodeContext.VS_RIVER_BET, bb_range, opener_range,
    )
