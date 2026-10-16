"""Persistence: every forecast day equals the last snapshot. The baseline for every other rung."""

import pandas as pd

from coster.common.schemas import forecast_schema


def persistence(
    daily: pd.DataFrame, run_date: str | pd.Timestamp, horizon_days: int = 14
) -> pd.DataFrame:
    """Forecast rows for one run, using only data up to `run_date`."""
    run_date = pd.Timestamp(run_date).normalize()
    known = daily[daily["date"] <= run_date]
    last = known[known["date"] == known["date"].max()]
    rows = [
        {
            "run_date": run_date,
            "cell_class": r.cell_class,
            "forecast_date": run_date + pd.Timedelta(days=h),
            "horizon_day": h,
            "fill_ratio_pred": float(r.fill_ratio),
            "method": "persistence",
        }
        for r in last.itertuples()
        for h in range(1, horizon_days + 1)
    ]
    out = pd.DataFrame(rows)
    out[["run_date", "forecast_date"]] = out[["run_date", "forecast_date"]].astype("datetime64[ns]")
    return forecast_schema.validate(out)
