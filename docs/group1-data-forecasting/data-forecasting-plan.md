# Data and forecasting plan (Group 1)

Draft v0.4, 15 October 2026. For the Group 1 folder in the repo.

What changed from v0.3:

- Most questions for Coster are already answered in our material. Section 1 lists the answers. Section 2 keeps only what is still open.
- The plan is now a concrete coding plan in Python. It covers setup, repo layout, how the warehouse looks in code, each module, tests, and who builds what by when.
- The code sketches below were run and tested with pandas 3.0, numpy 2.5 and pandera 0.34. They are starting points, not finished code.

Items marked (H) are hypotheses. Nothing here promises forecast accuracy.

## 1. What we already know

| Topic | What we know | Source |
|---|---|---|
| Flow | Every pallet passes through the AW. Moulding, punching and suppliers bring pallets in. Assembly picks from it and returns finished goods and partial pallboxes. Shipping takes pallets by truck to customers or to the central warehouse. Overflow goes to the 800-slot floor buffer and comes back when needed. | Briefs, flow diagram |
| Cells | 1,819 cells in use (1,824 positions) in 5 classes: Low 1,049, Medium 248, High 186, Medium W1000 144, High W1000 192 | Briefs |
| Layout change | The warehouse changed its shape in August. Older data is not directly comparable. | Team B |
| Snapshot | Every day at 06:00 the WMS saves the AW occupancy. It can be shared. | Kick-off, briefs, Coster 6 Oct |
| Allocation | The smallest cell that fits. If that type is full, the next bigger one. A fixed rule, no manual override. Each load-unit type may use only certain cell types. | Kick-off, flow diagram |
| Defrag | Moves small pallets back to small cells in idle time, above a configurable saturation threshold. 25–80 missions a week. Coster will send the defrag rules. | Kick-off, briefs, Coster 6 Oct |
| Picking | An LGV takes a pallbox to the machine. The operator takes some boxes and the partial pallbox returns. The cell frees only when the pallbox is empty (about 130 a week). Triggered by an operator call, or automatically when a machine runs low. Coster will send the picking rules and the LGV picking missions. | Kick-off, briefs, Team B, Coster 6 Oct |
| Retrieval | FIFO | Kick-off |
| Shipments | Use the shipping date in the assembly plan as the real date. Coster can add rules for special shipments (for example Argentina). | Coster 6 Oct |
| Purchased parts | Only next week's need goes into the AW. The rest goes to the floor buffer. The purchase order carries the packing data. Coster will send the rules for purchased components, which include ground-buffer moves. | Kick-off, Coster 6 Oct |
| Moulding inflow | Follows from the moulding plan | Coster 6 Oct |
| Plans | Assembly about 3 weeks ahead, next week frozen every Wednesday. Moulding 3–4+ weeks. Purchase orders 5–6 weeks. About 90% of the next 10 days is realised. Production timing is known to the hour. | Kick-off |
| Quarantine (QC) | Skip it for this scope | Coster 6 Oct |
| Manual operations | No log. Ignore them. | Coster 6 Oct |
| Saturation history | No records exist | Coster 6 Oct |
| Movement log | Hard to use without context. Coster offers the picking and defrag rules instead. Stacker crane missions are not available. | Coster 6 Oct |
| Plan versions | One week offered | Coster 6 Oct |
| Metal containers | About 300. They always need a cell, empty or full, mostly small cells, little effect on capacity. Empty metal containers return to the AW. Plastic ones do not. | Team B, kick-off |
| Pallet layers | Pallets in the AW hold 1 to 6 layers | Team B |
| Warning time | Coster wants an email at least 2 days ahead ("in about 40–48 h the AW will be full") and a dashboard per cell type | Kick-off |
| Levels | The WMS shows yellow above 80% and red above 90% (as remembered at the kick-off) | Briefs |
| Data delivery | Excel exports through the shared Drive. 2–5 years of history exist in Coster's systems. | Kick-off |

## 2. Still open (meeting on 16 October)

