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
recognized bet sizing (in-band open, recognized-fraction c-bet AND called,
recognized-fraction turn barrel AND called for river — see
`RECOGNIZED_BET_FRACS`) and return None on ANY doubt.
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
from app.domain.table.grade_map_preflop import _OVERSIZE_OPEN_CAP
from app.domain.table.sizing import (
    FACING_RAISE_MULTS,
    POSTFLOP_BET_FRACS,
    RECOGNIZED_BET_FRACS,
)


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
    if not (2.0 - _EPS <= open_to <= _OVERSIZE_OPEN_CAP + _EPS):
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
# Each mapper re-verifies the FULL prior line street by street. A recognized
# bet is any `RECOGNIZED_BET_FRACS` pot-fraction (M1-L4: the whole persona bet
# grid 0.33/0.5/0.75/1.0/1.5, every street — RES-I §3 L4 widened this from the
# street's two `POSTFLOP_BET_FRACS` hero sizes, which silently un-mapped every
# bot 0.5/1.0-pot flop c-bet). Any other size (or an uncalled bet, a raise, a
# lead, a check-back) ⇒ None. The ACTUAL bet amount always flows into the pot
# math and the built spot's CALL leg, so the graders price the TRUE live
# pot-fraction — recognition never collapses a size into another bucket
# (RES-I §5 HIGH flag).


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
    """M1-L4: recognition runs against the full persona grid on every street
    (`street` is kept for call-site documentation; the grid is street-uniform).
    Adjacent grid fractions are ≥0.17·pot apart, so at any postflop pot
    (≥4.5bb) the 0.06bb tolerance can never match two fractions at once."""
    del street
    return any(
        abs(amount_bb - f * pot_before) <= _CANON_BET_TOL
        for f in RECOGNIZED_BET_FRACS
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
    if not (2.0 - _EPS <= open_to <= _OVERSIZE_OPEN_CAP + _EPS):
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


# --- N5/M6: 3- and 4-way multiway BB-defense line ("minimum honest MW") ----
# ONE multiway family: hero = BB defender in a 3-way (N5) or 4-way (M6)
# single-raised pot (opener + one/two non-blind cold-callers + BB), facing
# the OPENER's canonical c-bet/barrel AFTER every cold-caller has already
# responded — hero CLOSES, verified from the ACTION ORDER of the street (the
# gates require the exact check(BB) -> bet(opener) -> respond(every caller)
# sequence; RES-H §1.2 re-proved "BB closes" is shape-dependent, never a
# positional rule). Any spot with a live player still to act behind hero, or
# a 5+-way field (RES-H §2.4 caps the calibrated tier at 4-way), stays "no
# baseline yet" (None). The cold-callers' VS_RFI call entries are mapping
# GATES only (never a grader input — grade_vs_* consume ONE villain_range,
# the aggressor's; `_apply_multiway` is the deliberate multiway correction).
# A caller folding to a bet degrades the field with his dead money correctly
# in the pot. Effective stack is min(hero, opener) — callers' stacks are
# ignored, an accepted simplification of the MW SPR. Everything else —
# limped pots, donk leads, caller raises, delayed c-bets — returns None.


def _mw_srp_preflop(state: HandState) -> tuple | None:
    """Gate: 3- or 4-way single-raised pot. One non-blind opener at an in-band
    open, one or two non-blind cold-callers (M6 widened from exactly one), the
    BB called, SB folded. Entrants are derived from the PREFLOP actions (not
    current statuses — a caller may legitimately have folded to a later
    postflop bet, leaving his dead money in the pot). Opener + BB must still
    be IN; every caller must be IN or postflop-FOLDED (never all-in); nobody
    else may be live. Three-plus cold-callers (5+-way) is past the calibrated
    tier (RES-H §2.4) -> None. Returns (opener, callers, bb, open_to) —
    `callers` a tuple in preflop call order — or None."""
    pre = _street_actions(state, Street.PREFLOP)
    if any(
        h.action not in (ActionType.FOLD, ActionType.RAISE, ActionType.CALL)
        for h in pre
    ):
        return None
    raises = [h for h in pre if h.action is ActionType.RAISE]
    calls = [h for h in pre if h.action is ActionType.CALL]
    if len(raises) != 1 or len(calls) not in (2, 3):
        return None  # not an SRP, or 5+-way (3+ cold-callers) — no baseline
    opener_pos = raises[0].position
    caller_pos = [c.position for c in calls if c.position is not Position.BB]
    if len(caller_pos) != len(calls) - 1 or len(set(caller_pos)) != len(caller_pos):
        return None  # BB didn't call, or a duplicate caller (limp-then-call)
    if opener_pos in _BLIND_POSITIONS or any(
        p in _BLIND_POSITIONS for p in caller_pos
    ):
        return None  # blind entrants (SB open/complete, BB raise) are off-shape
    opener = next((s for s in state.seats if s.position is opener_pos), None)
    callers = tuple(
        s for p in caller_pos for s in state.seats if s.position is p
    )
    bb = next((s for s in state.seats if s.position is Position.BB), None)
    if opener is None or len(callers) != len(caller_pos) or bb is None:
        return None
    if opener.status is not PlayerStatus.IN or bb.status is not PlayerStatus.IN:
        return None
    if any(c.status not in (PlayerStatus.IN, PlayerStatus.FOLDED) for c in callers):
        return None  # an all-in anywhere in the line is off-shape
    entrants = {opener.seat, bb.seat} | {c.seat for c in callers}
    if any(
        s.status is not PlayerStatus.FOLDED
        for s in state.seats
        if s.seat not in entrants
    ):
        return None  # an extra live player — not the gated 3/4-way shape
    open_to = raises[0].amount_bb
    if not (2.0 - _EPS <= open_to <= _OVERSIZE_OPEN_CAP + _EPS):
        return None
    return opener, callers, bb, open_to


def _mw_check_bet_responded(
    state, street: Street, opener_pos: Position, callers, pot_before: float
) -> tuple[float, int] | None:
    """Gate: this street went EXACTLY check(BB) -> bet(opener, canonical) ->
    call-or-fold(EVERY caller); hero (the BB) now faces the bet and CLOSES —
    the action-order requirement itself (all callers responded between the
    bet and hero) is the closing-seat guard. Returns (bet, n_called) or None.
    A caller RAISE is a different node -> None."""
    acts = _street_actions(state, street)
    if len(acts) != 2 + len(callers):
        return None
    chk, bet, *resps = acts
    if chk.action is not ActionType.CHECK or chk.position is not Position.BB:
        return None
    if bet.action is not ActionType.BET or bet.position is not opener_pos:
        return None
    if not _is_canonical_bet(bet.amount_bb, pot_before, street):
        return None
    if {r.position for r in resps} != {c.position for c in callers}:
        return None  # a non-caller acted, or a caller hasn't responded yet
    n_called = 0
    for resp in resps:
        if resp.action is ActionType.CALL:
            if abs(resp.amount_bb - bet.amount_bb) > _EPS:
                return None  # short call = someone is all-in — off-shape
            n_called += 1
        elif resp.action is not ActionType.FOLD:
            return None  # caller raised — hero faces a raise, not the bet
    return bet.amount_bb, n_called


def _mw_check_bet_call_call(
    state, street: Street, opener_pos: Position, callers, pot_before: float
) -> float | None:
    """Gate: a PRIOR street went EXACTLY check(BB) -> bet(opener, canonical) ->
    call(EVERY caller) -> call(BB) — the full MW continuation line stayed
    intact. Returns the bet size or None."""
    acts = _street_actions(state, street)
    if len(acts) != 3 + len(callers):
        return None
    chk, bet, *caller_calls, bb_call = acts
    if chk.action is not ActionType.CHECK or chk.position is not Position.BB:
        return None
    if bet.action is not ActionType.BET or bet.position is not opener_pos:
        return None
    if not _is_canonical_bet(bet.amount_bb, pot_before, street):
        return None
    if {c.position for c in caller_calls} != {c.position for c in callers}:
        return None
    if bb_call.action is not ActionType.CALL or bb_call.position is not Position.BB:
        return None
    for c in (*caller_calls, bb_call):
        if c.action is not ActionType.CALL or abs(c.amount_bb - bet.amount_bb) > _EPS:
            return None  # a fold/raise, or short call (all-in) — off-shape
    return bet.amount_bb


def _mw_ranges(opener_pos: Position, caller_positions) -> tuple[str, str] | None:
    """(BB defense call range for hero, opener RFI raise range for villain) —
    PLUS the cold-caller gate: EVERY (caller, opener) VS_RFI call entry must
    exist or the pot carries an unmodeled range -> None. Caller ranges are
    NOT returned: no grader consumes them (see module comment)."""
    ranges = _srp_ranges(opener_pos)
    if ranges is None:
        return None
    opener_range, bb_range = ranges
    for caller_pos in caller_positions:
        entry = _find_entry(NodeContext.VS_RFI, caller_pos, opener_pos)
        if entry is None or not _combos_for(entry, ActionType.CALL):
            return None
    return bb_range, opener_range


def map_mw_flop_vs_cbet(state: HandState, hero_seat: int) -> Spot | None:
    """3/4-way vs flop c-bet: hero = BB who called a MW open, checked, the
    opener c-bet a canonical size, EVERY cold-caller responded — hero closes."""
    hero = state.seats[hero_seat]
    if len(state.board) != 3 or hero.position is not Position.BB:
        return None
    gate = _mw_srp_preflop(state)
    if gate is None:
        return None
    opener, callers, bb, open_to = gate
    if bb.seat != hero_seat:
        return None
    flop_pot = round((2 + len(callers)) * open_to + 0.5, 2)
    faced = _mw_check_bet_responded(
        state, Street.FLOP, opener.position, callers, flop_pot
    )
    if faced is None:
        return None
    cbet, n_called = faced
    pot = _live_pot(state)
    expected = flop_pot + cbet * (1 + n_called)
    if abs(pot - expected) > _EPS:
        return None
    ranges = _mw_ranges(opener.position, [c.position for c in callers])
    if ranges is None:
        return None
    bb_range, opener_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, cbet,
        Street.FLOP, NodeContext.VS_CBET, bb_range, opener_range,
        mults=FACING_RAISE_MULTS["check_raise"],
    )


