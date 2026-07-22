"""Fixed bet-sizing helpers (R2) — pure domain, no web/DB import.

One place that turns the persona/content sizing levers into concrete bb amounts,
and one place that names the postflop node so bots, hero, and (later) the range
chart agree. Reuses `app.domain.texture` for board classification — never a
second taxonomy.

Anti-sizing-tell: `postflop_node_key` reads `board` and `legal` only, never a
hole-card / made-hand signal, so routing a size through the node never leaks
hand strength.
"""

from __future__ import annotations

from app.domain.action import ActionType
from app.domain.spot import HistoryAction, LegalAction, Position
from app.domain.texture import classify

# Hero's SINGLE predetermined postflop size per node, as a pot-fraction
# (RES-B §5.1 node baselines). The size R3 will later offer as one of two
# options. Nodes absent here (e.g. "flat") leave hero on the engine min-raise.
HERO_NODE_SIZE: dict[str, float] = {
    "cbet_dry": 0.33,
    "cbet_wet": 0.75,
    "cbet_mono": 0.33,
    "turn_barrel": 0.67,
    "river_value": 0.75,
    "raise": 1.0,
}

# N4a — the two OFFERED/graded hero BET pot-fractions per postflop street
# (RES-B §5.1). SINGLE source of truth for hero's two-button offered sizes and
# the graded `_barrel_spot` sizes. Flop stays 0.33/0.75 (the R3 flop c-bet pair
# is unchanged); only turn/river get the RES-B fix (previously all three were
# graded against the flop's 0.33/0.75). Hero's OFFERED sizes stay 2-button
# (M1-L4 widened faced-size RECOGNITION only — see RECOGNIZED_BET_FRACS).
POSTFLOP_BET_FRACS: dict[str, tuple[float, float]] = {
    "flop": (0.33, 0.75),
    "turn": (0.5, 0.75),
    "river": (0.5, 1.0),
}

# M1-L4 (RES-I §3 L4) — the faced-size RECOGNITION grid for the line gates in
# `grade_map_postflop._is_canonical_bet`: every pot-fraction the bot personas
# bet from (`postflop.sizing` keys across content/personas/*.json — 0.33 / 0.5
# / 0.75 / 1.0 plus the maniac's 1.5 overbet), on EVERY street. Before M1 the
# gate accepted only the street's POSTFLOP_BET_FRACS pair, so a bot's 0.5-pot
# or 1.0-pot flop c-bet silently un-mapped the whole line (RES-I §2: the
# dominant postflop line kill). RECOGNITION only — hero's offered sizes stay
# the POSTFLOP_BET_FRACS pairs. Every member maps to a defined RES-E bucket
# (`personas_postflop.size_bucket`: 0.33→SMALL, 0.5→MEDIUM, 0.75/1.0→LARGE,
# 1.5→OVERBET) and the graders always price the TRUE live pot-fraction
# (faced/pot), never a bucket-collapsed size (RES-I §5 HIGH flag; pinned by
# tests/test_grade_map_multiway.py::test_recognized_fracs_map_to_res_e_buckets).
RECOGNIZED_BET_FRACS: tuple[float, ...] = (0.33, 0.5, 0.75, 1.0, 1.5)

# N4b — the two graded/offered RAISE multipliers (on the faced bet/raise-to
# amount) when hero faces a postflop bet or check-raise (RES-B §5.1 :148-149).
# SINGLE source of truth for the mapper's graded legs, sim_session's offered
# sizes, AND the Practice builders. "check_raise" is FLOP-scoped research
# (hero check-raising the c-bet); every other facing raise — flop re-raise
# over a check-raise, all turn/river raises — uses "raise". The 3.0 big leg
# equals the historical flat 3x, keeping existing turn/river grades unchanged.
FACING_RAISE_MULTS: dict[str, tuple[float, float]] = {
    "check_raise": (2.5, 3.5),
    "raise": (2.5, 3.0),
}


