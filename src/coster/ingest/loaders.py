"""Shared helpers for the per-file loaders.

The first loaders to write are: cell master, load-unit master, snapshot,
assembly plan and moulding plan. Each one reads with `read_excel_as_text`,
renames with `apply_column_map`, casts its columns and validates with its
own pandera schema.
"""

from pathlib import Path

import pandas as pd

from coster.ingest.columns import COLUMN_MAPS


def read_excel_as_text(path: str | Path, sheet: str | int = 0) -> pd.DataFrame:
    """Read an Excel sheet with every cell as text. Excel guesses types badly,
    for example IDs with leading zeros or dates, so we cast on purpose later."""
    return pd.read_excel(path, sheet_name=sheet, dtype=str)


def apply_column_map(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Rename Coster's columns to ours for one source file."""
    return df.rename(columns=COLUMN_MAPS.get(source, {}))
