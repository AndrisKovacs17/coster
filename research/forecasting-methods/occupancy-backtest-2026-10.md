# Occupancy forecasting on the first Coster data drop (October 2026)

| | |
|---|---|
| What | Our own study: walk-forward backtest, nine follow-up investigations, a plan-based simulator and a pre-registered forecast |
| Data | The nine files Coster shared on 23 Oct 2026. History: daily occupancy per class, 1 Jan to 22 Oct 2026 |
| Code | [experiments/occupancy_2026_10/](experiments/occupancy_2026_10/) |
| Added by, date | Andris Kovács with Claude, 24 Oct 2026 |
| Status | done for this data drop. To be re-run as daily files arrive |

No Coster data is in this note. It gives error ratios and other relative results only, and no
stock levels, order, customer, article or machine codes. The full version with the numbers is in
the team's private material.

## Summary

1. With the occupancy history alone, a 48-hour forecast is only slightly better than persistence
   ("tomorrow equals today"). The best method cuts the error by about 5% on the stable classes and
   about 10% on the re-laid-out classes. At 1 day nothing beats persistence. The gain grows with the
   horizon: about 15% at 7 days and 20–25% at 14 days.
2. No single model wins. A simple mean-reversion model, LightGBM and Chronos-2 zero-shot are about
   equally good. Their average is the best or close to the best at every horizon.
3. Nine follow-up investigations looked for a large gain with this data and found none. The
   occupancy series has no hidden structure left. The realistic ceiling at 48 hours is close to
   where we are.
4. The error is concentrated in a few large moves, mostly drops (dispatches). If those were known
   in advance, the error could fall to roughly 0.56–0.67 of persistence. This is an upper bound,
   not an expected value.
5. The plan and the dispatch dates are the only route to a large gain. The data has no past plan
   versions, so this cannot be backtested. We built a plan-based simulator and froze its forecast
   on 24 Oct (pre-registration). From 26 Oct every daily file scores it against the statistical
   ensemble.

## Data and what it allows

- **Occupancy history (file 5)** is the target series: occupied and total cells per day, area
  and class. It behaves like an end-of-day state.
- **The re-layout** ran from 30 Jul to 21 Aug. Medium W1000 and High W1000 kept their meaning
  across it (Set A, 8 months of test origins). Low, Medium and High changed (Set B, only about
  6 weeks of test origins after enough training days).
- **The cell table (file 4)** lists every cell with its load unit ID, type, article, quantity,
  quality and last change date. It is extracted during the working day, not at 06:00 (see
  "Data facts" below). Two consecutive cell tables give the actual flows per class, as planned in
  `daily_flows` (data-forecasting plan, section 7).
- **The plan (file 1)** is one version. It holds only work orders that start on or after the file
  date. It cannot be used for past origins without leaking the future.
- **Deposits and releases (files 2 and 3)** cover one day.
- **The inbound file and the picking history** are partial. They explain almost none of the daily
  change (R² ≤ 0.03).

## Protocol

- **Origin and target.** Origin t is a day whose occupancy is known. The target is occupied cells
  at t+h, for h = 1, 2, 3, 5, 7 and 14 days. h = 2 stands for the 48-hour alert.
- **Test sets.** Set A: Medium W1000 and High W1000, origins 1 Mar to 21 Oct. Set B: Low, Medium and
  High, origins 12 Sep to 21 Oct.
- **Training.** Walk-forward. Models refit weekly, using only rows whose target day is on or
  before the refit date. Hyperparameters were fixed in advance, not tuned on test origins.
- **Metric.** MAE in cells, divided by the MAE of persistence on the same rows. Below 1 is better.
  90% confidence intervals come from a block bootstrap over 7-day blocks.
- **Alerts.** Brier score, AUC and precision/recall for "the class is at or above a threshold on
  day t+h".