def map_mw_vs_turn_bet(state: HandState, hero_seat: int) -> Spot | None:
    """3/4-way vs turn barrel: canonical MW flop bet-call(s)-call, then the
    opener bets the turn, EVERY caller responded — hero (BB) closes."""
    hero = state.seats[hero_seat]
    if len(state.board) != 4 or hero.position is not Position.BB:
        return None
    gate = _mw_srp_preflop(state)
    if gate is None:
        return None
    opener, callers, bb, open_to = gate
    if bb.seat != hero_seat:
        return None
    n_way = 2 + len(callers)
    flop_pot = round(n_way * open_to + 0.5, 2)
    fbet = _mw_check_bet_call_call(
        state, Street.FLOP, opener.position, callers, flop_pot
    )
    if fbet is None:
        return None
    turn_pot = round(flop_pot + n_way * fbet, 2)
    faced = _mw_check_bet_responded(
        state, Street.TURN, opener.position, callers, turn_pot
    )
    if faced is None:
        return None
    tbet, n_called = faced
    pot = _live_pot(state)
    expected = turn_pot + tbet * (1 + n_called)
    if abs(pot - expected) > _EPS:
        return None
    ranges = _mw_ranges(opener.position, [c.position for c in callers])
    if ranges is None:
        return None
    bb_range, opener_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, tbet,
        Street.TURN, NodeContext.VS_TURN_BET, bb_range, opener_range,
    )


