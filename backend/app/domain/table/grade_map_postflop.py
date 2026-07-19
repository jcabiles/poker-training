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

from app.domain.scenarios import _combos_for, _find_entry
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
from app.domain.table.sizing import FACING_RAISE_MULTS, POSTFLOP_BET_FRACS


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
    # Engine history stores the raise INCREMENT; a non-blind opener's increment
    # equals the raise-TO size. N5: same standard-open BAND `_hu_srp_preflop`
    # uses (was an exact per-seat `_OPEN_SIZE` match — a standard 3.0 open
    # mapped the turn barrel but not the flop c-bet on the same line). ALL
    # downstream pot/bet math keys on the ACTUAL open, never the canonical
    # size (refuter HIGH: a relaxed gate with canonical pot math would
    # re-reject — or mis-price — every non-canonical in-band open).
    open_to = raises[0].amount_bb
    if not (2.0 - _EPS <= open_to <= _STD_OPEN_CAP + _EPS):
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
    if abs(pot - (2 * open_to + 0.5)) > _EPS:
        return None  # anything but open + BB call + dead SB is off-shape
    _fsmall, _fbig = POSTFLOP_BET_FRACS["flop"]  # single source (shared w/ the canonical-bet gate)
    small = round(_fsmall * pot, 1)
    big = round(_fbig * pot, 1)
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
# bet buckets are the RES-B per-street pot-fractions (`POSTFLOP_BET_FRACS`)
# rounded to 1dp — any other size (or an uncalled bet, a raise, a lead, a
# check-back) ⇒ None. STREET-AWARE (N4a): a canonical FLOP bet is 0.33/0.75 pot,
# a TURN bet 0.5/0.75, a RIVER bet 0.5/1.0. Without this, re-verifying a prior
# 0.5-pot turn barrel against the flop-only 0.33/0.75 would orphan the river
# mapper (refuter HIGH).


# Fraction-recognition tolerance. Hero's offered sizes are `round(f*pot, 1)`
# (up to 0.05 off the exact fraction) but BOT bets are `round(f*pot, 2)`
# (personas_postflop, ≤0.005 off) — with the old exact-match-vs-1dp check a
# tag's 0.33-pot c-bet of 1.82bb never equalled the canonical 1.8bb, so every
# villain-bet-gated facing mapper was DEAD in live play (design-review HIGH:
# 0 postflop facing offers in 1,123 hands). 0.06bb accepts both roundings;
# the nearest wrong fraction (0.33 vs 0.5 vs 0.75 pot) is whole bbs away at
# any realistic pot, so no ambiguity.
_CANON_BET_TOL = 0.06


def _is_canonical_bet(amount_bb: float, pot_before: float, street: Street) -> bool:
    return any(
        abs(amount_bb - f * pot_before) <= _CANON_BET_TOL
        for f in POSTFLOP_BET_FRACS[street.value]
    )


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
    if not _is_canonical_bet(bet.amount_bb, pot_before, street):
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
    if not _is_canonical_bet(bet.amount_bb, pot_before, street):
        return None
    return bet.amount_bb


