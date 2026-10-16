"""Mock daily_dataset in the agreed schema, until Coster's data arrives.

This is a test fixture for the pipeline, not a model of Coster's warehouse.
Results on mock data only show that the code runs.
"""

from typing import Any

import numpy as np
import pandas as pd

from coster.common.schemas import CELL_CLASSES, daily_dataset_schema


def mock_daily_dataset(
    cfg: dict[str, Any], end: str | pd.Timestamp, days: int = 60, seed: int = 0
) -> pd.DataFrame:
    """Random daily flows per class, kept inside capacity."""
    rng = np.random.default_rng(seed)
    cap = pd.Series(cfg["capacity_default"]).reindex(CELL_CLASSES)
    dates = pd.date_range(end=pd.Timestamp(end).normalize(), periods=days, freq="D")
    occupied = (cap * rng.uniform(0.6, 0.85, len(cap))).round().astype(int)
    rows = []
    for date in dates:
        mean_flow = (cap * 0.04).to_numpy()
        inbound = rng.poisson(mean_flow)
        outbound = rng.poisson(mean_flow)
        new = np.clip(occupied.to_numpy() + inbound - outbound, 0, cap.to_numpy())
        outbound = occupied.to_numpy() + inbound - new
        occupied = pd.Series(new, index=CELL_CLASSES)
        rows.append(
            pd.DataFrame(
                {
                    "date": date,
                    "cell_class": CELL_CLASSES,
                    "capacity": cap.to_numpy(dtype=int),
                    "occupied": occupied.to_numpy(dtype=int),
                    "free": (cap - occupied).to_numpy(dtype=int),
                    "fill_ratio": (occupied / cap).to_numpy(dtype=float),
                    "inbound_planned": inbound.astype(float),
                    "inbound_actual": inbound.astype(float),
                    "outbound_planned": outbound.astype(float),
                    "outbound_actual": outbound.astype(float),
                    "qc_hold": np.nan,
                    "internal_transfer": 0.0,
                }
            )
        )
    out = pd.concat(rows, ignore_index=True)
    out["date"] = out["date"].astype("datetime64[ns]")
    return daily_dataset_schema.validate(out)
