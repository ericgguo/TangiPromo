"""Persist full workflow presets for TangiPromo."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QStandardPaths


def workflow_presets_path() -> Path:
    """Path to the shared workflow preset library (GUI + CLI)."""
    override = os.environ.get("TANGIPROMO_DATA_DIR", "").strip()
    if override:
        root = Path(override)
    else:
        root_str = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        if not root_str:
            root = Path.home() / "Library/Application Support/TangiPromo"
        else:
            root = Path(root_str)
    root.mkdir(parents=True, exist_ok=True)
    return root / "workflow_presets.json"


def _store_file() -> Path:
    return workflow_presets_path()


@dataclass
class WorkflowPreset:
    id: str
    name: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "payload": self.payload}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Optional["WorkflowPreset"]:
        try:
            pid = str(d.get("id", "")).strip()
            name = str(d.get("name", "")).strip()
            payload = d.get("payload", {})
            if not pid or not name or not isinstance(payload, dict):
                return None
            return WorkflowPreset(id=pid, name=name, payload=payload)
        except Exception:
            return None


class WorkflowPresetStore:
    def __init__(self) -> None:
        self._path = _store_file()
        self._presets: list[WorkflowPreset] = []
        self._load()

    @property
    def presets(self) -> list[WorkflowPreset]:
        return list(self._presets)

    def _load(self) -> None:
        self._presets = []
        if not self._path.is_file():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(raw, dict):
            return
        arr = raw.get("presets")
        if not isinstance(arr, list):
            return
        for item in arr:
            if isinstance(item, dict):
                pr = WorkflowPreset.from_dict(item)
                if pr:
                    self._presets.append(pr)

    def save_to_disk(self) -> None:
        data = {"version": 1, "presets": [p.to_dict() for p in self._presets]}
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def by_id(self, pid: str) -> Optional[WorkflowPreset]:
        for p in self._presets:
            if p.id == pid:
                return p
        return None

    def by_name(self, name: str) -> Optional[WorkflowPreset]:
        key = name.strip()
        if not key:
            return None
        for p in self._presets:
            if p.name == key:
                return p
        return None

    def upsert(
        self, name: str, payload: dict[str, Any], preset_id: Optional[str] = None
    ) -> WorkflowPreset:
        name = name.strip()
        if not preset_id:
            existing = self.by_name(name)
            if existing:
                preset_id = existing.id
        if preset_id:
            for i, p in enumerate(self._presets):
                if p.id == preset_id:
                    self._presets[i] = WorkflowPreset(
                        id=preset_id, name=name, payload=payload
                    )
                    self.save_to_disk()
                    return self._presets[i]
        new = WorkflowPreset(id=str(uuid.uuid4()), name=name, payload=payload)
        self._presets.append(new)
        self.save_to_disk()
        return new

    def delete(self, preset_id: str) -> bool:
        n = len(self._presets)
        self._presets = [p for p in self._presets if p.id != preset_id]
        if len(self._presets) < n:
            self.save_to_disk()
            return True
        return False


__all__ = [
    "WorkflowPreset",
    "WorkflowPresetStore",
    "workflow_presets_path",
]