def _check_bet_raise(
    state: HandState, street: Street, opener_pos: Position, pot_before: float
) -> tuple[float, float] | None:
    """Gate: this street went EXACTLY check(BB) → bet(opener=hero, canonical
    size) → raise(BB), hero now facing the check-raise. Returns
    (cbet, raise_to) or None.

    The check-raise SIZE is deliberately un-bucketed: personas raise on a
    continuous pot-fraction grid (`raise_to = bet + f*(pot+to_call)`), so a
    canonical-size gate would zero live coverage; the graders price any faced
    amount continuously. The raise must be COMPLETE — an incomplete all-in
    raise leaves the raiser ALLIN, which `_hu_srp_preflop` already rejects."""
    acts = _street_actions(state, street)
    if len(acts) != 3:
        return None
    chk, bet, cr = acts
    if chk.action is not ActionType.CHECK or chk.position is not Position.BB:
        return None
    if bet.action is not ActionType.BET or bet.position is not opener_pos:
        return None
    if not _is_canonical_bet(bet.amount_bb, pot_before, street):
        return None
    if cr.action is not ActionType.RAISE or cr.position is not Position.BB:
        return None
    # BB checked, so nothing invested this street: the history INCREMENT is the
    # full raise-TO.
    raise_to = cr.amount_bb
    if raise_to <= bet.amount_bb + _EPS:
        return None  # degenerate: a "raise" no bigger than the bet
    return bet.amount_bb, raise_to


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
    small_frac, big_frac = POSTFLOP_BET_FRACS[street.value]
    small = round(small_frac * pot, 1)
    big = round(big_frac * pot, 1)
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
    mults: tuple[float, float] = FACING_RAISE_MULTS["raise"],
    call_amt: float | None = None,
) -> Spot | None:
    """Hero facing a bet (or check-raise): fold / call / raise-small / raise-big
    (mirrors build_vs_turn_bet_spot / build_vs_river_bet_spot). `bet` is the
    raise-SIZING base (the faced bet, or the full raise-to for a check-raise);
    `call_amt` is the INCREMENTAL amount hero owes — defaults to `bet` (correct
    when hero has nothing invested this street), but a check-raise caller must
    pass `raise_to - hero's own bet` or pot-odds and `faced_bet_bucket` corrupt.

    N4b: two RAISE legs from `mults` (small first). Each leg clamps to hero's
    stack; legs collapse to one when big <= small after the clamp (short-stack).
    The affordability gate keys on the SMALL leg (widened from the old flat-3x
    single leg)."""
    hero = state.seats[hero_seat]
    small_mult, big_mult = mults
    raise_small = round(small_mult * bet, 1)
    raise_big = round(big_mult * bet, 1)
    hero_remaining = hero.stack_bb
    villain_remaining = villain.stack_bb
    # The legs are raise-TO totals, so affordability keys on hero's all-in-TO
    # (chips behind + already invested THIS street), not chips behind alone.
    # Zero-invested callers (vs_cbet, vs turn/river bet: hero=BB pre-decision)
    # are byte-identical; the check-raise-defense hero has the c-bet invested,
    # and gating on stack alone would silently un-map legal mid-stack raises
    # (refuter-on-diff HIGH).
    hero_raise_ceiling = round(hero.invested_street_bb + hero.stack_bb, 2)
    if hero_raise_ceiling < raise_small or villain_remaining <= 0:
        return None  # too shallow for even the small canonical raise bucket
    # Floor (not round) the clamped big leg to 1dp: stays <= the all-in ceiling
    # AND keeps both button labels at the same 1-dp precision (design-review LOW).
    raise_big = round(int(min(raise_big, hero_raise_ceiling) * 10 + 1e-9) / 10, 1)
    raise_legs = [raise_small]
    if raise_big - raise_small > _EPS:
        raise_legs.append(raise_big)
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
            LegalAction(action=ActionType.CALL, min_bb=call_amt if call_amt is not None else bet),
            *(
                LegalAction(action=ActionType.RAISE, min_bb=leg, max_bb=hero_raise_ceiling)
                for leg in raise_legs
            ),
        ],
        node_context=[ctx],
        facing=villain.position,
        hero_range=hero_range,
        villain_range=villain_range,
    )


def map_flop_vs_cbet(state: HandState, hero_seat: int) -> Spot | None:
    """HU vs flop c-bet (N4b): hero = BB who called a canonical open, checked
    the flop, and now faces the opener's canonical c-bet. Hero's RAISE here is
    a check-raise, so the legs use the flop-scoped check_raise mults
    (RES-B :148: 2.5x/3.5x the c-bet)."""
    hero = state.seats[hero_seat]
    if len(state.board) != 3 or hero.position is not Position.BB:
        return None
    gate = _hu_srp_preflop(state)
    if gate is None:
        return None
    opener, bb, osize = gate
    if bb.seat != hero_seat:
        return None
    flop_pot = round(2 * osize + 0.5, 2)
    cbet = _check_bet(state, Street.FLOP, opener.position, flop_pot)
    if cbet is None:
        return None
    pot = _live_pot(state)
    if abs(pot - (flop_pot + cbet)) > _EPS:
        return None
    ranges = _srp_ranges(opener.position)
    if ranges is None:
        return None
    opener_range, bb_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, cbet,
        Street.FLOP, NodeContext.VS_CBET, bb_range, opener_range,
        mults=FACING_RAISE_MULTS["check_raise"],
    )


