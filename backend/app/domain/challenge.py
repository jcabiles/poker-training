"""Challenge mode — difficulty-biased preflop RFI sampler (pure domain).

Unlike `scenarios.sample_rfi_spot` (uniform over entries, then a uniform random
deal), Challenge mode biases WHICH hand gets dealt toward genuinely contestable
raise-vs-fold decisions: hands that flip action across RFI seats and/or sit
near a raise/fold transition within a seat's own chart. See
docs/ai-dlc/specs/challenge-preflop-rfi.md ("Difficulty model") for the model
this implements; symbols below (F, E, D_obj, M, W) match that spec.

Everything downstream of hand selection (grading, feedback, Spot shape) is
reused as-is — this module only changes how `(position, hand)` is chosen, then
hands off to `scenarios.build_spot` for the actual Spot construction.

Pure domain: imports only `app.domain.*` (content index, range_grid, hand_rank,
scenarios' RFI spot builder, equity's combo expansion). No db/web import.
"""

from __future__ import annotations

import math
import random

from app.domain.content.models import Entry
from app.domain.content.registry import _key, build_index, load_preflop_packs
from app.domain.equity import combos_for_range
from app.domain.grading import range_grid
from app.domain.hand_rank import HAND_RANK
from app.domain.scenarios import RFI_POSITIONS, build_spot
from app.domain.spot import NodeContext, Position, Spot

# --- Tunable constants (named per the spec's shared contract; comment each) ---
wF = 0.6  # weight on the flip score F in the objective-difficulty blend
wE = 0.4  # weight on the edge score E in the objective-difficulty blend
EPS = 0.02  # sampling floor so every legal (position, hand) keeps nonzero probability
M_MIN = 0.5  # personal-multiplier floor (clamp)
M_MAX = 2.0  # personal-multiplier ceiling (clamp)

# Kernel bandwidth (in rank-ORDER steps) for the edge score's local-disagreement
# density (see `edge_score`). Not pinned by the spec's shared contract; chosen
# empirically against the actual RFI charts — small enough that a hand deep in
# a homogeneous block (e.g. 72o, AA) scores near 0, wide enough that a hand
# that's an isolated exception to its neighborhood (e.g. a suited connector
# tucked inside a sea of offsuit folds) is still recognized as "flippy."
EDGE_KERNEL_SCALE = 8.0

# All 169 hand classes ordered by `hand_rank` (weakest -> strongest). Distances
# in this order are the "rank-ORDER steps" the edge score is defined over.
# Depends on HAND_RANK's tie-break being deterministic (see hand_rank.py).
_RANK_ORDER: list[str] = sorted(HAND_RANK, key=HAND_RANK.get)
_RANK_INDEX: dict[str, int] = {h: i for i, h in enumerate(_RANK_ORDER)}
_N_HANDS = len(_RANK_ORDER)

_RFI_ENTRIES: dict[Position, Entry] | None = None
_RFI_GRIDS: dict[Position, dict[str, str]] | None = None
_EDGE_TABLE: dict[tuple[Position, str], float] | None = None
_D_OBJ_TABLE: dict[tuple[Position, str], float] | None = None


def _rfi_entries() -> dict[Position, Entry]:
    """The 6 RFI seats' content Entries, keyed via the registry index.

    RFI entries have facing=None, limper_count=0, villain_type=None (see
    content/preflop/rfi.json + registry.py's `_key`/`lookup`).
    """
    global _RFI_ENTRIES
    if _RFI_ENTRIES is None:
        idx = build_index(load_preflop_packs())
        _RFI_ENTRIES = {
            pos: idx[_key(NodeContext.RFI, pos, None, 0, None)]
            for pos in RFI_POSITIONS
            if _key(NodeContext.RFI, pos, None, 0, None) in idx
        }
    return _RFI_ENTRIES


def _rfi_grids() -> dict[Position, dict[str, str]]:
    """Per-seat range_grid: {hand_class: 'raise'|'fold'} (RFI has no mixed content)."""
    global _RFI_GRIDS
    if _RFI_GRIDS is None:
        _RFI_GRIDS = {pos: range_grid(entry) for pos, entry in _rfi_entries().items()}
    return _RFI_GRIDS


def flip_score(position: Position, hand: str) -> float:
    """F(P,H) in [0,1] — fraction of the OTHER 5 RFI seats whose range_grid
    action for `hand` differs from `hand`'s action at `position`.

    Raise-everywhere (AA) or fold-everywhere (72o) -> 0. Raise-some/fold-some
    (A9o, KTo, 66, low suited connectors) -> high; matches the position-flippy
    signal (e.g. A9o: raise at CO/BTN/SB, fold at UTG/LJ/HJ).
    """
    grids = _rfi_grids()
    action = grids[position][hand]
    others = [p for p in RFI_POSITIONS if p != position]
    diff = sum(1 for p in others if grids[p][hand] != action)
    return diff / len(others)


