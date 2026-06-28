"""Run Alembic migrations programmatically (used on app startup + in tests)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command
from app.db.session import DATABASE_URL

BACKEND_DIR = Path(__file__).resolve().parents[2]


def make_alembic_config(url: str | None = None) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url or DATABASE_URL)
    return cfg


def run_migrations(url: str | None = None) -> None:
    """alembic upgrade head."""
    command.upgrade(make_alembic_config(url), "head")
