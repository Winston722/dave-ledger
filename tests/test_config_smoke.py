from pathlib import Path

from dave_ledger.core.config import load_config
from dave_ledger.core.paths import config_dir, find_repo_root


def test_repo_root_exists():
    root = find_repo_root()
    assert (root / "pyproject.toml").exists()


def test_config_dir_exists():
    cdir = config_dir()
    assert cdir.exists()
    assert (cdir / "default.yaml").exists()


def test_load_config_returns_dict():
    cfg = load_config()
    assert isinstance(cfg, dict)