def map_mw_vs_river_bet(state: HandState, hero_seat: int) -> Spot | None:
    """3/4-way vs river bet: canonical MW flop AND turn bet-call(s)-call, then
    the opener bets the river, EVERY caller responded — hero (BB) closes."""
    hero = state.seats[hero_seat]
    if len(state.board) != 5 or hero.position is not Position.BB:
        return None
    gate = _mw_srp_preflop(state)
    if gate is None:
        return None
    opener, callers, bb, open_to = gate
    if bb.seat != hero_seat:
        return None
    n_way = 2 + len(callers)
    flop_pot = round(n_way * open_to + 0.5, 2)
    fbet = _mw_check_bet_call_call(
        state, Street.FLOP, opener.position, callers, flop_pot
    )
    if fbet is None:
        return None
    turn_pot = round(flop_pot + n_way * fbet, 2)
    tbet = _mw_check_bet_call_call(
        state, Street.TURN, opener.position, callers, turn_pot
    )
    if tbet is None:
        return None
    river_pot = round(turn_pot + n_way * tbet, 2)
    faced = _mw_check_bet_responded(
        state, Street.RIVER, opener.position, callers, river_pot
    )
    if faced is None:
        return None
    rbet, n_called = faced
    pot = _live_pot(state)
    expected = river_pot + rbet * (1 + n_called)
    if abs(pot - expected) > _EPS:
        return None
    ranges = _mw_ranges(opener.position, [c.position for c in callers])
    if ranges is None:
        return None
    bb_range, opener_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, rbet,
        Street.RIVER, NodeContext.VS_RIVER_BET, bb_range, opener_range,
    )


# --- M7 (RES-I L5): hero-seat widening — opener + cold-caller MW mappers ----
# Widens the multiway family beyond hero-as-BB (RES-I §4 measured the BB-only
# scope at 0.23–2.73/1000, below the ≥5/1000 rankability threshold; §6 = GO).
# Two new hero seats, graded by the EXISTING graders + M6's opp-aware
# `_apply_multiway` scalars — no new grader, no new NodeContext:
#
#   * hero as the OPENER in the BB-in MW shape (`_mw_srp_preflop`): c-bet /
#     turn-barrel / river-barrel decisions into 2–3 live players. These are
#     AGGRESSOR nodes — hero initiates the betting, so players acting after
#     him are inherent to the node (exactly like the HU barrel mappers, where
#     the villain always still holds an action); the "hero closes" invariant
#     governs FACING nodes only. `grade_cbet`/`grade_*_barrel`'s aggressor-side
#     `_apply_multiway` (bluff dampen / value lean, geometric in opp) is the
#     deliberate model for betting into a live field.
#   * hero as a COLD-CALLER, closing. Inside the BB-in `_mw_srp_preflop`
#     shape a cold-caller can NEVER close — postflop the BB acts first, so
#     after the opener's bet the action wraps caller(s)-then-BB and the BB
#     always holds a live action behind every caller (skip-and-document:
#     those facing nodes stay None under the closing invariant, same law as
#     4-way-live-behind-hero). The caller family therefore fires in the
#     no-BB MW shape — opener + exactly TWO non-blind cold-callers, blinds
#     folded (RES-I §2: 485/10k flops, the largest previously-structural
#     kill) — with hero as the LATER caller, who genuinely closes the street
#     once the earlier caller has responded.
#
# Both families reuse `_is_canonical_bet` (M1's RECOGNIZED_BET_FRACS — never
# a private fraction set, RES-I §5) and keep every prior-street gate exact.
# Existing BB-path mappers are untouched; all new shapes are disjoint from
# every existing mapper by hero role + preflop entrant shape.


def map_mw_flop_cbet(state: HandState, hero_seat: int) -> Spot | None:
    """3/4-way flop c-bet: hero opened the MW pot (`_mw_srp_preflop` shape),
    the BB checked, hero decides check / bet small / bet big into the live
    field. Mirrors `map_flop_cbet` with the MW preflop gate + `_mw_ranges`
    content gate (every cold-caller's VS_RFI entry must exist)."""
    hero = state.seats[hero_seat]
    if len(state.board) != 3 or hero.position in _BLIND_POSITIONS:
        return None
    gate = _mw_srp_preflop(state)
    if gate is None:
        return None
    opener, callers, bb, open_to = gate
    if opener.seat != hero_seat:
        return None
    if not _bb_checked_only(state, Street.FLOP):
        return None
    flop_pot = round((2 + len(callers)) * open_to + 0.5, 2)
    pot = _live_pot(state)
    if abs(pot - flop_pot) > _EPS:
        return None
    ranges = _mw_ranges(opener.position, [c.position for c in callers])
    if ranges is None:
        return None
    bb_range, opener_range = ranges
    return _barrel_spot(
        state, hero_seat, bb, pot, Street.FLOP, NodeContext.CBET,
        opener_range, bb_range,
    )


