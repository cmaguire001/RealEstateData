"""Configuration for the real estate market signal pipeline."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    state: str
    north_metro_cities: tuple[str, ...]
    export_path: str
    request_timeout_seconds: int
    request_retries: int
    use_anoka_open_data: bool
    production_scraper_mode: bool


def load_local_env(env_path: str = ".env") -> None:
    """Load key/value pairs from a local .env file if present.

    Existing environment variables are not overwritten.
    """
    path = Path(env_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    load_local_env()
    return Settings(
        database_url=os.getenv("DATABASE_URL"),
        state=os.getenv("STATE", "MN"),
        north_metro_cities=(
            "Andover",
            "Anoka",
            "Big Lake",
            "Blaine",
            "Champlin",
            "Coon Rapids",
            "Dayton",
            "Elk River",
            "Fridley",
            "Ham Lake",
            "Lino Lakes",
            "Mounds View",
            "Nowthen",
            "Oak Grove",
            "Ramsey",
            "Spring Lake Park",
            "Zimmerman",
        ),
        export_path=os.getenv("EXPORT_PATH", "frontend/data.json"),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
        request_retries=int(os.getenv("REQUEST_RETRIES", "3")),
        use_anoka_open_data=_to_bool(os.getenv("USE_ANOKA_OPEN_DATA"), default=True),
        production_scraper_mode=_to_bool(os.getenv("PRODUCTION_SCRAPER_MODE"), default=True),
    )


def configure_logging() -> None:
    load_local_env()
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