- **Rules for every investigation.**
  - Every number comes from a saved script output.
  - Every claim is labelled:
    - VALIDATED: out-of-sample, by this protocol.
    - DESCRIPTIVE: measured on the data, not a forecast test.
    - HYPOTHESIS: not tested.
  - Negative results are reported.
  - The number of variants tried is counted.
  - A result that looks too good is checked for leakage first.

## Results: point forecasts (VALIDATED)

Ensemble = mean of mean-reversion, LightGBM and Chronos-2. In Set B, Chronos-2 sees only the days
after the re-layout.

| Horizon (days) | Set A ratio [90% CI] | Set B ratio [90% CI] |
|---|---|---|
| 1 | 1.01 [0.98, 1.06] | 0.97 [0.89, 1.06] |
| 2 | 0.95 [0.90, 1.01] | 0.91 [0.84, 0.97] |
| 3 | 0.93 [0.87, 0.99] | 0.89 [0.79, 0.99] |
| 5 | 0.89 [0.82, 0.97] | 0.81 [0.62, 0.98] |
| 7 | 0.86 [0.76, 0.95] | 0.83 [0.63, 1.01] |
| 14 | 0.80 [0.69, 0.91] | 0.74 [0.54, 0.90] |

Single methods, Set A:

| Method | h = 2 | h = 7 | h = 14 |
|---|---|---|---|
| Mean reversion to the 28-day mean | 0.96 | 0.88 | 0.83 |
| LightGBM (small, regularised) | 1.02 | 0.95 | 0.86 |
| Chronos-2 zero-shot, weekday and holiday covariates | 0.98 | 0.88 | 0.81 |
| SARIMAX(1,0,1)(1,0,0,7) | 1.01 | 0.86 | 0.74 |
| Ridge | 1.03 | 0.97 | 0.83 |
| Weekday profile of changes | 1.04 | 1.01 | 1.00 |
| Seasonal naive (7 days) | 1.38 | 1.47 | 1.52 |

Notes:

- **SARIMAX in Set B** works only when fitted on the days after the re-layout. A window across the
  re-layout breaks it.
- **Set B number depends on the definition.** Its value at h = 2 moves between 0.905 and 0.946
  with the Chronos context (120 days vs post-layout only) and the row set. The table uses the
  post-layout context on all rows.
- **Pipeline fix.** The independent audit found that the early Set B origins used pre-layout days
  in their 28-day mean. Fixing this moves Set B at h = 7 from 0.83 to 0.81. Nothing changes at
  h = 2.

## Results: alerts and ranges (VALIDATED)

Set A, h = 2, threshold events:

| Method | Brier | AUC |
|---|---|---|
| Ensemble, Gaussian probability | 0.160 | 0.81 |
| Persistence, Gaussian probability | 0.159 | 0.81 |
| Logistic regression on the event | 0.182 | 0.76 |
| LightGBM classifier on the event | 0.184 | 0.74 |
| Quantile regression | 0.193 | |
| "Above the threshold today" rule | 0.228 | 0.73 |
| Climatology (base rate) | 0.226 | |

**Event models.** Classifiers trained directly on the event do worse than the Gaussian
probability from the ensemble. The Brier difference for logistic regression is +0.022 [0.010,
0.035]. A hazard model is also worse.

**Calibration.** The Gaussian probability is well calibrated: slope 0.96, ECE 0.02. Its skill
over climatology is 0.29 at 2 days, 0.19 at 3, 0.10 at 5 and 0.03 at 7. The useful alert horizon
is therefore 2–3 days.

**Alert rule.** Alert when p ≥ C_false / (C_false + C_missed), with the cost ratio to be agreed
with logistics:
- At p ≥ 0.2, 22 of 31 new threshold crossings were flagged at least 48 hours ahead, with about
  2.4 false alarms per week per series.
- At a 1:4 cost ratio, the Gaussian rule costs 0.44 per decision, against 0.56 for "above the
  threshold today".

**Ranges.**
- An 80% band built from the last 60 realised errors covers 73–91% of outcomes.
- Chronos-2's own 80% band under-covers (66–77%) and needs conformal recalibration.

