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
Deterministic ETL for **MSP north-metro** listings, persisted to Neon/Postgres and exported to a static dashboard payload.

## Security-first secret handling (recommended)

### Local
1. Copy template:
   ```bash
   cp .env.example .env
   ```
2. Put your real `DATABASE_URL` in `.env`.
3. `.env` is ignored by git, so it will not be committed.

### GitHub Actions
- Store `DATABASE_URL` in **GitHub Actions Secrets** (`Settings → Secrets and variables → Actions`).
- Workflow consumes `${{ secrets.DATABASE_URL }}` directly.
- Never commit connection strings to repo files.

> If a real connection string was ever pasted in chat/history, rotate credentials in Neon.

---

## Scope: Cities covered

Current configured city-level snapshots include:

- Andover
- Anoka
- Big Lake
- Blaine
- Champlin
- Coon Rapids
- Dayton
- Elk River
- Fridley
- Ham Lake
- Lino Lakes
- Mounds View
- Nowthen
- Oak Grove
- Ramsey
- Spring Lake Park
- Zimmerman

---

## Run locally

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
`src/runner.py` exits safely if `DATABASE_URL` is missing.

---

## Data flow

1. Fetch Realtor.com public-facing search pages (no browser automation).
2. Normalize rows into `{price, sqft, beds, baths}`.
3. Compute city-level metrics and deterministic signals.
4. Insert one snapshot per city.
5. Export `frontend/data.json` with city-level series.

---

## JSON export contract (`frontend/data.json`)

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

---

## CI schedule

Workflow: `.github/workflows/pipeline.yml`

- every 4 hours
- manual dispatch enabled
- runs `python src/runner.py`
- commits updated `frontend/data.json` when changed


# Real Estate Market Signal Agent (MVP)

A scheduled, deterministic market-monitoring system for the **Minneapolis–Saint Paul (MSP) North Metro** housing segment. The project treats residential listings as a high-frequency proxy for local housing market tightness, pricing pressure, and short-run regime shifts.

Rather than building a conversational interface, this repository implements a compact empirical pipeline:

1. collect listing microdata,
2. aggregate to market-level moments,
3. infer interpretable state signals,
4. persist a panel of snapshots,
5. publish a machine-readable time series for a static dashboard.

---

## 1) Research Motivation and Economic Framing

Housing markets adjust slowly in quantities (new supply, completions) and quickly in expectations (seller reservation prices, buyer urgency). In this context, listing-level observables provide practical reduced-form indicators:

- **Inventory level (`total_listings`)** as a near-term measure of market depth.
- **Average and median list prices** as noisy but useful price-level signals.
- **Average list price per square foot** as a scale-adjusted valuation proxy.
- **Inventory growth** as a directional stress indicator for market slack/tightness.

The objective is not structural identification; it is robust, low-latency monitoring for directional decision support.

---

## 2) System Overview

```text
GitHub Actions (every 4h)
        ↓
Data Fetcher (Realtor.com public-facing responses)
        ↓
Transformer / Signal Engine
        ↓
Postgres (Neon)
        ↓
JSON Exporter
        ↓
GitHub Pages (Chart.js dashboard)
```

### Scope constraint (strict)
Only MSP north-metro area coverage is used in the fetch stage:

- Blaine
- Coon Rapids
- Andover
- Ham Lake
- Anoka
- Champlin
- Dayton
- Lino Lakes
- Fridley
- Mounds View
- Spring Lake Park

---

## 3) Repository Layout

```text
real-estate-agent/
├── .github/workflows/pipeline.yml
├── src/
│   ├── config.py
│   ├── fetcher.py
│   ├── transformer.py
│   ├── signals.py
│   ├── db.py
│   ├── exporter.py
│   └── runner.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── data.json
├── sql/
│   └── schema.sql
├── requirements.txt
└── README.md
```

---

## 4) Data-Generating Process (DGP) and ETL Logic

### 4.1 Fetcher (`src/fetcher.py`)

- Pulls public-facing Realtor.com search responses (lightweight HTTP only).
- No Selenium, no browser automation.
- Retry policy: **3 attempts**.
- Request timeout: **10 seconds** (configurable).
- Failure policy: **never propagate fatal errors; return `[]`**.

Normalized row schema:

```json
{
  "price": 425000,
  "sqft": 2140,
  "beds": 4,
  "baths": 2.5
}
```

### 4.2 Transformer (`src/transformer.py`)

After type/validity filtering, the pipeline computes:

- `total_listings`
- `avg_price`
- `median_price`
- `avg_price_per_sqft`

Safe arithmetic is used for per-square-foot calculations (division-by-zero guarded).

### 4.3 Signal Engine (`src/signals.py`)

Deterministic state logic (non-LLM):

\[
\text{inventory\_growth}_t = \frac{L_t - L_{t-1}}{L_{t-1}}
\]

Status regime mapping:

- `inventory_growth > 0.15` → `expanding`
- `inventory_growth < -0.10` → `tightening`
- otherwise → `stable`

Additional diagnostics:

- `vs_7_day_avg = L_t / \bar{L}_{t-7:t-1}`
- `volatility = \sigma(L)` over recent totals

Interpretation: these are reduced-form monitoring statistics, not causal treatment effects.

---

## 5) Persistence Layer (Neon/Postgres)

Primary table: `listing_snapshots`

