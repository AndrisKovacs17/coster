# Problem definition: input, output, data, uncertainty, MVPs

Draft v0.1, 18 October 2026. This answers the review feedback on the deck. The deck should follow
this order: input and output first, then data, then the first MVP, and only then the methods.

Items marked (H) are hypotheses or our own estimates. Example numbers are made up to show the
format.

## Feedback this answers

| # | Feedback | Section |
|---|---|---|
| 1 | Define the input and output before choosing a method | [1](#1-input-and-output) |
| 2 | What is the time series? (Answer given at the meeting: hourly inflow and outflow per cell class) | [2](#2-what-the-time-series-is) |
| 3 | How much history and how long a plan horizon does the predictor need? Give a CLI-style example of input and output. | [1](#1-input-and-output), [3](#3-history-and-plan-horizon) |
| 4 | Separate epistemic from aleatoric uncertainty. The process is "extremely deterministic", so expect very high short-term accuracy. Ignored variables create epistemic uncertainty (partial observability). | [4](#4-where-the-uncertainty-comes-from) |
| 5 | Machine stops were discussed as epistemic uncertainty | [4](#4-where-the-uncertainty-comes-from) |
| 6 | Beware of hindsight data that will not exist at launch. The shape of the data may change. | [5](#5-hindsight-data-and-changing-data) |
| 7 | Work in MVPs, starting from what you know (the production plan) | [6](#6-mvps) |

## 1. Input and output

One run per day, after the 06:00 snapshot. The run sees only what exists at 06:00 on the run date.

**Input**

| Input | Content | Source |
|---|---|---|
| Run date | The date of the 06:00 snapshot | Scheduler |
| AW snapshot, 06:00 | One row per occupied cell: cell ID, cell class, load-unit ID, load-unit type | WMS, daily |
| Cell master | Cells in service per class, valid on the run date | WMS |
| Load-unit master | Size group per load-unit type and the cell classes it may use | WMS |
| Assembly plan | Work orders with hour, quantity, shipping date. **The version known at 06:00.** | ERP export |
| Moulding and punching plan | Production orders with hour and quantity. Same version rule. | ERP export |
| Purchase orders | Arrival date, packing data | ERP export |
| Rules | Allocation cascade, held-back cells, picking and defrag rules, thresholds | `config/config.yaml` |

**Output**, per cell class and day +1 to +14:

| Field | Meaning |
|---|---|
| `fill_ratio_pred` | Median forecast of the fill ratio at 06:00 on that day |
| `lo`, `hi` | 10% and 90% bounds |
| `p_critical_by` | Chance of reaching 90% on any day up to this one |
| `no_cell` | Pallets in the median run that found no allowed cell (saturation) |
| Alert level | `ok`, `warning` or `critical`, from the thresholds in config |

Only `fill_ratio_pred` is in the current `forecast` contract. Adding `lo`, `hi`, `p_critical_by`
and `no_cell` needs a schema PR that both groups approve.

**CLI example** (target behaviour, made-up numbers):

```text
$ uv run python -m coster.pipeline.run --run-date 2026-11-02

inputs as of 2026-11-02 06:00
  snapshot     snapshot_0600_20261102.xlsx    1,512 load units, 0 rejected rows
  cell master  valid from 2026-08-18          1,819 cells in service
  assembly     version 2026-11-01 17:40       412 work orders, horizon to 2026-11-23
  moulding     version 2026-11-01 16:05       236 orders, horizon to 2026-11-30
  purchases    version 2026-10-31 09:12       58 arrivals in the next 14 days

forecast  run 2026-11-02, method flow_balance, 500 runs
  class         now   +1    +2    +3   ...  +14   P(>=90% by +2)  alert
  Low           0.78  0.80  0.83  0.85      0.81  0.04            warning on +2
  Medium        0.86  0.88  0.91  0.92      0.84  0.58            critical on +2
  High          0.71  0.72  0.74  0.73      0.70  0.00            ok
  Medium W1000  0.69  0.70  0.70  0.72      0.66  0.00            ok
  High W1000    0.64  0.66  0.67  0.67      0.63  0.00            ok

written  data/processed/forecast.parquet (70 rows)
email    critical: Medium expected at 91% on 2026-11-04 06:00 (in about 48 h)
```

## 2. What the time series is

At the meeting we answered "hourly inflow and outflow per cell class". That should be corrected
for the deck:

- **The target is the daily fill ratio per cell class**, read from the 06:00 snapshot: five series,
  one value per day. This is what the alert is about.
- **The drivers are the planned flows**: pallets in and out per cell class. The plans are known to
  the hour, so the planned flows are hourly. We sum them into the 06:00-to-06:00 window.
- **Actual flows are only known per day.** There is no usable movement log, so we get actual in and
  out by comparing two snapshots (`dataset/flows.py`). Hourly actuals exist only if Coster can
  export the timestamped entry and exit records that Zishan asked for on 16 October.

So the MVP forecasts a daily series. Hourly forecasts become possible if the entry and exit records
arrive. They would let the email say "around 14:00 on Wednesday" instead of "by 06:00 on Thursday".

## 3. History and plan horizon

Our estimates (H). The backtest will confirm or change them.

| Predictor | History to run | History to validate | Plan horizon |
|---|---|---|---|
| Persistence | 1 snapshot | 2–4 weeks of snapshots | none |
| Flow balance (rules + plans) | 1 snapshot | 2–4 weeks of snapshots **with the plan versions known on each day** | 14 days ahead, or 2–3 days for the 48 h email. Assembly (about 3 weeks), moulding (3–4 weeks) and purchases (5–6 weeks) all cover this. |
| Range from backtest errors | 2–4 weeks of flow-balance errors | Another 2–4 weeks | Same as above |
| Learned correction (gradient boosting) | About 3 months (each day gives 5 classes × 14 horizons of errors, but they are strongly correlated) | Rolling backtest | Same as above |
| Zero-shot foundation model | A few weeks of context | 2–4 weeks | Plans as covariates if the model supports them |

All history must come from **after the August layout change**. Older occupancy is not comparable.

**The bottleneck is plan versions, not snapshots.** Coster offered one week of plan versions. We
need the plan as it looked each morning, so storing the daily exports starts now (open point 6 in
the Group 1 plan). By early December that gives about 6 weeks.

## 4. Where the uncertainty comes from

The reviewer's point: the warehouse follows fixed rules ("smallest cell that fits, then the next
bigger one"), so given complete inputs the short-term forecast should be very accurate. Most of the
remaining error is **epistemic**: it comes from variables we do not observe, not from randomness in
the warehouse.

The terms follow Hüllermeier and Waegeman 2021 (`hullermeier2021uncertainty`): epistemic means
reducible with more knowledge, aleatoric means irreducible.

| Source | Type | Can we reduce it? | How |
|---|---|---|---|
| Allocation rule | None (deterministic) | n/a | Coded as the cascade. Only the allowed-class list and held-back cells are still guesses (H). |
| Machine stops delaying work orders | Epistemic (not observed) | Partly | Machine-stop logs (offered by Riccardo). Stops already running at 06:00 are known. Future stops are not. |
| Picking: when a pallbox becomes empty | Epistemic | Yes | Plan × bill of materials ÷ pieces per pallbox, plus Coster's picking rules |
| Defrag moves | Epistemic | Yes | Coster's defrag rules |
| Manual operations | Epistemic | Hardly (no log) | Shows up in the plan gap |
| Supplier arrival times | Mostly aleatoric from our side | Little | Range from past delays |
| Plan changes after 06:00 | Aleatoric at run time | No | Range from past plan-vs-actual gaps |
| Data errors (wrong class, stale cell master) | Epistemic | Yes | Validation, rejected-row report |

What this means for the work:

- **The bar for day +1 and +2 is high.** A rule-based model with complete plans should beat
  persistence clearly. If it does not, a variable is missing. That is a reason to look for it, not
  to switch to a more flexible model.
- **The backtest error is a diagnostic.** A large plan gap on certain days points to a missing
  input such as a machine stop, picking, defrag or manual moves. We should read it before modelling
  it as noise.
- **The Monte Carlo slip parameter stands in for what we don't observe.** `p_realised = 0.9` (H)
  covers machine stops and plan changes together. Once the machine-stop logs arrive, part of it
  moves into the model as a known input, and the range should get narrower.
- **The range shown on the dashboard should be the leftover uncertainty after the known rules.**
  It should not be a generic statistical band around the occupancy series.

## 5. Hindsight data and changing data

Hindsight data is information in the training or backtest data that would not exist at 06:00 on the
run date (leakage, see `kaufman2012leakage`). Concrete traps for us:

| Trap | Why it is hindsight | Guard |
|---|---|---|
| Using the final plan instead of the plan known at 06:00 | The final plan already includes delays and changes | `forecast/backtest.py::as_of`. Store every daily export with its receive time. |
| Shipping dates from a later plan version | Coster said to use the assembly-plan shipping date as the real date. That holds only for the version known at the time. | Same as above |
| Today's cell master applied to past dates | The layout changed in August | Use capacity valid on each date. Start history after the change. |
| Machine-stop logs | Written after the stop. At 06:00 only past and running stops are known. | Use them as "state at 06:00", never as future input |
| Actual flows for the forecast day | Known only after the next snapshot | The forecast for day d uses snapshots up to the run date only |
| Rules estimated from the whole period (held-back cells, allowed classes, slip rate) | The estimate has seen the test period | Estimate on the training window only, in each backtest fold |
| **Our mock data** | `dataset/mock.py` sets `inbound_planned = inbound_actual`. That means perfect plans. | Never judge the flow balance on mock data. Add plan noise to the mock before using it for comparisons. |

The data may also change shape at launch:

- Export columns may change or the files may move from Excel to the SQL staging database.
  `ingest/columns.py` maps Coster's names to ours, each file has its own schema, and rejected rows go
  to a report.
- The layout or the cell classes may change again. Capacity and classes live in config and the cell
  master, not in code.
- Plan horizons and freeze rules may change. The forecast must handle a shorter plan by falling back
  to persistence for the days the plan does not cover, and say so in the output.

## 6. MVPs

Start from what we know: the production plan and the allocation rule. Each step has a clear exit
test against the step before.

| MVP | Input | Output | Exit test |
|---|---|---|---|
| 0, done | Mock `daily_dataset` | Persistence, 14 days | Runs end to end, schemas hold |
| 1 | Snapshot + assembly and moulding plans | Deterministic flow balance, median only | On 2–4 weeks of real data, beats persistence at +1 and +2 |
| 2 | + purchase orders, shipments, picking (pallbox emptying) | Same | Plan gap per class shrinks. Note which days still miss. |
| 3 | + backtest errors | Range and `p_critical_by`, alert levels, email | Hit rate and false alarms for the 90% crossing at +2 |
| 4 | + machine-stop logs, defrag rules | Narrower range | Range narrows and coverage holds |
| 5 | Challengers (gradient boosting on the errors, a zero-shot model) | Same output format | Must beat MVP 3–4 on the same backtest and the alert scores |

The method comparison in `research/2026-10-research-sprint.md` belongs to MVP 5. It does not
decide MVP 1.

## Open points

1. Does the snapshot list load-unit IDs and types? MVP 1 needs the size group per pallet.
2. Can Coster export timestamped entry and exit records? This decides daily or hourly (section 2).
3. Daily plan exports from now on, with their receive time
4. Machine-stop logs: format, and whether a stop's end time is known while it is still running
