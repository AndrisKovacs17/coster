# coster

Plant virtualisation prototype for Coster's automated warehouse (Industrial AI Challenge 2026,
Team 1). A daily pipeline forecasts the fill ratio of each cell class for days +1 to +14, raises
warning and critical alerts, and shows everything on a dashboard.

- How it is built and why: [ARCHITECTURE.md](ARCHITECTURE.md)
- Group plans: [docs/](docs/)
- Papers, library checks and experiments: [research/](research/)

## Quickstart

Install [uv](https://docs.astral.sh/uv/), then:

```bash
uv sync --all-groups                      # create .venv and install everything
uv run pytest                             # run the tests
uv run python -m coster.pipeline.run --mock   # run the pipeline on mock data
uv run pre-commit install                 # lint and format before every commit
```

The dashboard placeholder:

```bash
uv run --extra dashboard streamlit run src/coster/dashboard/app.py
```

## Data

Coster's data is confidential and never goes into git. Put the exports in `data/raw/`, which is
git-ignored. Notebook outputs are stripped on commit, because they can contain data.

## Status

| Part | State |
|---|---|
| Contract schemas (`daily_dataset`, `forecast`) | Done. Changes need a PR approved by both groups. |
| Mock pipeline | Runs end to end with the persistence baseline |
| Snapshot flows, allocation cascade, flow balance, Monte Carlo, as-of filter | Done and tested on toy data |
| Loaders for Coster's files | Waiting for the first sample files |
| Alerts, dashboard | Group 2 |
