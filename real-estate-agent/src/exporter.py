"""Export snapshots into frontend JSON."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from db import get_history


def export_history_json(cities: tuple[str, ...], export_path: str, limit: int = 30) -> dict[str, Any]:
    series: dict[str, list[dict[str, Any]]] = {}
    for city in cities:
        rows = get_history(city=city, limit=limit)
        rows = list(reversed(rows))
        series[city] = [
            {
                "timestamp": _to_iso(row.get("timestamp")),
                "city": city,
                "total_listings": _to_int(row.get("total_listings")),
                "avg_price": _to_float(row.get("avg_price")),
                "avg_price_per_sqft": _to_float(row.get("avg_price_per_sqft")),
                "inventory_growth": _to_float(row.get("inventory_growth")),
                "status": row.get("status"),
            }
            for row in rows
        ]

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "cities": list(cities),
        "series": series,
    }

    out = Path(export_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _to_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None
