"""N8 — concept-card content + matcher + endpoint tests."""

import json

from fastapi.testclient import TestClient

from app.domain.content import ConceptCard, card_json_schema, load_cards
from app.domain.content.card_registry import CARDS_DIR
from app.domain.leaks import LeakCategory
from app.main import app
from app.services.concept_cards import match_card


def test_at_least_ten_cards_load():
    cards = load_cards()
    assert len(cards) >= 10


def test_all_cards_validate_against_schema():
    """Every raw card dict on disk validates as a ConceptCard (pydantic IS the
    schema, same convention as test_content.py's ContentPack checks)."""
    count = 0
    for path in sorted(CARDS_DIR.glob("*.json")):
        raw = json.loads(path.read_text())
        for entry in raw:
            ConceptCard.model_validate(entry)
            count += 1
    assert count >= 10
    # sanity: the generated schema file is well-formed and matches the model
    assert card_json_schema()["title"] == "ConceptCard"


def test_leak_categories_exist_in_taxonomy():
    valid = {int(c) for c in LeakCategory}
    for card in load_cards():
        for leak in card.leak_categories:
            assert leak in valid, f"{card.id} references unknown leak_category {leak}"


def test_drill_mode_is_a_real_mode():
    valid_modes = {
        "random",
        "review",
        "leak_focus",
        "exploit",
        "challenge",
        "postflop",
        "vs_cbet",
        "vs_check_raise",
    }
    for card in load_cards():
        assert card.drill_mode in valid_modes


# --- Matcher ---


def test_leak_only_match():
    card = match_card(int(LeakCategory.FLOP_CBET), [])
    assert card is not None
    assert int(LeakCategory.FLOP_CBET) in card.leak_categories


def test_vs_rfi_disambiguates_by_tags():
    """VS_RFI (112) covers call/3bet/fold nuance together — different
    rationale_tags on the SAME leak_category must resolve to different cards."""
    over_fold = match_card(int(LeakCategory.VS_RFI), ["over_fold"])
    loose_call = match_card(int(LeakCategory.VS_RFI), ["loose_call"])
    over_aggressive = match_card(int(LeakCategory.VS_RFI), ["over_aggressive"])
    assert over_fold is not None and loose_call is not None and over_aggressive is not None
    assert over_fold.id != loose_call.id != over_aggressive.id
    assert over_fold.id == "vs-rfi-fold-discipline"
    assert loose_call.id == "vs-rfi-loose-call"
    assert over_aggressive.id == "vs-rfi-3bet-discipline"


def test_no_match_returns_none():
    # No card covers a leak_category with no authored content.
    assert match_card(999_999, []) is None


def test_match_is_deterministic():
    a = match_card(int(LeakCategory.VS_RFI), ["over_fold", "chart"])
    b = match_card(int(LeakCategory.VS_RFI), ["over_fold", "chart"])
    assert a is not None and b is not None
    assert a.id == b.id


# --- Endpoint ---


def test_endpoint_returns_matching_card():
    client = TestClient(app)
    resp = client.get(f"/api/v1/cards/match?leak_category={int(LeakCategory.FLOP_CBET)}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["card"] is not None
    assert body["card"]["id"] == "cbet-range-advantage"


def test_endpoint_returns_empty_on_no_match():
    client = TestClient(app)
    resp = client.get("/api/v1/cards/match?leak_category=999999")
    assert resp.status_code == 200
    assert resp.json() == {"card": None}


def test_endpoint_disambiguates_by_tags_query_param():
    client = TestClient(app)
    resp = client.get(
        f"/api/v1/cards/match?leak_category={int(LeakCategory.VS_RFI)}&tags=loose_call"
    )
    assert resp.status_code == 200
    assert resp.json()["card"]["id"] == "vs-rfi-loose-call"
