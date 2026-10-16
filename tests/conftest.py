import pandas as pd
import pytest

from coster.common.config import load_config
from coster.common.schemas import CELL_CLASSES


@pytest.fixture
def cfg(tmp_path):
    """Repo config, with output paths redirected to a temp folder."""
    c = load_config()
    c["paths"] = {k: str(tmp_path / k) for k in c["paths"]}
    return c


@pytest.fixture
def capacity(cfg):
    return pd.Series(cfg["capacity_default"]).reindex(CELL_CLASSES)


@pytest.fixture
def empty_state(cfg):
    return pd.DataFrame(0, index=list(cfg["cascade"]), columns=CELL_CLASSES)