```sql
CREATE TABLE listing_snapshots (
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

CREATE INDEX idx_city_time ON listing_snapshots(city, timestamp);
```

The pipeline writes one snapshot per successful run and reads recent history for signal computation and frontend export.

---

## 6) Export Contract for Frontend

Exporter writes `frontend/data.json` as a time-ordered series of up to 30 observations:

```json
[
  {
    "timestamp": "2026-04-08T20:00:00",
    "total_listings": 120,
    "avg_price": 350000,
    "avg_price_per_sqft": 210,
    "inventory_growth": 0.12,
    "status": "expanding"
  }
]
```

This contract is intentionally narrow to reduce dashboard coupling and deployment fragility.

---

## 7) Automation and Idempotent Orchestration

### GitHub Actions (`.github/workflows/pipeline.yml`)

- Cron schedule: every 4 hours (`0 */4 * * *`)
- Also supports manual dispatch
- Job steps:
  1. checkout
  2. Python 3.11 setup
  3. dependency install
  4. run `python src/runner.py`
  5. commit `frontend/data.json` if changed

### Runner guarantees (`src/runner.py`)

Execution sequence:

1. `init_db()`
2. fetch listings
3. if empty, exit safely
4. compute metrics
5. compute signals
6. insert snapshot
7. export JSON

Operational guarantees:

- safe exit on empty data
- safe exit on handled failures
- stage-level logging for observability
- no hard dependency on optional insight generation

---

## 8) Local Setup

From `real-estate-agent/`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Environment variables:

```bash
export DATABASE_URL='postgresql://<user>:<password>@<host>/<db>?sslmode=require'
export STATE='MN'                         # optional (default: MN)
export EXPORT_PATH='frontend/data.json'   # optional
export REQUEST_TIMEOUT_SECONDS='10'       # optional
export REQUEST_RETRIES='3'                # optional
```

Run once:

```bash
python src/runner.py
```

---

## 9) Reliability Design (Why this survives production drift)

- **Fetcher resilience:** bounded retries + timeout + empty fallback.
- **Schema hygiene:** explicit type checks before aggregation.
- **Failure containment:** runner catches and logs runtime failures, then exits without crashing CI.
- **Workflow tolerance:** JSON commit step is non-fatal if nothing changed.

This design prefers continuity of operation over brittle completeness.

---

## 10) Frontend Notes

Dashboard is intentionally minimal:

- Chart.js only
- no framework runtime
- three line charts: listings, avg price, avg price/sqft
- labels: city and last update

Suitable for GitHub Pages static hosting.

---

## 11) Non-Goals and Boundaries

This system is **not**:

- a chatbot,
- a full MLS ingestion platform,
- a structural econometric model,
- or a heavy scraper requiring browser automation.

It is a lightweight market signal engine designed for dependable periodic monitoring.

---

## 12) Optional Insight Layer (Non-Core)

An optional LLM interpreter may be attached downstream using:

```json
{
  "metrics": {"...": "..."},
  "trend_last_7_days": ["..."]
}
```

with output constrained to short narrative interpretation. It must not generate or alter numeric metrics.


# Real Estate Market Signal Agent (MVP)

Lightweight ETL + deterministic signal engine for the **MSP North Metro** market using Realtor.com public-facing responses.

## What it does

- Fetches listing data (MSP north metro cities only).
- Computes inventory and price metrics.
- Computes deterministic market signals (growth/state + additional indicators).
- Stores snapshots in Postgres (Neon-compatible).
- Exports the last 30 snapshots to `frontend/data.json`.
- Renders a static Chart.js dashboard.
- Runs every 4 hours via GitHub Actions.

## Project structure

```text
real-estate-agent/
├── .github/workflows/pipeline.yml
├── src/
│   ├── config.py
│   ├── fetcher.py
│   ├── transformer.py
│   ├── signals.py
│   ├── db.py
│   ├── exporter.py
│   └── runner.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── data.json
├── sql/
│   └── schema.sql
├── requirements.txt
└── README.md
```

## Setup

1. Create a Python 3.11 virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set environment variables:

```bash
export DATABASE_URL='postgresql://<user>:<password>@<host>/<db>?sslmode=require'
export STATE='MN'                  # optional, defaults to MN
export EXPORT_PATH='frontend/data.json'  # optional
```

4. Run locally:

```bash
python src/runner.py
```

## Reliability behavior

- Fetch retries 3x with timeout (10s default).
- Failures return empty list and do not crash pipeline.
- Runner exits safely (code 0) on empty fetch or any handled exception.
- Basic schema/type validation is performed before metrics.
- Logging is emitted at each major stage.

## Signal definitions

- `inventory_growth = (today_total - yesterday_total) / yesterday_total`
- Status logic:
  - `> 0.15` => `expanding`
  - `< -0.10` => `tightening`
  - otherwise => `stable`
- Additional diagnostics:
  - `vs_7_day_avg`
  - `volatility` (population std dev of total listings)

## GitHub Actions

Workflow: `.github/workflows/pipeline.yml`

- Triggered every 4 hours and manually.
- Installs dependencies and runs `python src/runner.py`.
- Commits `frontend/data.json` when changed.
- No-op commit failures are tolerated.

## Notes

- This project is a market signal pipeline, not a chatbot.
- LLM insight generation can be added later, but is intentionally not required for core operation.
