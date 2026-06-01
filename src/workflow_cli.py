"""CLI helpers for the shared workflow preset library."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

from .workflow_preset_store import WorkflowPreset, WorkflowPresetStore, workflow_presets_path


def get_workflow_store() -> WorkflowPresetStore:
    return WorkflowPresetStore()


def resolve_preset(
    store: WorkflowPresetStore,
    *,
    name: Optional[str] = None,
    preset_id: Optional[str] = None,
) -> WorkflowPreset:
    if preset_id:
        pr = store.by_id(preset_id.strip())
        if pr:
            return pr
        raise ValueError(f"找不到 workflow preset id: {preset_id!r}")
    if name:
        pr = store.by_name(name)
        if pr:
            return pr
        names = [p.name for p in store.presets]
        hint = f" 已有: {names}" if names else " 库为空，先用 save-workflow-preset 或 workflow-import 添加"
        raise ValueError(f"找不到 workflow preset 名称: {name!r}.{hint}")
    raise ValueError("需要 --workflow-preset NAME 或 --workflow-id ID")


def load_workflow_sources(session, args) -> list[str]:
    """
    Load workflow from --workflow-preset / --workflow-id then optional --workflow file.
    Returns combined missing asset paths.
    """
    missing: list[str] = []
    preset = getattr(args, "workflow_preset", None)
    preset_id = getattr(args, "workflow_id", None)
    workflow_path = getattr(args, "workflow", None)

    if preset and preset_id:
        print("[警告] 同时指定了 --workflow-preset 与 --workflow-id，使用 --workflow-id", file=sys.stderr)
        preset = None

    if preset or preset_id:
        store = get_workflow_store()
        pr = resolve_preset(store, name=preset, preset_id=preset_id)
        missing.extend(session.load_workflow(pr.payload))

    if workflow_path:
        missing.extend(session.load_workflow(workflow_path))

    return missing


def payload_from_workflow_file(path: str | Path) -> dict[str, Any]:
    """Read a workflow JSON file; return payload dict."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("workflow 文件必须是 JSON 对象")
    if "presets" in raw:
        presets = raw.get("presets")
        if not isinstance(presets, list) or not presets:
            raise ValueError("workflow 文件 presets 为空")
        first = presets[0]
        if not isinstance(first, dict):
            raise ValueError("workflow preset 项格式无效")
        payload = first.get("payload", first)
        if not isinstance(payload, dict):
            raise ValueError("workflow payload 必须是对象")
        return payload
    return raw


def preset_to_jsonable(pr: WorkflowPreset) -> dict[str, Any]:
    return {
        "id": pr.id,
        "name": pr.name,
        "payload": pr.payload,
    }
