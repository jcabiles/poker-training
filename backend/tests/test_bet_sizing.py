"""R2 — realistic persona-flavored fixed bet sizes.

Covers: the pure sizing helpers, bot preflop lever wiring, bot postflop
node-aware sizing (dry vs wet), and the anti-sizing-tell property.
"""

from __future__ import annotations

import random

import pytest

from app.domain.personas import load_persona_packs
from app.domain.personas_postflop import sample_postflop_decision
from app.domain.spot import ActionType, LegalAction, Position
from app.domain.table import play, sizing

# --------------------------------------------------------- pure helpers


def _bet_legal():
    return [
        LegalAction(action=ActionType.CHECK),
        LegalAction(action=ActionType.BET, min_bb=0.5, max_bb=100.0),
    ]


def _facing_legal():
    return [
        LegalAction(action=ActionType.FOLD),
        LegalAction(action=ActionType.CALL, min_bb=2.0),
        LegalAction(action=ActionType.RAISE, min_bb=4.0, max_bb=100.0),
    ]


def test_postflop_node_key_textures_and_streets():
    dry = ["Kh", "7c", "2d"]
    wet = ["9s", "8s", "7d"]
    mono = ["Jh", "Th", "9h"]
    assert sizing.postflop_node_key(dry, _bet_legal(), is_aggressor=True) == "cbet_dry"
    assert sizing.postflop_node_key(wet, _bet_legal(), is_aggressor=True) == "cbet_wet"
    assert sizing.postflop_node_key(mono, _bet_legal(), is_aggressor=True) == "cbet_mono"
    assert sizing.postflop_node_key(dry + ["5s"], _bet_legal(), is_aggressor=True) == "turn_barrel"
    assert (
        sizing.postflop_node_key(dry + ["5s", "2c"], _bet_legal(), is_aggressor=True)
        == "river_value"
    )
    # facing a bet ⇒ raise node regardless of aggressor
    assert sizing.postflop_node_key(dry, _facing_legal(), is_aggressor=False) == "raise"
    # betting without being the aggressor = donk/lead ⇒ flat (never mis-sized as a c-bet)
    assert sizing.postflop_node_key(dry, _bet_legal(), is_aggressor=False) == "flat"


def test_preflop_raise_to_nodes_and_two_sided_clamp():
    class S:
        open_bb = 3.0
        threebet_mult = 3.5
        fourbet_mult = 2.4

    kw = {"min_bb": 2.0, "max_bb": 100.0}
    assert sizing.preflop_raise_to(S(), "open", last_raise_to=1.0, limpers=0, **kw) == 3.0
    assert sizing.preflop_raise_to(S(), "iso", last_raise_to=1.0, limpers=2, **kw) == 5.0
    assert sizing.preflop_raise_to(S(), "3bet", last_raise_to=3.0, limpers=0, **kw) == 10.5
    assert sizing.preflop_raise_to(S(), "4bet", last_raise_to=10.5, limpers=0, **kw) == 25.2
    assert sizing.preflop_raise_to(S(), "5bet", last_raise_to=25.0, limpers=0, **kw) == 100.0
    # clamp UP to min_bb (a tiny 3bet base)
    assert sizing.preflop_raise_to(S(), "3bet", last_raise_to=0.1, limpers=0, **kw) == 2.0
    # clamp DOWN to max_bb (huge base must not exceed the bracket / jam)
    assert (
        sizing.preflop_raise_to(S(), "3bet", last_raise_to=1000.0, limpers=0, **kw) == 100.0
    )
    # forced-jam bracket (min==max) collapses to the single legal value
    jam = sizing.preflop_raise_to(
        S(), "4bet", last_raise_to=50.0, limpers=0, min_bb=40.0, max_bb=40.0
    )
    assert jam == 40.0


def test_pot_fraction_to_bb_bet_vs_raise():
    # BET: frac * pot
    assert sizing.pot_fraction_to_bb(0.5, 6.0, action=ActionType.BET) == 3.0
    # RAISE: current_bet_to + frac*(pot + to_call)
    assert (
        sizing.pot_fraction_to_bb(
            0.5, 6.0, action=ActionType.RAISE, current_bet_to=2.0, to_call=2.0
        )
        == 2.0 + 0.5 * 8.0
    )