def last_aggressor_position(action_history: list[HistoryAction]) -> Position | None:
    """Position of the most recent BET/RAISE in the hand, or None if the pot was
    never raised/bet (e.g. a limped, checked-down pot). Used to decide whether
    the seat about to act is the aggressor (⇒ a c-bet/barrel) or not (⇒ a
    donk/lead, which is NOT persona-node-sized)."""
    for h in reversed(action_history):
        if h.action in (ActionType.BET, ActionType.RAISE):
            return h.position
    return None


def postflop_node_key(
    board: list[str], legal: list[LegalAction], *, is_aggressor: bool
) -> str:
    """Node name for a postflop BET/RAISE the actor is about to make.

    `is_aggressor` is REQUIRED — `board`+`legal` alone cannot separate a c-bet
    from a donk-lead (both present a {CHECK, BET} legal shape). Returns "flat"
    for any spot without a persona-authored size (donk/lead, or an unhandled
    street) ⇒ caller falls back to the flat `sizing` distribution.
    """
    kinds = {la.action for la in legal}
    if ActionType.CALL in kinds:
        # There is a bet to face; sizing a RAISE = check-raise / facing-bet raise.
        return "raise"
    if not is_aggressor:
        return "flat"  # betting without being the aggressor = donk/lead
    street = len(board)
    if street == 3:
        tex = classify(board)
        if tex.suitedness == "monotone":
            return "cbet_mono"
        # wetness is dry|medium|wet; medium folds into the small/dry bucket.
        return "cbet_wet" if tex.wetness == "wet" else "cbet_dry"
    if street == 4:
        return "turn_barrel"
    if street == 5:
        return "river_value"
    return "flat"


def pot_fraction_to_bb(
    frac: float,
    pot_bb: float,
    *,
    action: ActionType,
    current_bet_to: float = 0.0,
    to_call: float = 0.0,
) -> float:
    """Pot-fraction → bb, byte-matching the sampler's existing formula: a BET is
    `frac*pot`; a RAISE is `current_bet_to + frac*(pot + to_call)`."""
    if action is ActionType.BET:
        return frac * pot_bb
    return current_bet_to + frac * (pot_bb + to_call)


def _clamp(value: float, min_bb: float | None, max_bb: float | None) -> float:
    """Two-sided clamp into the legal raise bracket. When the engine forces a jam
    (`min_bb == max_bb`) the bracket collapses to that single legal value."""
    v = round(value, 2)
    if max_bb is not None:
        v = min(v, max_bb)
    if min_bb is not None:
        v = max(v, min_bb)
    return round(v, 2)


def preflop_raise_to(
    sizing,
    node: str,
    *,
    last_raise_to: float,
    limpers: int,
    min_bb: float | None,
    max_bb: float | None,
) -> float:
    """Persona preflop lever → a legal raise-TO in bb, clamped to
    `[min_bb, max_bb]`. `node` ∈ {open, iso, 3bet, 4bet, 5bet}. `last_raise_to`
    is the last raise-TO faced (= `state.current_bet_bb`)."""
    if node == "open":
        v = sizing.open_bb
    elif node == "iso":
        v = sizing.open_bb + 1.0 * limpers  # open + 1bb per limper (live iso)
    elif node == "3bet":
        v = sizing.threebet_mult * last_raise_to
    elif node == "4bet":
        v = sizing.fourbet_mult * last_raise_to
    elif node == "5bet":
        v = max_bb if max_bb is not None else last_raise_to
    else:
        v = min_bb if min_bb is not None else last_raise_to
    return _clamp(v, min_bb, max_bb)


def preflop_node(facing: str) -> str:
    """Map `_preflop_facing()` output → the raise node the actor makes.
    unopened→open · vs_limpers→iso · vs_rfi→3bet · vs_3bet→4bet · vs_4bet→5bet."""
    return {
        "unopened": "open",
        "vs_limpers": "iso",
        "vs_rfi": "3bet",
        "vs_3bet": "4bet",
        "vs_4bet": "5bet",
    }.get(facing, "open")
