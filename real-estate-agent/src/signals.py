"""Deterministic market signal logic."""

from __future__ import annotations

import math
from statistics import pstdev


def compute_signals(
    today_total: int,
    historical_totals: list[int],
) -> dict[str, float | str | None]:
    yesterday_total = historical_totals[-1] if historical_totals else None
    inventory_growth = _inventory_growth(today_total=today_total, yesterday_total=yesterday_total)
    status = _status_from_growth(inventory_growth)
    vs_7_day_avg = _vs_7_day_avg(today_total=today_total, historical_totals=historical_totals)
    volatility = _volatility(historical_totals + [today_total])

    return {
        "inventory_growth": inventory_growth,
        "status": status,
        "vs_7_day_avg": vs_7_day_avg,
        "volatility": volatility,
    }


def _inventory_growth(today_total: int, yesterday_total: int | None) -> float | None:
    if yesterday_total is None or yesterday_total == 0:
        return None
    return (today_total - yesterday_total) / yesterday_total


def _status_from_growth(inventory_growth: float | None) -> str:
    if inventory_growth is None:
        return "stable"
    if inventory_growth > 0.15:
        return "expanding"
    if inventory_growth < -0.10:
        return "tightening"
    return "stable"


def _vs_7_day_avg(today_total: int, historical_totals: list[int]) -> float | None:
    if not historical_totals:
        return None
    trailing = historical_totals[-7:]
    avg = sum(trailing) / len(trailing)
    if math.isclose(avg, 0.0):
        return None
    return today_total / avg


def _volatility(totals: list[int]) -> float | None:
    if len(totals) < 2:
        return None
    return float(pstdev(totals))
