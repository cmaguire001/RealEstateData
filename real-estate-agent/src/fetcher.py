"""Data fetcher using pyRealtor for Realtor.com listing extraction."""

from __future__ import annotations

import logging
from typing import Any

try:
    from .production_mode import get_runtime
except ImportError:  # running as script
    from production_mode import get_runtime

LOGGER = logging.getLogger(__name__)


def fetch_city_listings(
    city: str,
    state: str,
    timeout_seconds: int = 10,
    retries: int = 3,
) -> list[dict[str, Any]]:
    """Fetch normalized listing rows for a city/state pair using pyRealtor.

    Production mode adds caching, throttling, retry backoff, and local raw storage.
    """
    runtime = get_runtime()
    cache_key = f"pyrealtor::{state}::{city}"

    cached = runtime.get_cache(cache_key)
    if cached is not None:
        return cached

    def _run_fetch() -> list[dict[str, Any]]:
        runtime.throttle("pyrealtor")
        return _fetch_with_pyrealtor(city=city, state=state, timeout_seconds=timeout_seconds)

    try:
        rows = runtime.retry_with_backoff(_run_fetch, retries=retries, label=f"pyRealtor({city},{state})")
    except Exception as exc:
        LOGGER.error("All retries exhausted for %s, %s: %s", city, state, exc)
        return []

    if rows:
        runtime.set_cache(cache_key, rows)
        runtime.store_raw_dataset("pyrealtor", city, rows)
        LOGGER.info("Fetched %s normalized listings for %s, %s", len(rows), city, state)
    else:
        LOGGER.warning("No listings returned by pyRealtor for %s, %s", city, state)
    return rows


def _fetch_with_pyrealtor(city: str, state: str, timeout_seconds: int) -> list[dict[str, Any]]:
    """Fetch city listings via pyRealtor facade."""
    del timeout_seconds  # pyRealtor controls HTTP internals.

    try:
        import pyRealtor
    except ModuleNotFoundError as exc:
        raise RuntimeError("pyRealtor is not installed. Run: pip install -r requirements.txt") from exc

    facade = pyRealtor.HousesFacade()
    facade.search_save_houses(
        search_area=city,
        country="United States",
        state=state,
        listing_type="for_sale",
        get_summary=False,
    )

    houses_df = getattr(facade, "houses_df", None)
    if houses_df is None:
        houses_df = getattr(facade, "houses_df_preprocess", None)

    rows: list[dict[str, Any]] = []
    for listing in _iter_rows(houses_df):
        mapped = _normalize_listing(listing)
        if mapped is not None:
            rows.append(mapped)
    return rows


def _iter_rows(houses_df: Any) -> list[dict[str, Any]]:
    """Convert pyRealtor DataFrame-like output to list[dict]."""
    if houses_df is None:
        return []

    if hasattr(houses_df, "to_dict"):
        try:
            return list(houses_df.to_dict(orient="records"))
        except TypeError:
            pass

    if isinstance(houses_df, list):
        return [row for row in houses_df if isinstance(row, dict)]

    return []


def _normalize_listing(row: dict[str, Any]) -> dict[str, Any] | None:
    price = _to_int(_pick_first(row, ["Price", "price", "list_price", "Listing Price"]))
    sqft = _to_int(_pick_first(row, ["Square Footage", "sqft", "Sqft", "Area", "Total Sqft"]))
    beds = _to_int(_pick_first(row, ["Bedrooms", "beds", "Beds"]))
    baths = _to_float(_pick_first(row, ["Bathrooms", "baths", "Baths"]))

    normalized = {
        "price": price,
        "sqft": sqft,
        "beds": beds,
        "baths": baths,
    }

    if not _is_valid_normalized_listing(normalized):
        return None
    return normalized


def _pick_first(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _is_valid_normalized_listing(row: dict[str, Any]) -> bool:
    price = row.get("price")
    sqft = row.get("sqft")
    beds = row.get("beds")
    baths = row.get("baths")

    return (
        isinstance(price, int)
        and price > 0
        and isinstance(sqft, int)
        and sqft > 0
        and isinstance(beds, int)
        and beds >= 0
        and isinstance(baths, float)
        and baths >= 0.0
    )


def _to_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.replace(",", "").replace("$", "").strip()
        return int(float(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.replace(",", "").strip()
        return float(value)
    except (TypeError, ValueError, AttributeError):
        return None
