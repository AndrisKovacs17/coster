"""Statistical forecasts from the newest File 5 day (the origin).

Methods: persist (last value, range from past h-day changes), ens (mean of meanrev, LightGBM
and Chronos-2, as in backtest.py), persist_f4 (the File 4 level held flat). The ens range uses
the RMS of the last 60 realised backtest errors per class and horizon, interpolated over h.

Usage: python forecast_stat.py DATA_DIR OUT_DIR (--results BT2_RESULTS_PKL | --sigma SIGMA_CSV)
"""

import argparse
import os
import warnings

import numpy as np
import pandas as pd
import sim_lib as L
from backtest import POST, Panel, run_class
from chronos_backtest import covariates
from scipy.stats import norm

warnings.filterwarnings("ignore")
Z80 = 1.2816


def ens_sigma_table(results_pkl, t0):
    """Online RMS error of the backtest ensemble per class and horizon, before t0."""
    r = pd.read_pickle(results_pkl).rename(columns={"cz_0.5": "cz", "czp_0.5": "czp"})
    set_b = r["set"].str.startswith("B")
    r["ens"] = r[["meanrev", "lgb", "cz"]].mean(axis=1, skipna=False)
    r.loc[set_b, "ens"] = r.loc[set_b, ["meanrev", "lgb", "czp"]].mean(axis=1, skipna=False)
    rows = []
    for (c, h), g in r.groupby(["cls", "h"]):
        g = g.sort_values("origin")
        known = g.origin + pd.to_timedelta(g.h, unit="D") <= t0
        e = (g.ens - g.actual)[known].dropna().values[-60:]
        sigma = float(np.sqrt(np.mean(e**2))) if len(e) >= 15 else np.nan
        rows.append(dict(cls=c, h=int(h), sigma=sigma, n=len(e)))
    raw = pd.DataFrame(rows)
    out = []
    for c, g in raw.groupby("cls"):
        g = g.dropna().sort_values("h")
        for h in range(1, 31):
            out.append(dict(cls=c, h=h, sigma=float(np.interp(h, g.h, g.sigma))))
    return raw, pd.DataFrame(out)


def band_row(d, c, method, anchor, h, q10, q50, q90, mean, thr, capc, p_thr, p_full):
    return dict(
        date=d.date().isoformat(),
        cls=c,
        method=method,
        anchor=anchor,
        h=h,
        q10=round(q10, 2),
        q50=round(q50, 2),
        q90=round(q90, 2),
        mean=round(mean, 2),
        thr_cells=round(thr, 2),
        P_thr=round(p_thr, 4),
        P_full=round(p_full, 4),
    )


def empirical_row(d, c, method, anchor, h, base, changes, thr, capc):
    y = np.clip(base + changes, 0, capc)
    return band_row(
        d,
        c,
        method,
        anchor,
        h,
        np.quantile(y, 0.1),
        base,
        np.quantile(y, 0.9),
        y.mean(),
        thr,
        capc,
        float((y >= thr - 1e-9).mean()),
        float((y >= capc - 1e-9).mean()),
    )


