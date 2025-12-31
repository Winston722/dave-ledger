from __future__ import annotations

import os
from pathlib import Path

def find_repo_root(start: Path | None = None) -> Path:
    """
    Finds the repository root by walking upward until pyproject.toml is found.
    Works for:
      - uv runs from repo
      - notebooks launched from /notebooks
      - docker WORKDIR=/app
    """
    here = start or Path.cwd()
    here = here.resolve()

    for p in [here, *here.parents]:
        if (p / "pyproject.toml").exists():
            return p
    raise RuntimeError("Could not locate repo root (pyproject.toml not found).")

def config_dir() -> Path:
    """
    Returns config directory path.
    Allows override via DAVE_LEDGER_CONFIG_DIR.
    """
    override = os.getenv("DAVE_LEDGER_CONFIG_DIR")
    if override:
        return Path(override).expanduser().resolve()

    return find_repo_root() / "config"