def map_flop_vs_check_raise(state: HandState, hero_seat: int) -> Spot | None:
    """HU vs flop check-raise (N4b): hero opened canonically, c-bet the flop at
    a canonical size, and the BB check-raised (any complete size). Hero's
    re-raise is a plain facing-bet raise (RES-B :149: 2.5x/3.0x the raise-to).
    CALL is the INCREMENTAL amount hero owes (raise_to - cbet) — hero already
    has the c-bet invested this street (mirrors build_check_raise_spot)."""
    hero = state.seats[hero_seat]
    if len(state.board) != 3 or hero.position in _BLIND_POSITIONS:
        return None
    gate = _hu_srp_preflop(state)
    if gate is None:
        return None
    opener, bb, osize = gate
    if opener.seat != hero_seat:
        return None
    flop_pot = round(2 * osize + 0.5, 2)
    faced = _check_bet_raise(state, Street.FLOP, hero.position, flop_pot)
    if faced is None:
        return None
    cbet, raise_to = faced
    pot = _live_pot(state)
    if abs(pot - (flop_pot + cbet + raise_to)) > _EPS:
        return None
    ranges = _srp_ranges(hero.position)
    if ranges is None:
        return None
    opener_range, bb_range = ranges
    return _faced_bet_spot(
        state, hero_seat, bb, pot, raise_to,
        Street.FLOP, NodeContext.VS_CHECK_RAISE, opener_range, bb_range,
        mults=FACING_RAISE_MULTS["raise"],
        call_amt=round(raise_to - cbet, 2),
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


# --- N5: 3-way multiway BB-defense line (the "minimum honest multiway") ----
# ONE new multiway family: hero = BB defender in a 3-way single-raised pot
# (opener + one non-blind cold-caller + BB), facing the OPENER's canonical
# c-bet/barrel AFTER the cold-caller has already responded — so hero CLOSES
# the action (engine-verified: in every 3-way postflop order the BB responds
# last to a bet; players-still-behind spots the graders can't see stay "no
# baseline yet"). The cold-caller's VS_RFI call entry is a mapping GATE only
# (never a grader input — grade_vs_* consume ONE villain_range, the
# aggressor's; `_apply_multiway` is the deliberate multiway correction).
# Caller folded to the bet => the built spot has 2 live players and grades on
# the plain HU model with the caller's dead money correctly in the pot.
# Effective stack is min(hero, opener) — the caller's stack is ignored, an
# accepted simplification of the 3-way SPR. Everything else — limped pots,
# donk leads, 4+ way, caller raises, delayed c-bets — returns None.


def _mw_srp_preflop(state: HandState) -> tuple | None:
    """Gate: 3-way single-raised pot. One non-blind opener at an in-band open,
    exactly one non-blind cold-caller, the BB called, SB folded. Entrants are
    derived from the PREFLOP actions (not current statuses — the caller may
    legitimately have folded to a later postflop bet, leaving his dead money
    in the pot). Opener + BB must still be IN; the caller must be IN or
    postflop-FOLDED (never all-in); nobody else may be live.
    Returns (opener, caller, bb, open_to) seat-states or None."""
    pre = _street_actions(state, Street.PREFLOP)
    if any(
        h.action not in (ActionType.FOLD, ActionType.RAISE, ActionType.CALL)
        for h in pre
    ):
        return None
    raises = [h for h in pre if h.action is ActionType.RAISE]
    calls = [h for h in pre if h.action is ActionType.CALL]
    if len(raises) != 1 or len(calls) != 2:
        return None
    opener_pos = raises[0].position
    caller_pos = next((c.position for c in calls if c.position is not Position.BB), None)
    if caller_pos is None or Position.BB not in {c.position for c in calls}:
        return None
    if opener_pos in _BLIND_POSITIONS or caller_pos in _BLIND_POSITIONS:
        return None  # blind entrants (SB open/complete, BB raise) are off-shape
    opener = next((s for s in state.seats if s.position is opener_pos), None)
    caller = next((s for s in state.seats if s.position is caller_pos), None)
    bb = next((s for s in state.seats if s.position is Position.BB), None)
    if opener is None or caller is None or bb is None:
        return None
    if opener.status is not PlayerStatus.IN or bb.status is not PlayerStatus.IN:
        return None
    if caller.status not in (PlayerStatus.IN, PlayerStatus.FOLDED):
        return None  # an all-in anywhere in the line is off-shape
    entrants = {opener.seat, caller.seat, bb.seat}
    if any(
        s.status is not PlayerStatus.FOLDED
        for s in state.seats
        if s.seat not in entrants
    ):
        return None  # a fourth live player — not the 3-way shape
    open_to = raises[0].amount_bb
    if not (2.0 - _EPS <= open_to <= _STD_OPEN_CAP + _EPS):
        return None
    return opener, caller, bb, open_to


def _mw_check_bet_responded(
    state, street: Street, opener_pos: Position, caller_pos: Position, pot_before: float
) -> tuple[float, bool] | None:
    """Gate: this street went EXACTLY check(BB) -> bet(opener, canonical) ->
    call-or-fold(caller); hero (the BB) now faces the bet and CLOSES. Returns
    (bet, caller_called) or None. A caller RAISE is a different node -> None."""
    acts = _street_actions(state, street)
    if len(acts) != 3:
        return None
    chk, bet, resp = acts
    if chk.action is not ActionType.CHECK or chk.position is not Position.BB:
        return None
    if bet.action is not ActionType.BET or bet.position is not opener_pos:
        return None
    if not _is_canonical_bet(bet.amount_bb, pot_before, street):
        return None
    if resp.position is not caller_pos:
        return None
    if resp.action is ActionType.CALL:
        if abs(resp.amount_bb - bet.amount_bb) > _EPS:
            return None  # short call = someone is all-in — off-shape
        return bet.amount_bb, True
    if resp.action is ActionType.FOLD:
        return bet.amount_bb, False
    return None  # caller raised — hero faces a raise, not the canonical bet


def _mw_check_bet_call_call(
    state, street: Street, opener_pos: Position, caller_pos: Position, pot_before: float
) -> float | None:
    """Gate: a PRIOR street went EXACTLY check(BB) -> bet(opener, canonical) ->
    call(caller) -> call(BB) — the 3-way continuation line stayed intact.
    Returns the bet size or None."""
    acts = _street_actions(state, street)
    if len(acts) != 4:
        return None
    chk, bet, c1, c2 = acts
    if chk.action is not ActionType.CHECK or chk.position is not Position.BB:
        return None
    if bet.action is not ActionType.BET or bet.position is not opener_pos:
        return None
    if not _is_canonical_bet(bet.amount_bb, pot_before, street):
        return None
    if c1.action is not ActionType.CALL or c1.position is not caller_pos:
        return None
    if c2.action is not ActionType.CALL or c2.position is not Position.BB:
        return None
    if abs(c1.amount_bb - bet.amount_bb) > _EPS or abs(c2.amount_bb - bet.amount_bb) > _EPS:
        return None  # short call = someone is all-in — off-shape
    return bet.amount_bb


def _mw_ranges(opener_pos: Position, caller_pos: Position) -> tuple[str, str] | None:
    """(BB defense call range for hero, opener RFI raise range for villain) —
    PLUS the cold-caller gate: the (caller, opener) VS_RFI call entry must
    exist or the pot's third range is unmodeled -> None. The caller's range is
    NOT returned: no grader consumes it (see module comment)."""
    ranges = _srp_ranges(opener_pos)
    if ranges is None:
        return None
    opener_range, bb_range = ranges
    caller_entry = _find_entry(NodeContext.VS_RFI, caller_pos, opener_pos)
    if caller_entry is None or not _combos_for(caller_entry, ActionType.CALL):
        return None
    return bb_range, opener_range


def map_mw_flop_vs_cbet(state: HandState, hero_seat: int) -> Spot | None:
    """3-way vs flop c-bet: hero = BB who called a 3-way open, checked, the
    opener c-bet a canonical size, the cold-caller responded — hero closes."""
    hero = state.seats[hero_seat]
    if len(state.board) != 3 or hero.position is not Position.BB:
        return None
    gate = _mw_srp_preflop(state)
    if gate is None:
        return None
    opener, caller, bb, open_to = gate
    if bb.seat != hero_seat:
        return None
    flop_pot = round(3 * open_to + 0.5, 2)
    faced = _mw_check_bet_responded(
        state, Street.FLOP, opener.position, caller.position, flop_pot
    )
    if faced is None:
        return None
    cbet, caller_called = faced
    pot = _live_pot(state)
    expected = flop_pot + cbet + (cbet if caller_called else 0.0)
    if abs(pot - expected) > _EPS:
        return None
    ranges = _mw_ranges(opener.position, caller.position)
    if ranges is None:
        return None
    bb_range, opener_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, cbet,
        Street.FLOP, NodeContext.VS_CBET, bb_range, opener_range,
        mults=FACING_RAISE_MULTS["check_raise"],
    )


