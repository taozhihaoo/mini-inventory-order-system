"""Application configuration, read from environment variables.

DATABASE_URL  - SQLAlchemy database URL (default: local SQLite file)
CORS_ORIGINS  - comma-separated list of allowed browser origins
APP_ENV       - "dev" (default) or "test"; "test" skips schema auto-init
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _split_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "ShopStock API"
    app_version: str = "1.0.0"
    app_env: str = os.getenv("APP_ENV", "dev")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./shopstock.db")
    cors_origins: list[str] = field(
        default_factory=lambda: _split_origins(
            os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            )
        )
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
