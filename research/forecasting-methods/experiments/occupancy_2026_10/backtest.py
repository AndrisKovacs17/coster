"""Walk-forward backtest of occupied cells per class (Set A and Set B of the findings note).

Origin t = the day whose snapshot is known. Target = occupied cells at t+h.
Models are refit weekly, using only rows whose target day is on or before the refit date.

Usage: python backtest.py [DATA_DIR] OUT_DIR
Writes OUT_DIR/bt_results.pkl. Keep OUT_DIR outside the repo: the results contain Coster data.
"""

import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from history import CLASSES, HOLIDAYS, LAYOUT_STABLE_FROM, data_dir, find, load_history
from sklearn.linear_model import Ridge
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")
HORIZONS = [1, 2, 3, 5, 7, 14]
POST = LAYOUT_STABLE_FROM
BASE_COLS = [
    "fill",
    "free",
    "d1",
    "d2",
    "d3",
    "d7",
    "d14",
    "ma7",
    "ma28",
    "sd7",
    "t_eom",
    "t_hol",
    "wd_between",
    "post",
]


@dataclass
class Panel:
    """Daily occupied (occ) and total (cap) cells per class."""

    occ: pd.DataFrame
    cap: pd.DataFrame


def workdays_between(t, h):
    days = pd.date_range(t + pd.Timedelta(days=1), t + pd.Timedelta(days=h))
    return int(sum((d.dayofweek < 5) and (d not in HOLIDAYS) for d in days))


def build_features(p: Panel, c: str) -> pd.DataFrame:
    o, cp = p.occ[c], p.cap[c]
    f = pd.DataFrame(index=o.index)
    f["occ"] = o
    f["fill"] = o / cp
    f["free"] = cp - o
    f["cap"] = cp
    for k in (1, 2, 3, 7, 14):
        f[f"d{k}"] = o - o.shift(k)
    f["ma7"] = o.rolling(7, min_periods=5).mean() - o
    f["ma28"] = o.rolling(28, min_periods=14).mean() - o
    f["sd7"] = o.rolling(7, min_periods=5).std()
    f["dow"] = f.index.dayofweek
    f["post"] = (f.index >= POST).astype(int)
    for oc in CLASSES:
        if oc != c:
            f[f"x_{oc}_d1"] = (p.occ[oc] - p.occ[oc].shift(1)).fillna(0)
    return f


def target_feats(f: pd.DataFrame, h: int) -> pd.DataFrame:
    g = f.copy()
    tgt = g.index + pd.Timedelta(days=h)
    g["tdow"] = tgt.dayofweek
    g["t_eom"] = ((tgt.days_in_month - tgt.day) <= 2).astype(int)
    g["t_hol"] = tgt.isin(HOLIDAYS).astype(int)
    g["wd_between"] = [workdays_between(t, h) for t in g.index]
    return g


def cross_cols(c):
    return [f"x_{oc}_d1" for oc in CLASSES if oc != c]


def design(g: pd.DataFrame, cols) -> pd.DataFrame:
    x = g[cols].copy()
    for d in range(7):
        x[f"dow{d}"] = (g["dow"] == d).astype(int)
        x[f"tdow{d}"] = (g["tdow"] == d).astype(int)
    return x


LGB_PARAMS = dict(
    n_estimators=120,
    learning_rate=0.04,
    num_leaves=5,
    min_child_samples=12,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    reg_lambda=5.0,
    verbose=-1,
    n_jobs=1,
)


def fit_models(trn: pd.DataFrame, c: str, kinds, post_weight: float) -> dict:
    w = np.where(trn.index >= POST, post_weight, 1.0)
    m = {"prof": trn.groupby("dow")["y"].mean(), "drift": trn["y"].mean()}
    xmr = np.c_[trn["ma28"].values, np.ones(len(trn))]
    m["mr"] = np.linalg.lstsq(xmr * np.sqrt(w)[:, None], trn["y"].values * np.sqrt(w), rcond=None)[
        0
    ]
    for name, cols, alpha in (
        ("ridge", BASE_COLS, 20.0),
        ("ridgex", BASE_COLS + cross_cols(c), 40.0),
    ):
        xtr = design(trn, cols)
        mu, sd = xtr.mean(), xtr.std().replace(0, 1)
        m[name + "_cols"] = (mu, sd, xtr.columns)
        m[name] = Ridge(alpha=alpha).fit(((xtr - mu) / sd).values, trn["y"].values, sample_weight=w)
    if "lgb" in kinds:
        xl = design(trn, BASE_COLS + ["dow", "tdow"])
        m["lgb_cols"] = xl.columns
        m["lgb"] = lgb.LGBMRegressor(**LGB_PARAMS).fit(xl, trn["y"].values, sample_weight=w)
    return m