def map_mw_vs_turn_bet(state: HandState, hero_seat: int) -> Spot | None:
    """3-way vs turn barrel: canonical 3-way flop bet-call-call, then the
    opener bets the turn, the caller responded — hero (BB) closes."""
    hero = state.seats[hero_seat]
    if len(state.board) != 4 or hero.position is not Position.BB:
        return None
    gate = _mw_srp_preflop(state)
    if gate is None:
        return None
    opener, caller, bb, open_to = gate
    if bb.seat != hero_seat:
        return None
    flop_pot = round(3 * open_to + 0.5, 2)
    fbet = _mw_check_bet_call_call(
        state, Street.FLOP, opener.position, caller.position, flop_pot
    )
    if fbet is None:
        return None
    turn_pot = round(flop_pot + 3 * fbet, 2)
    faced = _mw_check_bet_responded(
        state, Street.TURN, opener.position, caller.position, turn_pot
    )
    if faced is None:
        return None
    tbet, caller_called = faced
    pot = _live_pot(state)
    expected = turn_pot + tbet + (tbet if caller_called else 0.0)
    if abs(pot - expected) > _EPS:
        return None
    ranges = _mw_ranges(opener.position, caller.position)
    if ranges is None:
        return None
    bb_range, opener_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, tbet,
        Street.TURN, NodeContext.VS_TURN_BET, bb_range, opener_range,
    )


