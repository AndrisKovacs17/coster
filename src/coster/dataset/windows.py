"""Map event timestamps to the daily snapshot window."""

import pandas as pd


def snapshot_date(ts: pd.Series, hour: int = 6) -> pd.Series:
    """Date of the first snapshot that sees an event at `ts`.

    The row for date d covers events from 06:00 on d-1 up to (not including)
    06:00 on d. So a shipment during day d shows up in the snapshot of d+1.
    """
    return (ts - pd.Timedelta(hours=hour)).dt.normalize() + pd.Timedelta(days=1)
