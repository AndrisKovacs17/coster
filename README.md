# coster

# Architecture (draft v0.1)

## Goal
A daily pipeline that forecasts the fill ratio of the warehouse per cell class for days +1 to +14, raises warning/critical alerts, and shows everything on a dashboard.

## Decision: modular monolith
One repo, one Python package, separate modules with clear interfaces. Modules talk to each other through **data tables**, not network calls.

Why not microservices (for now):
- The workload is a **daily batch job**, not request-driven traffic.
- 4 people, a few weeks: service boundaries, deployment, versioning and networking would cost more time than they save.
- Everything runs locally and in CI with one command, which makes the demo reliable.

## Modules and data flow

```
ingest  ->  dataset  ->  forecast  ->  alerts
                |            |            |
                +------------+------------+--> dashboard (reads outputs)
```

| Module | Responsibility |
|---|---|
| `ingest` | Loaders and validation for inbound, warehouse status, outbound data; cell class mapping |
| `dataset` | Builds the daily dataset per cell class; consistency checks (yesterday + in - out ~ today) |
| `forecast` | Persistence baseline, flow balance, ML model, backtesting |
| `alerts` | Warning/critical thresholds, email / Teams notifications |
| `dashboard` | Streamlit app: fill ratio per cell class, 14-day forecast, alert levels |
| `common` | Schemas, config loading, I/O helpers |

(Adapt folder names to what is already in the repo.)

## Contracts between modules
Two tables are the interfaces. Schemas live in `common/schemas.py` (pandera) and are changed only via PR reviewed by both groups.

**daily_dataset** (one row per date and cell class):
`date, cell_class, capacity, occupied, free, fill_ratio, inbound_planned, inbound_actual, outbound_planned, outbound_actual, qc_hold, internal_transfer`

**forecast** (one row per run, cell class and horizon day):
`run_date, cell_class, forecast_date, horizon_day (1-14), fill_ratio_pred, method`

Storage: parquet files in `data/processed/` (can move to DuckDB/SQLite later without changing the schemas).
Thresholds and paths live in `config/config.yaml`.

## Runtime
- `python -m pipeline.run` runs ingest -> dataset -> forecast -> alerts once.
- Scheduled daily (cron or GitHub Actions).
- Dashboard reads the latest outputs.
- Until real data arrives, a mock data generator produces `daily_dataset` in the agreed schema.

## Tech stack
Python 3.11+, pandas, pandera, scikit-learn / LightGBM, Streamlit, pytest, ruff, pre-commit.

## When to split into services
Only if there is a concrete need, for example the dashboard must request forecasts on demand or another system must integrate with ours. Then wrap `forecast` in a FastAPI endpoint. Because modules already communicate through fixed contracts, that split stays cheap.

## Working agreements
- One branch per feature, PR with at least one review.
- Schema changes need a PR that both groups approve.
- Tests for loaders and for the flow-balance logic; CI runs tests and linting.
