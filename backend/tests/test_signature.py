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
