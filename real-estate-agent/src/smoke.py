"""Network smoke tests for pyRealtor and Anoka OpenData connectivity."""

from __future__ import annotations

import json

from .anoka_fetcher import fetch_anoka_city_records, fetch_anoka_fields
from .config import get_settings
from .fetcher import fetch_city_listings


def main() -> int:
    settings = get_settings()
    city = settings.north_metro_cities[0]

    realtor_rows = fetch_city_listings(
        city=city,
        state=settings.state,
        timeout_seconds=settings.request_timeout_seconds,
        retries=1,
    )

    anoka_rows = fetch_anoka_city_records(city=city, retries=1)

    try:
        field_names = [f.get("name") for f in fetch_anoka_fields()[:20]]
    except Exception as exc:  # smoke should not crash
        field_names = [f"ERROR: {exc}"]

    print(
        json.dumps(
            {
                "city": city,
                "pyrealtor_rows": len(realtor_rows),
                "anoka_rows": len(anoka_rows),
                "anoka_field_names_preview": field_names,
                "anoka_sample": anoka_rows[:3],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