**Medium.** Medium is almost always full, so a fill threshold carries no information there. Use
the Medium plus High family, or the "no cell" count (proposal C5 in the plan).

## The nine follow-up investigations

| Direction | Question | Result | Label |
|---|---|---|---|
| Noise anatomy | Is there structure left in the series? | No. Most of the 48-hour error is innovation noise. Realistic ceiling about 0.92–0.94 for Set A. Weekday, month-end, holidays, the two areas, logit or free-cell targets: no gain. | VALIDATED |
| Cascade | Does the allocation cascade help (forecast the sum, then split)? | No. With the mean-reversion and LightGBM ensemble, split vs direct: Set A h = 2: 0.954 vs 0.959. Set B h = 2: 0.938 vs 0.913, worse. VAR and reduced-rank models: no gain. Classes co-move rather than offset each other. | VALIDATED |
| Stock survival | Is outflow predictable from the age of the stock or the dispatch dates? | The plan gives a dispatch date for only about 1% of stored load units (about 5% when matched on the sales order alone). An age feature cannot be rebuilt for past days without leakage. | DESCRIPTIVE |
| Plan inflow | How much does the plan say about the next days? | The plan has no past work orders, so no backtest is possible. Lagged recorded flows do not help: 36 paired tests, 5 significant (2 better, 3 worse), about what chance gives. | VALIDATED (negative), DESCRIPTIVE |
| Event models | Is forecasting the alert event directly better? | No. See the alerts section. | VALIDATED |
| Pooling and transfer | Can other classes or pre-layout data make up for the short history? | No measurable gain. Pre-layout data rescaled to fill shares is already enough. The learning curve is still falling at 240 days (h = 2: 0.94 with 60 training days, 0.87 with 240). | VALIDATED |
| Forensics | Can past gross flows be rebuilt from the cell table (load unit ID counters, change dates)? | Only for one load unit family, whose daily count equals a column already in the picking file. No class-level gross inflow or outflow. | VALIDATED (negative), DESCRIPTIVE |
| Independent audit | Did the first round rule out a large gain by mistake? | No. A recomputation from the raw file matched to the cell. One pipeline issue fixed (above). Plus the error anatomy and the data ranking below. | VALIDATED |
| Plan simulator | Can the plan be tested at all? | Built, checked where one day allows, and pre-registered (below). | DESCRIPTIVE, HYPOTHESIS |

Where the error comes from (audit, DESCRIPTIVE):
- The top 20% of rows carry about half of the persistence error.
- Moves larger than 1.5 standard deviations are 10–14% of rows but 33–44% of the error. 58–69% of
  them are drops.
- About 60% of false alarms are a class above the threshold that then drops sharply.
- Knowing the aggregate recorded flows perfectly (an oracle test) still gives no gain (0.975–0.99).
  So the information has to be at class and load unit level.

Two investigations caught their own bugs:
- A loop that predicted with the final models gave ratios of 0.47–0.64.
- An aggregation that dropped rows gave 0.50.
Both were caught by the "too good, check for leakage" rule. The bugs were fixed and the outputs
quarantined.

## Data facts that change how we model

- **Do not use the cell table as the 06:00 origin.** It is extracted during the working day:
  every empty Medium and High cell on the extraction day had changed that same day. The history
  file is the target.
- **The last change date.** For finished goods (one load unit ID family) it is in practice the
  day the unit came in: rank correlation 0.98 with the ID order. For the other families it can be
  any change of the cell.
- **The inactive weekend day is not the same all year.** In some months the Monday record repeats
  Sunday's, in others the Sunday record repeats Saturday's. A fixed day-of-week encoding mixes two
  regimes. A recency-based activity flag helps at 1 day (0.990 vs 1.019, significant) and slightly
  at 2 days (0.945 vs 0.952, borderline). A shift calendar from Coster would be better.
- **The plan does not cover all production.** On the one day where plan and actual overlap, the
  plan covers roughly 70% of what was produced.
