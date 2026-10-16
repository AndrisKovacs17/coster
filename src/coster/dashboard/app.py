"""Placeholder dashboard: shows the latest forecast run as a table.

Group 2 replaces this with the real views (overview, class detail, alerts, data status).
"""

import streamlit as st

from coster.common.config import load_config
from coster.common.io import read_table, table_path

cfg = load_config()
st.title("Coster AW: fill ratio forecast")

if not table_path(cfg, "forecast").exists():
    st.info("No forecast yet. Run: uv run python -m coster.pipeline.run --mock")
else:
    fc = read_table(cfg, "forecast")
    latest = fc[fc["run_date"] == fc["run_date"].max()]
    st.caption(f"Run date: {latest['run_date'].max():%Y-%m-%d}")
    st.dataframe(
        latest.pivot(index="forecast_date", columns="cell_class", values="fill_ratio_pred")
    )
