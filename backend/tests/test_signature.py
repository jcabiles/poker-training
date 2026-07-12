import pytest
from factories import make_rfi_spot

from app.domain.spot import Position
from app.domain.srs import spot_signature


def test_signature_ignores_hole_cards_and_amounts():
    a = make_rfi_spot(hole_cards=("Ah", "Ks"), pot_bb=1.5)
    b = make_rfi_spot(hole_cards=("2c", "7d"), pot_bb=99.0)
    assert spot_signature(a) == spot_signature(b)


def test_signature_differs_by_position():
    a = make_rfi_spot(position=Position.CO)
    b = make_rfi_spot(position=Position.BTN)
    assert spot_signature(a) != spot_signature(b)


def test_signature_stack_bucket_stable_within_diff_across():
    same_a = make_rfi_spot(eff_bb=100.0)
    same_b = make_rfi_spot(eff_bb=120.0)  # both in 75-125 bucket
    assert spot_signature(same_a) == spot_signature(same_b)

    diff = make_rfi_spot(eff_bb=30.0)  # <=40 bucket
    assert spot_signature(same_a) != spot_signature(diff)


def test_signature_survives_content_version_bump():
    """Mutating only non-canonical fields must not change the signature."""
    base = make_rfi_spot()
    bumped = base.model_copy(deep=True)
    bumped.pot_bb = 7.0
    bumped.spr = 5.0
    bumped.legal_actions = []
    assert spot_signature(base) == spot_signature(bumped)


def test_signature_includes_opener_position():
    """BB vs a UTG open and BB vs a BTN open are different spots -> different SRS items."""
    from app.domain.spot import NodeContext

    base = make_rfi_spot(position=Position.BB)
    a = base.model_copy(update={"node_context": [NodeContext.VS_RFI], "facing": Position.UTG})
    b = base.model_copy(update={"node_context": [NodeContext.VS_RFI], "facing": Position.BTN})
    assert spot_signature(a) != spot_signature(b)


def test_signature_includes_limper_count():
    base = make_rfi_spot()
    one = base.model_copy(update={"limper_count": 1})
    two = base.model_copy(update={"limper_count": 2})
    assert spot_signature(one) != spot_signature(two)


def test_signature_separates_villain_type():
    from app.domain.archetypes import VillainType

    base = make_rfi_spot()
    exploit = base.model_copy(update={"villain_type": VillainType.CALLING_STATION})
    other = base.model_copy(update={"villain_type": VillainType.NIT})
    assert spot_signature(base) != spot_signature(exploit)
    assert spot_signature(exploit) != spot_signature(other)


# --- Postflop signature (Phase 2a) ---


def _flop_spot(board, spr=5.0):
    from app.domain.spot import (
        GameConfig,
        Hero,
        NodeContext,
        PlayerState,
        Spot,
        Stakes,
        Street,
    )

    return Spot(
        game=GameConfig(stakes=Stakes(sb=0.5, bb=1.0), table_size=9),
        street=Street.FLOP,
        board=board,
        pot_bb=6.0,
        hero=Hero(position=Position.BTN, hole_cards=("Ah", "Kh"), stack_bb=100),
        players=[
            PlayerState(position=Position.BTN, stack_bb=100, is_hero=True),
            PlayerState(position=Position.BB, stack_bb=100),
        ],
        effective_stack_bb=100,
        spr=spr,
        to_act=Position.BTN,
        node_context=[NodeContext.CBET],
        facing=Position.BB,
    )


def test_postflop_same_texture_class_same_signature():
    a = spot_signature(_flop_spot(["As", "Kd", "2c"]))
    b = spot_signature(_flop_spot(["Ah", "Qd", "3c"]))  # same class, different board
    assert a == b


def test_postflop_different_texture_different_signature():
    dry = spot_signature(_flop_spot(["As", "Kd", "2c"]))
    wet = spot_signature(_flop_spot(["9h", "8h", "7h"]))
    assert dry != wet


