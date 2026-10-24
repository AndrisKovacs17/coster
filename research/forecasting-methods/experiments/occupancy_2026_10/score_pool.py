"""Pool score_rows.csv of all scored pre-registrations (one folder per origin) and compute the
declared contrasts with a target-date cluster bootstrap.

Usage: python score_pool.py SCORES_DIR [OUT_CSV]
"""

import glob
import os
import sys

import numpy as np
import pandas as pd

d = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(d, "pooled_contrasts.csv")
fs = glob.glob(os.path.join(d, "*", "score_rows.csv"))
r = pd.concat(
    [pd.read_csv(f).assign(src=os.path.basename(os.path.dirname(f))) for f in fs], ignore_index=True
)
r = r[r.fg]
rows = []
for m1, m0 in [
    ("sim_f5", "ens"),
    ("sim_f4", "persist_f4"),
    ("sim_f4", "ens"),
    ("sim_f4_raw", "sim_f4"),
    ("ens", "persist"),
]:
    for hs, lab in ((range(2, 4), "2-3"), (range(4, 8), "4-7"), (range(2, 8), "2-7")):
        x = r[r.h.isin(list(hs))]
        k = ["origin_f5", "date", "cls"]
        p = (
            x[x.method == m1]
            .set_index(k)
            .ae.rename("a1")
            .to_frame()
            .join(x[x.method == m0].set_index(k).ae.rename("a0"), how="inner")
            .dropna()
        )
        if len(p) == 0:
            continue
        dates = p.index.get_level_values("date").unique().values
        rng = np.random.default_rng(0)
        bs = []
        for _ in range(2000):
            s = rng.choice(dates, len(dates))
            q = pd.concat([p.xs(t, level="date") for t in s])
            bs.append(q.a1.mean() / q.a0.mean())
        lo, hi = np.nanquantile(bs, [0.05, 0.95]) if len(dates) > 2 else (np.nan, np.nan)
        rows.append(
            dict(
                contrast=f"{m1}/{m0}",
                h=lab,
                n_rows=len(p),
                n_origins=p.index.get_level_values(0).nunique(),
                n_dates=len(dates),
                ratio=round(p.a1.mean() / p.a0.mean(), 3),
                ci90=(round(lo, 3), round(hi, 3)),
            )
        )
t = pd.DataFrame(rows)
t.to_csv(out, index=False)
print(t.to_string(index=False))
