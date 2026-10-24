"""Add Chronos-2 zero-shot forecasts and a post-layout SARIMAX to the backtest results.

Usage: python chronos_backtest.py [DATA_DIR] OUT_DIR
Reads OUT_DIR/bt_results.pkl (from backtest.py), writes OUT_DIR/bt2_results.pkl.
Chronos-2 runs on CPU. The weights are downloaded from Hugging Face on first use.

Columns added (q = 0.1, 0.5, 0.9):
  cz_q   Chronos-2, last 120 days as context
  czx_q  the same, with the other classes as past covariates
  czp_q  Chronos-2, context from the end of the re-layout only (Set B)
  sarpost  SARIMAX(1,0,0)(1,0,0,7) fitted from the end of the re-layout (Set B)
Known future covariates for Chronos: day of week, public holiday, last 3 days of the month.
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from backtest import HORIZONS, POST, Panel, run_sarimax
from history import CLASSES, HOLIDAYS, data_dir, find, load_history

warnings.filterwarnings("ignore")
Q = [0.1, 0.25, 0.5, 0.75, 0.9]
HMAX = 14


def covariates(idx: pd.DatetimeIndex) -> pd.DataFrame:
    d = pd.DataFrame({"timestamp": idx})
    d["dow"] = idx.dayofweek
    d["hol"] = idx.isin(HOLIDAYS).astype(int)
    d["eom"] = ((idx.days_in_month - idx.day) <= 2).astype(int)
    return d


def chronos_pred(pipe, p: Panel, c, t, ctx_days=120, post_only=False, cross=False):
    o = p.occ[c].loc[:t]
    o = o.loc[POST:] if post_only else o.iloc[-ctx_days:]
    ctx = covariates(o.index)
    ctx["target"] = o.values
    ctx["id"] = c
    if cross:
        for oc in CLASSES:
            if oc != c:
                ctx["x_" + oc] = p.occ[oc].reindex(o.index).values
    fut = covariates(pd.date_range(t + pd.Timedelta(days=1), periods=HMAX))
    fut["id"] = c
    pr = pipe.predict_df(
        ctx,
        future_df=fut,
        prediction_length=HMAX,
        quantile_levels=Q,
        id_column="id",
        timestamp_column="timestamp",
        target="target",
    )
    return pr.set_index("timestamp")[[str(q) for q in Q]]


def main(data: str | None, out: str) -> pd.DataFrame:
    from chronos import Chronos2Pipeline

    occ, cap = load_history(find(data_dir(data), " 5 - PU"))
    p = Panel(occ, cap)
    res = pd.read_pickle(Path(out) / "bt_results.pkl")
    pipe = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map="cpu")
    variants = {"cz": {}, "czx": {"cross": True}, "czp": {"post_only": True}}
    new_cols: dict[str, dict] = {}
    for (s, c), g in res.groupby(["set", "cls"]):
        origins = sorted(g["origin"].unique())
        set_b = s.startswith("B")
        cache = {}
        for t in origins:
            for v, kw in variants.items():
                if v == "czp" and (not set_b or (t - POST).days < 14):
                    continue
                cache[(v, t)] = chronos_pred(pipe, p, c, t, **kw)
        sp = (
            run_sarimax(p, c, origins, HORIZONS, start=POST, order=(1, 0, 0), sorder=(1, 0, 0, 7))
            if set_b
            else None
        )
        for i, r in g.iterrows():
            t, h = r["origin"], int(r["h"])
            td = t + pd.Timedelta(days=h)
            for v in variants:
                pr = cache.get((v, t))
                if pr is None:
                    continue
                for q in ("0.1", "0.5", "0.9"):
                    new_cols.setdefault(f"{v}_{q}", {})[i] = pr.loc[td, q]
            if sp is not None and t in sp[h].index:
                new_cols.setdefault("sarpost", {})[i] = sp[h][t]
        print(s, c, "done", flush=True)
    for k, d in new_cols.items():
        res[k] = np.clip(pd.Series(d, dtype=float).reindex(res.index), 0, res["cap_target"])
    res.to_pickle(Path(out) / "bt2_results.pkl")
    return res


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0] if len(args) > 1 else None, args[-1])
