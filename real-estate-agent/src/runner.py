"""Main orchestrator for ETL + signal pipeline."""

from __future__ import annotations

import logging

from anoka_fetcher import fetch_anoka_city_records
from config import configure_logging, get_settings
from db import get_history_totals, init_db, insert_snapshot
from exporter import export_history_json
from fetcher import fetch_city_listings
from signals import compute_signals
from transformer import compute_base_metrics

LOGGER = logging.getLogger(__name__)


def run() -> int:
    configure_logging()
    settings = get_settings()
    LOGGER.info("Pipeline starting")

    if not settings.database_url:
        LOGGER.error("DATABASE_URL missing. Exiting safely.")
        return 0

    try:
        init_db(settings.database_url)

        inserted_count = 0
        for city in settings.north_metro_cities:
            LOGGER.info("Processing city=%s", city)
            listings = fetch_city_listings(
                city=city,
                state=settings.state,
                timeout_seconds=settings.request_timeout_seconds,
                retries=settings.request_retries,
            )

            if settings.use_anoka_open_data and not listings:
                LOGGER.info("Falling back to Anoka OpenData for %s", city)
                listings = fetch_anoka_city_records(
                    city=city,
                    timeout_seconds=max(settings.request_timeout_seconds, 15),
                    retries=settings.request_retries,
                )

            if not listings:
                LOGGER.warning("No listings fetched for %s; skipping snapshot insert.", city)
                continue

            base_metrics = compute_base_metrics(listings)
            history_totals = get_history_totals(
                city=city,
                limit=30,
                database_url=settings.database_url,
            )
            signal_metrics = compute_signals(
                today_total=int(base_metrics["total_listings"]),
                historical_totals=history_totals,
            )

            snapshot = {**base_metrics, **signal_metrics}
            insert_snapshot(city=city, metrics=snapshot, database_url=settings.database_url)
            inserted_count += 1

        if inserted_count == 0:
            LOGGER.warning("No city snapshots inserted. Exiting without export.")
            return 0

        export_history_json(
            cities=settings.north_metro_cities,
            export_path=settings.export_path,
            limit=30,
        )
        LOGGER.info("Pipeline completed successfully with %s city snapshots", inserted_count)
        return 0
    except Exception as exc:  # resilient orchestration
        LOGGER.exception("Pipeline failed but handled safely: %s", exc)
        return 0


if __name__ == "__main__":
    raise SystemExit(run())
