"""Point-of-need concept-card matcher (N8).

Deliberately in `app/services`, NOT `app/domain` — the roadmap mandates the
leak->card map live here since it's presentation-adjacent lookup logic, not
core strategy grading. Cards themselves are pure content-data
(`app.domain.content.ConceptCard`).

Matching rule: filter to cards whose `leak_categories` contains the given
`leak_category`, then rank by rationale-tag overlap with the given `tags`
(count of shared tags, descending). Ties — including the common case where no
tags overlap at all — break on the card's `id` (stable, deterministic) so the
same inputs always resolve to the same card.
"""

from __future__ import annotations

from functools import lru_cache

from app.domain.content.card_registry import load_cards
from app.domain.content.models import ConceptCard


@lru_cache(maxsize=1)
def _cards() -> tuple[ConceptCard, ...]:
    return tuple(load_cards())


def _tag_overlap(card: ConceptCard, tags: frozenset[str]) -> int:
    return len(tags & frozenset(card.rationale_tags))


def match_card(leak_category: int, tags: list[str] | None = None) -> ConceptCard | None:
    """Best-fitting card for a graded result's (leak_category, rationale_tags).

    Returns None cleanly when no card covers this leak_category at all.
    """
    tag_set = frozenset(tags or [])
    candidates = [c for c in _cards() if leak_category in c.leak_categories]
    if not candidates:
        return None
    best_overlap = max(_tag_overlap(c, tag_set) for c in candidates)
    ties = [c for c in candidates if _tag_overlap(c, tag_set) == best_overlap]
    return min(ties, key=lambda c: c.id)
