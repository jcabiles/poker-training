"""N1 — tiered teaching feedback (verdict / reasoning / deep-dive).

The TieredFeedbackProvider wrapper must populate distinct, non-tautological
tiers on every provider path: preflop, postflop, exploit, and the graceful
not-found fallback. The verdict tier must carry the chosen action's freq/EV.
"""

import asyncio
import random

from factories import make_cbet_spot, make_rfi_spot

from app.domain.action import Decision
from app.domain.archetypes import VillainType
from app.domain.content.registry import build_index, load_preflop_packs
from app.domain.evaluation import Coverage
from app.domain.providers import get_provider
from app.domain.scenarios import build_spot
from app.domain.spot import ActionType, NodeContext, Position, Street

_IDX = build_index(load_preflop_packs())


def _run(coro):
    return asyncio.run(coro)


def _assert_tiers_distinct(res):
    t = res.tiers
    assert t is not None
    assert t.verdict and t.reasoning and t.deep_dive
    assert len({t.verdict, t.reasoning, t.deep_dive}) == 3  # distinct tiers


def test_preflop_tiers_carry_chosen_freq_and_ev():
    p = get_provider()
    spot = make_rfi_spot(hole_cards=("Ah", "Ks"), position=Position.CO)
    res = _run(p.evaluate(spot, Decision(action=ActionType.RAISE, size_bb=2.5)))
    _assert_tiers_distinct(res)
    # chosen-action freq + EV surface in the verdict tier (≈ EV convention)
    assert f"{round(res.chosen_eval.frequency * 100)}%" in res.tiers.verdict
    assert f"≈{res.chosen_eval.ev_bb}bb" in res.tiers.verdict


def test_preflop_mistake_reasoning_is_non_tautological():
    p = get_provider()
    spot = make_rfi_spot(hole_cards=("Ah", "Ad"), position=Position.UTG)
    res = _run(p.evaluate(spot, Decision(action=ActionType.FOLD)))
    reasoning = res.tiers.reasoning
    assert "is the play" not in reasoning  # more than the old tautology
    assert "range's edge" in reasoning  # the over_fold mechanism phrase
    assert "Blunder" in res.tiers.verdict or "Mistake" in res.tiers.verdict


def test_postflop_tiers_compose_from_rich_tags():
    p = get_provider()
    spot = make_cbet_spot()  # AhKs on AcKdQh — hero is the aggressor
    res = _run(p.evaluate(spot, Decision(action=ActionType.CHECK)))
    _assert_tiers_distinct(res)
    reasoning = res.tiers.reasoning
    # composed from the 4-wide [node, adv, cat, wetness] tags, not the f-string
    assert "c-bet" in reasoning
    assert "is the play" not in reasoning
    assert any(w in reasoning for w in ("dry", "medium", "wet"))
    # deep-dive carries the full per-action mix
    for e in res.per_action:
        assert f"≈{e.ev_bb}bb" in res.tiers.deep_dive


def test_exploit_reasoning_carries_authored_rationale():
    p = get_provider()
    entry = _IDX[(NodeContext.VS_RFI, Position.BTN, Position.CO, 0, VillainType.CALLING_STATION)]
    spot = build_spot(entry, random.Random(1))
    res = _run(p.optimal(spot))
    _assert_tiers_distinct(res)
    assert res.authored_rationale  # provider surfaced the Entry.rationale
    assert "station" in res.tiers.reasoning.lower()  # authored prose reaches the tier
    assert res.tiers.reasoning != res.explanation  # composed, not the flat string


def test_not_found_tiers_degrade_gracefully():
    p = get_provider()
    spot = make_rfi_spot(position=Position.CO).model_copy(
        update={"street": Street.TURN, "board": ["As", "Kd", "2c", "7h"], "node_context": []}
    )
    res = _run(p.evaluate(spot, Decision(action=ActionType.FOLD)))
    assert res.coverage == Coverage.NOT_FOUND
    _assert_tiers_distinct(res)
    assert "No strategy content" in res.tiers.verdict


def test_optimal_call_still_populates_tiers():
    # optimal() (no Decision) — verdict falls back to the best-action summary.
    p = get_provider()
    res = _run(p.optimal(make_rfi_spot(position=Position.CO)))
    _assert_tiers_distinct(res)
    assert res.chosen_eval is None
    assert "Best play" in res.tiers.verdict
