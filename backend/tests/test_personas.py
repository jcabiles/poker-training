"""Persona pack schema + engine tests, incl. the S3 closed-loop stat bands.

Stat metrics are PROXIES, not tracker VPIP (true VPIP needs full-hand
simulation — S4's table-texture loop): open-freq ~ VPIP, first-in-raise ~ PFR,
plus 3-bet% and vs_rfi continue% (spec `docs/ai-dlc/specs/simulate-s3.md`).
"""

import json
import random

import pytest
from pydantic import ValidationError

from app.domain.archetypes import VillainType
from app.domain.content.models import PersonaPack
from app.domain.personas import load_persona_packs, sample_preflop_action
from app.domain.spot import ActionType, Position
from app.domain.table.deck import deal_hand, positions_for_button

# ---------------------------------------------------------------- fixtures


def _pack(preflop: list[dict], persona: str = "tag") -> dict:
    return {
        "id": f"persona_{persona}",
        "version": "1.0.0",
        "domain": "persona",
        "persona": persona,
        "display_name": persona,
        "sizing": {"open_bb": 2.5, "threebet_mult": 3.0, "fourbet_mult": 2.2},
        "preflop": preflop,
    }


FIXTURE = PersonaPack.model_validate(
    _pack(
        [
            {
                "facing": "unopened",
                "positions": ["BTN"],
                "mixes": [
                    {"combos": "AA,KK", "weights": {"raise": 1.0}},
                    {"combos": "22+", "weights": {"raise": 0.5, "limp": 0.5}},
                ],
            },
            {
                "facing": "unopened",
                "positions": None,
                "mixes": [{"combos": "QQ+", "weights": {"raise": 1.0}}],
            },
            {
                "facing": "vs_rfi",
                "positions": None,
                "mixes": [
                    {"combos": "77", "weights": {"call": 1.0}},
                    {"combos": "AA", "weights": {"3bet": 0.4}},  # remainder = implicit fold
                ],
            },
        ]
    )
)

AA = ("As", "Ad")
SEVENS = ("7c", "7d")
FIVES = ("5c", "5d")
TREY_DEUCE = ("3c", "2d")

# ------------------------------------------------------- schema validation


def test_persona_pack_rejects_bad_action_vocabulary():
    with pytest.raises(ValidationError, match="not allowed facing"):
        _validate([{"facing": "unopened", "positions": None,
                    "mixes": [{"combos": "AA", "weights": {"call": 1.0}}]}])


def test_persona_pack_rejects_weights_sum_above_one():
    with pytest.raises(ValidationError, match="sum"):
        _validate([{"facing": "unopened", "positions": None,
                    "mixes": [{"combos": "AA", "weights": {"raise": 0.7, "limp": 0.7}}]}])


def test_persona_pack_rejects_unsupported_range_token():
    with pytest.raises(ValidationError, match="range token"):
        _validate([{"facing": "unopened", "positions": None,
                    "mixes": [{"combos": "A5s-A2s", "weights": {"raise": 1.0}}]}])


def test_persona_pack_rejects_explicit_node_after_wildcard():
    with pytest.raises(ValidationError, match="after wildcard"):
        _validate([
            {"facing": "unopened", "positions": None,
             "mixes": [{"combos": "AA", "weights": {"raise": 1.0}}]},
            {"facing": "unopened", "positions": ["BTN"],
             "mixes": [{"combos": "AA", "weights": {"raise": 1.0}}]},
        ])


def test_persona_pack_rejects_second_wildcard_per_facing():
    with pytest.raises(ValidationError, match="wildcard"):
        _validate([
            {"facing": "unopened", "positions": None,
             "mixes": [{"combos": "AA", "weights": {"raise": 1.0}}]},
            {"facing": "unopened", "positions": None,
             "mixes": [{"combos": "KK", "weights": {"raise": 1.0}}]},
        ])


def test_persona_pack_rejects_overlapping_explicit_positions():
    with pytest.raises(ValidationError, match="duplicate position coverage"):
        _validate([
            {"facing": "unopened", "positions": ["BTN", "CO"],
             "mixes": [{"combos": "AA", "weights": {"raise": 1.0}}]},
            {"facing": "unopened", "positions": ["CO"],
             "mixes": [{"combos": "KK", "weights": {"raise": 1.0}}]},
        ])


def _validate(preflop: list[dict]) -> PersonaPack:
    return PersonaPack.model_validate(_pack(preflop))


def test_loader_raises_on_duplicate_persona(tmp_path):
    pack = _pack([{"facing": "unopened", "positions": None,
                   "mixes": [{"combos": "AA", "weights": {"raise": 1.0}}]}])
    (tmp_path / "a.json").write_text(json.dumps(pack))
    (tmp_path / "b.json").write_text(json.dumps(pack))
    with pytest.raises(ValueError, match="duplicate persona"):
        load_persona_packs(tmp_path)


# --------------------------------------------------------------- sampling