def map_mw_turn_barrel(state: HandState, hero_seat: int) -> Spot | None:
    """3/4-way turn barrel: hero opened the MW pot, the canonical flop
    bet-call(s)-call line stayed intact, and the BB has checked the turn."""
    hero = state.seats[hero_seat]
    if len(state.board) != 4 or hero.position in _BLIND_POSITIONS:
        return None
    gate = _mw_srp_preflop(state)
    if gate is None:
        return None
    opener, callers, bb, open_to = gate
    if opener.seat != hero_seat:
        return None
    n_way = 2 + len(callers)
    flop_pot = round(n_way * open_to + 0.5, 2)
    fbet = _mw_check_bet_call_call(
        state, Street.FLOP, hero.position, callers, flop_pot
    )
    if fbet is None:
        return None
    if not _bb_checked_only(state, Street.TURN):
        return None
    pot = _live_pot(state)
    if abs(pot - (flop_pot + n_way * fbet)) > _EPS:
        return None
    ranges = _mw_ranges(opener.position, [c.position for c in callers])
    if ranges is None:
        return None
    bb_range, opener_range = ranges
    return _barrel_spot(
        state, hero_seat, bb, pot, Street.TURN, NodeContext.TURN_BARREL,
        opener_range, bb_range,
    )


def map_mw_river_barrel(state: HandState, hero_seat: int) -> Spot | None:
    """3/4-way river barrel: hero opened the MW pot, canonical flop AND turn
    bet-call(s)-call stayed intact, and the BB has checked the river."""
    hero = state.seats[hero_seat]
    if len(state.board) != 5 or hero.position in _BLIND_POSITIONS:
        return None
    gate = _mw_srp_preflop(state)
    if gate is None:
        return None
    opener, callers, bb, open_to = gate
    if opener.seat != hero_seat:
        return None
    n_way = 2 + len(callers)
    flop_pot = round(n_way * open_to + 0.5, 2)
    fbet = _mw_check_bet_call_call(
        state, Street.FLOP, hero.position, callers, flop_pot
    )
    if fbet is None:
        return None
    turn_pot = round(flop_pot + n_way * fbet, 2)
    tbet = _mw_check_bet_call_call(
        state, Street.TURN, hero.position, callers, turn_pot
    )
    if tbet is None:
        return None
    if not _bb_checked_only(state, Street.RIVER):
        return None
    pot = _live_pot(state)
    if abs(pot - (turn_pot + n_way * tbet)) > _EPS:
        return None
    ranges = _mw_ranges(opener.position, [c.position for c in callers])
    if ranges is None:
        return None
    bb_range, opener_range = ranges
    return _barrel_spot(
        state, hero_seat, bb, pot, Street.RIVER, NodeContext.RIVER_BARREL,
        opener_range, bb_range,
    )


def _mw_nobb_srp_preflop(state: HandState) -> tuple | None:
    """Gate: no-BB 3-way single-raised pot. One non-blind opener at an in-band
    open, exactly TWO non-blind cold-callers, BOTH blinds folded. Entrants are
    derived from the PREFLOP actions (a caller may legitimately have folded to
    a later postflop bet). Opener must still be IN; callers IN or
    postflop-FOLDED (never all-in); nobody else live. Returns
    (opener, callers, open_to) — `callers` a tuple in preflop call order,
    which equals position/postflop-act order — or None."""
    pre = _street_actions(state, Street.PREFLOP)
    if any(
        h.action not in (ActionType.FOLD, ActionType.RAISE, ActionType.CALL)
        for h in pre
    ):
        return None
    raises = [h for h in pre if h.action is ActionType.RAISE]
    calls = [h for h in pre if h.action is ActionType.CALL]
    if len(raises) != 1 or len(calls) != 2:
        return None  # not an SRP with exactly two callers
    opener_pos = raises[0].position
    caller_pos = [c.position for c in calls]
    if opener_pos in _BLIND_POSITIONS or any(
        p in _BLIND_POSITIONS for p in caller_pos
    ):
        return None  # a blind entrant is the `_mw_srp_preflop` family instead
    if len(set(caller_pos)) != 2:
        return None  # duplicate caller (limp-then-call chain)
    opener = next((s for s in state.seats if s.position is opener_pos), None)
    callers = tuple(
        s for p in caller_pos for s in state.seats if s.position is p
    )
    if opener is None or len(callers) != 2:
        return None
    if opener.status is not PlayerStatus.IN:
        return None
    if any(c.status not in (PlayerStatus.IN, PlayerStatus.FOLDED) for c in callers):
        return None  # an all-in anywhere in the line is off-shape
    entrants = {opener.seat} | {c.seat for c in callers}
    if any(
        s.status is not PlayerStatus.FOLDED
        for s in state.seats
        if s.seat not in entrants
    ):
        return None  # blinds (or anyone else) must be dead
    open_to = raises[0].amount_bb
    if not (2.0 - _EPS <= open_to <= _OVERSIZE_OPEN_CAP + _EPS):
        return None
    return opener, callers, open_to


