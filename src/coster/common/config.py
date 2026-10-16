"""Load config/config.yaml. Every number and rule comes from there."""

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Read the YAML config. Defaults to config/config.yaml in the repo."""
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(path: str | Path) -> Path:
    """Make a config path absolute. Relative paths are relative to the repo root."""
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p
