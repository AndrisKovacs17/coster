import pandas as pd

from coster.common.io import read_table
from coster.pipeline.run import run


def test_mock_pipeline_runs_end_to_end(cfg):
    run(cfg, mock=True, run_date=pd.Timestamp("2026-10-15"))
    run(cfg, mock=True, run_date=pd.Timestamp("2026-10-16"))
    fc = read_table(cfg, "forecast")
    assert fc["run_date"].nunique() == 2
    assert len(fc) == 2 * 5 * 14