def test_wire_translation_limp_is_call_and_3bet_is_raise():
    rng = random.Random(7)
    # BTN 55 hits the mixed 22+ row: limp draws must translate to CALL.
    names = set()
    for _ in range(200):
        act = sample_preflop_action(FIXTURE, Position.BTN, "unopened", FIVES, rng)
        names.add(act.name)
        assert act.action == (ActionType.CALL if act.name == "limp" else ActionType.RAISE)
    assert names == {"limp", "raise"}  # a mixed row genuinely mixes

    threebet = sample_preflop_action(FIXTURE, Position.SB, "vs_rfi", AA, random.Random(0))
    while threebet.name == "fold":  # 0.4 3bet / 0.6 implicit fold
        threebet = sample_preflop_action(FIXTURE, Position.SB, "vs_rfi", AA, rng)
    assert threebet == ("3bet", ActionType.RAISE)


def test_first_matching_mix_wins():
    # AA on BTN is in both mixes; the first (raise 1.0) must win every time.
    rng = random.Random(3)
    for _ in range(50):
        assert sample_preflop_action(FIXTURE, Position.BTN, "unopened", AA, rng).name == "raise"


def test_explicit_position_node_beats_wildcard_and_wildcard_covers_rest():
    rng = random.Random(11)
    # 77 unopened: BTN hits the explicit node (22+ row); CO falls to wildcard (QQ+ only) -> fold.
    assert sample_preflop_action(FIXTURE, Position.BTN, "unopened", SEVENS, rng).name != "fold"
    assert sample_preflop_action(FIXTURE, Position.CO, "unopened", SEVENS, rng).name == "fold"


def test_unmatched_hand_or_facing_folds():
    rng = random.Random(5)
    assert sample_preflop_action(FIXTURE, Position.CO, "unopened", TREY_DEUCE, rng) == (
        "fold",
        ActionType.FOLD,
    )
    assert sample_preflop_action(FIXTURE, Position.CO, "vs_4bet", AA, rng).name == "fold"


def test_same_seed_is_deterministic():
    def draw(seed):
        rng = random.Random(seed)
        return [
            sample_preflop_action(FIXTURE, Position.BTN, "unopened", FIVES, rng).name
            for _ in range(100)
        ]

    assert draw(42) == draw(42)
    assert draw(42) != draw(43)  # and the mix isn't degenerate


# ---------------------------------------------- closed-loop stat bands (S3)

# persona -> (open-freq/VPIP, first-in raise/PFR, 3-bet, vs_rfi continue), all %.
BANDS = {
    "passive_fish": ((28, 45), (3, 9), (0, 2), (35, 55)),
    "calling_station": ((40, 60), (0, 8), (0, 1), (50, 70)),
    "nit": ((7, 14), (2, 9), (1, 2), (5, 15)),
    "tag": ((15, 20), (12, 17), (6, 7), (15, 28)),
    "lag": ((24, 36), (18, 24), (8, 12), (25, 42)),
    "maniac": ((45, 60), (30, 40), (12, 20), (45, 70)),
}

DEALS = 1112  # pinned: 1,112 deals x 9 seats ~= 10k samples per facing


def _stats(pack: PersonaPack) -> tuple[float, float, float, float]:
    rng = random.Random(20260710)
    positions = positions_for_button(0)
    n = DEALS * 9
    opened = first_in_raised = threebet = continued = 0
    for _ in range(DEALS):
        dealt = deal_hand(rng)
        for seat, pos in enumerate(positions):
            hole = dealt.hole_cards[seat]
            a = sample_preflop_action(pack, pos, "unopened", hole, rng)
            opened += a.name != "fold"
            first_in_raised += a.name == "raise"
            b = sample_preflop_action(pack, pos, "vs_rfi", hole, rng)
            threebet += b.name == "3bet"
            continued += b.name != "fold"
    return tuple(100.0 * c / n for c in (opened, first_in_raised, threebet, continued))


def test_all_six_persona_packs_load():
    packs = load_persona_packs()
    missing = set(VillainType) - set(packs)
    if missing:
        pytest.skip(f"personas not authored yet (T2/T3 land at fan-in): {sorted(missing)}")
    assert set(packs) == set(VillainType)
    for vt, pack in packs.items():
        assert pack.persona == vt
        assert pack.preflop


@pytest.mark.parametrize("persona", sorted(BANDS))
def test_persona_stat_bands(persona):
    packs = load_persona_packs()
    vt = VillainType(persona)
    if vt not in packs:
        pytest.skip(f"content/personas/{persona}.json not authored yet — lands at fan-in")
    stats = _stats(packs[vt])
    labels = ("open-freq", "first-in-raise", "3-bet", "vs_rfi-continue")
    for label, value, (lo, hi) in zip(labels, stats, BANDS[persona], strict=True):
        assert lo <= value <= hi, f"{persona} {label} {value:.2f}% outside [{lo}, {hi}]"
