from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

from .paths import config_dir


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge override into base (override wins)."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text()) if path.exists() else None
    return data or {}


def load_config() -> Dict[str, Any]:
    """
    Load config from:
      1) DAVE_LEDGER_CONFIG_FILE (optional explicit file)
      2) config/default.yaml (required)
      3) config/local.yaml (optional override)
    """
    cfg_root = config_dir()

    explicit = os.getenv("DAVE_LEDGER_CONFIG_FILE")
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"DAVE_LEDGER_CONFIG_FILE not found: {p}")
        return _read_yaml(p)

    default_path = cfg_root / "default.yaml"
    if not default_path.exists():
        raise FileNotFoundError(f"Missing required config: {default_path}")

    cfg = _read_yaml(default_path)

    local_path = cfg_root / "local.yaml"
    if local_path.exists():
        cfg = _deep_merge(cfg, _read_yaml(local_path))

    return cfg
