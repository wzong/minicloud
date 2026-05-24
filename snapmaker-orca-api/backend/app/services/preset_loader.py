"""Discover and resolve Snapmaker Orca / OrcaSlicer JSON presets.

OrcaSlicer profiles live under ``<resources>/profiles/<vendor>/<kind>/*.json`` with three
kinds: ``machine`` (printer), ``filament``, ``process``. Profiles use a string-valued
``inherits`` field for inheritance. Resolution walks the chain back to the root and merges
values (children override parents).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

KIND_DIRS = {
    "printer": ("machine",),
    "filament": ("filament",),
    "process": ("process",),
}


class PresetLoader:
    def __init__(self, resources_dir: str | Path) -> None:
        self.resources_dir = Path(resources_dir)
        self._index: dict[tuple[str, str], Path] = {}
        self._raw_cache: dict[Path, dict[str, Any]] = {}

    # ------------------------------------------------------------------ scan

    def scan(self) -> None:
        self._index.clear()
        profiles_root = self.resources_dir / "profiles"
        if not profiles_root.exists():
            return
        for kind, subdirs in KIND_DIRS.items():
            for sub in subdirs:
                for jp in profiles_root.rglob(f"*/{sub}/*.json"):
                    try:
                        data = self._load_raw(jp)
                    except (OSError, json.JSONDecodeError):
                        continue
                    name = data.get("name") or jp.stem
                    self._index[(kind, str(name))] = jp

    # ----------------------------------------------------------------- lists

    def list_presets(self, kind: str | None = None) -> list[dict[str, Any]]:
        if not self._index:
            self.scan()
        out: list[dict[str, Any]] = []
        for (k, name), path in sorted(self._index.items()):
            if kind and k != kind:
                continue
            data = self._load_raw(path)
            out.append(
                {
                    "name": name,
                    "kind": k,
                    "inherits": data.get("inherits"),
                    "source": str(path.relative_to(self.resources_dir)),
                }
            )
        return out

    # ---------------------------------------------------------------- resolve

    def resolve(self, kind: str, name: str) -> dict[str, Any]:
        """Return the fully-flattened settings for a preset (inheritance applied)."""
        if not self._index:
            self.scan()
        chain = self._chain(kind, name)
        merged: dict[str, Any] = {}
        # walk root -> leaf so leaves override parents
        for ancestor in reversed(chain):
            raw = self._load_raw(self._index[(kind, ancestor)])
            for k, v in raw.items():
                if k in ("inherits", "name", "type", "from", "version", "instantiation"):
                    continue
                merged[k] = v
        return merged

    def chain(self, kind: str, name: str) -> list[str]:
        if not self._index:
            self.scan()
        return self._chain(kind, name)

    # ----------------------------------------------------------------- utils

    def _chain(self, kind: str, name: str) -> list[str]:
        chain: list[str] = []
        cur: str | None = name
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            key = (kind, cur)
            if key not in self._index:
                break
            chain.append(cur)
            data = self._load_raw(self._index[key])
            cur = data.get("inherits") or None
        return chain

    def _load_raw(self, path: Path) -> dict[str, Any]:
        cached = self._raw_cache.get(path)
        if cached is not None:
            return cached
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        self._raw_cache[path] = data
        return data
