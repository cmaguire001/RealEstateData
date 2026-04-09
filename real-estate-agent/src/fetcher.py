"""Data fetcher using pyRealtor for Realtor.com listing extraction."""

from __future__ import annotations

import logging
from typing import Any

try:
    from .production_mode import get_runtime
except ImportError:  # running as script
    from production_mode import get_runtime

LOGGER = logging.getLogger(__name__)
"""Data fetcher for Realtor.com listing pages.

This module intentionally uses lightweight requests against public-facing pages,
without browser automation.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)
NEXT_DATA_PATTERN = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    flags=re.DOTALL,
)


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
    """Fetch normalized listing rows for a city/state pair.

    Returns an empty list on all failures and never raises to caller.
    """
    url_city = city.replace(" ", "-")
    url = f"https://www.realtor.com/realestateandhomes-search/{url_city}_{state}"

    for attempt in range(1, retries + 1):
        try:
            LOGGER.info("Fetching listings from %s (attempt %s/%s)", url, attempt, retries)
            response_text = _http_get(url=url, timeout_seconds=timeout_seconds)
            rows = _parse_realtor_html(response_text)
            if rows:
                LOGGER.info("Fetched %s normalized listings for %s, %s", len(rows), city, state)
            else:
                LOGGER.warning("No listings parsed for %s, %s", city, state)
            return rows
        except Exception as exc:  # intentionally broad for resilience
            LOGGER.warning("Fetch failed for %s, %s: %s", city, state, exc)
            if attempt < retries:
                time.sleep(1.0 * attempt)

    LOGGER.error("All retries exhausted for %s, %s. Returning empty list.", city, state)
    return []


def fetch_north_metro_listings(
    cities: tuple[str, ...],
    state: str,
    timeout_seconds: int = 10,
    retries: int = 3,
) -> list[dict[str, Any]]:
    """Fetch and combine listings for the MSP north metro area."""
    all_rows: list[dict[str, Any]] = []
    for city in cities:
        city_rows = fetch_city_listings(
            city=city,
            state=state,
            timeout_seconds=timeout_seconds,
            retries=retries,
        )
        all_rows.extend(city_rows)
    LOGGER.info("Combined normalized listings for MSP north metro: %s", len(all_rows))
    return all_rows


def _http_get(url: str, timeout_seconds: int) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; RealEstateSignalBot/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"HTTP request failed: {exc}") from exc


def _parse_realtor_html(html: str) -> list[dict[str, Any]]:
    match = NEXT_DATA_PATTERN.search(html)
    if not match:
        return []

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    candidates = _extract_listing_candidates(payload)
    normalized: list[dict[str, Any]] = []
    for row in candidates:
        mapped = _normalize_listing(row)
        if mapped is not None:
            normalized.append(mapped)
    return normalized


def _extract_listing_candidates(payload: Any) -> list[dict[str, Any]]:
    """Walk unknown nested JSON and pull likely listing objects."""
    candidates: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "list_price" in node and ("description" in node or "beds" in node):
                candidates.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return candidates


def _normalize_listing(row: dict[str, Any]) -> dict[str, Any] | None:
    description = row.get("description") if isinstance(row.get("description"), dict) else {}

    price = _to_int(row.get("list_price"))
    sqft = _to_int(description.get("sqft") if description else row.get("sqft"))
    beds = _to_int(description.get("beds") if description else row.get("beds"))
    baths = _to_float(description.get("baths") if description else row.get("baths"))

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
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.replace(",", "").strip()
        return float(value)
    except (TypeError, ValueError, AttributeError):
        return float(value)
    except (TypeError, ValueError):
        return None
