"""The two contract tables between the groups.

Change these only through a PR that both groups approve (ARCHITECTURE.md).
"""

import pandera.pandas as pa

CELL_CLASSES = ["Low", "Medium", "High", "Medium W1000", "High W1000"]

_FLOW_COLUMNS = [
    "inbound_planned",
    "inbound_actual",
    "outbound_planned",
    "outbound_actual",
    "qc_hold",
    "internal_transfer",
]

# One row per date and cell class. `date` is the date of the 06:00 snapshot.
# Flows cover 06:00 on date-1 up to 06:00 on date.
daily_dataset_schema = pa.DataFrameSchema(
    {
        "date": pa.Column("datetime64[ns]"),
        "cell_class": pa.Column(str, pa.Check.isin(CELL_CLASSES)),
        "capacity": pa.Column(int, pa.Check.ge(0)),
        "occupied": pa.Column(int, pa.Check.ge(0)),
        "free": pa.Column(int, pa.Check.ge(0)),
        "fill_ratio": pa.Column(float, pa.Check.in_range(0, 1)),
        **{col: pa.Column(float, nullable=True) for col in _FLOW_COLUMNS},
    },
    checks=pa.Check(lambda df: df["occupied"] + df["free"] == df["capacity"]),
    unique=["date", "cell_class"],
    strict=True,
)

# One row per run, cell class and horizon day. Keeps all past runs.
forecast_schema = pa.DataFrameSchema(
    {
        "run_date": pa.Column("datetime64[ns]"),
        "cell_class": pa.Column(str, pa.Check.isin(CELL_CLASSES)),
        "forecast_date": pa.Column("datetime64[ns]"),
        "horizon_day": pa.Column(int, pa.Check.in_range(1, 14)),
        "fill_ratio_pred": pa.Column(float, pa.Check.in_range(0, 1)),
        "method": pa.Column(str),
    },
    unique=["run_date", "cell_class", "horizon_day"],
    strict=True,
)