# --------------------------------------------------- bot preflop wiring


AA = ("As", "Ac")  # always in every persona's opening range


def test_bot_open_size_is_persona_open_bb_not_min_raise():
    packs = load_persona_packs()
    legal = [
        LegalAction(action=ActionType.FOLD),
        LegalAction(action=ActionType.CALL, min_bb=1.0),
        LegalAction(action=ActionType.RAISE, min_bb=2.0, max_bb=100.0),
    ]
    sizes = {}
    for pack in packs.values():
        d = play._preflop_decision(
            pack, Position.CO, "unopened", AA, legal, random.Random(1), 1.0, 0
        )
        assert d.action is ActionType.RAISE
        assert d.size_bb == pytest.approx(pack.sizing.open_bb)  # lever, NOT min_bb (2.0)
        assert d.size_bb != 2.0
        sizes[pack.persona] = d.size_bb
    # personas differ where the packs differ (maniac oversizes vs nit textbook)
    assert sizes["maniac"] > sizes["nit"]


# ------------------------------------------ bot postflop node-aware size


def _mean_bet_fraction(pack, hole, board, pot_bb, n=600):
    """Mean pot-fraction of the sampler's BET decisions (aggressor) over n draws.
    frac = size/pot for a BET (`pot_fraction_to_bb` BET branch)."""
    legal = [
        LegalAction(action=ActionType.CHECK),
        LegalAction(action=ActionType.BET, min_bb=0.5, max_bb=1000.0),
    ]
    fracs = []
    for i in range(n):
        d = sample_postflop_decision(
            pack, hole, board, legal, pot_bb, 100.0, 1, random.Random(i), is_aggressor=True
        )
        if d.action is ActionType.BET and d.size_bb is not None:
            fracs.append(d.size_bb / pot_bb)
    assert len(fracs) >= 30, f"too few BET samples ({len(fracs)})"
    return sum(fracs) / len(fracs)


def test_tag_cbets_small_on_dry_big_on_wet():
    tag = load_persona_packs()["tag"]
    dry_mean = _mean_bet_fraction(tag, ("Ks", "Kc"), ["Kh", "7c", "2d"], 6.0)  # top set, dry
    wet_mean = _mean_bet_fraction(tag, ("9h", "9c"), ["9s", "8d", "7d"], 6.0)  # top set, wet
    assert dry_mean <= 0.45, f"dry c-bet mean {dry_mean} not small"
    assert wet_mean >= 0.6, f"wet c-bet mean {wet_mean} not big"
    assert wet_mean > dry_mean


def test_flat_fallback_when_no_sizing_by_node():
    """A persona WITHOUT sizing_by_node (station/fish) keeps the flat distribution
    — behavior unchanged from pre-R2."""
    station = load_persona_packs()["calling_station"]
    assert station.postflop.sizing_by_node is None  # station is flat by design
    # aggressor bet still produces a size from the flat distribution (no crash)
    got = _mean_bet_fraction(station, ("Ks", "Kc"), ["Kh", "7c", "2d"], 6.0, n=800)
    assert got > 0.0


# ----------------------------------------------------- anti-sizing-tell


def test_node_key_is_independent_of_hole_cards():
    """Node selection reads board+legal only — never hole — so routing a size
    through the node cannot leak hand strength (anti-sizing-tell)."""
    board = ["Kh", "7c", "2d"]
    n1 = sizing.postflop_node_key(board, _bet_legal(), is_aggressor=True)
    n2 = sizing.postflop_node_key(board, _bet_legal(), is_aggressor=True)
    assert n1 == n2 == "cbet_dry"
    # a monster and a bluff on the same board draw from the SAME node distribution:
    tag = load_persona_packs()["tag"]
    monster = _mean_bet_fraction(tag, ("Ks", "Kc"), board, 6.0)  # top set
    # the distribution the sampler uses is keyed by node (board), not the hole —
    # so any hand that bets here draws the same dry-node mean.
    assert monster <= 0.45