1. **Question.** On 20 May the email counted 22 free places while the WMS showed 293. What did the 22 count? Are 80% and 90% the levels logistics works with?
2. **Question.** What changed in August? Are the cell counts above the current ones?
3. **Question.** Does the snapshot list each load unit (ID, load-unit type, item, quantity)? Does a pallbox keep the same ID when it comes back from picking? Section 7 depends on this.
4. **Question.** Are transfers to the central warehouse in the assembly plan, or are they separate?
5. **Request.** Daily occupancy per class since the August change. It is five numbers a day. Without it, no backtest is possible.
6. **Request.** The plan exports every day from now on. We store each version, so by December we have plan history for an honest backtest.
7. **Question.** How should the tool fit into Coster's systems? The briefs say it should fit the existing systems and later read from the SQL Server staging database. The form is open:
   - Do you work with a microservice architecture? If so, in which language and on which platform?
   - Should we build our forecast as such a service in your language? Or can it stay a Python service that your systems call through an API, for example in a Docker container? Or is it a fully separate application with its own dashboard?
   - Should the dashboard be a separate web page, or part of a screen you already use?
   - For the prototype, are Excel exports fine, or should we read from the staging database from the start?

Why 110 wide cells stayed free on 20 May will show in the master data, in the list of classes each load-unit type may use. That is a data check, not a question.

## 3. What Group 1 builds

```
Coster Excel exports ──> ingest ──> dataset ──> forecast ──> (alerts, dashboard: Group 2)
                    validated tables  daily_dataset   forecast
```

The idea in one paragraph. The warehouse state is a small table: how many pallets of each size group sit in each cell class. Each forecast day adds the planned inflow through the allocation cascade and removes the planned outflow. Pallets that find no allowed free cell are counted as "no cell". That is the saturation event. Repeating this a few hundred times with random plan slips gives a range and the chance of crossing a threshold.

## 4. Setup

**Python 3.11+.** Use **uv** for the environment and dependencies. It creates the virtual environment, pins versions in a lock file, and runs commands the same way on every laptop. pip with venv works too.

```bash
uv init --package coster
uv add pandas numpy pyarrow openpyxl pandera pyyaml
uv add --dev pytest ruff pre-commit
uv run pytest
```

| Package | Use |
|---|---|
| pandas, numpy | Tables and arrays. The data is small (1,819 cells), so nothing heavier is needed. |
| openpyxl | Reading Coster's Excel exports |
| pyarrow | Parquet files in `data/` |
| pandera | Schemas for the shared tables and for each loaded file |
| pyyaml | `config/config.yaml` |
| pytest, ruff, pre-commit | Tests, formatting and linting, run before every commit |
| later: scikit-learn or LightGBM, mapie | Only for rung 3 in section 8, when there is enough history |

**Coster's data never goes into git.** We signed a confidentiality agreement. The repo's `.gitignore` does not yet exclude data. Add `data/` to it in the first PR. Notebooks go in `notebooks/`, with outputs stripped (`nbstripout`), because outputs can contain data.

## 5. Repo layout (Group 1 part)

```
coster/
├── pyproject.toml
├── config/config.yaml
├── data/                  # git-ignored
│   ├── raw/               # Coster files, untouched
│   ├── interim/           # validated parquet, one per file
│   └── processed/         # daily_dataset.parquet, forecast.parquet
├── src/coster/
│   ├── common/   config.py  schemas.py  io.py
│   ├── ingest/   loaders.py  columns.py
│   ├── dataset/  build.py  flows.py  windows.py
│   ├── forecast/ allocation.py  flow_balance.py  uncertainty.py  baselines.py  backtest.py
│   └── pipeline/ run.py
├── tests/
└── notebooks/
```

With this `src` layout, ARCHITECTURE.md's `python -m pipeline.run` becomes `python -m coster.pipeline.run`. It is a small change. Agree on it in the first PR.

## 6. How the warehouse looks in code

**Cell classes:** a fixed list in config with height and width.

**Size groups.** We group the 25 load-unit types by size. The master data gives each type a size. The briefs list six sizes in the AW: 650×800, 650×1000, 1200×800, 2200×800, 1200×1000 and 2200×1000.

**Cascade.** Each size group has an ordered list of the classes it may use. The first entry is its own class. Until Coster's allowed-class list arrives, the default order is same width first, then wider (H).

**Held-back cells.** These are the cells a class keeps free for its own pallets. Start with the 20 May values (45 free Medium W1000, 65 free High W1000) and re-estimate them from snapshots (H).

**State.** A pandas DataFrame, rows = size groups, columns = cell classes, values = pallet counts. Five columns and six rows. Every step is cheap.

