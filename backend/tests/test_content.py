import pytest
from pydantic import ValidationError

from app.domain.content import (
    ContentPack,
    all_hands,
    hole_cards_to_class,
    load_pack,
    parse_range,
)


def test_all_hands_count():
    assert len(all_hands()) == 169  # 13 pairs + 78 suited + 78 offsuit


def test_pair_plus():
    assert parse_range("77+") == {"77", "88", "99", "TT", "JJ", "QQ", "KK", "AA"}


def test_pair_range():
    assert parse_range("QQ-99") == {"99", "TT", "JJ", "QQ"}


def test_suited_plus():
    assert parse_range("ATs+") == {"ATs", "AJs", "AQs", "AKs"}


def test_offsuit_plus_non_ace():
    assert parse_range("KTo+") == {"KTo", "KJo", "KQo"}


def test_both_suits_when_unspecified():
    assert parse_range("AK") == {"AKs", "AKo"}


def test_single_hands_and_union():
    assert parse_range("AKo") == {"AKo"}
    assert parse_range("77+, ATs+, KQs") == (
        {"77", "88", "99", "TT", "JJ", "QQ", "KK", "AA"} | {"ATs", "AJs", "AQs", "AKs"} | {"KQs"}
    )


def test_star_is_everything():
    assert parse_range("*") == all_hands()


def test_bad_token_raises():
    with pytest.raises(ValueError):
        parse_range("XYZ")


@pytest.mark.parametrize(
    "c1,c2,expected",
    [
        ("Ah", "Ks", "AKo"),
        ("Ah", "Kh", "AKs"),
        ("Kd", "Ac", "AKo"),  # order-independent
        ("7c", "7d", "77"),
    ],
)
def test_hole_cards_to_class(c1, c2, expected):
    assert hole_cards_to_class(c1, c2) == expected


def test_contentpack_loads_and_validates():
    pack = load_pack(
        {
            "id": "preflop-rfi-test",
            "version": 1,
            "domain": "preflop",
            "entries": [
                {
                    "node_context": "RFI",
                    "position": "CO",
                    "actions": [
                        {"action": "raise", "combos": "77+, ATs+, KQs", "frequency": 1.0},
                    ],
                    "sizing_bb": 2.5,
                }
            ],
        }
    )
    assert isinstance(pack, ContentPack)
    assert pack.entries[0].actions[0].action.value == "raise"


def test_contentpack_rejects_bad_frequency():
    with pytest.raises(ValidationError):
        load_pack(
            {
                "id": "x",
                "version": 1,
                "domain": "preflop",
                "entries": [
                    {
                        "node_context": "RFI",
                        "position": "CO",
                        "actions": [{"action": "raise", "combos": "AA", "frequency": 2.0}],
                    }
                ],
            }
        )
