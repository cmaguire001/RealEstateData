"""Feature engineering and metric aggregation."""

from __future__ import annotations

import statistics
from typing import Any


def clean_listings(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for row in listings:
        if not isinstance(row, dict):
            continue
        price = row.get("price")
        sqft = row.get("sqft")
        beds = row.get("beds")
        baths = row.get("baths")
        if (
            isinstance(price, int)
            and price > 0
            and isinstance(sqft, int)
            and sqft > 0
            and isinstance(beds, int)
            and beds >= 0
            and isinstance(baths, (int, float))
            and float(baths) >= 0
        ):
            cleaned.append(
                {
                    "price": price,
                    "sqft": sqft,
                    "beds": beds,
                    "baths": float(baths),
                    "price_per_sqft": safe_divide(price, sqft),
                }
            )
    return cleaned


def compute_base_metrics(listings: list[dict[str, Any]]) -> dict[str, float | int | None]:
    rows = clean_listings(listings)
    if not rows:
        return {
            "total_listings": 0,
            "avg_price": None,
            "median_price": None,
            "avg_price_per_sqft": None,
        }

    prices = [row["price"] for row in rows]
    ppsf_values = [row["price_per_sqft"] for row in rows if row["price_per_sqft"] is not None]

    return {
        "total_listings": len(rows),
        "avg_price": float(sum(prices) / len(prices)),
        "median_price": float(statistics.median(prices)),
        "avg_price_per_sqft": float(sum(ppsf_values) / len(ppsf_values)) if ppsf_values else None,
    }


def safe_divide(numerator: float | int, denominator: float | int) -> float | None:
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)
