"""AI Tool Database access (spec §14).

Phase 1 storage is a directory of one JSON file per tool (``data/tools/*.json``).
Simple, diff-friendly, and trivially swappable for SQLite/Postgres later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ToolDatabase:
    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._cache: dict[str, dict[str, Any]] | None = None

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._cache is None:
            records: dict[str, dict[str, Any]] = {}
            if self._dir.exists():
                for path in sorted(self._dir.glob("*.json")):
                    data = json.loads(path.read_text(encoding="utf-8"))
                    name = data.get("tool")
                    if name:
                        records[name] = data
            self._cache = records
        return self._cache

    def all(self) -> dict[str, dict[str, Any]]:
        return dict(self._load())

    def get(self, tool: str) -> dict[str, Any] | None:
        return self._load().get(tool)

    def known_tools(self) -> list[str]:
        return sorted(self._load().keys())
