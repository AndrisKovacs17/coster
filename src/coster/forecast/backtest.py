"""Backtest helpers. A forecast for run date t may only use what was known at 06:00 on t."""

import pandas as pd


def as_of(versions: pd.DataFrame, t: str | pd.Timestamp, key: str = "order_id") -> pd.DataFrame:
    """Latest plan version of each order that was known at time `t`.

    `versions` needs a `version_created_at` column. Store every plan export
    with its receive time, so these versions build up from now on.
    """
    known = versions[versions["version_created_at"] <= pd.Timestamp(t)]
    latest = known.groupby(key)["version_created_at"].transform("max")
    return known[known["version_created_at"] == latest]