def test_postflop_spr_bucket_changes_signature():
    low = spot_signature(_flop_spot(["As", "Kd", "2c"], spr=2.0))
    high = spot_signature(_flop_spot(["As", "Kd", "2c"], spr=10.0))
    assert low != high


def test_preflop_signature_ignores_new_range_fields():
    base = make_rfi_spot()
    with_ranges = base.model_copy(update={"hero_range": "AA", "villain_range": "KK"})
    assert spot_signature(base) == spot_signature(with_ranges)


# --- Phase 2b: faced-bet bucket in the postflop signature ---


def _vs_cbet_spot(board, cbet, flop_pot=6.0, spr=5.0):
    from app.domain.spot import (
        ActionType,
        GameConfig,
        Hero,
        HistoryAction,
        LegalAction,
        NodeContext,
        PlayerState,
        Spot,
        Stakes,
        Street,
    )

    return Spot(
        game=GameConfig(stakes=Stakes(sb=0.5, bb=1.0), table_size=9),
        street=Street.FLOP,
        board=board,
        pot_bb=flop_pot + cbet,
        hero=Hero(position=Position.BB, hole_cards=("Ah", "Kh"), stack_bb=100),
        players=[
            PlayerState(position=Position.BB, stack_bb=100, is_hero=True),
            PlayerState(position=Position.BTN, stack_bb=100),
        ],
        effective_stack_bb=100,
        spr=spr,
        to_act=Position.BB,
        node_context=[NodeContext.VS_CBET],
        facing=Position.BTN,
        action_history=[
            HistoryAction(
                street=Street.FLOP, position=Position.BTN, action=ActionType.BET, amount_bb=cbet
            ),
        ],
        legal_actions=[LegalAction(action=ActionType.CALL, min_bb=cbet)],
    )


def test_faced_bet_size_changes_signature():
    small = spot_signature(_vs_cbet_spot(["As", "Kd", "2c"], cbet=2.0))  # 33% of 6
    big = spot_signature(_vs_cbet_spot(["As", "Kd", "2c"], cbet=4.5))  # 75% of 6
    assert small != big  # small vs big c-bet must not collapse to one SRS item


def test_same_faced_bet_same_signature():
    a = spot_signature(_vs_cbet_spot(["As", "Kd", "2c"], cbet=2.0))
    b = spot_signature(_vs_cbet_spot(["Ah", "Qd", "3c"], cbet=2.0))  # same texture+size
    assert a == b


def test_vs_cbet_distinct_from_cbet_node():
    assert spot_signature(_vs_cbet_spot(["As", "Kd", "2c"], cbet=2.0)) != spot_signature(
        _flop_spot(["As", "Kd", "2c"])
    )


# --- Phase 2c: srs_signature is metadata, excluded from the hash ---


def test_srs_signature_excluded_from_hash():
    base = make_rfi_spot()
    assert spot_signature(base) == spot_signature(
        base.model_copy(update={"srs_signature": "deadbeef0000"})
    )
    flop = _flop_spot(["As", "Kd", "2c"])
    assert spot_signature(flop) == spot_signature(flop.model_copy(update={"srs_signature": "x"}))


# --- S5: pinned-hash tripwire ---
#
# These literals were computed ONCE from the canonical fixtures below and are
# hardcoded on purpose. spot_signature() hashes are persisted as SRS item ids:
# any reorder/insert/rename in the signature tuple silently orphans ALL stored
# SM-2 history while every relative-comparison test above stays green. These
# pins fail loudly instead. If one fails, you changed the persisted-data
# contract — do NOT update the literal without an explicit migration decision.


def test_pinned_hash_flop_cbet_signature():
    assert spot_signature(_flop_spot(["As", "Kd", "2c"])) == "6832a54693ba5f6c"


def test_pinned_hash_preflop_rfi_signature():
    assert spot_signature(make_rfi_spot()) == "0cdf437e044b0bc5"


