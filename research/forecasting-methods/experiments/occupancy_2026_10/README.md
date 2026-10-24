# Occupancy backtest, plan simulator and pre-registration (October 2026)

Code behind [../../occupancy-backtest-2026-10.md](../../occupancy-backtest-2026-10.md).
These are research scripts, not part of the `coster` package.

**Coster's data never goes into the repo.**
- The scripts read Coster's files from a folder you pass on the command line, or from
  `COSTER_DATA_DIR`.
- Every output goes to a folder outside the repo: results, forecasts and scores all contain
  Coster data.
- Coster's internal codes (pallet material prefixes, the finished-goods article prefix, wide load
  unit types) live in `coster_codes.json` next to the data. Fill it in from
  `coster_codes.example.json` and never commit it.

## Setup

Use a separate environment. The project environment does not include these packages.

```bash
python -m venv .venv-occ
.venv-occ/bin/pip install pandas numpy scipy scikit-learn lightgbm statsmodels openpyxl
.venv-occ/bin/pip install torch chronos-forecasting   # Chronos-2, CPU is enough
```

Run the scripts from this folder. They import each other.

## Files

| File | What it does |
|---|---|
| `history.py` | Finds Coster's files and loads the occupancy history (file 5) per class |
| `backtest.py` | Walk-forward backtest, Set A and Set B: persistence, seasonal naive, weekday profile, mean reversion, Ridge, LightGBM, SARIMAX |
| `chronos_backtest.py` | Adds Chronos-2 zero-shot (three context variants) and a post-layout SARIMAX |
| `evaluate.py` | MAE ratios to persistence, block-bootstrap CIs, threshold alerts, interval coverage |
| `sim_lib.py`, `sim_mc.py` | Plan-based flow-balance Monte Carlo simulator (finished-goods classes) |
| `forecast_sim.py` | Simulator forecasts and a sensitivity analysis |
| `forecast_stat.py` | Statistical forecasts from the newest day (persist, ens, persist_f4) |
| `prereg.py` | Freezes one pre-registered forecast: CSV, `.sha256` and a manifest |
| `score.py`, `score_pool.py` | Score registered forecasts against newer files, pooled over origins |
| `run_daily.py` | Daily driver: score all earlier registrations, freeze a new one |
| `make_synthetic_test.py` | Fake future days for testing the scoring (not real data) |

## Backtest

```bash
export COSTER_DATA_DIR=/path/to/coster/files      # outside the repo
OUT=/path/outside/the/repo/backtest
python backtest.py "$OUT"                # about 10 min on 2 cores
python chronos_backtest.py "$OUT"        # downloads Chronos-2 on first use
python evaluate.py "$OUT"                # ratio_table.csv, ratio_ci.csv, alert_eval.csv, coverage.csv
```

## Daily pre-registration and scoring

Put each day's files, and a copy of `coster_codes.json`, in a folder. Then run:

```bash
WORK=/path/outside/the/repo/prereg       # holds prereg_<origin>/ and scores_<date>/
python run_daily.py --data /path/to/day_folder --static /path/to/one_off_files \
    --base "$WORK" --results "$OUT/bt2_results.pkl"
```

`run_daily.py` never overwrites a registered forecast. `score.py` stops if a registered file's
hash no longer matches its `.sha256`. The decision rule is in `prereg.py` and in the findings
note.

The forecast registered on 24 Oct 2026 was produced by the first version of this code, before it
was moved into the repo. Its manifest lists the hashes of that code. The repo version is the same
logic with configurable paths and the codes moved to `coster_codes.json`.