def main(D, OUT, results_pkl=None, sigma_csv=None, end_date=None):
    import torch
    from chronos import Chronos2Pipeline

    torch.set_num_threads(1)
    os.makedirs(OUT, exist_ok=True)
    occ, cap = L.load_f5(L.find(D, " 5 - PU"))
    t0 = occ.index.max()
    end = pd.Timestamp(end_date) if end_date else t0 + pd.Timedelta(days=15)
    horizon = (end - t0).days
    ext = pd.date_range(occ.index.min(), end + pd.Timedelta(days=1))
    p = Panel(occ.reindex(ext), cap.reindex(ext).ffill())
    pipe = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map="cpu")

    def chronos(c, post_only):
        o = p.occ[c].loc[:t0]
        o = o.loc[POST:] if post_only else o.iloc[-120:]
        ctx = covariates(o.index)
        ctx["target"] = o.values
        ctx["id"] = c
        fut = covariates(pd.date_range(t0 + pd.Timedelta(days=1), periods=horizon))
        fut["id"] = c
        pr = pipe.predict_df(
            ctx,
            future_df=fut,
            prediction_length=horizon,
            quantile_levels=[0.1, 0.5, 0.9],
            id_column="id",
            timestamp_column="timestamp",
            target="target",
        )
        return pr.set_index("timestamp")["0.5"]

    if sigma_csv and os.path.exists(sigma_csv):
        sig = pd.read_csv(sigma_csv)
    elif results_pkl:
        raw, sig = ens_sigma_table(results_pkl, t0)
        raw.to_csv(os.path.join(OUT, "ens_sigma_raw.csv"), index=False)
        sig.to_csv(os.path.join(OUT, "ens_sigma_interp.csv"), index=False)
    else:
        raise SystemExit("pass --results (bt2_results.pkl) or --sigma (ens_sigma_interp.csv)")
    sig = sig.set_index(["cls", "h"]).sigma
    codes = L.load_codes(D)
    snap = L.load_snapshot(L.find(D, " 4 - PU"), codes)
    f4, tx = L.snapshot_level(snap), snap.xdate.iloc[0]
    rows, comp = [], []
    for c in L.CLS:
        set_a = c in ("MedW", "HighW")
        cz = chronos(c, post_only=not set_a)
        capc = float(cap.loc[t0, c])
        thr = L.THR[c] * capc
        o = occ[c].loc[:t0]
        win = o.iloc[-120:] if set_a else o.loc[POST:]
        for h in range(1, horizon + 1):
            d = t0 + pd.Timedelta(days=h)
            df = run_class(
                p,
                c,
                [t0],
                h,
                ["persist", "meanrev", "lgb"],
                train_min=40 if set_a else 60,
                post_weight=1.0 if set_a else 4.0,
            )
            mr, lg = float(df.meanrev.iloc[0]), float(df.lgb.iloc[0])
            czv = float(min(max(cz.loc[d], 0), capc))
            ens = float(np.clip(np.mean([mr, lg, czv]), 0, capc))
            s = max(float(sig.get((c, h), np.nan)), 1.0)
            comp.append(
                dict(
                    date=d.date().isoformat(),
                    cls=c,
                    h=h,
                    meanrev=mr,
                    lgb=lg,
                    chronos=czv,
                    ens=ens,
                    sigma=s,
                )
            )
            rows.append(
                band_row(
                    d,
                    c,
                    "ens",
                    t0.date().isoformat(),
                    h,
                    max(ens - Z80 * s, 0),
                    ens,
                    min(ens + Z80 * s, capc),
                    ens,
                    thr,
                    capc,
                    float(1 - norm.cdf((thr - 1e-9 - ens) / s)),
                    float(1 - norm.cdf((capc - 1e-9 - ens) / s)),
                )
            )
            changes = (win.shift(-h) - win).dropna().values
            rows.append(
                empirical_row(
                    d, c, "persist", t0.date().isoformat(), h, float(o.iloc[-1]), changes, thr, capc
                )
            )
            hp = (d - tx).days
            if hp >= 0:
                ch2 = (win.shift(-max(hp, 1)) - win).dropna().values * (0.5 if hp == 0 else 1.0)
                rows.append(
                    empirical_row(
                        d, c, "persist_f4", tx.date().isoformat(), h, float(f4[c]), ch2, thr, capc
                    )
                )
        print(c, "done", flush=True)
    pd.DataFrame(comp).to_csv(os.path.join(OUT, "stat_components.csv"), index=False)
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(OUT, "stat_forecasts.csv"), index=False)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out")
    ap.add_argument("--results")
    ap.add_argument("--sigma")
    ap.add_argument("--end")
    a = ap.parse_args()
    main(a.data, a.out, a.results, a.sigma, a.end)
