"""M1 belt test (pass/fail a): the 3-way MW mappers fire on ORGANIC bot play.

Drives seeded hands through the REAL engine + REAL bot policy (RES-I §1
method: hero seat 0 plays a persona-pack proxy, button rotates, stacks reset
to 100bb per hand, lineup shuffled per hand, one seeded Random) and counts
non-None returns from the real `map_mw_*` mappers at hero pre-decision states.

Pre-M1 this measured ~0 fires/1000 hands (RES-I §2). Post-M1 (L3 content
pairs + L4 grid recognition) the calling_station proxy band is ~1.5-7.5/1000
(RES-I §3 L3+L4 plus the 1.5-pot overbet grid extension; see RES-I §6). The
assertion is a BAND, not an exact count: >=1 fire proves the funnel is open;
the ceiling guards against a gate accidentally going vacuous. Deterministic
(seeded), so drift means bot behavior or mapper gates changed — investigate,
don't retune.
"""

from __future__ import annotations

import random

from app.domain.personas import load_persona_packs
from app.domain.table.deck import deal_hand
from app.domain.table.engine import apply, start_hand
from app.domain.table.grade_map_postflop import (
    map_mw_flop_vs_cbet,
    map_mw_vs_river_bet,
    map_mw_vs_turn_bet,
)
from app.domain.table.play import assign_lineup, bot_decision

HERO_SEAT = 0
SEED = 20260722
HANDS = 2000  # ~4s; expected fires at the station proxy: ~9 (4.5/1000)


def _count_mw_fires(proxy: str, seed: int, hands: int) -> int:
    packs = load_persona_packs()
    hero_pack = packs[proxy]
    rng = random.Random(seed)
    fires = 0
    for hand_no in range(hands):
        lineup = assign_lineup(rng)
        seat_packs = {s: packs[t.value] for s, t in lineup.items()}
        state = start_hand(
            deal_hand(rng), button_seat=hand_no % 9, stacks_bb=[100.0] * 9
        )
        guard = 0
        while not state.hand_over and state.to_act_seat is not None:
            guard += 1
            assert guard <= 500, "bot playout did not terminate"
            seat = state.to_act_seat
            if seat == HERO_SEAT:
                if (
                    map_mw_flop_vs_cbet(state, HERO_SEAT) is not None
                    or map_mw_vs_turn_bet(state, HERO_SEAT) is not None
                    or map_mw_vs_river_bet(state, HERO_SEAT) is not None
                ):
                    fires += 1
                dec = bot_decision(state, seat, hero_pack, rng)
            else:
                dec = bot_decision(state, seat, seat_packs[seat], rng)
            state = apply(state, dec)
    return fires


def test_mw_mappers_fire_on_organic_play():
    fires = _count_mw_fires("calling_station", SEED, HANDS)
    # Band, not exact: measured 9 at this exact seed post-M1 vs 1 pre-M1
    # (deterministic). Floor 3 fails the pre-M1 gates; ceiling 40 (=20/1000,
    # far above any measured rate) catches a gate accidentally going vacuous.
    assert 3 <= fires <= 40, f"MW fires out of band: {fires} in {HANDS} hands"
