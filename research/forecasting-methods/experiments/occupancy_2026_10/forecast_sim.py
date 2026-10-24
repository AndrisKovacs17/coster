"""Simulator forecasts (sim_f5, sim_f4, sim_f4_raw) and a sensitivity analysis.

Usage: python forecast_sim.py DATA_DIR OUT_DIR [N] [STATIC_DIR]
OUT_DIR must be outside the repo: the forecasts contain Coster data.
"""

import json
import os
import sys
import time

import numpy as np
import pandas as pd
import sim_lib as L
import sim_mc as M


def summarize(out, inp, method, end_date):
    rows = []
    capd = dict(zip(L.FGC, inp["cap"], strict=False))
    for i, d in enumerate(inp["days"]):
        if d <= inp["t_f5"] or d > pd.Timestamp(end_date):
            continue
        for j, c in enumerate(L.FGC):
            y = out[:, i, j]
            thr = L.THR[c] * capd[c]
            q10, q50, q90 = np.quantile(y, [0.1, 0.5, 0.9])
            rows.append(
                dict(
                    date=d.date().isoformat(),
                    cls=c,
                    method=method,
                    anchor=inp["start"].date().isoformat(),
                    h=(d - inp["t_f5"]).days,
                    q10=round(q10, 2),
                    q50=round(q50, 2),
                    q90=round(q90, 2),
                    mean=round(y.mean(), 2),
                    thr_cells=round(thr, 2),
                    P_thr=round(float((y >= thr - 1e-9).mean()), 4),
                    P_full=round(float((y >= capd[c] - 1e-9).mean()), 4),
                )
            )
    return pd.DataFrame(rows)


def sensitivity(inp, N, seed, dates):
    out, P, _, _ = M.run_mc(inp, N=N, seed=seed, add_noise=False)
    outn, _, _, _ = M.run_mc(inp, N=N, seed=seed + 1, add_noise=True)
    pars = ["eta", "slip", "beta80", "betaL", "mu_d", "mu_g", "phi", "m_res", "backlog_u"]
    rows = []
    for d in dates:
        i = list(inp["days"]).index(pd.Timestamp(d))
        for j, c in enumerate(L.FGC):
            y = out[:, i, j]
            vy = y.var()
            vt = outn[:, i, j].var()
            r = dict(
                date=d,
                cls=c,
                sd_total=round(np.sqrt(vt), 2),
                sd_noisefree=round(np.sqrt(vy), 2),
                share_var_noise=round(1 - vy / vt, 3) if vt > 0 else np.nan,
            )
            for p in pars:
                x = P[p].values
                if len(np.unique(x)) <= 10:
                    b = x
                else:
                    b = pd.qcut(x, 10, labels=False, duplicates="drop")
                cm = pd.Series(y).groupby(b).transform("mean")
                r["S1_" + p] = round(cm.var() / vy, 3) if vy > 0 else np.nan
            rows.append(r)
    return pd.DataFrame(rows)


def main(D, OUT, N=1000, static_dir=None, end_date=None, sens=True, v_ledger=None):
    os.makedirs(OUT, exist_ok=True)
    if end_date is None:
        t_f5 = L.load_f5(L.find(D, " 5 - PU"))[0].index.max()
        end_date = (t_f5 + pd.Timedelta(days=15)).date().isoformat()
    res, meta = [], {}
    for anchor in ("f5", "f4"):
        t = time.time()
        inp = M.build_inputs(
            D,
            anchor,
            end_date=(pd.Timestamp(end_date) + pd.Timedelta(days=8)).date().isoformat(),
            static_dir=static_dir,
            v_ledger=v_ledger,
        )
        r, hist = M.calibrate_unmodelled(inp, N=30, iters=6)
        hist.to_csv(f"{OUT}/sim_calibration_{anchor}.csv", index=False)
        meta[anchor] = dict(
            start=str(inp["start"].date()),
            level=inp["level"].to_dict(),
            nfg=inp["nfg"].tolist(),
            r_unmodelled=dict(zip(L.FGC, np.round(r, 3).tolist(), strict=False)),
            littles_beta=M.littles_beta(inp),
            n_groups=int(len(inp["grp"])),
            groups_with_U=int(inp["grp"].U_day.notna().sum()),
        )
        inp["r_unm"] = r
        out, P, unp, _ = M.run_mc(inp, N=N, seed=101 if anchor == "f5" else 202)
        res.append(summarize(out, inp, f"sim_{anchor}", end_date))
        P.to_csv(f"{OUT}/sim_params_{anchor}.csv", index=False)
        np.save(f"{OUT}/sim_draws_{anchor}.npy", out.astype(np.float32))
        meta[anchor]["P_any_unplaced_by_end"] = float((unp.sum(1) > 0).mean())
        if anchor == "f4":
            inp["r_unm"] = np.zeros(4)
            outr, Pr, unpr, _ = M.run_mc(inp, N=N, seed=303)
            res.append(summarize(outr, inp, "sim_f4_raw", end_date))
            meta["f4_raw"] = dict(P_any_unplaced_by_end=float((unpr.sum(1) > 0).mean()))
            if sens:
                inp["r_unm"] = r
                sd = [
                    (inp["t_f5"] + pd.Timedelta(days=k)).date().isoformat()
                    for k in (2, 4, 5, 7, 11, 15)
                ]
                sd = [d for d in sd if pd.Timestamp(d) <= pd.Timestamp(end_date)]
                sensitivity(inp, 400, 404, sd).to_csv(f"{OUT}/sim_sensitivity_f4.csv", index=False)
        meta[anchor]["seconds"] = round(time.time() - t, 1)
        print(anchor, meta[anchor], flush=True)
    df = pd.concat(res, ignore_index=True)
    df.to_csv(f"{OUT}/sim_forecasts.csv", index=False)
    json.dump(meta, open(f"{OUT}/sim_meta.json", "w"), indent=1, default=str)
    return df, meta


if __name__ == "__main__":
    D, OUT = sys.argv[1], sys.argv[2]
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    sd = sys.argv[4] if len(sys.argv) > 4 else None
    main(D, OUT, N, sd)
