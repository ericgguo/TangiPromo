"""Persist user-defined effect code presets (name + code)."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QStandardPaths


def _store_file() -> Path:
    root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not root:
        root = str(Path.home() / ".promokit_data")
    p = Path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p / "effects.json"


@dataclass
class EffectPreset:
    id: str
    name: str
    code: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "code": self.code}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Optional["EffectPreset"]:
        try:
            pid = str(d.get("id", "")).strip()
            name = str(d.get("name", "")).strip()
            code = str(d.get("code", ""))
            if not pid or not name:
                return None
            return EffectPreset(id=pid, name=name, code=code)
        except Exception:
            return None


class EffectStore:
    def __init__(self) -> None:
        self._path = _store_file()
        self._presets: list[EffectPreset] = []
        self._load()

    @property
    def presets(self) -> list[EffectPreset]:
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
                pr = EffectPreset.from_dict(item)
                if pr:
                    self._presets.append(pr)

    def save_to_disk(self) -> None:
        data = {"version": 1, "presets": [p.to_dict() for p in self._presets]}
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def by_id(self, pid: str) -> Optional[EffectPreset]:
        for p in self._presets:
            if p.id == pid:
                return p
        return None

    def upsert(self, name: str, code: str, preset_id: Optional[str] = None) -> EffectPreset:
        name = name.strip()
        if preset_id:
            for i, p in enumerate(self._presets):
                if p.id == preset_id:
                    self._presets[i] = EffectPreset(id=preset_id, name=name, code=code)
                    self.save_to_disk()
                    return self._presets[i]
        new = EffectPreset(id=str(uuid.uuid4()), name=name, code=code)
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

