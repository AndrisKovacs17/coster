"""Freeze one pre-registered forecast: merge the simulator and statistical forecasts into one CSV,
with a creation time, a sha256 file and a manifest (input and code hashes, declared contrasts).

Usage: python prereg.py OUT_DIR DATA_DIR
Never edit a registered file. score.py refuses a file whose hash no longer matches.
"""

import datetime
import glob
import hashlib
import json
import os
import sys

import pandas as pd

DECLARED = {
    "primary_contrasts": [
        "P1 plan merit, same File 5 anchor: MAE(sim_f5) / MAE(ens), Med/High/MedW/HighW, h=2..7",
        "P2 plan merit, newest anchor: MAE(sim_f4) / MAE(persist_f4), same classes and horizons",
        "P3 operational: MAE(sim_f4) / MAE(ens), same classes and horizons",
        "secondary: sim_f4_raw (no balance calibration) vs sim_f4",
        "events: Brier of P_thr and P_full, coverage of q10-q90 (nominal 0.80)",
    ],
    "decision_rule": (
        "after >= 15 scored origins: 'plan helps' if the 90% date-cluster bootstrap CI "
        "of the P2 ratio lies below 1.0 and the P3 ratio is below 0.95. "
        "Otherwise: 'no demonstrated gain'."
    ),
    "multiple_testing": (
        "6 methods registered (persist, ens, persist_f4, sim_f5, sim_f4, sim_f4_raw). "
        "Primary = sim_f4. No variant is added afterwards."
    ),
}
COLUMNS = ["date", "cls", "method", "q10", "q50", "q90", "P_thr", "P_full", "thr_cells", "h"]
COLUMNS += ["origin_f5", "anchor", "mean", "created_utc"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(OUT, D, code_dir=None):
    code_dir = code_dir or os.path.dirname(os.path.abspath(__file__))
    a = pd.read_csv(os.path.join(OUT, "sim_forecasts.csv"))
    b = pd.read_csv(os.path.join(OUT, "stat_forecasts.csv"))
    df = pd.concat([b, a], ignore_index=True)
    origin = b[b.method == "persist"].anchor.iloc[0]
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    df.insert(0, "origin_f5", origin)
    df["created_utc"] = now
    df = df[COLUMNS].sort_values(["date", "cls", "method"]).reset_index(drop=True)
    name = f"prereg_forecast_origin{origin}_created{now.replace(':', '').replace('-', '')}.csv"
    path = os.path.join(OUT, name)
    df.to_csv(path, index=False)
    digest = sha(path)
    with open(path + ".sha256", "w") as f:
        f.write(f"{digest}  {name}\n")
    manifest = dict(
        file=name,
        sha256=digest,
        created_utc=now,
        origin_f5=origin,
        n_rows=len(df),
        methods=sorted(df.method.unique()),
        dates=[df.date.min(), df.date.max()],
        inputs={os.path.basename(f): sha(f) for f in sorted(glob.glob(os.path.join(D, "*.xlsx")))},
        code={
            os.path.basename(f): sha(f) for f in sorted(glob.glob(os.path.join(code_dir, "*.py")))
        },
        **DECLARED,
    )
    with open(path.replace(".csv", "_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(path, digest, len(df))
    return path


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
