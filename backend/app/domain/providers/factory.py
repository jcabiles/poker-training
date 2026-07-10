"""Provider factory.

Returns a StrategyProvider by name so SolverTableProvider / HybridProvider drop
in later untouched. The heuristic provider is seeded with the real preflop
content-pack index (loaded once).
"""

from __future__ import annotations

from app.domain.content.registry import build_index, load_preflop_packs
from app.domain.providers.composite import CompositeProvider
from app.domain.providers.heuristic import HeuristicProvider
from app.domain.providers.postflop import PostflopHeuristicProvider
from app.domain.providers.tiered import TieredFeedbackProvider
from app.domain.providers.turn import TurnHeuristicProvider

_INDEX: dict | None = None


def _preflop_index() -> dict:
    global _INDEX
    if _INDEX is None:
        _INDEX = build_index(load_preflop_packs())
    return _INDEX


def get_provider(name: str = "composite"):
    # The default routed provider: preflop -> heuristic, flop -> postflop,
    # turn -> turn heuristic (S6).
    # "heuristic" kept as an alias so existing callers keep working unchanged.
    # Every provider returned here is wrapped in TieredFeedbackProvider — the
    # shared teaching seam a future solver/hybrid provider inherits for free.
    if name in ("composite", "heuristic"):
        return TieredFeedbackProvider(
            CompositeProvider(
                HeuristicProvider(_preflop_index()),
                PostflopHeuristicProvider(),
                TurnHeuristicProvider(),
            )
        )
    if name == "preflop":
        return TieredFeedbackProvider(HeuristicProvider(_preflop_index()))
    raise ValueError(f"unknown provider: {name!r}")
