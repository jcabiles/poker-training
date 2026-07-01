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
from app.domain.srs import faced_bet_bucket, quality_from_correctness, sm2


def _vs_bet_spot(cbet: float, flop_pot: float = 6.0) -> Spot:
    """Hero facing a first bet this street (no prior hero investment) — the
    vs_cbet shape. hero_prior_this_street == 0, so faced_bet_bucket must reduce
    to the legacy `pot_bb - faced` formula byte-identically."""
    return Spot(
        game=GameConfig(stakes=Stakes(sb=0.5, bb=1.0), table_size=9),
        street=Street.FLOP,
        board=["As", "Kd", "2c"],
        pot_bb=flop_pot + cbet,
        hero=Hero(position=Position.BB, hole_cards=("Ah", "Kh"), stack_bb=100),
        players=[
            PlayerState(position=Position.BB, stack_bb=100, is_hero=True),
            PlayerState(position=Position.BTN, stack_bb=100),
        ],
        effective_stack_bb=100,
        spr=5.0,
        to_act=Position.BB,
        node_context=[NodeContext.VS_CBET],
        facing=Position.BTN,
        action_history=[
            HistoryAction(street=Street.FLOP, position=Position.BTN, action=ActionType.BET, amount_bb=cbet),
        ],
        legal_actions=[LegalAction(action=ActionType.CALL, min_bb=cbet)],
    )


def _vs_check_raise_spot(flop_pot: float, cbet: float, raise_total: float) -> Spot:
    """Hero c-bets this street, then faces a raise (check-raise shape) — hero
    HAS prior investment (`cbet`) on the current street before the raise.

    `raise_total` is villain's total street commitment for the raise (matches
    the codebase's existing RAISE convention, see build_spot's VS_3BET branch:
    amount_bb is the "raise to" total, and the incremental CALL is
    `raise_total - cbet`).
    """
    faced = round(raise_total - cbet, 2)
    pot_bb = round(flop_pot + cbet + raise_total, 2)
    return Spot(
        game=GameConfig(stakes=Stakes(sb=0.5, bb=1.0), table_size=9),
        street=Street.FLOP,
        board=["As", "Kd", "2c"],
        pot_bb=pot_bb,
        hero=Hero(position=Position.BTN, hole_cards=("Ah", "Kh"), stack_bb=100),
        players=[
            PlayerState(position=Position.BTN, stack_bb=100, is_hero=True),
            PlayerState(position=Position.BB, stack_bb=100),
        ],
        effective_stack_bb=100,
        spr=5.0,
        to_act=Position.BTN,
        node_context=[NodeContext.VS_CBET],
        facing=Position.BB,
        action_history=[
            HistoryAction(street=Street.FLOP, position=Position.BTN, action=ActionType.BET, amount_bb=cbet),
            HistoryAction(street=Street.FLOP, position=Position.BB, action=ActionType.RAISE, amount_bb=raise_total),
        ],
        legal_actions=[LegalAction(action=ActionType.CALL, min_bb=faced)],
    )


def test_faced_bet_bucket_first_bet_matches_legacy_formula():
    """hero_prior_this_street == 0 (facing a first bet): the rewrite must be
    byte-identical to the old `pot_bb - faced` formula for every existing
    vs_cbet case."""
    small = _vs_bet_spot(cbet=2.0, flop_pot=6.0)  # pre_bet_pot = 6.0, faced=2.0 <= 3.0
    big = _vs_bet_spot(cbet=4.5, flop_pot=6.0)  # pre_bet_pot = 6.0, faced=4.5 > 3.0
    assert faced_bet_bucket(small) == "small"
    assert faced_bet_bucket(big) == "big"


def test_faced_bet_bucket_none_when_hero_is_bettor():
    spot = _vs_bet_spot(cbet=2.0)
    hero_is_bettor = spot.model_copy(update={"legal_actions": [LegalAction(action=ActionType.RAISE, min_bb=6.0)]})
    assert faced_bet_bucket(hero_is_bettor) == "none"


def test_faced_bet_bucket_check_raise_small_baseline_a():
    # flop_pot=6, cbet=3 -> pre_bet_pot = flop_pot + cbet = 9.0, threshold = 4.5
    # raise_total=7 -> faced = 7 - 3 = 4.0 <= 4.5 -> small
    spot = _vs_check_raise_spot(flop_pot=6.0, cbet=3.0, raise_total=7.0)
    faced = 7.0 - 3.0
    pre_bet_pot = spot.pot_bb - faced - 3.0
    assert pre_bet_pot == 9.0
    assert faced <= 0.5 * pre_bet_pot
    assert faced_bet_bucket(spot) == "small"


def test_faced_bet_bucket_check_raise_big_baseline_a():
    # Same baseline (flop_pot=6, cbet=3, threshold=4.5) but a much bigger raise.
    # raise_total=15 -> faced = 15 - 3 = 12.0 > 4.5 -> big
    spot = _vs_check_raise_spot(flop_pot=6.0, cbet=3.0, raise_total=15.0)
    faced = 15.0 - 3.0
    pre_bet_pot = spot.pot_bb - faced - 3.0
    assert pre_bet_pot == 9.0
    assert faced > 0.5 * pre_bet_pot
    assert faced_bet_bucket(spot) == "big"


def test_faced_bet_bucket_check_raise_small_baseline_b():
    # A second, different cbet baseline (flop_pot=10, cbet=5) -> pre_bet_pot=15, threshold=7.5
    # raise_total=10 -> faced = 10 - 5 = 5.0 <= 7.5 -> small
    spot = _vs_check_raise_spot(flop_pot=10.0, cbet=5.0, raise_total=10.0)
    faced = 10.0 - 5.0
    pre_bet_pot = spot.pot_bb - faced - 5.0
    assert pre_bet_pot == 15.0
    assert faced <= 0.5 * pre_bet_pot
    assert faced_bet_bucket(spot) == "small"


def test_faced_bet_bucket_check_raise_big_baseline_b():
    # Same second baseline (flop_pot=10, cbet=5, threshold=7.5) with a bigger raise.
    # raise_total=20 -> faced = 20 - 5 = 15.0 > 7.5 -> big
    spot = _vs_check_raise_spot(flop_pot=10.0, cbet=5.0, raise_total=20.0)
    faced = 20.0 - 5.0
    pre_bet_pot = spot.pot_bb - faced - 5.0
    assert pre_bet_pot == 15.0
    assert faced > 0.5 * pre_bet_pot
    assert faced_bet_bucket(spot) == "big"


def test_quality_mapping():
    assert quality_from_correctness("optimal") == 5
    assert quality_from_correctness("acceptable") == 4
    assert quality_from_correctness("mistake") == 2
    assert quality_from_correctness("blunder") == 0
    assert quality_from_correctness(None) == 0


def test_failed_resets_interval():
    ease, interval, reps = sm2(2.5, 30, 5, quality=0)
    assert reps == 0
    assert interval == 1
    assert ease >= 1.3


def test_success_grows_interval():
    ease, interval, reps = sm2(2.5, 0, 0, quality=5)
    assert (interval, reps) == (1, 1)
    ease, interval, reps = sm2(ease, interval, reps, quality=5)
    assert (interval, reps) == (6, 2)
    ease, interval, reps = sm2(ease, interval, reps, quality=5)
    assert interval > 6 and reps == 3


def test_ease_floor():
    ease, _, _ = sm2(1.3, 5, 3, quality=0)
    assert ease >= 1.3