```yaml
# config/config.yaml (excerpt)
snapshot_hour: 6
cascade:                       # default until Coster's allowed-class list arrives (H)
  650x800:   [Low, Medium, High, Medium W1000, High W1000]
  650x1000:  [Medium W1000, High W1000]
  1200x800:  [Medium, High, Medium W1000, High W1000]
  2200x800:  [High, High W1000]
  1200x1000: [Medium W1000, High W1000]
  2200x1000: [High W1000]
held_back: {Medium W1000: 45, High W1000: 65}   # 20 May values, re-estimate (H)
forecast: {horizon_days: 14, method: flow_balance, p_realised: 0.9, n_runs: 500, seed: 42}
thresholds: {warning: 0.80, critical: 0.90}
```

## 7. Ingest and dataset

### Ingest rules

- One loader function per Coster file. It returns a validated DataFrame.
- Keep `data/raw` untouched. Write each validated table to `data/interim` as parquet.
- Read Excel as text first (`pd.read_excel(path, dtype=str)`), then cast each column on purpose. Excel guesses types badly, for example IDs with leading zeros, or dates.
- Coster's column names map to ours in `ingest/columns.py`. If an export changes, only that mapping changes.
- Timestamps are Coster's local time (H, the data request asks them to confirm).
- Validate with a pandera schema per file. Write rejected rows to a report. Do not drop them silently.
- The first files are the cell master, the load-unit master, the snapshot, the assembly plan and the moulding plan.

### Time windows

The daily row for date d covers events from 06:00 on d−1 up to 06:00 on d. So a shipment dated d shows up in the snapshot of d+1.

```python
def snapshot_date(ts: pd.Series, hour: int = 6) -> pd.Series:
    """Date of the first snapshot that sees an event at ts."""
    return (ts - pd.Timedelta(hours=hour)).dt.normalize() + pd.Timedelta(days=1)
```

### Actual flows from two snapshots

There is no usable movement log. If the snapshot lists load-unit IDs (open point 3), two consecutive snapshots give the actual flows per class:

- a new ID is a filled cell
- a missing ID is a freed cell
- an ID in another class is an internal transfer

```python
def daily_flows(prev: pd.DataFrame, curr: pd.DataFrame) -> pd.DataFrame:
    """Flows per class between two snapshots, matched on udc_id."""
    p = prev.set_index("udc_id")["cell_class"]
    c = curr.set_index("udc_id")["cell_class"]
    new = c[~c.index.isin(p.index)].value_counts()
    gone = p[~p.index.isin(c.index)].value_counts()
    both = p.index.intersection(c.index)
    moved = pd.DataFrame({"src": p[both], "dst": c[both]})
    moved = moved[moved["src"] != moved["dst"]]
    net = moved["dst"].value_counts().sub(moved["src"].value_counts(), fill_value=0)
    out = pd.DataFrame({"inbound_actual": new, "outbound_actual": gone, "internal_transfer": net})
    return out.reindex(CELL_CLASSES).fillna(0).astype(int)
```

With these flows, yesterday + in − out ± transfers = today holds by construction. The useful check becomes the **plan gap**: actual flows minus planned flows, per class and day. A large gap means a flow that the plans miss, such as manual moves or ground-buffer returns. If a pallbox gets a new ID after picking, it shows as one out and one in. That inflates both flows, but the occupancy stays right.

### `daily_dataset`

| Column | How it is built |
|---|---|
| `capacity` | Cells in service per class, from the cell master |
| `occupied`, `free`, `fill_ratio` | Count of the snapshot per class |
| `inbound_actual`, `outbound_actual`, `internal_transfer` | `daily_flows` |
| `inbound_planned`, `outbound_planned` | Plan pallets per window, each mapped to its own class |
| `qc_hold` | Empty, because Coster asked us to skip QC |

The schema is the first PR, and both groups approve it:

```python
import pandera.pandas as pa

daily_dataset_schema = pa.DataFrameSchema(
    {
        "date": pa.Column("datetime64[ns]"),
        "cell_class": pa.Column(str, pa.Check.isin(CELL_CLASSES)),
        "capacity": pa.Column(int, pa.Check.ge(0)),
        "occupied": pa.Column(int, pa.Check.ge(0)),
        "free": pa.Column(int, pa.Check.ge(0)),
        "fill_ratio": pa.Column(float, pa.Check.in_range(0, 1)),
        "inbound_planned": pa.Column(float, nullable=True),
        # ... the other flow columns and qc_hold, all nullable floats
    },
    checks=pa.Check(lambda df: df["occupied"] + df["free"] == df["capacity"]),
    unique=["date", "cell_class"],
    strict=True,
)
```