# --- S5: turn/river signature fixtures ---
#
# Golden coverage that street (tuple index 2) separates streets in the hash.
# These fixtures are for spot_signature() ONLY — they must never be passed to
# grade_cbet/grade_vs_cbet/grade_vs_check_raise (flop-only; guarded).
# spot_signature() internally calling texture.classify() on board[:3] is fine.


def test_turn_signature_differs_from_flop():
    from app.domain.spot import Street

    flop = _flop_spot(["As", "Kd", "2c"])
    turn = flop.model_copy(update={"street": Street.TURN, "board": ["As", "Kd", "2c", "7h"]})
    assert spot_signature(turn) != spot_signature(flop)


def test_river_signature_differs_from_flop_and_turn():
    from app.domain.spot import Street

    flop = _flop_spot(["As", "Kd", "2c"])
    turn = flop.model_copy(update={"street": Street.TURN, "board": ["As", "Kd", "2c", "7h"]})
    river = flop.model_copy(
        update={"street": Street.RIVER, "board": ["As", "Kd", "2c", "7h", "9s"]}
    )
    assert spot_signature(river) != spot_signature(flop)
    assert spot_signature(river) != spot_signature(turn)


# --- S6: turn-card class dimension (CONDITIONALLY appended for turn/river) ---


def _turn_spot(turn_card):
    from app.domain.spot import Street

    flop = _flop_spot(["As", "Kd", "2c"])
    return flop.model_copy(
        update={"street": Street.TURN, "board": ["As", "Kd", "2c", turn_card]}
    )


def test_turn_card_class_changes_turn_signature():
    # Same flop, same everything — only the turn card's CLASS differs:
    # Ad pairs the board ("pairing"); 7h is a "blank" on As Kd 2c.
    pairing = spot_signature(_turn_spot("Ad"))
    blank = spot_signature(_turn_spot("7h"))
    assert pairing != blank


def test_same_turn_card_class_same_signature():
    # Two different blanks collapse to one SRS item.
    assert spot_signature(_turn_spot("7h")) == spot_signature(_turn_spot("6d"))


def test_flop_signature_unchanged_by_turn_dimension():
    # Companion to the pinned-hash test: the S6 turn dimension is OMITTED (not
    # constant-valued) for flop spots, so the flop hash stays byte-identical.
    assert spot_signature(_flop_spot(["As", "Kd", "2c"])) == "6832a54693ba5f6c"


# --- S7: river-card class dimension (CONDITIONALLY appended for river only) ---


def _river_spot(river_card):
    from app.domain.spot import Street

    flop = _flop_spot(["As", "Kd", "2c"])
    return flop.model_copy(
        update={"street": Street.RIVER, "board": ["As", "Kd", "2c", "7h", river_card]}
    )


def test_river_card_class_changes_river_signature():
    # Same flop, same (blank) turn, same everything — only the river card's
    # CLASS differs: Ad pairs the board ("pairing"); 9s is a "blank" on
    # As Kd 2c 7h (no pair, no flush, no straight, not an overcard).
    pairing = spot_signature(_river_spot("Ad"))
    blank = spot_signature(_river_spot("9s"))
    assert pairing != blank


def test_same_river_card_class_same_signature():
    # Two different blanks collapse to one SRS item.
    assert spot_signature(_river_spot("9s")) == spot_signature(_river_spot("8d"))


def test_turn_signature_unchanged_by_river_dimension():
    # The S7 river dimension is OMITTED (not constant-valued) for turn spots,
    # so the turn hash stays byte-identical. This literal was computed from the
    # pre-S7 code (turn parts list: 10 elements ending in turn_card_class) —
    # do NOT update it without an explicit migration decision.
    assert spot_signature(_turn_spot("7h")) == "9c1aae003ae79de0"


