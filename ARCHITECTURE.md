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

All modules live in one package, `src/coster/`.

## Repository layout

```
coster/
├── ARCHITECTURE.md         # this file
├── README.md               # quickstart
├── pyproject.toml          # dependencies (uv), ruff and pytest settings
├── uv.lock                 # pinned versions
├── config/config.yaml      # every number and rule: capacities, cascade, thresholds, paths
├── src/coster/
│   ├── common/             # schemas.py (the two contracts), config.py, io.py
│   ├── ingest/             # loaders for Coster's Excel exports
│   ├── dataset/            # daily_dataset: snapshots -> flows per class, mock data
│   ├── forecast/           # persistence, allocation cascade, flow balance, Monte Carlo, backtest
│   ├── alerts/             # Group 2
│   ├── dashboard/          # Group 2, Streamlit
│   └── pipeline/run.py     # the daily run
├── tests/                  # one test per function, tiny hand-made tables, never Coster data
├── data/                   # git-ignored: raw/ (Coster files), interim/, processed/
├── notebooks/              # exploration only, outputs stripped on commit
├── docs/
│   ├── group1-data-forecasting/   # Group 1 plan
│   └── group2-ui-alerts/          # Group 2 plan
└── research/               # papers, library checks, experiments, one folder per topic
```

`research/` holds everything we read or test that informs a decision. Each topic folder has an
index of its sources. Shared BibTeX is in `research/references.bib`. See `research/README.md`.

## Contracts between modules
Two tables are the interfaces. Schemas live in `src/coster/common/schemas.py` (pandera) and are changed only via PR reviewed by both groups.

**daily_dataset** (one row per date and cell class):
`date, cell_class, capacity, occupied, free, fill_ratio, inbound_planned, inbound_actual, outbound_planned, outbound_actual, qc_hold, internal_transfer`

**forecast** (one row per run, cell class and horizon day):
`run_date, cell_class, forecast_date, horizon_day (1-14), fill_ratio_pred, method`

Storage: parquet files in `data/processed/` (can move to DuckDB/SQLite later without changing the schemas).
Thresholds and paths live in `config/config.yaml`.

## Runtime
- `uv run python -m coster.pipeline.run` runs ingest -> dataset -> forecast -> alerts once.
- Scheduled daily (cron or GitHub Actions).
- Dashboard reads the latest outputs.
- Until real data arrives, `--mock` builds a mock `daily_dataset` in the agreed schema.

## Tech stack
Python 3.11+, uv, pandas, pandera, pyarrow, openpyxl, scikit-learn / LightGBM, Streamlit, pytest, ruff, pre-commit.

## When to split into services
Only if there is a concrete need, for example the dashboard must request forecasts on demand or another system must integrate with ours. Then wrap `forecast` in a FastAPI endpoint. Because modules already communicate through fixed contracts, that split stays cheap.

## Working agreements
- One branch per feature, PR with at least one review.
- Schema changes need a PR that both groups approve.
- Tests for loaders and for the flow-balance logic; CI runs tests and linting.
- Coster's data never goes into git. `data/` and Excel files are git-ignored.
- Sources and experiments behind a decision go in `research/`.
