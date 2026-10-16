"""Allocation cascade: a pallet takes the smallest class that fits, then the next bigger one."""

import numpy as np
import pandas as pd


def allocate(
    n: int, order: list[str], free: dict[str, int], held_back: dict[str, int]
) -> tuple[dict[str, int], int]:
    """Place `n` pallets along the cascade `order`. `order[0]` is the pallet's own class.

    Other classes keep `held_back` cells free for their own pallets.
    `free` is updated in place. Returns pallets placed per class, and the
    number of pallets that found no cell (the saturation event).
    """
    placed: dict[str, int] = {}
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


def remove_proportional(row: pd.Series, n: int) -> pd.Series:
    """Remove `n` pallets of one size group, spread over the classes by where they sit now."""
    total = int(row.sum())
    n = min(n, total)
    if n == 0:
        return row
    share = row / total * n
    take = np.floor(share).astype(int)
    rest = n - int(take.sum())
    top = (share - take).sort_values(ascending=False).index[:rest]
    take[top] += 1
    return row - take
