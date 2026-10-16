"""Actual flows per cell class from two consecutive snapshots.

There is no usable movement log, so we compare snapshots by load-unit ID:
a new ID is a filled cell, a missing ID is a freed cell, and an ID that sits
in another class is an internal transfer. This needs the snapshot to list
load-unit IDs (open point 3 in the Group 1 plan).
"""

import pandas as pd

from coster.common.schemas import CELL_CLASSES


def daily_flows(prev: pd.DataFrame, curr: pd.DataFrame) -> pd.DataFrame:
    """Flows per class between two snapshots, matched on `udc_id`.

    Both inputs need the columns `udc_id` and `cell_class`. By construction,
    prev occupancy + inbound - outbound + internal_transfer = curr occupancy.
    """
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
