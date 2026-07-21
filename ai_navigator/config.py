"""Configuration loading (stdlib only).

Reads ``config/default.toml`` via tomllib, applies an optional override file,
and loads ``.env`` (a minimal parser, so python-dotenv is not required).
Secrets stay in the environment; only non-secret settings live in TOML.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

# Repo root = two levels up from this file (ai_navigator/config.py -> repo/).
REPO_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from .env into os.environ (does not overwrite)."""
    path = path or (REPO_ROOT / ".env")
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get(self, path: str, default: Any = None) -> Any:
        """Dotted lookup, e.g. cfg.get('planner.judge.video_min')."""
        node: Any = self._data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def raw(self) -> dict[str, Any]:
        return self._data

    def report_root(self) -> Path:
        return REPO_ROOT / self.get("paths.reports_dir", "reports")

    def tools_db_dir(self) -> Path:
        return REPO_ROOT / self.get("paths.tools_db_dir", "data/tools")


def load_config(override_path: Path | None = None) -> Config:
    load_dotenv()
    default_path = REPO_ROOT / "config" / "default.toml"
    with default_path.open("rb") as fh:
        data = tomllib.load(fh)
    if override_path and override_path.exists():
        with override_path.open("rb") as fh:
            data = _deep_merge(data, tomllib.load(fh))
    return Config(data)
