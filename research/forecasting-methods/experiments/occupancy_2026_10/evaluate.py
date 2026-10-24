"""Score the backtest: MAE ratio to persistence with block-bootstrap CIs, and threshold alerts.

Usage: python evaluate.py OUT_DIR
Reads OUT_DIR/bt2_results.pkl, writes ratio_table.csv, ratio_ci.csv and alert_eval.csv to OUT_DIR.

Ensemble definitions (fixed before scoring):
  Set A (MedW, HighW): mean of meanrev, lgb and cz (Chronos-2, 120-day context)
  Set B (Low, Med, High): mean of meanrev, lgb and czp (Chronos-2, post-layout context)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

METHODS = ["persist", "snaive7", "profile", "meanrev", "ridge", "ridgex", "lgb", "sarimax"]
METHODS += ["sarpost", "cz", "czx", "czp", "ens"]


def load(out: Path) -> pd.DataFrame:
    r = pd.read_pickle(out / "bt2_results.pkl")
    r = r.rename(columns={"cz_0.5": "cz", "czx_0.5": "czx", "czp_0.5": "czp"})
    set_b = r["set"].str.startswith("B")
    r["ens"] = r[["meanrev", "lgb", "cz"]].mean(axis=1, skipna=False)
    r.loc[set_b, "ens"] = r.loc[set_b, ["meanrev", "lgb", "czp"]].mean(axis=1, skipna=False)
    r["sig_lo"] = np.where(set_b, r["czp_0.1"], r["cz_0.1"])
    r["sig_hi"] = np.where(set_b, r["czp_0.9"], r["cz_0.9"])
    return r.sort_values(["set", "cls", "h", "origin"]).reset_index(drop=True)


def ratio_table(r: pd.DataFrame) -> pd.DataFrame:
    """MAE of each method / MAE of persistence, on the rows where that method has a value."""
    rows = []
    for (s, h), g in r.groupby(["set", "h"]):
        for m in METHODS[1:]:
            if m not in g or g[m].isna().all():
                continue
            x = g.dropna(subset=[m, "actual"])
            base = (x["persist"] - x["actual"]).abs().mean()
            mae = (x[m] - x["actual"]).abs().mean()
            rows.append(dict(set=s, h=h, method=m, n=len(x), ratio=round(mae / base, 3)))
    return pd.DataFrame(rows)


def block_ci(g: pd.DataFrame, m: str, n_boot=3000, block=7, seed=1):
    """Ratio to persistence and its 90% CI from a bootstrap over 7-day blocks of origins."""
    g = g.sort_values(["cls", "origin"])
    diff = ((g[m] - g["actual"]).abs() - (g["persist"] - g["actual"]).abs()).values
    base = (g["persist"] - g["actual"]).abs().mean()
    nb = len(diff) // block
    blocks = [diff[i * block : (i + 1) * block] for i in range(nb)]
    rng = np.random.default_rng(seed)
    boot = [
        np.concatenate([blocks[i] for i in rng.integers(0, nb, nb)]).mean() for _ in range(n_boot)
    ]
    lo, hi = np.percentile(boot, [5, 95])
    return round(1 + diff.mean() / base, 3), round(1 + lo / base, 3), round(1 + hi / base, 3)


def ratio_ci(r: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (s, h), g in r.groupby(["set", "h"]):
        ms = ["meanrev", "lgb", "czp" if s.startswith("B") else "cz", "ens"]
        g = g.dropna(subset=ms + ["persist", "actual"])
        for m in ms:
            ratio, lo, hi = block_ci(g, m)
            rows.append(dict(set=s, h=h, method=m, n=len(g), ratio=ratio, ci90_lo=lo, ci90_hi=hi))
    return pd.DataFrame(rows)


def online_sigma(g: pd.DataFrame, col: str, win=60, minn=15) -> np.ndarray:
    """RMS of the last win realised errors (target day <= origin) for each origin."""
    out = np.full(len(g), np.nan)
    org = g["origin"].values
    tgt = org + np.timedelta64(int(g["h"].iloc[0]), "D")
    err = (g[col] - g["actual"]).values
    for i in range(len(g)):
        e = err[(tgt <= org[i]) & ~np.isnan(err)][-win:]
        if len(e) >= minn:
            out[i] = np.sqrt(np.mean(e**2))
    return out


def auc(y, p):
    y, p = np.asarray(y), np.asarray(p)
    if y.sum() in (0, len(y)):
        return np.nan
    rk = pd.Series(p).rank().values
    n1 = y.sum()
    return (rk[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


# Thresholds as a share of capacity, fixed before scoring. HighW rarely nears full: illustrative.
EVENTS = [
    ("MedW", [0.90, 0.95]),
    ("HighW", [0.60, 0.70]),
    ("High", [0.90, 0.95]),
    ("Low", [0.88, 0.90]),
]


def alert_eval(r: pd.DataFrame) -> pd.DataFrame:
    for col in ("persist", "ens"):
        r["sig_" + col] = np.nan
        for _, g in r.groupby(["set", "cls", "h"]):
            r.loc[g.index, "sig_" + col] = online_sigma(g, col)
    rows = []
    for c, ths in EVENTS:
        for h in (2, 3, 7):
            need = ["persist", "ens", "sig_persist", "sig_ens", "actual", "cap_target"]
            g = r[(r["cls"] == c) & (r["h"] == h)].dropna(subset=need)
            if len(g) < 20:
                continue
            for th in ths:
                thr = th * g["cap_target"]
                y = (g["actual"] >= thr - 1e-9).astype(int)
                pp = 1 - norm.cdf((thr - g["persist"]) / g["sig_persist"].clip(lower=1))
                pe = 1 - norm.cdf((thr - g["ens"]) / g["sig_ens"].clip(lower=1))
                hard = (g["persist"] >= thr).astype(float)
                base = y.mean()

                def brier(prob, y=y):
                    return float(np.mean((prob - y) ** 2))

                rows.append(
                    dict(
                        cls=c,
                        h=h,
                        thr=th,
                        n=len(g),
                        event_rate=round(base, 2),
                        brier_climatology=round(brier(np.full(len(y), base)), 3),
                        brier_hard_persistence=round(brier(hard), 3),
                        brier_persistence_gauss=round(brier(pp), 3),
                        brier_ensemble_gauss=round(brier(pe), 3),
                        auc_persistence_gauss=round(auc(y, pp), 3),
                        auc_ensemble_gauss=round(auc(y, pe), 3),
                    )
                )
    return pd.DataFrame(rows)


def coverage(r: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (c, h), g in r[r["h"].isin([2, 7])].groupby(["cls", "h"]):
        g = g.dropna(subset=["ens", "sig_ens", "actual"])
        z = 1.2816
        inside = (g["actual"] >= g["ens"] - z * g["sig_ens"]) & (
            g["actual"] <= g["ens"] + z * g["sig_ens"]
        )
        native = (g["actual"] >= g["sig_lo"]) & (g["actual"] <= g["sig_hi"])
        rows.append(
            dict(
                cls=c,
                h=h,
                n=len(g),
                online80=round(inside.mean(), 2),
                chronos80=round(native.mean(), 2),
            )
        )
    return pd.DataFrame(rows)


def main(out: str):
    out = Path(out)
    r = load(out)
    for name, table in (
        ("ratio_table", ratio_table(r)),
        ("ratio_ci", ratio_ci(r)),
        ("alert_eval", alert_eval(r)),
        ("coverage", coverage(r)),
    ):
        table.to_csv(out / f"{name}.csv", index=False)
        print(f"== {name}\n{table.to_string(index=False)}\n")


if __name__ == "__main__":
    main(sys.argv[1])