def test_flop_signature_unchanged_by_river_dimension():
    # Companion to the pinned-hash test: flop spots reach NEITHER conditional
    # append, so the flop hash stays byte-identical through S7 too.
    assert spot_signature(_flop_spot(["As", "Kd", "2c"])) == "6832a54693ba5f6c"


# --- S8: `mw` dimension (THIRD conditional append, after river_class) ---
#
# Authored to T4's frozen srs.py interface (docs/ai-dlc/specs/simulate-s8.md)
# ahead of T4's srs.py landing mid-wave. `players_in_pot(spot) > 2` triggers the
# append; heads-up spots (every existing fixture here, all 2-IN) never reach
# it, so their hashes MUST stay byte-identical to the pins above. NEVER edit a
# pinned literal — these tests only ADD companions, they never modify the
# existing pins.


def _has_multiway_seams() -> bool:
    try:
        from app.domain.spot import is_multiway, players_in_pot  # noqa: F401

        return True
    except ImportError:
        return False


def _mw_flop_spot(board, spr=5.0):
    """A 3-way flop spot: same shape as _flop_spot but with a 3rd IN player."""
    from app.domain.spot import (
        GameConfig,
        Hero,
        NodeContext,
        PlayerState,
        Spot,
        Stakes,
        Street,
    )

    return Spot(
        game=GameConfig(stakes=Stakes(sb=0.5, bb=1.0), table_size=9),
        street=Street.FLOP,
        board=board,
        pot_bb=6.0,
        hero=Hero(position=Position.BTN, hole_cards=("Ah", "Kh"), stack_bb=100),
        players=[
            PlayerState(position=Position.BTN, stack_bb=100, is_hero=True),
            PlayerState(position=Position.BB, stack_bb=100),
            PlayerState(position=Position.CO, stack_bb=100),
        ],
        effective_stack_bb=100,
        spr=spr,
        to_act=Position.BTN,
        node_context=[NodeContext.CBET],
        facing=Position.BB,
    )


def _mw_turn_spot(turn_card, extra_players=1):
    """A (2+extra_players)-way turn spot — extra_players=1 -> 3-way,
    extra_players=2 -> 4-way (both must collapse to the same 'mw' bucket)."""
    from app.domain.spot import PlayerState, Position, Street

    flop = _mw_flop_spot(["As", "Kd", "2c"])
    extra = [
        PlayerState(position=p, stack_bb=100)
        for p in (Position.CO, Position.HJ)[:extra_players]
    ]
    return flop.model_copy(
        update={
            "street": Street.TURN,
            "board": ["As", "Kd", "2c", turn_card],
            "players": [flop.players[0], flop.players[1], *extra],
        }
    )


def _mw_river_spot(river_card, extra_players=1):
    from app.domain.spot import PlayerState, Position, Street

    flop = _mw_flop_spot(["As", "Kd", "2c"])
    extra = [
        PlayerState(position=p, stack_bb=100)
        for p in (Position.CO, Position.HJ)[:extra_players]
    ]
    return flop.model_copy(
        update={
            "street": Street.RIVER,
            "board": ["As", "Kd", "2c", "7h", river_card],
            "players": [flop.players[0], flop.players[1], *extra],
        }
    )


def test_flop_signature_unchanged_by_multiway_dimension():
    if not _has_multiway_seams():
        pytest.skip("T4 multiway seams (players_in_pot/is_multiway) not yet landed")
    # A heads-up flop spot (2 IN) must never reach the `mw` append, so this
    # stays byte-identical to the pinned literal after S8 lands.
    assert spot_signature(_flop_spot(["As", "Kd", "2c"])) == "6832a54693ba5f6c"


def test_turn_signature_unchanged_by_multiway_dimension():
    if not _has_multiway_seams():
        pytest.skip("T4 multiway seams (players_in_pot/is_multiway) not yet landed")
    assert spot_signature(_turn_spot("7h")) == "9c1aae003ae79de0"


