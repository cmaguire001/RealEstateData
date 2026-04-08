"""Main orchestrator for ETL + signal pipeline."""

from __future__ import annotations

import logging

from config import configure_logging, get_settings
from db import get_history_totals, init_db, insert_snapshot
from exporter import export_history_json
from fetcher import fetch_north_metro_listings
from signals import compute_signals
from transformer import compute_base_metrics

LOGGER = logging.getLogger(__name__)
CITY_LABEL = "MSP North Metro"


def run() -> int:
    configure_logging()
    settings = get_settings()
    LOGGER.info("Pipeline starting")

    if not settings.database_url:
        LOGGER.error("DATABASE_URL missing. Exiting safely.")
        return 0

    try:
        init_db(settings.database_url)

        listings = fetch_north_metro_listings(
            cities=settings.north_metro_cities,
            state=settings.state,
            timeout_seconds=settings.request_timeout_seconds,
            retries=settings.request_retries,
        )

        if not listings:
            LOGGER.warning("No listings fetched. Exiting without insert/export.")
            return 0

        base_metrics = compute_base_metrics(listings)

        history_totals = get_history_totals(
            city=CITY_LABEL,
            limit=30,
            database_url=settings.database_url,
        )
        signal_metrics = compute_signals(
            today_total=int(base_metrics["total_listings"]),
            historical_totals=history_totals,
        )

        snapshot = {**base_metrics, **signal_metrics}
        insert_snapshot(city=CITY_LABEL, metrics=snapshot, database_url=settings.database_url)

        export_history_json(city=CITY_LABEL, export_path=settings.export_path, limit=30)
        LOGGER.info("Pipeline completed successfully")
        return 0
    except Exception as exc:  # resilient orchestration
        LOGGER.exception("Pipeline failed but handled safely: %s", exc)
        return 0


if __name__ == "__main__":
    raise SystemExit(run())
