"""Range and threshold risk from random plan slips (Monte Carlo)."""

import numpy as np
import pandas as pd

from coster.common.schemas import CELL_CLASSES
from coster.forecast.flow_balance import step


def realise(planned: np.ndarray, p: float, rng: np.random.Generator) -> np.ndarray:
    """Each planned pallet happens on its day with probability `p`, otherwise it
    slips to the next day. `p` comes from "about 90% of the plan is realised" (H)."""
    out = np.zeros_like(planned)
    carry = 0
    for d, n in enumerate(planned):
        due = n + carry
        done = rng.binomial(due, p)
        out[d] = done
        carry = due - done
    return out


def simulate(
    state0: pd.DataFrame,
    plan_in: dict[str, np.ndarray],
    plan_out: dict[str, np.ndarray],
    capacity: pd.Series,
    cascade: dict[str, list[str]],
    held_back: dict[str, int],
    p_real: float,
    n_runs: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Run the flow balance `n_runs` times with random slips.

    `plan_in` and `plan_out` map a size group to daily pallet counts.
    Returns occupied cells (runs, days, classes) and pallets with no cell (runs, days).
    """
    days = len(next(iter(plan_in.values())))
    paths = np.zeros((n_runs, days, len(CELL_CLASSES)))
    no_cell = np.zeros((n_runs, days))
    for r in range(n_runs):
        real_in = {g: realise(a, p_real, rng) for g, a in plan_in.items()}
        real_out = {g: realise(a, p_real, rng) for g, a in plan_out.items()}
        state = state0
        for d in range(days):
            state, no_cell[r, d] = step(
                state,
                {g: int(a[d]) for g, a in real_in.items()},
                {g: int(a[d]) for g, a in real_out.items()},
                capacity,
                cascade,
                held_back,
            )
            paths[r, d] = state.sum(axis=0).reindex(CELL_CLASSES).to_numpy()
    return paths, no_cell


def summarise(paths: np.ndarray, capacity: pd.Series, critical: float) -> dict[str, np.ndarray]:
    """Median, 10-90% range and the chance of reaching `critical` by each day."""
    fill = paths / capacity.reindex(CELL_CLASSES).to_numpy()
    lo, mid, hi = np.quantile(fill, [0.1, 0.5, 0.9], axis=0)
    crossed = np.maximum.accumulate(fill >= critical, axis=1)
    return {"pred": mid, "lo": lo, "hi": hi, "p_critical_by": crossed.mean(axis=0)}