- **Dead capacity.** Some cells have been disabled for a long time, and some load units have been
  blocked for weeks. Ask Coster whether to count them as capacity.

## What this means for the forecast ladder

The rungs are in the data-forecasting plan, section 8.

1. **Persistence** stays the baseline. At 1 day it is the forecast.
2. **Statistical ensemble.** Mean reversion, LightGBM and Chronos-2 zero-shot, with a 60-day error
   band, is the stand-in until plan versions exist. It is cheap and robust.
3. **Flow balance** (rung 2) is built as an experiment. It can only be validated prospectively,
   with the daily files.
4. **More complex models** (rung 3 and 4) did not help on this data. TabPFN-TS is untested: it
   needs a licence key.
5. **Alerts.** Use the Gaussian probability, with the threshold set from the cost ratio. Recalibrate
   window events ("full within 2–4 days") with a one-parameter Platt fit.

## Pre-registration (24 Oct 2026)

The forecasts below were frozen before any later data existed. Only their SHA-256 hashes are
public: they prove that the files are not changed afterwards. The files themselves contain Coster
data and stay in the team's private storage.

| File | SHA-256 | What it states |
|---|---|---|
| `prereg_forecast_origin2026-10-22_created20261024T102128Z.csv` | `4aa0d5e7f63313c46ee9ab9a3fd6715f8771867c7507dc82e0da70d6db39d71d` | 405 rows, 23 Oct to 6 Nov. Six methods per class and day: persist, ens, persist_f4, sim_f5, sim_f4 (primary), sim_f4_raw. Quantiles 10/50/90 and threshold probabilities |
| `PREREG_auditor_forecast_origin20261022.csv` | `1909e8e84ff76941f021e019e0625ef9293d7b255eebb5bed4ea3b2a225429a0` | Activity-aware statistical forecast |
| `PREREG_auditor_activity_20261023-30.csv` | `0e9f02013f9416946fa909e6b42e2b7ad6210c539869846658fdb662ba32c98f` | Which days of 23–30 Oct will show activity |
| `prereg_forensics_20261024.csv` | `f8f778154f4345cdecb226572cd82ce71a58296dcc717a3c9fb1fe7caf24ab5a` | Three hypotheses about ID counters, the picking file and the cell table timing |

**Decision rule, fixed in advance.** After at least 15 scored origins (about 3 weeks), we say
"the plan helps" if both hold:
- the 90% bootstrap CI of MAE(sim_f4) / MAE(persist_f4) at h = 2–7 lies below 1;
- MAE(sim_f4) / MAE(ens) is below 0.95.

Otherwise we report "no demonstrated gain".

Our expectation (HYPOTHESIS): 0–15% gain at 2–7 days on Medium W1000 and High W1000, and none on
Medium and High. Most finished goods have no known dispatch date, and the plan misses part of
production.

`run_daily.py` scores all earlier registrations and freezes a new one every day.

## What to ask Coster for, ranked by expected value

1. **A dispatch schedule for the stock already in the warehouse:** sales order to expected
   dispatch date. It targets the large drops, which carry most of the error and most false alarms.
2. **A daily archive of every file from now on**, especially plan versions and cell tables. This
   gives honest as-of backtests and the actual flows per class.
3. **A movement log per load unit:** time, cell, in or out, and reason.
4. **The shift and plant calendar.** Cheap, small gain.
5. **Clarifications:**
   - What the deposits and releases count (several machines show more than 24 hours of output in
     one day).
   - When the cell table is extracted.
   - What the load unit ID prefixes mean.
   - Why some work orders are produced outside the plan.

## Limits

- Set B has about 6 weeks of test origins, so its intervals are wide.
- Each horizon was tested on one 8-month (Set A) or 6-week (Set B) period. Results may not hold
  in other seasons.
- The simulator's assumptions are documented in its code and in the manifest of the registered
  forecast. Several assumptions rest on one day of data.