def test_river_signature_unchanged_by_multiway_dimension():
    if not _has_multiway_seams():
        pytest.skip("T4 multiway seams (players_in_pot/is_multiway) not yet landed")
    # No pinned river-only literal exists pre-S8 in this file (river's S7
    # companions use relative comparisons, not a pin) — so this companion
    # instead proves byte-identity the same way S7's own river companions did:
    # the HU (2-IN) river spot must still match the pre-existing S7 relative
    # fixture behavior (river-card-class dimension only), i.e. two different
    # blanks still collapse to one SRS item post-S8, unaffected by the new
    # (omitted, for HU) `mw` dimension.
    assert spot_signature(_river_spot("9s")) == spot_signature(_river_spot("8d"))


def test_multiway_flop_signature_differs_from_hu_twin():
    if not _has_multiway_seams():
        pytest.skip("T4 multiway seams (players_in_pot/is_multiway) not yet landed")
    hu = spot_signature(_flop_spot(["As", "Kd", "2c"]))
    mw = spot_signature(_mw_flop_spot(["As", "Kd", "2c"]))
    assert mw != hu


def test_multiway_turn_signature_differs_from_hu_twin():
    if not _has_multiway_seams():
        pytest.skip("T4 multiway seams (players_in_pot/is_multiway) not yet landed")
    hu = spot_signature(_turn_spot("7h"))
    mw = spot_signature(_mw_turn_spot("7h"))
    assert mw != hu


def test_multiway_river_signature_differs_from_hu_twin():
    if not _has_multiway_seams():
        pytest.skip("T4 multiway seams (players_in_pot/is_multiway) not yet landed")
    hu = spot_signature(_river_spot("9s"))
    mw = spot_signature(_mw_river_spot("9s"))
    assert mw != hu


def test_multiway_3way_and_4way_hash_identically_binary_bucket():
    if not _has_multiway_seams():
        pytest.skip("T4 multiway seams (players_in_pot/is_multiway) not yet landed")
    from app.domain.spot import PlayerState

    flop_3 = _mw_flop_spot(["As", "Kd", "2c"])
    flop_4 = flop_3.model_copy(
        update={"players": [*flop_3.players, PlayerState(position=Position.HJ, stack_bb=100)]}
    )
    three_way = spot_signature(flop_3)
    four_way = spot_signature(flop_4)
    hu = spot_signature(_flop_spot(["As", "Kd", "2c"]))
    assert three_way == four_way
    assert three_way != hu
    assert four_way != hu


def test_multiway_3way_and_4way_turn_hash_identically():
    if not _has_multiway_seams():
        pytest.skip("T4 multiway seams (players_in_pot/is_multiway) not yet landed")
    three_way = spot_signature(_mw_turn_spot("7h", extra_players=1))
    four_way = spot_signature(_mw_turn_spot("7h", extra_players=2))
    hu = spot_signature(_turn_spot("7h"))
    assert three_way == four_way
    assert three_way != hu


def test_multiway_3way_and_4way_river_hash_identically():
    if not _has_multiway_seams():
        pytest.skip("T4 multiway seams (players_in_pot/is_multiway) not yet landed")
    three_way = spot_signature(_mw_river_spot("9s", extra_players=1))
    four_way = spot_signature(_mw_river_spot("9s", extra_players=2))
    hu = spot_signature(_river_spot("9s"))
    assert three_way == four_way
    assert three_way != hu


# NOTE: the refuter pre-computed 3 multiway hash literals in the ticket
# (flop-MW f5a26ff25cb7ea4d / turn-MW ef1ac33ae4cf6042 / river-MW
# e2d884cec8d5336d) against their OWN fixture construction, which this file's
# local `_mw_*_spot` helpers do not reproduce byte-for-byte (different player
# list shape/positions). Rather than pin a literal that doesn't match this
# file's fixtures (and would silently drift from what it claims to guard),
# the tests above assert the CONTRACT relatively — HU unchanged, MW != HU,
# 3-way == 4-way — which is the behavior those literals were meant to prove.
