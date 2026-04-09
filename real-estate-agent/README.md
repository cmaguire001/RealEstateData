# Real Estate Market Signal Agent (MVP)

Deterministic ETL for **MSP north-metro** markets, persisted to Neon/Postgres and exported as static JSON for dashboarding.

## 🔥 Production scraper mode

This project now includes a hardened scraper runtime with:

- request throttling,
- exponential retry backoff (+ 429-sensitive delays),
- local response caching,
- local raw dataset storage,
- source fallback (pyRealtor → Anoka OpenData).

Set via `.env`:

```env
PRODUCTION_SCRAPER_MODE=true
SCRAPER_THROTTLE_SECONDS=2.0
SCRAPER_CACHE_TTL_MINUTES=60
SCRAPER_MAX_BACKOFF_SECONDS=30
SCRAPER_CACHE_DIR=.cache/scraper
LOCAL_DATASET_STORE_DIR=data/local_store
```

> “Zero 429 failures” in production means: avoid hard crashes and degraded runs from 429s by throttling + backoff + cache fallback. No public API can guarantee literal zero upstream 429 responses forever.

---

## ✅ Anoka County OpenData integration

- Layer metadata URL:
  - `https://gis.anokacountymn.gov/anoka_gis/rest/services/OpenData_Property/MapServer/1?f=json`
- Query URL:
  - `https://gis.anokacountymn.gov/anoka_gis/rest/services/OpenData_Property/MapServer/1/query`

Pipeline behavior:

1. Try pyRealtor first.
2. If pyRealtor returns empty, fallback to Anoka OpenData.
3. Normalize records into `{price, sqft, beds, baths}`.

---

## Security-first secret handling

```bash
cp .env.example .env
```
Set `DATABASE_URL` in `.env` and keep it out of git.

---

## Run and test locally

```bash
cd real-estate-agent
python -m unittest discover -s tests -v
python -m src.smoke
python src/runner.py
```

`src/smoke.py` now verifies pyRealtor path, Anoka path, and field metadata preview.

---

## Local machine raw-query script

```python
import requests

url = "https://gis.anokacountymn.gov/anoka_gis/rest/services/OpenData_Property/MapServer/1/query"
params = {
    'where': "CITY='ANDOVER'",
    'outFields': '*',
    'returnGeometry': 'false',
    'f': 'json',
    'resultRecordCount': 3
}

response = requests.get(url, params=params, timeout=30)
print(response.json())
```

Check for fields like `SALE_DATE`, `SALE_PRICE`, `ASSESSED_VALUE`, `TAX_YEAR`.

---

## City coverage

Andover, Anoka, Big Lake, Blaine, Champlin, Coon Rapids, Dayton, Elk River, Fridley, Ham Lake, Lino Lakes, Mounds View, Nowthen, Oak Grove, Ramsey, Spring Lake Park, Zimmerman.

---

## Export format

`frontend/data.json`:

```json
{
  "generated_at": "2026-04-09T00:00:00Z",
  "cities": ["Andover", "Blaine"],
  "series": {
    "Andover": [
      {
        "timestamp": "2026-04-09T00:00:00",
        "city": "Andover",
        "total_listings": 120,
        "avg_price": 410000,
        "avg_price_per_sqft": 210,
        "inventory_growth": 0.08,
        "status": "stable"
      }
    ]
  }
}
```
