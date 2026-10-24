"""SYNTHETIC input for testing score.py and run_daily.py (not real data).

Appends six fake days to the real File 5 and writes a fake File 4 dated three days later.
Usage: python make_synthetic_test.py DATA_DIR OUT_DIR   (OUT_DIR outside the repo)
"""

import os
import shutil
import sys

import numpy as np
import pandas as pd
import sim_lib as L


def main(D, OUT):
    os.makedirs(OUT, exist_ok=True)
    f5 = pd.read_excel(L.find(D, " 5 - PU"))
    rng = np.random.default_rng(123)
    last_day = f5.DT_ANALISI.max()
    cur = f5[f5.DT_ANALISI == last_day].copy()
    rows = []
    for d in pd.date_range(last_day + pd.Timedelta(days=1), periods=6):
        cur = cur.copy()
        cur["DT_ANALISI"] = d
        step = 0 if d.dayofweek == 6 else rng.normal(0, 8, len(cur)).round()
        cur["OCCUPATE"] = np.clip(cur.OCCUPATE + step, 0, cur.TOTALI).astype(int)
        cur["LIBERE"] = cur.TOTALI - cur.OCCUPATE
        cur["PERC_RIEMPIMENTO"] = (100 * cur.OCCUPATE / cur.TOTALI).round(2)
        rows.append(cur)
    new_end = rows[-1].DT_ANALISI.iloc[0] + pd.Timedelta(days=1)
    syn = pd.concat([f5] + rows, ignore_index=True)
    syn.to_excel(
        os.path.join(OUT, f"{new_end:%Y%m%d} - 5 - PU - ANALISI STORICA SATURAZIONE CELLE.xlsx"),
        index=False,
    )
    snap_day = last_day + pd.Timedelta(days=4)
    s4 = pd.read_excel(L.find(D, " 4 - PU"), sheet_name=0)
    s4["DT_ESTRAZIONE"] = snap_day
    s4.to_excel(
        os.path.join(OUT, f"{snap_day:%Y%m%d} - 4 - PU - SATURAZIONE CELLE MAGAZZINO.xlsx"),
        index=False,
    )
    shutil.copy(os.path.join(D, "coster_codes.json"), OUT)
    with open(os.path.join(OUT, "README_SYNTHETIC.txt"), "w") as f:
        f.write("SYNTHETIC FILES FOR TESTING ONLY. Values after the last real day are random.\n")
    print("written", OUT)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
