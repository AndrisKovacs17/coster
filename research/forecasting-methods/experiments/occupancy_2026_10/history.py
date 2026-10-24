"""Shared helpers: find Coster's daily files and load the occupancy history (file 5).

Coster's data never lives in the repo. Every script takes the data folder as an argument,
or reads it from the COSTER_DATA_DIR environment variable.
"""

import glob
import os
import re
from pathlib import Path

import pandas as pd

SHORT = {
    "Cella Bassa": "Low",
    "Cella Media": "Med",
    "Cella Alta": "High",
    "Cella Media (L1000)": "MedW",
    "Cella Alta (L1000)": "HighW",
}
CLASSES = ["Low", "Med", "High", "MedW", "HighW"]
# The August re-layout ended on 21 Aug 2026. From this day the classes are stable.
LAYOUT_STABLE_FROM = pd.Timestamp("2026-08-22")
# Italian public holidays in 2026.
HOLIDAYS = pd.to_datetime(
    [
        "2026-01-01",
        "2026-01-06",
        "2026-04-05",
        "2026-04-06",
        "2026-04-25",
        "2026-05-01",
        "2026-06-02",
        "2026-08-15",
        "2026-11-01",
        "2026-12-08",
        "2026-12-25",
        "2026-12-26",
    ]
)


def data_dir(arg: str | None = None) -> Path:
    """The folder with Coster's files: the argument, else $COSTER_DATA_DIR."""
    d = arg or os.environ.get("COSTER_DATA_DIR")
    if not d:
        raise SystemExit("Pass the data folder or set COSTER_DATA_DIR (outside the repo).")
    return Path(d)


def find(folder: str | Path, key: str) -> str:
    """Newest file in folder whose name contains key, e.g. ' 5 - PU'."""
    files = sorted(glob.glob(os.path.join(str(folder), f"*{key}*.xlsx")))
    if not files:
        raise FileNotFoundError(f"no file with '{key}' in {folder}")
    return files[-1]


def file_date(path: str | Path) -> pd.Timestamp | None:
    """Date at the start of a Coster file name (YYYYMMDD), if any."""
    m = re.match(r"(\d{8})", os.path.basename(str(path)))
    return pd.Timestamp(m.group(1)) if m else None


def load_history(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Daily occupied and total cells per class (both areas added), one row per calendar day.

    A day missing for every class is interpolated from its neighbours (capacity carried forward).
    Days missing for only some classes stay NaN.
    """
    f5 = pd.read_excel(path)
    f5.columns = [c.strip() for c in f5.columns]
    f5["cls"] = f5["TP_CELLA_DESC"].str.strip().map(SHORT)
    g = f5.groupby(["DT_ANALISI", "cls"])[["TOTALI", "OCCUPATE"]].sum().unstack()
    occ = g["OCCUPATE"][CLASSES].astype(float)
    cap = g["TOTALI"][CLASSES].astype(float)
    idx = pd.date_range(occ.index.min(), occ.index.max())
    occ, cap = occ.reindex(idx), cap.reindex(idx)
    for d in idx[1:-1]:
        prev, nxt = d - pd.Timedelta(days=1), d + pd.Timedelta(days=1)
        if occ.loc[d].isna().all() and occ.loc[prev].notna().all() and occ.loc[nxt].notna().all():
            occ.loc[d] = (occ.loc[prev] + occ.loc[nxt]) / 2
            cap.loc[d] = cap.loc[prev]
    return occ, cap