def _mw_nobb_bet_responded(
    state, street: Street, opener_pos: Position, prior_callers, pot_before: float
) -> tuple[float, int] | None:
    """Gate: this street went EXACTLY bet(opener, canonical) ->
    call-or-fold(EVERY caller before hero); hero — the LAST caller — now
    faces the bet and CLOSES (no BB exists in this shape; the opener acts
    first postflop and holds no further action once hero responds). Returns
    (bet, n_called) or None. A raise is a different node -> None."""
    acts = _street_actions(state, street)
    if len(acts) != 1 + len(prior_callers):
        return None
    bet, *resps = acts
    if bet.action is not ActionType.BET or bet.position is not opener_pos:
        return None
    if not _is_canonical_bet(bet.amount_bb, pot_before, street):
        return None
    if {r.position for r in resps} != {c.position for c in prior_callers}:
        return None  # a non-caller acted, or a prior caller hasn't responded
    n_called = 0
    for resp in resps:
        if resp.action is ActionType.CALL:
            if abs(resp.amount_bb - bet.amount_bb) > _EPS:
                return None  # short call = someone is all-in — off-shape
            n_called += 1
        elif resp.action is not ActionType.FOLD:
            return None  # a raise — hero faces a raise, not the bet
    return bet.amount_bb, n_called


def _mw_nobb_bet_call_call(
    state, street: Street, opener_pos: Position, callers, pot_before: float
) -> float | None:
    """Gate: a PRIOR street went EXACTLY bet(opener, canonical) -> call(EVERY
    caller) — the full no-BB MW continuation line stayed intact. Returns the
    bet size or None."""
    acts = _street_actions(state, street)
    if len(acts) != 1 + len(callers):
        return None
    bet, *caller_calls = acts
    if bet.action is not ActionType.BET or bet.position is not opener_pos:
        return None
    if not _is_canonical_bet(bet.amount_bb, pot_before, street):
        return None
    if {c.position for c in caller_calls} != {c.position for c in callers}:
        return None
    for c in caller_calls:
        if c.action is not ActionType.CALL or abs(c.amount_bb - bet.amount_bb) > _EPS:
            return None  # a fold/raise, or short call (all-in) — off-shape
    return bet.amount_bb


def _mw_caller_ranges(
    opener_pos: Position, hero_pos: Position, other_caller_positions
) -> tuple[str, str] | None:
    """(hero's VS_RFI call range, opener RFI raise range) for the caller
    family — PLUS the content gate on every OTHER caller's VS_RFI call entry
    (an unmodeled range in the pot -> None, same law as `_mw_ranges`). Other
    callers' ranges are gates only, never a grader input."""
    rfi_entry = _find_entry(NodeContext.RFI, opener_pos, None)
    hero_entry = _find_entry(NodeContext.VS_RFI, hero_pos, opener_pos)
    opener_range = _combos_for(rfi_entry, ActionType.RAISE)
    hero_range = _combos_for(hero_entry, ActionType.CALL)
    if not opener_range or not hero_range:
        return None
    for p in other_caller_positions:
        entry = _find_entry(NodeContext.VS_RFI, p, opener_pos)
        if entry is None or not _combos_for(entry, ActionType.CALL):
            return None
    return hero_range, opener_range


def map_mw_caller_vs_cbet(state: HandState, hero_seat: int) -> Spot | None:
    """No-BB 3-way vs flop c-bet: hero = the LATER of two non-blind
    cold-callers, the opener c-bet a canonical size, the earlier caller
    responded — hero closes. Hero's raise is a plain in-position raise (hero
    never checked), so the legs use the facing-bet mults."""
    hero = state.seats[hero_seat]
    if len(state.board) != 3 or hero.position in _BLIND_POSITIONS:
        return None
    gate = _mw_nobb_srp_preflop(state)
    if gate is None:
        return None
    opener, callers, open_to = gate
    if callers[-1].seat != hero_seat:
        return None  # the earlier caller never closes (hero-not-closing -> None)
    flop_pot = round(3 * open_to + 1.5, 2)  # both blinds dead
    faced = _mw_nobb_bet_responded(
        state, Street.FLOP, opener.position, callers[:-1], flop_pot
    )
    if faced is None:
        return None
    cbet, n_called = faced
    pot = _live_pot(state)
    if abs(pot - (flop_pot + cbet * (1 + n_called))) > _EPS:
        return None
    ranges = _mw_caller_ranges(
        opener.position, hero.position, [c.position for c in callers[:-1]]
    )
    if ranges is None:
        return None
    hero_range, opener_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, cbet,
        Street.FLOP, NodeContext.VS_CBET, hero_range, opener_range,
        mults=FACING_RAISE_MULTS["raise"],
    )


def map_mw_caller_vs_turn_bet(state: HandState, hero_seat: int) -> Spot | None:
    """No-BB 3-way vs turn barrel: canonical flop bet-call-call, then the
    opener bets the turn and the earlier caller responded — hero closes."""
    hero = state.seats[hero_seat]
    if len(state.board) != 4 or hero.position in _BLIND_POSITIONS:
        return None
    gate = _mw_nobb_srp_preflop(state)
    if gate is None:
        return None
    opener, callers, open_to = gate
    if callers[-1].seat != hero_seat:
        return None
    flop_pot = round(3 * open_to + 1.5, 2)
    fbet = _mw_nobb_bet_call_call(
        state, Street.FLOP, opener.position, callers, flop_pot
    )
    if fbet is None:
        return None
    turn_pot = round(flop_pot + 3 * fbet, 2)
    faced = _mw_nobb_bet_responded(
        state, Street.TURN, opener.position, callers[:-1], turn_pot
    )
    if faced is None:
        return None
    tbet, n_called = faced
    pot = _live_pot(state)
    if abs(pot - (turn_pot + tbet * (1 + n_called))) > _EPS:
        return None
    ranges = _mw_caller_ranges(
        opener.position, hero.position, [c.position for c in callers[:-1]]
    )
    if ranges is None:
        return None
    hero_range, opener_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, tbet,
        Street.TURN, NodeContext.VS_TURN_BET, hero_range, opener_range,
    )


