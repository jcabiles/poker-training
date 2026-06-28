"""Load the preflop content packs from content/preflop/ and index entries for
node-aware lookup. Pure (filesystem read only; no web/DB)."""

from __future__ import annotations

from pathlib import Path

from app.domain.content.loader import load_pack_file
from app.domain.content.models import ContentPack, Entry

# backend/app/domain/content/registry.py -> parents[4] == repo root
CONTENT_DIR = Path(__file__).resolve().parents[4] / "content" / "preflop"


def load_preflop_packs(content_dir: Path | None = None) -> list[ContentPack]:
    d = content_dir or CONTENT_DIR
    return [load_pack_file(p) for p in sorted(d.glob("*.json"))]


def _key(node_context, position, facing, limper_count, villain_type=None):
    return (node_context, position, facing, limper_count or 0, villain_type)


def build_index(packs: list[ContentPack]) -> dict[tuple, Entry]:
    idx: dict[tuple, Entry] = {}
    for pack in packs:
        for e in pack.entries:
            idx[_key(e.node_context, e.position, e.facing, e.limper_count, e.villain_type)] = e
    return idx


def lookup(index: dict[tuple, Entry], spot, villain_type="__spot__") -> Entry | None:
    """Look up the entry for a spot. Pass villain_type=None to force the baseline
    entry even for an exploit spot (used for the GTO-vs-exploit contrast)."""
    ctx = spot.node_context[0] if spot.node_context else None
    vt = spot.villain_type if villain_type == "__spot__" else villain_type
    return index.get(_key(ctx, spot.hero.position, spot.facing, spot.limper_count, vt))
