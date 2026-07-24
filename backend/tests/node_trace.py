"""W0-c — seeded node-trace realism pack (persona-realism foundation).

A lightweight, seeded replay: run each persona through a fixed set of crafted
spots and log the decision NODE — bucket, draw class, the (normalized) action
probability vector, the seeded chosen action, and the intended prescription.
Its purpose is to catch "right stat, WRONG node" later (e.g. a maniac hitting
its aggression number by over-valuing made hands instead of bluffing): a human
or a later slice reads bucket + probs + prescription and sees whether the mix
at the node is coherent.

Design notes:
- **Merits via capture, no domain edit.** `sample_postflop_decision`'s action
  draw is its FIRST `rng.choices` call, and the weights it passes are already
  NORMALIZED (`w/total`) — so a capture rng records the exact action
  *probabilities* with zero domain instrumentation. (Raw pre-clamp merits would
  need domain changes = out of scope; hence `action_probabilities`, not
  "merits".)
- **The capture rng WRAPS a seeded inner rng** and delegates every call, so the
  chosen action is a real seeded sample — not a forced `population[0]` (which
  would always be CHECK/FOLD, the first candidate).
- Reuses only the public sampler API on crafted fixtures — no dependency on the
  `_play_hand` harness and no `range_estimate` coupling (so: no parity risk).
"""

from __future__ import annotations

import random
from typing import NamedTuple

from app.domain import personas_postflop
from app.domain.action import ActionType
from app.domain.archetypes import VillainType
from app.domain.personas import load_persona_packs
from app.domain.spot import LegalAction, Street

sample_postflop_decision = personas_postflop.sample_postflop_decision
strength_bucket = personas_postflop.strength_bucket


class _TraceRng:
    """Capture rng: records the FIRST `choices()` call (the action draw — whose
    weights are the normalized action probabilities) and delegates EVERY call
    to an inner seeded rng, so the chosen action is a real seeded sample and the
    later sizing draw still resolves normally."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self.population: list[ActionType] | None = None
        self.weights: list[float] | None = None

    def choices(self, population, weights, k=1):  # noqa: ANN001 — rng protocol
        if self.population is None:
            self.population = list(population)
            self.weights = list(weights)
        return self._rng.choices(population, weights=weights, k=k)


class Spot(NamedTuple):
    spot_id: str
    hole: tuple[str, str]
    board: tuple[str, ...]
    legal: tuple[LegalAction, ...]
    pot_bb: float
    stack_bb: float
    opponents: int
    current_bet_to: float
    street: Street
    is_aggressor: bool
    prescription: str


class TraceRow(NamedTuple):
    persona: str
    spot_id: str
    bucket: str
    draw_class: str
    action_probabilities: dict[str, float]  # ActionType.value -> normalized prob
    chosen_action: str
    prescription: str


def _first_in(stack: float) -> tuple[LegalAction, ...]:
    """Unbet street: the actor can CHECK or BET (a c-bet / lead / barrel)."""
    return (
        LegalAction(action=ActionType.CHECK),
        LegalAction(action=ActionType.BET, min_bb=1.0, max_bb=stack),
    )


def _facing(to_call: float, stack: float, jam: float | None = None) -> tuple[LegalAction, ...]:
    """Facing a bet: FOLD / CALL / RAISE. `jam` forces the raise bracket to a
    single all-in value (a low-SPR shove)."""
    r_min = jam if jam is not None else to_call * 2
    r_max = jam if jam is not None else stack
    return (
        LegalAction(action=ActionType.FOLD),
        LegalAction(action=ActionType.CALL, min_bb=to_call),
        LegalAction(action=ActionType.RAISE, min_bb=r_min, max_bb=r_max),
    )


# The seeded spot set — one representative per node the roadmap names. Each is
# deliberately a non-degenerate candidate set (>=2 actions with real merit) so
# the capture never hits the zero-total-merit fallback (Sol #9 / theory nit).
SPOTS: tuple[Spot, ...] = (
    Spot("flop_ip_toppair_dry", ("Ah", "Th"), ("As", "7d", "2c"),
         _first_in(100.0), 6.0, 100.0, 1, 0.0, Street.FLOP, True,
         "IP c-bet, top pair dry board: value-heavy, high c-bet freq"),
    Spot("flop_oop_secondpair_overcards", ("Th", "9h"), ("9s", "Ah", "Kd"),
         _first_in(100.0), 6.0, 100.0, 1, 0.0, Street.FLOP, True,
         "OOP middle pair + 2 overcards: vulnerable, check-heavy / thin"),
    Spot("flop_facing_bet_strong_draw", ("Jh", "Th"), ("9h", "8c", "2h"),
         _facing(4.0, 100.0), 10.0, 100.0, 1, 4.0, Street.FLOP, False,
         "strong combo draw vs a bet: semi-bluff raise / call, few folds"),
    Spot("turn_barrel_toppair", ("Ah", "Th"), ("As", "7d", "2c", "4s"),
         _first_in(100.0), 12.0, 100.0, 1, 0.0, Street.TURN, True,
         "turn barrel with top pair: continuation vs give-up"),
    Spot("river_busted_draw", ("Jh", "Th"), ("9h", "8c", "2s", "3d", "Kc"),
         _first_in(100.0), 18.0, 100.0, 1, 0.0, Street.RIVER, True,
         "busted draw on the river: polarized bluff vs give-up"),
    Spot("flop_multiway_toppair", ("Ah", "Th"), ("As", "7d", "2c"),
         _first_in(100.0), 8.0, 100.0, 3, 0.0, Street.FLOP, True,
         "top pair 4-way: value tightens as opponents rise"),
    Spot("flop_lowspr_commit_overpair", ("Ah", "Ad"), ("Ks", "7d", "2c"),
         _facing(10.0, 15.0, jam=15.0), 20.0, 15.0, 1, 10.0, Street.FLOP, False,
         "overpair, low SPR facing a bet: commit / stack off"),
)


def build_trace(seed: int = 20260724) -> list[TraceRow]:
    """Run every persona through every spot; return the node-trace rows."""
    packs = load_persona_packs()
    rows: list[TraceRow] = []
    for vt in VillainType:
        pack = packs[vt]
        for i, spot in enumerate(SPOTS):
            bucket, draw = strength_bucket(spot.hole, list(spot.board))
            cap = _TraceRng(seed + i)
            decision = sample_postflop_decision(
                pack,
                spot.hole,
                list(spot.board),
                list(spot.legal),
                spot.pot_bb,
                spot.stack_bb,
                spot.opponents,
                cap,
                current_bet_to=spot.current_bet_to,
                is_aggressor=spot.is_aggressor,
                street=spot.street,
            )
            if cap.population is None:  # zero-total-merit fallback (deterministic)
                probs = {decision.action.value: 1.0}
            else:
                assert cap.weights is not None
                probs = {a.value: w for a, w in zip(cap.population, cap.weights, strict=True)}
            rows.append(
                TraceRow(
                    persona=vt.value,
                    spot_id=spot.spot_id,
                    bucket=bucket.value,
                    draw_class=draw.value,
                    action_probabilities=probs,
                    chosen_action=decision.action.value,
                    prescription=spot.prescription,
                )
            )
    return rows
