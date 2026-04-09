"""Anoka County OpenData fetcher (ArcGIS REST)."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from .production_mode import get_runtime
except ImportError:  # running as script
    from production_mode import get_runtime

LOGGER = logging.getLogger(__name__)
LAYER_URL = "https://gis.anokacountymn.gov/anoka_gis/rest/services/OpenData_Property/MapServer/1"


def fetch_anoka_city_records(
    city: str,
    timeout_seconds: int = 15,
    retries: int = 3,
    result_record_count: int = 500,
) -> list[dict[str, Any]]:
    """Fetch normalized records from Anoka county ArcGIS layer."""
    runtime = get_runtime()
    cache_key = f"anoka::{city}::{result_record_count}"
    cached = runtime.get_cache(cache_key)
    if cached is not None:
        return cached

    query_url = f"{LAYER_URL}/query"
    params = {
        "where": f"CITY='{city.upper()}'",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": str(result_record_count),
    }

    def _run_fetch() -> list[dict[str, Any]]:
        runtime.throttle("anoka")
        payload = _http_get_json(query_url, params=params, timeout_seconds=timeout_seconds)
        features = payload.get("features", []) if isinstance(payload, dict) else []
        rows: list[dict[str, Any]] = []
        for feature in features:
            attrs = feature.get("attributes", {}) if isinstance(feature, dict) else {}
            normalized = _normalize_attributes(attrs)
            if normalized is not None:
                rows.append(normalized)
        return rows

    try:
        rows = runtime.retry_with_backoff(_run_fetch, retries=retries, label=f"AnokaOpenData({city})")
    except Exception as exc:
        LOGGER.error("All Anoka OpenData retries exhausted for %s: %s", city, exc)
        return []

    if rows:
        runtime.set_cache(cache_key, rows)
        runtime.store_raw_dataset("anoka", city, rows)
    return rows


def fetch_anoka_fields(timeout_seconds: int = 15) -> list[dict[str, Any]]:
    """Return available ArcGIS fields for visibility/debugging."""
    runtime = get_runtime()
    runtime.throttle("anoka")
    payload = _http_get_json(LAYER_URL, params={"f": "json"}, timeout_seconds=timeout_seconds)
    fields = payload.get("fields", []) if isinstance(payload, dict) else []
    return [f for f in fields if isinstance(f, dict)]


def _http_get_json(url: str, params: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
    query = urlencode(params)
    req = Request(
        f"{url}?{query}",
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; RealEstateSignalBot/1.0)",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Anoka OpenData request failed: {exc}") from exc


def _normalize_attributes(attrs: dict[str, Any]) -> dict[str, Any] | None:
    price = _to_int(_pick_first(attrs, ["SALE_PRICE", "SALEPRICE", "PRICE", "MARKET_VALUE"]))
    sqft = _to_int(
        _pick_first(
            attrs,
            [
                "SQFT",
                "FIN_SQ_FT",
                "LIVING_AREA",
                "BLDG_SQFT",
                "TOTAL_SQFT",
                "BUILDING_SQFT",
            ],
        )
    )

    if price is None or price <= 0:
        return None

    beds = _to_int(_pick_first(attrs, ["BEDS", "BEDROOMS", "BR"])) or 0
    baths = _to_float(_pick_first(attrs, ["BATHS", "BATHROOMS", "BA"])) or 0.0

    if sqft is None or sqft <= 0:
        return None

    return {
        "price": price,
        "sqft": sqft,
        "beds": beds,
        "baths": baths,
    }


def _pick_first(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


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
