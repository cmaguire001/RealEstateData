"""Configuration for the real estate market signal pipeline."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    state: str
    north_metro_cities: tuple[str, ...]
    export_path: str
    request_timeout_seconds: int
    request_retries: int


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL"),
        state=os.getenv("STATE", "MN"),
        north_metro_cities=(
            "Blaine",
            "Coon Rapids",
            "Andover",
            "Ham Lake",
            "Anoka",
            "Champlin",
            "Dayton",
            "Lino Lakes",
            "Fridley",
            "Mounds View",
            "Spring Lake Park",
        ),
        export_path=os.getenv("EXPORT_PATH", "frontend/data.json"),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
        request_retries=int(os.getenv("REQUEST_RETRIES", "3")),
    )


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
