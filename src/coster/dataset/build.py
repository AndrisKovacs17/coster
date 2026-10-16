"""Build daily_dataset from a series of 06:00 snapshots."""

import numpy as np
import pandas as pd

from coster.common.schemas import CELL_CLASSES, daily_dataset_schema
from coster.dataset.flows import daily_flows


def build_daily_dataset(snapshots: pd.DataFrame, capacity: pd.Series) -> pd.DataFrame:
    """One row per snapshot date and cell class.

    `snapshots` has one row per occupied cell and day, with the columns
    `snapshot_date`, `udc_id` and `cell_class`. `capacity` holds the cells in
    service per class. Planned flows are filled in later from the plans.
    Quarantine stays empty, because Coster asked us to skip QC.
    """
    capacity = capacity.reindex(CELL_CLASSES)
    rows = []
    prev = None
    for date, snap in snapshots.groupby("snapshot_date", sort=True):
        occupied = snap["cell_class"].value_counts().reindex(CELL_CLASSES, fill_value=0)
        if prev is None:
            flows = pd.DataFrame(
                np.nan,
                index=CELL_CLASSES,
                columns=["inbound_actual", "outbound_actual", "internal_transfer"],
            )
        else:
            flows = daily_flows(prev, snap).astype(float)
        rows.append(
            pd.DataFrame(
                {
                    "date": pd.Timestamp(date),
                    "cell_class": CELL_CLASSES,
                    "capacity": capacity.to_numpy(dtype=int),
                    "occupied": occupied.to_numpy(dtype=int),
                    "free": (capacity - occupied).to_numpy(dtype=int),
                    "fill_ratio": (occupied / capacity).to_numpy(dtype=float),
                    "inbound_planned": np.nan,
                    "inbound_actual": flows["inbound_actual"].to_numpy(),
                    "outbound_planned": np.nan,
                    "outbound_actual": flows["outbound_actual"].to_numpy(),
                    "qc_hold": np.nan,
                    "internal_transfer": flows["internal_transfer"].to_numpy(),
                }
            )
        )
        prev = snap
    out = pd.concat(rows, ignore_index=True)
    out["date"] = out["date"].astype("datetime64[ns]")
    return daily_dataset_schema.validate(out)
