"""M2 belt test (RES-G Slice A, pass/fail a): the missing vs_limpers coverage
fill (UTG2/LJ/HJ/SB x1, CO/SB x2) now maps on ORGANIC bot play.

Drives seeded hands through the REAL engine + REAL bot policy (same method as
`test_mw_funnel_belt.py`: hero seat 0 plays a persona-pack proxy, button
rotates, stacks reset to 100bb per hand, lineup shuffled per hand, one seeded
Random) and records, for each hero pre-decision preflop spot that
`map_preflop` grades, the (hero position, limper_count) pair. Before M2 these
six named pairs returned None (RES-G §1d/§5); after M2's content fill they
must each fire at least once over a large-enough organic sample.

Refuter correction (M2 post-review): RES-G §3a authored the EP faces-1 entry
as "UTG", but §1d's own measurement is UTG2 — and UTG structurally cannot
face a limper (it acts first preflop, `_before(UTG) == []`), which also broke
`scenarios.build_spot`'s Practice-mode path (empty seat-fill loop → incoherent
Spot). The entry was renamed UTG->UTG2 in content; asserted here accordingly.

Deterministic (seeded); a failure here means either the content fill regressed
or organic bot play stopped generating these decision shapes — investigate,
don't retune.
"""

from __future__ import annotations

import random

from app.domain.personas import load_persona_packs
from app.domain.table.deck import deal_hand
from app.domain.table.engine import apply, start_hand
from app.domain.table.grade_map_preflop import map_preflop
from app.domain.table.play import assign_lineup, bot_decision

HERO_SEAT = 0
SEED = 20260722
HANDS = 4000

_WANT_1 = {"UTG2", "LJ", "HJ", "SB"}
_WANT_2 = {"CO", "SB"}
# M3 (RES-G Slice B): the BB check-or-iso option node fires organically too.
_WANT_BB = {("BB", 1), ("BB", 2), ("BB", 3)}
# M3 regression pin: fire counts for every pair that mapped BEFORE M3, at this
# exact seed. Originally pinned to prove M3's BB-only builder/grader path
# moved no non-BB pair. RE-PINNED for P1 (persona-realism-p1, 2026-07-23):
# P1's own preflop content fixes — B1 (station premiums stop folding
# unopened), M3 (maniac/lag non-SB open-limps deleted) and N3 (maniac
# vs_4bet rebuild), plus A1's air-call drop — deliberately change bot
# preflop mixes, which shifts the shared-rng hand stream and therefore every
# organic fire count at this seed (old counts: UTG2¹ 99, LJ¹ 128, HJ¹ 142,
# CO¹ 139, CO² 39, SB¹ 102, SB² 54, BTN¹ 111, BTN² 56). Counts below are
# the re-measured post-P1 values; every coverage pair still fires (the
# _WANT_* assertions are the real belt). A future drift here again means a
# limped-shape-producing behavior changed — investigate, don't retune.
# RE-PINNED for P2a (persona-realism-p2a Q3, 2026-07-23): play.py now passes
# `street` to the postflop sampler, and river polarization (one-pair never
# raises the river, air never calls) changes bot RIVER decisions — which
# consume draws from the SAME shared rng that deals/plays every subsequent
# hand, shifting the whole organic stream at this seed (old post-P1 counts:
# UTG2¹ 94, LJ¹ 127, HJ¹ 140, CO¹ 133, CO² 29, SB¹ 101, SB² 43, BTN¹ 125,
# BTN² 48). No preflop content changed in P2a; the drift is stream
# displacement only.
_PRE_M3_FIRES = {
    ("UTG2", 1): 84, ("LJ", 1): 123, ("HJ", 1): 142, ("CO", 1): 131,
    ("CO", 2): 31, ("SB", 1): 95, ("SB", 2): 42, ("BTN", 1): 122,
    ("BTN", 2): 49,
}


def _count_limper_coverage(proxy: str, seed: int, hands: int) -> dict[tuple[str, int], int]:
    packs = load_persona_packs()
    hero_pack = packs[proxy]
    rng = random.Random(seed)
    fires: dict[tuple[str, int], int] = {}
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
                spot = map_preflop(state, HERO_SEAT)
                if spot is not None and spot.limper_count > 0:
                    key = (spot.to_act.value, spot.limper_count)
                    fires[key] = fires.get(key, 0) + 1
                dec = bot_decision(state, seat, hero_pack, rng)
            else:
                dec = bot_decision(state, seat, seat_packs[seat], rng)
            state = apply(state, dec)
    return fires


def test_limper_coverage_fires_on_organic_play():
    fires = _count_limper_coverage("calling_station", SEED, HANDS)
    for pos in _WANT_1:
        assert fires.get((pos, 1), 0) >= 1, f"faces-1 @ {pos} never fired: {fires}"
    for pos in _WANT_2:
        assert fires.get((pos, 2), 0) >= 1, f"faces-2 @ {pos} never fired: {fires}"
    for key in _WANT_BB:
        assert fires.get(key, 0) >= 1, f"BB x{key[1]} never fired: {fires}"
    for key, count in _PRE_M3_FIRES.items():
        assert fires.get(key, 0) == count, (
            f"pre-M3 pair {key} fire count moved: {fires.get(key, 0)} != {count}"
        )
