"""Database layer for snapshot persistence."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ModuleNotFoundError:  # pragma: no cover
    psycopg2 = None
    RealDictCursor = None

LOGGER = logging.getLogger(__name__)


@contextmanager
def connect(database_url: str | None = None) -> Iterator[Any]:
    db_url = database_url or os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is required")

    if psycopg2 is None:
        raise ModuleNotFoundError("psycopg2 is required. Install dependencies from requirements.txt")

    conn = psycopg2.connect(db_url)
    try:
        yield conn
    finally:
        conn.close()


def init_db(database_url: str | None = None) -> None:
    schema_sql = """
    CREATE TABLE IF NOT EXISTS listing_snapshots (
        id SERIAL PRIMARY KEY,
        city TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_listings INT,
        avg_price NUMERIC,
        median_price NUMERIC,
        avg_price_per_sqft NUMERIC,
        inventory_growth NUMERIC,
        status TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_city_time ON listing_snapshots(city, timestamp);
    """
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
    LOGGER.info("Database initialized.")


def insert_snapshot(
    city: str,
    metrics: dict[str, Any],
    database_url: str | None = None,
) -> None:
    sql = """
    INSERT INTO listing_snapshots (
        city,
        total_listings,
        avg_price,
        median_price,
        avg_price_per_sqft,
        inventory_growth,
        status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    city,
                    metrics.get("total_listings"),
                    metrics.get("avg_price"),
                    metrics.get("median_price"),
                    metrics.get("avg_price_per_sqft"),
                    metrics.get("inventory_growth"),
                    metrics.get("status"),
                ),
            )
        conn.commit()
    LOGGER.info("Inserted snapshot for city=%s", city)


def get_history(city: str, limit: int = 30, database_url: str | None = None) -> list[dict[str, Any]]:
    sql = """
    SELECT
        id,
        city,
        timestamp,
        total_listings,
        avg_price,
        median_price,
        avg_price_per_sqft,
        inventory_growth,
        status
    FROM listing_snapshots
    WHERE city = %s
    ORDER BY timestamp DESC
    LIMIT %s;
    """
    with connect(database_url) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (city, limit))
            rows = cur.fetchall()
    return list(rows)


def get_history_totals(city: str, limit: int = 30, database_url: str | None = None) -> list[int]:
    sql = """
    SELECT total_listings
    FROM listing_snapshots
    WHERE city = %s
    ORDER BY timestamp ASC
    LIMIT %s;
    """
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (city, limit))
            rows = cur.fetchall()
    return [int(row[0]) for row in rows if row[0] is not None]
