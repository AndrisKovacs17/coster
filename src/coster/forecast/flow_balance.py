"""One day of the flow balance.

State: a DataFrame with rows = pallet size groups, columns = cell classes,
values = pallet counts.
"""

import pandas as pd

from coster.forecast.allocation import allocate, remove_proportional


def step(
    state: pd.DataFrame,
    inflow: dict[str, int],
    outflow: dict[str, int],
    capacity: pd.Series,
    cascade: dict[str, list[str]],
    held_back: dict[str, int],
) -> tuple[pd.DataFrame, int]:
    """Apply one day of inflow and outflow. Inflow first, then outflow,
    which is the cautious order for alerts. Returns the new state and the
    number of pallets that found no cell."""
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