def map_mw_caller_vs_river_bet(state: HandState, hero_seat: int) -> Spot | None:
    """No-BB 3-way vs river bet: canonical flop AND turn bet-call-call, then
    the opener bets the river and the earlier caller responded — hero closes."""
    hero = state.seats[hero_seat]
    if len(state.board) != 5 or hero.position in _BLIND_POSITIONS:
        return None
    gate = _mw_nobb_srp_preflop(state)
    if gate is None:
        return None
    opener, callers, open_to = gate
    if callers[-1].seat != hero_seat:
        return None
    flop_pot = round(3 * open_to + 1.5, 2)
    fbet = _mw_nobb_bet_call_call(
        state, Street.FLOP, opener.position, callers, flop_pot
    )
    if fbet is None:
        return None
    turn_pot = round(flop_pot + 3 * fbet, 2)
    tbet = _mw_nobb_bet_call_call(
        state, Street.TURN, opener.position, callers, turn_pot
    )
    if tbet is None:
        return None
    river_pot = round(turn_pot + 3 * tbet, 2)
    faced = _mw_nobb_bet_responded(
        state, Street.RIVER, opener.position, callers[:-1], river_pot
    )
    if faced is None:
        return None
    rbet, n_called = faced
    pot = _live_pot(state)
    if abs(pot - (river_pot + rbet * (1 + n_called))) > _EPS:
        return None
    ranges = _mw_caller_ranges(
        opener.position, hero.position, [c.position for c in callers[:-1]]
    )
    if ranges is None:
        return None
    hero_range, opener_range = ranges
    return _faced_bet_spot(
        state, hero_seat, opener, pot, rbet,
        Street.RIVER, NodeContext.VS_RIVER_BET, hero_range, opener_range,
    )


# --- M4 (RES-H H1): caller-re-raises-c-bet — hero = opener facing the raise --
# Hero opened an SRP, c-bet the flop at a canonical size, and the NON-BB
# preflop cold-caller raised the c-bet; hero faces/closes. Two entrant shapes
# share the family (both rejected by `_hu_srp_preflop`'s strict villain-is-BB
# 2-live gate, hence the dedicated `_flop_caller_raise_preflop` gate):
#   * opener + caller + BB (3-way): flop check(BB) → c-bet → raise(caller) →
#     BB folds (degrade-to-2-live, dead money stays in the pot) or calls
#     (still 3-live at hero's decision → `_apply_multiway` composes).
#   * opener + caller only (BB folded preflop): flop c-bet → raise(caller).
# The caller's VS_RFI call entry is the content gate AND his villain range
# (he is the aggressor hero faces). The raise size is un-bucketed (personas
# raise on a continuous grid — same rule as `_check_bet_raise`); the C-BET
# recognition reuses `_is_canonical_bet`'s RECOGNIZED_BET_FRACS grid, every
# member of which maps to a defined RES-E bucket. Donk leads, limped pots,
# delayed c-bets, BB raises and hero-not-opener all return None.


def _flop_caller_raise_preflop(state: HandState) -> tuple | None:
    """Gate: SRP where a non-blind opener at an in-band open was flatted by
    exactly ONE non-blind cold-caller, plus optionally the BB; SB (and every
    other seat) folded. Structurally the `_mw_srp_preflop` entrant shape with
    the BB optional. Returns (opener, caller, bb_or_None, open_to) — bb is
    None when the BB folded preflop — or None."""
    pre = _street_actions(state, Street.PREFLOP)
    if any(
        h.action not in (ActionType.FOLD, ActionType.RAISE, ActionType.CALL)
        for h in pre
    ):
        return None
    raises = [h for h in pre if h.action is ActionType.RAISE]
    calls = [h for h in pre if h.action is ActionType.CALL]
    if len(raises) != 1 or len(calls) not in (1, 2):
        return None
    opener_pos = raises[0].position
    if opener_pos in _BLIND_POSITIONS:
        return None
    non_bb_calls = [c for c in calls if c.position is not Position.BB]
    if len(non_bb_calls) != 1:
        return None  # exactly one cold-caller; two calls ⇒ the other is the BB's
    caller_pos = non_bb_calls[0].position
    if caller_pos in _BLIND_POSITIONS:
        return None  # an SB cold-call is off-shape
    bb_called = len(calls) == 2  # the other call can only be the BB's
    opener = next((s for s in state.seats if s.position is opener_pos), None)
    caller = next((s for s in state.seats if s.position is caller_pos), None)
    bb = (
        next((s for s in state.seats if s.position is Position.BB), None)
        if bb_called
        else None
    )
    if opener is None or caller is None or (bb_called and bb is None):
        return None
    if opener.status is not PlayerStatus.IN or caller.status is not PlayerStatus.IN:
        return None  # an all-in anywhere in the line is off-shape
    if bb is not None and bb.status not in (PlayerStatus.IN, PlayerStatus.FOLDED):
        return None  # BB may fold to the flop raise, never be all-in
    entrants = {opener.seat, caller.seat} | ({bb.seat} if bb is not None else set())
    if any(
        s.status is not PlayerStatus.FOLDED
        for s in state.seats
        if s.seat not in entrants
    ):
        return None
    open_to = raises[0].amount_bb
    if not (2.0 - _EPS <= open_to <= _OVERSIZE_OPEN_CAP + _EPS):
        return None
    return opener, caller, bb, open_to


