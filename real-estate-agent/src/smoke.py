"""Network smoke tests for fetcher connectivity and parse path."""

from __future__ import annotations

import json

from .config import get_settings
from .fetcher import fetch_city_listings


def main() -> int:
    settings = get_settings()
    city = settings.north_metro_cities[0]
    rows = fetch_city_listings(
        city=city,
        state=settings.state,
        timeout_seconds=settings.request_timeout_seconds,
        retries=1,
    )

    print(json.dumps({"city": city, "rows": len(rows), "sample": rows[:3]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
