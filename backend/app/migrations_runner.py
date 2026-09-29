"""Programmatic Alembic execution for application startup and seeding.

Behavior:
- empty database            -> runs `upgrade head` (creates the full schema)
- legacy database (tables exist from the pre-Alembic `create_all` era,
  no alembic_version table) -> `stamp head`, then future migrations apply
  cleanly on top
- migrated database         -> `upgrade head` (no-op when up to date)

The test suite does NOT go through this module: it builds in-memory
databases directly with Base.metadata.create_all.
"""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database import engine

logger = logging.getLogger("shopstock")

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

# Any table from our domain marks a pre-Alembic database.
_DOMAIN_TABLE = "products"


def make_alembic_config() -> Config:
    config = Config(str(BASE_DIR / "alembic.ini"))
    script_location = BASE_DIR / "migrations"
    config.set_main_option("script_location", str(script_location))
    return config


def run_migrations() -> None:
    """Bring the database schema up to head (see module docstring)."""
    config = make_alembic_config()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if "alembic_version" in table_names:
        command.upgrade(config, "head")
    elif _DOMAIN_TABLE in table_names:
        logger.info("Legacy database detected (no alembic_version); stamping head.")
        command.stamp(config, "head")
    else:
        command.upgrade(config, "head")