def _edge_table() -> dict[tuple[Position, str], float]:
    """Precompute E(P,H) for the full 6x169 grid (cached; independent of rng
    and personal_weights, so it's built once per process).

    E(P,H): kernel-decayed LOCAL DENSITY of disagreement around H in the
    rank-ORDER sequence of P's chart — not a distance to the single nearest
    differing hand. `hand_rank` is a strength PROXY (not solver-accurate), so
    the raise/fold split is non-monotonic in rank order: a lone suited
    connector "raise" can sit rank-order-adjacent to a sea of offsuit "fold"
    trash (see spec refuter HIGH-1). A naive nearest-neighbor distance would
    score that trash HIGH (its immediate neighbor differs) even though the
    trash is deep inside a homogeneous fold block. The weighted-density
    formulation fixes this: E(P,H) = kernel-weighted fraction of H's
    neighborhood (all other 168 hands, weight decaying with rank-order
    distance) whose action differs from H's. A hand that IS the local
    majority action (e.g. offsuit trash surrounded by other fold hands) scores
    LOW even if one lone neighbor differs; a hand that's a local minority/
    outlier (an isolated raise amid fold, or a hand genuinely adjacent to a
    real transition) scores HIGH. Empirically verified against BTN's chart:
    74o/82o/93o (unambiguous folds near BTN's loose floor) score ~0.1-0.2;
    hands adjacent to a real transition (or isolated suited-connector
    exceptions) score ~0.9+.
    """
    global _EDGE_TABLE
    if _EDGE_TABLE is None:
        grids = _rfi_grids()
        weights = [math.exp(-d / EDGE_KERNEL_SCALE) for d in range(_N_HANDS)]
        table: dict[tuple[Position, str], float] = {}
        for pos in RFI_POSITIONS:
            seq = [grids[pos][h] for h in _RANK_ORDER]
            for k in range(_N_HANDS):
                action_k = seq[k]
                num = 0.0
                den = 0.0
                for j in range(_N_HANDS):
                    if j == k:
                        continue
                    w = weights[abs(j - k)]
                    den += w
                    if seq[j] != action_k:
                        num += w
                table[(pos, _RANK_ORDER[k])] = num / den if den else 0.0
        _EDGE_TABLE = table
    return _EDGE_TABLE


def edge_score(position: Position, hand: str) -> float:
    """E(P,H) in [0,1] — see `_edge_table` for the definition and rationale."""
    return _edge_table()[(position, hand)]


def objective_difficulty(position: Position, hand: str) -> float:
    """D_obj(P,H) = wF*F(P,H) + wE*E(P,H), cached over the 6x169 grid."""
    global _D_OBJ_TABLE
    if _D_OBJ_TABLE is None:
        edge = _edge_table()
        _D_OBJ_TABLE = {
            (pos, hand): wF * flip_score(pos, hand) + wE * edge[(pos, hand)]
            for pos in RFI_POSITIONS
            for hand in _RANK_ORDER
        }
    return _D_OBJ_TABLE[(position, hand)]


def personal_multiplier(hand: str, personal_weights: dict[str, float] | None) -> float:
    """M(H) in [M_MIN, M_MAX] — from the injected per-hand-class weight dict.

    Default 1.0 (neutral) for hands absent from `personal_weights`, and for a
    cold-start (None/empty) dict entirely -> pure objective difficulty.
    """
    if not personal_weights:
        return 1.0
    raw = personal_weights.get(hand, 1.0)
    return min(M_MAX, max(M_MIN, raw))


def sampling_weight(
    position: Position, hand: str, personal_weights: dict[str, float] | None = None
) -> float:
    """W(P,H) = (EPS + D_obj(P,H)) * M(H)."""
    d_obj = objective_difficulty(position, hand)
    m = personal_multiplier(hand, personal_weights)
    return (EPS + d_obj) * m


def sample_challenge_spot(
    rng: random.Random,
    personal_weights: dict[str, float] | None = None,
    eff_bb: float = 100.0,
) -> Spot:
    """Sample a preflop RFI Spot with `(position, hand)` drawn jointly ~ W(P,H)
    over the 6x169 grid, then deal a random concrete combo of `hand` and build
    the Spot via the existing RFI builder (so the shape matches every other
    RFI sampler — grid, legal_actions, pot, node_context, etc.).

    `personal_weights` empty/None => M(H)=1.0 everywhere => pure objective
    difficulty (cold start is fully useful). `rng` is injected for
    determinism/testability.
    """
    entries = _rfi_entries()
    pairs = [(pos, hand) for pos in RFI_POSITIONS for hand in _RANK_ORDER]
    weights = [sampling_weight(pos, hand, personal_weights) for pos, hand in pairs]
    position, hand = rng.choices(pairs, weights=weights, k=1)[0]

    combo = rng.choice(combos_for_range(hand))
    return build_spot(entries[position], rng, eff_bb=eff_bb, hole_cards=combo)
