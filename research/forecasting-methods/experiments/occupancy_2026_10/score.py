"""Score pre-registered forecasts against newly arrived daily files.

Usage: python score.py --prereg PREREG_CSV --f5 FILE5_XLSX [--f4 FILE4_XLSX] [--f2 FILE2_XLSX]
                       [--out DIR_OUTSIDE_THE_REPO] [--allow-hash-mismatch]
Outputs: score_rows.csv (joined rows), score_by_method_h.csv, score_by_method_bucket.csv,
         score_by_cls.csv, score_contrasts.csv, score_scenarios.csv, score_diagnostics.json
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd
import sim_lib as L

ap = argparse.ArgumentParser()
ap.add_argument("--prereg", required=True)
ap.add_argument("--f5", required=True)
ap.add_argument("--f4")
ap.add_argument("--f2")
ap.add_argument("--out", default="score_out")
ap.add_argument("--allow-hash-mismatch", action="store_true")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
diag = {}
# 1) integrity
h = hashlib.sha256(open(a.prereg, "rb").read()).hexdigest()
ref = open(a.prereg + ".sha256").read().split()[0] if os.path.exists(a.prereg + ".sha256") else None
diag["sha256_ok"] = h == ref
diag["sha256"] = h
if not diag["sha256_ok"] and not a.allow_hash_mismatch:
    sys.exit(f"HASH MISMATCH: {h} vs {ref} -> forecast file was modified after registration")
fc = pd.read_csv(a.prereg)
# 2) actuals
occ, cap = L.load_f5(a.f5)
act = occ.stack().rename("y").reset_index()
act.columns = ["date", "cls", "y"]
act["date"] = act.date.dt.date.astype(str)
capl = cap.stack().rename("cap").reset_index()
capl.columns = ["date", "cls", "cap"]
capl["date"] = capl.date.dt.date.astype(str)
r = fc.merge(act, on=["date", "cls"]).merge(capl, on=["date", "cls"])
r = r[r.y.notna()].copy()
diag["n_scored_rows"] = int(len(r))
diag["scored_dates"] = sorted(r.date.unique().tolist())
diag["last_actual_date"] = str(occ.index.max().date())
if len(r) == 0:
    json.dump(diag, open(os.path.join(a.out, "score_diagnostics.json"), "w"), indent=1)
    print("no realised targets yet", diag)
    sys.exit(0)
r["ae"] = (r.q50 - r.y).abs()
r["cov80"] = ((r.y >= r.q10 - 1e-9) & (r.y <= r.q90 + 1e-9)).astype(float)
r["ev_thr"] = (r.y >= r.thr_cells - 1e-9).astype(float)
r["ev_full"] = (r.y >= r.cap - 1e-9).astype(float)
r["brier_thr"] = (r.P_thr - r.ev_thr) ** 2
r["brier_full"] = (r.P_full - r.ev_full) ** 2
r["bucket"] = pd.cut(r.h, [0, 1, 3, 7, 30], labels=["h1", "h2-3", "h4-7", "h8+"])
r["fg"] = r.cls.isin(L.FGC)
r.to_csv(os.path.join(a.out, "score_rows.csv"), index=False)


def table(g, keys):
    # MAE ratio vs persistence on identical (date, cls) rows
    base = g[g.method == "persist"].set_index(["date", "cls"]).ae
    out = []
    for k, x in g.groupby(keys, observed=True):
        k = k if isinstance(k, tuple) else (k,)
        b = base.reindex(pd.MultiIndex.from_frame(x[["date", "cls"]])).values
        out.append(
            dict(
                zip(keys, k, strict=False),
                n=len(x),
                MAE=round(x.ae.mean(), 2),
                MAE_ratio_vs_persist=round(x.ae.mean() / np.nanmean(b), 3)
                if np.nanmean(b) > 0
                else np.nan,
                cov80=round(x.cov80.mean(), 3),
                brier_thr=round(x.brier_thr.mean(), 4),
                brier_full=round(x.brier_full.mean(), 4),
                event_rate_thr=round(x.ev_thr.mean(), 3),
            )
        )
    return pd.DataFrame(out)


fg = r[r.fg]
t1 = table(fg, ["method", "h"])
t1.to_csv(os.path.join(a.out, "score_by_method_h.csv"), index=False)
t2 = table(fg, ["method", "bucket"])
t2.to_csv(os.path.join(a.out, "score_by_method_bucket.csv"), index=False)
t3 = table(r, ["method", "cls"])
t3.to_csv(os.path.join(a.out, "score_by_cls.csv"), index=False)


def contrast(m1, m0, hs=range(2, 8), nb=2000, seed=0):
    x = fg[fg.h.isin(list(hs))]
    p = (
        x[x.method == m1]
        .set_index(["date", "cls"])
        .ae.rename("a1")
        .to_frame()
        .join(x[x.method == m0].set_index(["date", "cls"]).ae.rename("a0"), how="inner")
        .dropna()
    )
    if len(p) == 0:
        return dict(contrast=f"{m1}/{m0}", n=0)
    ratio = p.a1.mean() / p.a0.mean() if p.a0.mean() > 0 else np.nan
    dates = p.index.get_level_values(0).unique().values
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(nb):  # cluster bootstrap over target dates
        s = rng.choice(dates, len(dates))
        q = pd.concat([p.loc[d] for d in s])
        bs.append(q.a1.mean() / q.a0.mean() if q.a0.mean() > 0 else np.nan)
    lo, hi = np.nanquantile(bs, [0.05, 0.95]) if len(dates) > 2 else (np.nan, np.nan)
    return dict(
        contrast=f"{m1}/{m0}",
        h="2-7",
        n_rows=len(p),
        n_dates=len(dates),
        MAE_1=round(p.a1.mean(), 2),
        MAE_0=round(p.a0.mean(), 2),
        ratio=round(ratio, 3),
        ci90_lo=round(lo, 3),
        ci90_hi=round(hi, 3),
    )


cons = pd.DataFrame(
    [
        contrast("sim_f5", "ens"),
        contrast("sim_f4", "persist_f4"),
        contrast("sim_f4", "ens"),
        contrast("sim_f4_raw", "sim_f4"),
        contrast("ens", "persist"),
        contrast("persist_f4", "persist"),
    ]
)
cons.to_csv(os.path.join(a.out, "score_contrasts.csv"), index=False)
# 3) scenario checks: every (date, cls) where some method gave P_thr >= 0.5 or P_full >= 0.5
sc = r[(r.P_thr >= 0.5) | (r.P_full >= 0.5)]
sc = sc[
    [
        "date",
        "cls",
        "method",
        "q50",
        "y",
        "thr_cells",
        "cap",
        "P_thr",
        "ev_thr",
        "P_full",
        "ev_full",
    ]
].sort_values(["date", "cls", "method"])
sc.to_csv(os.path.join(a.out, "score_scenarios.csv"), index=False)
# 4) diagnostics with optional files
if a.f4:
    s = L.load_snapshot(a.f4, L.load_codes(os.path.dirname(a.f4)))
    lv = L.snapshot_level(s)
    d = s.xdate.iloc[0]
    if d in occ.index:
        diag["f4_minus_f5_same_day"] = {
            "date": str(d.date()),
            **(lv - occ.loc[d]).round(1).to_dict(),
        }
    else:
        diag["f4_level"] = {"date": str(d.date()), **lv.to_dict()}
if a.f2:
    v = L.load_vr(a.f2)
    diag["f2"] = dict(
        dates=sorted(v.DT.dt.date.astype(str).unique().tolist()),
        rows=len(v),
        pieces=int(v.QTA.sum()),
        n_odl=int(v.OdL.nunique()),
        odl_in_prereg_plan="n/a (plan not stored in forecast CSV)",
    )
json.dump(diag, open(os.path.join(a.out, "score_diagnostics.json"), "w"), indent=1, default=str)
pd.set_option("display.width", 200)
print(
    "integrity:",
    diag["sha256_ok"],
    "| scored rows",
    diag["n_scored_rows"],
    "| dates",
    diag["scored_dates"],
)
print(t2.to_string(index=False))
print(cons.to_string(index=False))
print(sc.head(40).to_string(index=False))
