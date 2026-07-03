"""Load the concept-card content packs from content/cards/ (N8). Pure
(filesystem read only; no web/DB) — mirrors registry.py's pattern for the
preflop content packs.

Each file under content/cards/ is a JSON array of ConceptCard objects (a
"deck"), grouped by theme (e.g. preflop.json, postflop.json) rather than one
file per card.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import TypeAdapter

from app.domain.content.models import ConceptCard

# backend/app/domain/content/card_registry.py -> parents[4] == repo root
CARDS_DIR = Path(__file__).resolve().parents[4] / "content" / "cards"

_CardList = TypeAdapter(list[ConceptCard])


def load_cards(content_dir: Path | None = None) -> list[ConceptCard]:
    d = content_dir or CARDS_DIR
    cards: list[ConceptCard] = []
    for p in sorted(d.glob("*.json")):
        cards.extend(_CardList.validate_json(p.read_text()))
    return cards


def card_json_schema() -> dict:
    """JSON Schema for a single card (for editors / external validation)."""
    return ConceptCard.model_json_schema()
