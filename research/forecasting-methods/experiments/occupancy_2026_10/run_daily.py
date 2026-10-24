"""Daily driver for the pre-registered forecasts.

1. Score every earlier pre-registered forecast against the newest File 5 (plus File 4 and File 2
   diagnostics).
2. Build and freeze a new pre-registered forecast from the newest files (origin = last File 5 day).

Usage:
  python run_daily.py --data DAY_FOLDER --base WORK_DIR [--static FOLDER] [--results BT2_PKL]
                      [--N 1000] [--no-forecast] [--no-score]

DAY_FOLDER  the day's six daily files plus coster_codes.json
WORK_DIR    where prereg_<origin>/ and scores_<date>/ folders live (default $COSTER_WORK_DIR).
            Keep it outside the repo: it holds Coster data.
--static    folder with the one-off files (B01_B02, PCS-HOUR, UDC vs CELLE). Default: DAY_FOLDER.
--results   bt2_results.pkl from chronos_backtest.py, used for the ensemble's error band
            when no ens_sigma_interp.csv exists yet in WORK_DIR.
Never edits an existing prereg_* file.
"""

import argparse
import glob
import os
import subprocess
import sys

import forecast_sim
import forecast_stat
import pandas as pd
import prereg
import sim_lib as L

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--base", default=os.environ.get("COSTER_WORK_DIR"))
    ap.add_argument("--static")
    ap.add_argument("--results")
    ap.add_argument("--N", type=int, default=1000)
    ap.add_argument("--no-forecast", action="store_true")
    ap.add_argument("--no-score", action="store_true")
    a = ap.parse_args()
    if not a.base:
        raise SystemExit("pass --base or set COSTER_WORK_DIR (outside the repo)")
    static = a.static or a.data
    f5 = L.find(a.data, " 5 - PU")
    occ, _ = L.load_f5(f5)
    last = occ.index.max().date().isoformat()
    print("newest File 5 ends", last)
    py = [sys.executable]
    if not a.no_score:
        for p in sorted(glob.glob(os.path.join(a.base, "prereg_*", "prereg_forecast_*.csv"))):
            tag = os.path.basename(os.path.dirname(p))
            out = os.path.join(a.base, f"scores_{last}", tag)
            cmd = py + [os.path.join(HERE, "score.py"), "--prereg", p, "--f5", f5, "--out", out]
            for flag, key in (("--f4", " 4 - PU"), ("--f2", " 2 - PU")):
                try:
                    cmd += [flag, L.find(a.data, key)]
                except FileNotFoundError:
                    pass
            print(">> score", tag, flush=True)
            subprocess.run(cmd, check=False)
    if not a.no_forecast:
        out = os.path.join(a.base, f"prereg_{last}")
        if glob.glob(os.path.join(out, "prereg_forecast_*.csv")):
            raise SystemExit(f"{out} already holds a registered forecast. Refusing to overwrite.")
        os.makedirs(out, exist_ok=True)
        end = (pd.Timestamp(last) + pd.Timedelta(days=15)).date().isoformat()
        sigmas = sorted(glob.glob(os.path.join(a.base, "prereg_*", "ens_sigma_interp.csv")))
        ledger = os.path.join(a.base, "v_ledger.csv")  # File 2 rows accumulated across days
        v = L.load_vr(L.find(a.data, " 2 - PU"))
        if os.path.exists(ledger):
            old = pd.read_csv(ledger, parse_dates=["DT"])
            v = pd.concat([old, v]).drop_duplicates(subset=["OdL", "DT", "QTA"])
        v.to_csv(ledger, index=False)
        forecast_sim.main(a.data, out, a.N, static_dir=static, end_date=end, v_ledger=v)
        forecast_stat.main(
            a.data,
            out,
            results_pkl=a.results,
            sigma_csv=sigmas[0] if sigmas else None,
            end_date=end,
        )
        prereg.main(out, a.data)
    if not a.no_score:
        sd = os.path.join(a.base, f"scores_{last}")
        if glob.glob(os.path.join(sd, "*", "score_rows.csv")):
            subprocess.run(py + [os.path.join(HERE, "score_pool.py"), sd], check=False)


if __name__ == "__main__":
    main()
