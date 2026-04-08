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
