import numpy as np
import pandas as pd

from coster.common.schemas import CELL_CLASSES
from coster.forecast.allocation import allocate, remove_proportional
from coster.forecast.backtest import as_of
from coster.forecast.flow_balance import step
from coster.forecast.uncertainty import realise, simulate, summarise


def test_allocate_follows_cascade_and_held_back(cfg):
    free = {"Medium": 2, "High": 5, "Medium W1000": 10, "High W1000": 10}
    placed, rest = allocate(
        10, cfg["cascade"]["1200x800"], free, {"Medium W1000": 8, "High W1000": 10}
    )
    assert placed == {"Medium": 2, "High": 5, "Medium W1000": 2}
    assert rest == 1
    assert free["Medium W1000"] == 8


def test_remove_proportional():
    row = pd.Series([0, 10, 5, 0, 0], index=CELL_CLASSES)
    assert remove_proportional(row, 7).sum() == 8
    assert (remove_proportional(row, 7) >= 0).all()
    assert remove_proportional(row, 100).sum() == 0


def test_step_conserves_pallets(cfg, capacity, empty_state):
    s = empty_state.copy()
    s.loc["1200x800", "Medium"] = 240
    s2, no_cell = step(s, {"1200x800": 20}, {"1200x800": 5}, capacity, cfg["cascade"], {})
    assert s2.loc["1200x800"].sum() + no_cell == 240 + 20 - 5
    assert (s2.sum(axis=0) <= capacity).all()


def test_full_classes_give_no_cell(cfg, capacity, empty_state):
    s = empty_state.copy()
    s.loc["1200x800", "Medium"] = 248
    s.loc["2200x800", "High"] = 186
    held = {"Medium W1000": 144, "High W1000": 192}
    _, no_cell = step(s, {"1200x800": 10}, {}, capacity, cfg["cascade"], held)
    assert no_cell == 10


def test_realise_never_creates_pallets():
    out = realise(np.array([10, 10, 10, 0]), 0.9, np.random.default_rng(1))
    assert out.sum() <= 30


def test_simulate_and_summarise(cfg, capacity, empty_state):
    s = empty_state.copy()
    s.loc["1200x800", "Medium"] = 230
    paths, no_cell = simulate(
        s,
        {"1200x800": np.full(14, 6)},
        {"1200x800": np.full(14, 4)},
        capacity,
        cfg["cascade"],
        {},
        0.9,
        100,
        np.random.default_rng(42),
    )
    assert paths.shape == (100, 14, 5) and no_cell.shape == (100, 14)
    res = summarise(paths, capacity, 0.9)
    assert (res["lo"] <= res["hi"]).all()
    assert (np.diff(res["p_critical_by"][:, CELL_CLASSES.index("Medium")]) >= 0).all()


def test_as_of_never_returns_future_versions():
    v = pd.DataFrame(
        {
            "order_id": [1, 1, 2],
            "version_created_at": pd.to_datetime(["2026-10-01", "2026-10-05", "2026-10-06"]),
            "planned_end": pd.to_datetime(["2026-10-10", "2026-10-12", "2026-10-11"]),
        }
    )
    got = as_of(v, "2026-10-04")
    assert list(got["planned_end"]) == [pd.Timestamp("2026-10-10")]
