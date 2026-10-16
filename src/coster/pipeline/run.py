"""Run the daily pipeline once.

    uv run python -m coster.pipeline.run --mock

`--mock` builds a mock daily_dataset in the agreed schema, so the whole chain
runs before Coster's data arrives. Real-data ingest follows with the first
sample files.
"""

import argparse
import logging

import pandas as pd

from coster.common.config import load_config
from coster.common.io import read_table, table_path, write_table
from coster.common.schemas import forecast_schema
from coster.dataset.mock import mock_daily_dataset
from coster.forecast.baselines import persistence

log = logging.getLogger("coster.pipeline")


def run(cfg: dict, mock: bool, run_date: pd.Timestamp) -> None:
    if not mock:
        raise SystemExit("Real-data ingest is not implemented yet. Use --mock for now.")

    daily = mock_daily_dataset(cfg, end=run_date, seed=cfg["forecast"]["seed"])
    log.info("dataset: %d rows up to %s", len(daily), daily["date"].max().date())
    write_table(daily, cfg, "daily_dataset")

    method = cfg["forecast"]["method"]
    if method != "persistence":
        raise SystemExit(f"Forecast method '{method}' needs plan data. Use persistence for now.")
    fc = persistence(daily, run_date, cfg["forecast"]["horizon_days"])

    # The forecast table keeps all past runs. Replace only this run's rows.
    if table_path(cfg, "forecast").exists():
        old = read_table(cfg, "forecast")
        fc = pd.concat([old[old["run_date"] != fc["run_date"].iloc[0]], fc], ignore_index=True)
    write_table(forecast_schema.validate(fc), cfg, "forecast")
    log.info("forecast: %d rows, method %s", len(fc), method)
    log.info("alerts: not implemented yet (Group 2)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument("--mock", action="store_true", help="use mock data")
    parser.add_argument("--run-date", default=None, help="YYYY-MM-DD, default today")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run_date = pd.Timestamp(args.run_date or pd.Timestamp.today()).normalize()
    run(load_config(args.config), args.mock, run_date)


if __name__ == "__main__":
    main()