def run_class(p: Panel, c, origins, h, kinds, train_min=40, post_weight=1.0):
    """Predicted occupied cells at t+h for each origin t and method in kinds."""
    f = target_feats(build_features(p, c), h)
    f["y"] = p.occ[c].shift(-h) - p.occ[c]
    preds = {k: [] for k in kinds}
    last_refit, models = None, {}
    for t in origins:
        if last_refit is None or (t - last_refit).days >= 7:
            last_refit = t
            trn = f[f.index + pd.Timedelta(days=h) <= t].dropna(subset=["y"] + BASE_COLS)
            models = fit_models(trn, c, kinds, post_weight) if len(trn) >= train_min else {}
        row, base = f.loc[t], p.occ.loc[t, c]
        ok = "prof" in models and not row[BASE_COLS].isna().any()
        for k in kinds:
            preds[k].append(predict_one(p, c, f, t, h, k, models, row, base, ok))
    out = pd.DataFrame(preds, index=pd.DatetimeIndex(origins))
    capc = p.cap[c].reindex(out.index + pd.Timedelta(days=h)).values
    out = out.clip(lower=0).apply(lambda s: np.minimum(s.values, capc), axis=0)
    out["actual"] = p.occ[c].reindex(out.index + pd.Timedelta(days=h)).values
    out["cap_t"] = p.cap[c].reindex(out.index).values
    out["cap_target"] = capc
    out["occ_t"] = p.occ[c].reindex(out.index).values
    return out


def predict_one(p, c, f, t, h, k, models, row, base, ok):
    if k == "persist":
        return base
    if k == "snaive7":
        lag = 7 if h <= 7 else 14
        prev = p.occ[c].get(t + pd.Timedelta(days=h - lag), np.nan)
        prev0 = p.occ[c].get(t - pd.Timedelta(days=lag), np.nan)
        return base + (prev - prev0)
    if not ok:
        return np.nan
    if k == "profile":
        return base + models["prof"].get(int(row["dow"]), models["drift"])
    if k == "meanrev":
        return base + models["mr"][0] * row["ma28"] + models["mr"][1]
    if k in ("ridge", "ridgex"):
        mu, sd, cols = models[k + "_cols"]
        x = design(f.loc[[t]], [cc for cc in cols if not cc.startswith(("dow", "tdow"))])
        x = x.reindex(columns=cols, fill_value=0)
        return base + models[k].predict(((x - mu) / sd).values)[0]
    if k == "lgb":
        x = design(f.loc[[t]], BASE_COLS + ["dow", "tdow"]).reindex(
            columns=models["lgb_cols"], fill_value=0
        )
        return base + models["lgb"].predict(x)[0]
    return np.nan


def run_sarimax(
    p: Panel, c, origins, h_list, win=120, start=None, order=(1, 0, 1), sorder=(1, 0, 0, 7)
):
    """Weekly refit, daily state update.

    start: first day of the fitting window (None = the last win days).
    """
    res_by_h = {h: {} for h in h_list}
    last, res, last_end = None, None, None
    o = p.occ[c]
    for t in origins:
        if last is None or (t - last).days >= 7:
            hist = o.loc[start:t].dropna() if start is not None else o.loc[:t].dropna().iloc[-win:]
            res = None
            if len(hist) >= 28:
                try:
                    res = SARIMAX(
                        hist,
                        order=order,
                        seasonal_order=sorder,
                        trend="c",
                        enforce_stationarity=False,
                    ).fit(disp=False, maxiter=60)
                except Exception:
                    res = None
            last, last_end = t, (hist.index[-1] if len(hist) else t)
        if res is None:
            continue
        new = o.loc[last_end + pd.Timedelta(days=1) : t].dropna()
        try:
            fc = (res.append(new, refit=False) if len(new) else res).forecast(max(h_list))
        except Exception:
            continue
        for h in h_list:
            res_by_h[h][t] = float(fc.iloc[h - 1])
    return {h: pd.Series(v, dtype=float) for h, v in res_by_h.items()}


SETS = {
    "A_stable_MedW_HighW": (["MedW", "HighW"], ("2026-03-01", "2026-10-21"), 40, 1.0),
    "B_changed_Low_Med_High": (["Low", "Med", "High"], ("2026-09-12", "2026-10-21"), 60, 4.0),
}
KINDS = ["persist", "snaive7", "profile", "meanrev", "ridge", "ridgex", "lgb"]


def main(data: str | None, out: str) -> pd.DataFrame:
    occ, cap = load_history(find(data_dir(data), " 5 - PU"))
    p = Panel(occ, cap)
    rows = []
    for sname, (cls, (a, b), train_min, pw) in SETS.items():
        origins = pd.date_range(a, b)
        for c in cls:
            sar = run_sarimax(p, c, origins, HORIZONS)
            for h in HORIZONS:
                o2 = [t for t in origins if t + pd.Timedelta(days=h) <= occ.index.max()]
                df = run_class(p, c, o2, h, KINDS, train_min=train_min, post_weight=pw)
                df["sarimax"] = np.clip(sar[h].reindex(df.index).values, 0, df["cap_target"])
                df["set"], df["cls"], df["h"] = sname, c, h
                rows.append(df.reset_index().rename(columns={"index": "origin"}))
                print(sname, c, h, len(df), flush=True)
    res = pd.concat(rows, ignore_index=True)
    Path(out).mkdir(parents=True, exist_ok=True)
    res.to_pickle(Path(out) / "bt_results.pkl")
    return res


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0] if len(args) > 1 else None, args[-1])