`forecast_schema` follows the same pattern: `horizon_day` between 1 and 14, `fill_ratio_pred` between 0 and 1, unique on `run_date, cell_class, horizon_day`.

## 8. Forecast engine

Rungs, in order. A rung stays only if it beats the one below on the alerts it gives, not only on average error.

1. **Persistence.** Every day equals the last snapshot. Three lines of code. It is the baseline everything is measured against.
2. **Flow balance with the cascade.** The core, below.
3. **Learned correction** of rung 2's errors (gradient boosting). Only with months of history.
4. **Probabilistic candidates** from earlier drafts (fuzzy time series, a pretrained time-series model). Only if history allows a fair test.

### Allocation and one day of flow balance

```python
def allocate(n, order, free, held_back):
    """Place n pallets along the cascade. order[0] is the pallet's own class.
    Other classes keep held_back cells free.
    Returns pallets placed per class, and pallets that found no cell."""
    placed = {}
    for i, cls in enumerate(order):
        room = free[cls] - (0 if i == 0 else held_back.get(cls, 0))
        take = max(0, min(n, room))
        if take:
            placed[cls] = take
            free[cls] -= take
            n -= take
        if n == 0:
            break
    return placed, n


def step(state, inflow, outflow, capacity, cascade, held_back):
    """One day. Inflow first, then outflow, which is the cautious order for alerts."""
    state = state.copy()
    free = (capacity - state.sum(axis=0)).to_dict()
    no_cell = 0
    for group, n_in in inflow.items():
        placed, rest = allocate(n_in, cascade[group], free, held_back)
        for cls, k in placed.items():
            state.loc[group, cls] += k
        no_cell += rest
    for group, n_out in outflow.items():
        state.loc[group] = remove_proportional(state.loc[group], n_out)
    return state, no_cell
```

`remove_proportional` takes outgoing pallets of a size group from the classes in proportion to where that group sits. Snapshot-level tracking per load unit can replace this later.

**Inflow per day and size group** comes from the moulding and punching plans, finished goods from the assembly plan, and purchase orders after the weekly cap rule.

**Outflow per day and size group** comes from shipments (the assembly plan date) and emptied pallboxes. Emptied pallboxes come from plan × bill of materials ÷ pieces per pallbox, checked against the emptied-pallbox log and Coster's picking rules. Metal containers come back and take a cell again.

**Defrag** is added as one more step once Coster's rules arrive. Above the threshold, it moves pallets from a bigger class back to their own class if that class has free cells.

### Range and threshold risk

"About 90% of the next 10 days is realised." We read this as: each planned pallet happens on its day with probability 0.9, otherwise it slips by a day (H). The value lives in config.

```python
def realise(planned, p, rng):
    """Each planned pallet happens on its day with probability p, else slips a day."""
    out, carry = np.zeros_like(planned), 0
    for d, n in enumerate(planned):
        due = n + carry
        out[d] = rng.binomial(due, p)
        carry = due - out[d]
    return out


def summarise(paths, capacity, critical):
    """paths: occupied cells, shape (runs, days, classes)."""
    fill = paths / capacity.reindex(CELL_CLASSES).to_numpy()
    lo, mid, hi = np.quantile(fill, [0.1, 0.5, 0.9], axis=0)
    crossed = np.maximum.accumulate(fill >= critical, axis=1)
    return {"pred": mid, "lo": lo, "hi": hi, "p_critical_by": crossed.mean(axis=0)}
```

`simulate` runs `realise` and `step` 500 times with a fixed seed. It returns the occupied cells and the no-cell count per run and day. The median goes into `fill_ratio_pred`. The 10–90% range and `p_critical_by` wait for proposals C1 and C2.

## 9. Backtest and tests

**As-of rule.** A forecast for run date t may only use what was known at 06:00 on t.

```python
def as_of(versions, t, key="order_id"):
    """Latest plan version of each order that was known at time t."""
    known = versions[versions["version_created_at"] <= t]
    latest = known.groupby(key)["version_created_at"].transform("max")
    return known[known["version_created_at"] == latest]
```

**Two replays:**

- **Oracle replay:** past days with the actual flows from `daily_flows`. It tests the cascade, the held-back cells and the rules, without plan error. This is the "flows balance" gate.
- **Realistic replay:** past days with the plan versions known at the time. It works only for days with stored versions.

**Metrics** per class and horizon:

