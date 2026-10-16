"""Read and write the shared tables as parquet files in data/processed."""

from pathlib import Path
from typing import Any

import pandas as pd

from coster.common.config import resolve


def table_path(cfg: dict[str, Any], name: str) -> Path:
    return resolve(cfg["paths"]["processed"]) / f"{name}.parquet"


def write_table(df: pd.DataFrame, cfg: dict[str, Any], name: str) -> Path:
    path = table_path(cfg, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def read_table(cfg: dict[str, Any], name: str) -> pd.DataFrame:
    return pd.read_parquet(table_path(cfg, name))