def map_mw_vs_river_bet(state: HandState, hero_seat: int) -> Spot | None:
    """3-way vs river bet: canonical 3-way flop AND turn bet-call-call, then
    the opener bets the river, the caller responded — hero (BB) closes."""
    hero = state.seats[hero_seat]
    if len(state.board) != 5 or hero.position is not Position.BB:
        return None
    gate = _mw_srp_preflop(state)
    if gate is None:
        return None
    opener, caller, bb, open_to = gate
    if bb.seat != hero_seat:
        return None
    flop_pot = round(3 * open_to + 0.5, 2)
    fbet = _mw_check_bet_call_call(
        state, Street.FLOP, opener.position, caller.position, flop_pot
    )
    if fbet is None:
        return None
    turn_pot = round(flop_pot + 3 * fbet, 2)
    tbet = _mw_check_bet_call_call(
        state, Street.TURN, opener.position, caller.position, turn_pot
    )
    if tbet is None:
        return None
    river_pot = round(turn_pot + 3 * tbet, 2)
    faced = _mw_check_bet_responded(
        state, Street.RIVER, opener.position, caller.position, river_pot
    )
    if faced is None:
        return None
    rbet, caller_called = faced
    pot = _live_pot(state)
    expected = river_pot + rbet + (rbet if caller_called else 0.0)
    if abs(pot - expected) > _EPS:
        return None
    ranges = _mw_ranges(opener.position, caller.position)
    if ranges is None:
        return None
    bb_range, opener_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, rbet,
        Street.RIVER, NodeContext.VS_RIVER_BET, bb_range, opener_range,
    )