def _flop_cbet_caller_raise(
    state: HandState,
    opener_pos: Position,
    caller_pos: Position,
    bb_entrant: bool,
    pot_before: float,
) -> tuple[float, float, bool] | None:
    """Gate: the flop went EXACTLY [check(BB) →] bet(opener, canonical) →
    raise(caller) [→ fold-or-call(BB)], hero (the opener) now facing the
    caller's raise and CLOSING. Returns (cbet, raise_to, bb_called_raise) or
    None. The raise size is deliberately un-bucketed (see `_check_bet_raise`);
    an incomplete raise or a short BB call is off-shape."""
    acts = _street_actions(state, Street.FLOP)
    if bb_entrant:
        if len(acts) != 4:
            return None
        chk, bet, cr, resp = acts
        if chk.action is not ActionType.CHECK or chk.position is not Position.BB:
            return None
    else:
        if len(acts) != 2:
            return None
        bet, cr = acts
        resp = None
    if bet.action is not ActionType.BET or bet.position is not opener_pos:
        return None
    if not _is_canonical_bet(bet.amount_bb, pot_before, Street.FLOP):
        return None
    if cr.action is not ActionType.RAISE or cr.position is not caller_pos:
        return None
    # The caller had nothing invested this street: the history INCREMENT is
    # the full raise-TO.
    raise_to = cr.amount_bb
    if raise_to <= bet.amount_bb + _EPS:
        return None  # degenerate: a "raise" no bigger than the bet
    bb_called_raise = False
    if resp is not None:
        if resp.position is not Position.BB:
            return None
        if resp.action is ActionType.CALL:
            if abs(resp.amount_bb - raise_to) > _EPS:
                return None  # short call = someone is all-in — off-shape
            bb_called_raise = True
        elif resp.action is not ActionType.FOLD:
            return None  # a BB re-raise is a different (unmapped) node
    return bet.amount_bb, raise_to, bb_called_raise


def map_flop_vs_caller_raise(state: HandState, hero_seat: int) -> Spot | None:
    """Flop caller-re-raises-c-bet (M4): hero opened an SRP at an in-band
    size, c-bet the flop canonically, and the non-BB preflop cold-caller
    raised; hero faces/closes. Hero's re-raise legs are the plain facing-bet
    mults on the raise-to; CALL is the INCREMENTAL amount (raise_to - cbet) —
    hero already has the c-bet invested this street."""
    hero = state.seats[hero_seat]
    if len(state.board) != 3 or hero.position in _BLIND_POSITIONS:
        return None
    gate = _flop_caller_raise_preflop(state)
    if gate is None:
        return None
    opener, caller, bb, open_to = gate
    if opener.seat != hero_seat:
        return None
    flop_pot = round(
        (3 * open_to + 0.5) if bb is not None else (2 * open_to + 1.5), 2
    )
    faced = _flop_cbet_caller_raise(
        state, hero.position, caller.position, bb is not None, flop_pot
    )
    if faced is None:
        return None
    cbet, raise_to, bb_called_raise = faced
    pot = _live_pot(state)
    expected = flop_pot + cbet + raise_to + (raise_to if bb_called_raise else 0.0)
    if abs(pot - expected) > _EPS:
        return None
    # Ranges: hero = the opener's RFI raise range; villain = the CALLER's
    # VS_RFI call range (the same content entry `_mw_ranges` gates on — here
    # the caller IS the aggressor hero faces, so his range is consumed).
    rfi_entry = _find_entry(NodeContext.RFI, hero.position, None)
    caller_entry = _find_entry(NodeContext.VS_RFI, caller.position, hero.position)
    hero_range = _combos_for(rfi_entry, ActionType.RAISE)
    caller_range = _combos_for(caller_entry, ActionType.CALL)
    if not hero_range or not caller_range:
        return None
    return _faced_bet_spot(
        state, hero_seat, caller, pot, raise_to,
        Street.FLOP, NodeContext.VS_CALLER_RAISE, hero_range, caller_range,
        mults=FACING_RAISE_MULTS["raise"],
        call_amt=round(raise_to - cbet, 2),
    )


# --- M5 (Epic 5, RES-G Slice C): HU limped-pot flop mappers -----------------
# The FIRST limped-pot postflop node family, HU only (the tractable 31% of
# limped flops). The gate derives the ENTRANT COUNT from the PREFLOP actions —
# never from current flop statuses — so a 3+-entrant limped pot stays None
# even after it degrades to 2-live postflop (multiway limped is deferred
# Slice D "no baseline yet"; deliberately NOT M4's degrade-to-2-live
# pattern). Flop only; turn/river of a limped pot stays None (v1).