- error in cells
- share of real values inside the 10–90% range
- warning lead time
- missed and late warnings
- false alarms per month

**Unit tests**, each on a tiny hand-made table, never on Coster data:

- `allocate` follows the cascade, respects held-back cells and reports pallets with no cell.
- `step` conserves pallets: before + in − out = after + no cell.
- `daily_flows` closes the balance between two snapshots.
- `snapshot_date` puts 05:59 and 06:00 in the right window.
- `simulate` gives a range with lo ≤ hi and a `p_critical_by` that never decreases.
- `as_of` never returns a version from after t.
- **Leakage guard:** a forecast for t is the same whether or not the input also holds data from after t.
- Both contract schemas accept a valid table and reject a broken one.

## 10. Who builds what, by when

Group 1 has two people. One takes the data role and one the forecast role. The phases and dates follow the plan in the briefs.

| Phase | Data role | Forecast role | Gate |
|---|---|---|---|
| **Day 1** (both) | uv project, `.gitignore` with `data/`, package skeleton, `config.yaml`, contract schemas, CI running pytest and ruff | same | First PR approved by both groups |
| **Simulator v0, until 25 Oct** | Loaders for cell master, load-unit master and snapshot. Size groups. `daily_flows`. `daily_dataset` for the first week of data. Plan loaders. | `allocate`, `step`, persistence and flow balance on toy data. Then the oracle replay on the first week. | Flows balance |
| **Uncertainty, 26 Oct – 15 Nov** | Plan-version store, `as_of`, picking estimate from the bill of materials, defrag rule from Coster's rules, longer history if Coster sends it | `realise`, `simulate`, `summarise`, backtest harness, metrics per horizon. PR for C1 and C2 with Group 2. | 48 h error known |
| **Alerts and UI, 16 Nov – 6 Dec** | Daily run on fresh exports, data issues | Shadow run from mid-November, tuning, support for Group 2 | Coster feedback |
| **Final event, mid-December** | Runbook and handover | Results and demo | |

Until Coster's files arrive, the loaders are tested on the synthetic files from the simulation workstream. Those files use the same columns as the data request. Results on synthetic data only test the code.

## 11. How we write the code

- Functions take DataFrames and return DataFrames. No global state.
- Every number comes from config. Nothing is hard-coded.
- Use type hints and short docstrings. ruff formats and lints.
- Notebooks are for exploring only. Logic moves into the package within a day.
- One branch per task. Small PRs with at least one review.
- Every function gets a test. Tests use tiny tables, never Coster data.
- Use a fixed random seed, and `logging` instead of `print`.

## 12. The shared tables (proposals, not applied)

`daily_dataset` and `forecast` stay as in ARCHITECTURE.md. These need a PR approved by both groups:

- **C1:** `fill_ratio_lo` and `fill_ratio_hi` in `forecast`
- **C2:** `p_warning_by` and `p_critical_by` in `forecast`
- **C3:** the expected inflow and outflow behind each forecast day, so alerts can name drivers
- **C4:** stored plan versions, inside Group 1 only
- **C5:** pallets with no cell and free compatible cells per size group and day. This is what "full" means for a pallet.

One change from v0.3: `fill_ratio_pred` now stays between 0 and 1, because the cascade only uses free cells. What does not fit is counted in C5.

## Appendix: variables and where they live in code

| Variable | Source | In code |
|---|---|---|
| Occupied cells per class | Snapshot | `dataset/build.py` |
| Load-unit type and size group per cell | Snapshot, load-unit master | state rows |
| Cells in service | Cell master | `capacity` |
| Allowed classes per load-unit type | Load-unit master | `cascade` in config |
| Held-back wide cells | Estimated from snapshots | `held_back` in config |
| Moulding and punching inflow | Plans | inflow |
| Finished goods | Assembly plan | inflow |
| Purchased parts | Purchase orders, weekly cap rule | inflow |
| Shipments | Assembly plan date, special shipment rules | outflow |
| Emptied pallboxes | Plan × bill of materials, log, picking rules | outflow |
| Metal containers returning | Load-unit master (material) | inflow |
| Defrag | Coster's rules | extra step |
| Plan slips | 90% realisation | `p_realised` |
| Month-end and weekday effects | History, once there is enough | rung 3 |
| Manual moves, ground-buffer returns, consolidation | Not logged | plan gap (monitored) |
| QC quarantine | Skipped per Coster | `qc_hold` empty |
| Actions after alerts | Group 2's alert log | backtest after go-live |
