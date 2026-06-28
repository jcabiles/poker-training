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

_INDEX: dict | None = None


def _preflop_index() -> dict:
    global _INDEX
    if _INDEX is None:
        _INDEX = build_index(load_preflop_packs())
    return _INDEX


def get_provider(name: str = "composite"):
    # The default routed provider: preflop -> heuristic, flop -> postflop.
    # "heuristic" kept as an alias so existing callers keep working unchanged.
    if name in ("composite", "heuristic"):
        return CompositeProvider(
            HeuristicProvider(_preflop_index()),
            PostflopHeuristicProvider(),
        )
    if name == "preflop":
        return HeuristicProvider(_preflop_index())
    raise ValueError(f"unknown provider: {name!r}")
