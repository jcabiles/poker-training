"""Load + validate content packs. Pydantic IS the runtime validator."""

from __future__ import annotations

from pathlib import Path

from app.domain.content.models import ContentPack


def load_pack(data: dict) -> ContentPack:
    return ContentPack.model_validate(data)


def load_pack_file(path: str | Path) -> ContentPack:
    return ContentPack.model_validate_json(Path(path).read_text())


def content_pack_json_schema() -> dict:
    """JSON Schema for the pack format (for editors / external validation)."""
    return ContentPack.model_json_schema()