def _limped_flop_hu_preflop(state: HandState) -> tuple | None:
    """Gate: HU limped pot (ZERO preflop raises). Entrants = every preflop
    CALLer (open-limp, or the SB completing) + the BB (posted; its option
    close is the lone legal preflop CHECK). Exactly 2 entrants, hero-agnostic;
    both must still be IN (an all-in anywhere is off-shape) and every other
    seat FOLDED. Returns (entrant_a, entrant_b, preflop_pot) — the preflop pot
    is 2.0 (SB completed) or 2.5 (one limper + the folded SB's dead 0.5) — or
    None."""
    pre = _street_actions(state, Street.PREFLOP)
    if any(
        h.action not in (ActionType.FOLD, ActionType.CALL, ActionType.CHECK)
        for h in pre
    ):
        return None  # any raise/bet: not a limped pot
    if any(
        h.action is ActionType.CHECK and h.position is not Position.BB for h in pre
    ):
        return None  # only the BB holds a free preflop option
    calls = [h for h in pre if h.action is ActionType.CALL]
    entrant_pos = {c.position for c in calls} | {Position.BB}
    if len(entrant_pos) != 2:
        return None  # 3+ preflop entrants (even if since degraded to 2-live)
    entrants = [s for s in state.seats if s.position in entrant_pos]
    if len(entrants) != 2:
        return None
    if any(s.status is not PlayerStatus.IN for s in entrants):
        return None  # an all-in (or an entrant already folded) is off-shape
    if any(
        s.status is not PlayerStatus.FOLDED
        for s in state.seats
        if s.position not in entrant_pos
    ):
        return None
    sb_dead = 0.0 if Position.SB in entrant_pos else 0.5
    pre_pot = round(2.0 + sb_dead, 2)
    return entrants[0], entrants[1], pre_pot


def _limped_lead_spot(
    state: HandState, hero_seat: int, villain, pot: float
) -> Spot | None:
    """Hero can lead the limped flop: check / bet small / bet big (mirrors
    `_barrel_spot`'s legal-action shape, but `facing` is the LIVE villain —
    hero may itself be the BB here). The small leg clamps up to the engine's
    1BB legal minimum (limped pots are small enough that 0.33·pot can fall
    under it)."""
    hero = state.seats[hero_seat]
    small_frac, big_frac = POSTFLOP_BET_FRACS["flop"]
    small = max(round(small_frac * pot, 1), 1.0)
    big = max(round(big_frac * pot, 1), 1.0)
    if big <= small:
        return None  # degenerate: both canonical sizes collapse onto the min bet
    hero_remaining = hero.stack_bb
    villain_remaining = villain.stack_bb
    if hero_remaining < big or villain_remaining <= 0:
        return None  # too shallow for the canonical small/big bet buckets
    effective = round(min(hero_remaining, villain_remaining), 2)
    return Spot(
        game=GameConfig(stakes=Stakes(sb=1.0, bb=2.0), table_size=9, max_buyin_bb=200.0),
        street=Street.FLOP,
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
        node_context=[NodeContext.LIMPED_LEAD],
        facing=villain.position,
        hero_range=None,
        villain_range=None,
    )


def map_limped_flop_lead(state: HandState, hero_seat: int) -> Spot | None:
    """HU limped flop, hero can lead: zero preflop raises, exactly 2 preflop
    entrants incl. hero, and no flop bet yet (hero first to act, or the OOP
    villain checked to hero)."""
    hero = state.seats[hero_seat]
    if len(state.board) != 3:
        return None
    gate = _limped_flop_hu_preflop(state)
    if gate is None:
        return None
    a, b, pre_pot = gate
    if hero.seat not in (a.seat, b.seat):
        return None
    villain = b if hero.seat == a.seat else a
    acts = _street_actions(state, Street.FLOP)
    if acts and not (
        len(acts) == 1
        and acts[0].action is ActionType.CHECK
        and acts[0].position is villain.position
    ):
        return None
    pot = _live_pot(state)
    if abs(pot - pre_pot) > _EPS:
        return None
    return _limped_lead_spot(state, hero_seat, villain, pot)


def map_limped_flop_vs_lead(state: HandState, hero_seat: int) -> Spot | None:
    """HU limped flop, hero faces a villain lead at a recognized size: either
    the OOP villain led outright, or hero checked and the villain stabbed
    (hero's RAISE is then a check-raise, sized with the check_raise mults)."""
    hero = state.seats[hero_seat]
    if len(state.board) != 3:
        return None
    gate = _limped_flop_hu_preflop(state)
    if gate is None:
        return None
    a, b, pre_pot = gate
    if hero.seat not in (a.seat, b.seat):
        return None
    villain = b if hero.seat == a.seat else a
    acts = _street_actions(state, Street.FLOP)
    hero_checked = False
    if len(acts) == 2:
        if acts[0].action is not ActionType.CHECK or acts[0].position is not hero.position:
            return None
        hero_checked = True
        lead = acts[1]
    elif len(acts) == 1:
        lead = acts[0]
    else:
        return None
    if lead.action is not ActionType.BET or lead.position is not villain.position:
        return None
    if not _is_canonical_bet(lead.amount_bb, pre_pot, Street.FLOP):
        return None
    pot = _live_pot(state)
    if abs(pot - (pre_pot + lead.amount_bb)) > _EPS:
        return None
    return _faced_bet_spot(
        state, hero_seat, villain, pot, lead.amount_bb,
        Street.FLOP, NodeContext.LIMPED_VS_LEAD, None, None,
        mults=FACING_RAISE_MULTS["check_raise" if hero_checked else "raise"],
    )
