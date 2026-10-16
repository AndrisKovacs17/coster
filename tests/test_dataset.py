import numpy as np
import pandas as pd
import pytest
from pandera.errors import SchemaError

from coster.common.schemas import CELL_CLASSES, daily_dataset_schema, forecast_schema
from coster.dataset.build import build_daily_dataset
from coster.dataset.flows import daily_flows
from coster.dataset.mock import mock_daily_dataset
from coster.dataset.windows import snapshot_date
from coster.forecast.baselines import persistence


def test_daily_flows_close_the_balance():
    prev = pd.DataFrame({"udc_id": ["a", "b", "c"], "cell_class": ["Medium", "High", "Low"]})
    curr = pd.DataFrame(
        {"udc_id": ["a", "c", "d", "e"], "cell_class": ["High", "Low", "Medium", "Medium"]}
    )
    f = daily_flows(prev, curr)
    occ_p = prev["cell_class"].value_counts().reindex(CELL_CLASSES, fill_value=0)
    occ_c = curr["cell_class"].value_counts().reindex(CELL_CLASSES, fill_value=0)
    balance = occ_p + f["inbound_actual"] - f["outbound_actual"] + f["internal_transfer"]
    assert (balance == occ_c).all()


def test_snapshot_window_edges():
    ts = pd.Series(
        pd.to_datetime(
            ["2026-10-15 06:00", "2026-10-15 23:00", "2026-10-16 05:59", "2026-10-16 06:00"]
        )
    )
    assert snapshot_date(ts).dt.strftime("%m-%d").tolist() == ["10-16", "10-16", "10-16", "10-17"]


def test_build_daily_dataset_from_snapshots(capacity):
    snaps = pd.DataFrame(
        {
            "snapshot_date": pd.to_datetime(["2026-10-14"] * 3 + ["2026-10-15"] * 4),
            "udc_id": ["a", "b", "c", "a", "c", "d", "e"],
            "cell_class": ["Medium", "High", "Low", "High", "Low", "Medium", "Medium"],
        }
    )
    d = build_daily_dataset(snaps, capacity)
    day2 = d[d["date"] == "2026-10-15"].set_index("cell_class")
    assert day2.loc["Medium", "occupied"] == 2
    assert day2.loc["Medium", "inbound_actual"] == 2
    assert day2.loc["High", "internal_transfer"] == 1


def test_mock_dataset_and_persistence_match_the_contracts(cfg):
    daily = mock_daily_dataset(cfg, end="2026-10-15", days=30)
    daily_dataset_schema.validate(daily)
    fc = persistence(daily, "2026-10-15", 14)
    forecast_schema.validate(fc)
    assert len(fc) == 5 * 14


def test_schema_rejects_broken_rows(cfg):
    daily = mock_daily_dataset(cfg, end="2026-10-15", days=2)
    bad = daily.copy()
    bad.loc[0, "free"] = bad.loc[0, "free"] + 1
    with pytest.raises(SchemaError):
        daily_dataset_schema.validate(bad)


def test_persistence_ignores_future_data(cfg):
    """Leakage guard: data after the run date must not change the forecast."""
    daily = mock_daily_dataset(cfg, end="2026-10-20", days=30)
    cut = daily[daily["date"] <= "2026-10-15"]
    a = persistence(daily, "2026-10-15")
    b = persistence(cut, "2026-10-15")
    assert np.allclose(a["fill_ratio_pred"], b["fill_ratio_pred"])
