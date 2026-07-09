"""
AI 编辑桥接 — GUI / CLI 与外部 Agent 之间的文件协议。

目录（默认）: AppData/TangiPromo/ai_bridge/
  snapshot.json  — 当前剪辑全貌（含设备归一化布局）
  request.json   — 用户自然语言需求
  response.json  — Agent 写回的 patch（由人工或脚本应用）
  bridge.log     — 追加日志，终端可 tail -f
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import QStandardPaths


REF_WIDTH = 1920
REF_HEIGHT = 1080


def _ensure_qt_app() -> None:
    """CLI / 脚本在未创建 QApplication 时也能解析到与 GUI 一致的数据目录。"""
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is not None:
        return
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QCoreApplication.setApplicationName("TangiPromo")
    QCoreApplication.setOrganizationName("TangiPromo")
    QCoreApplication.setOrganizationDomain("promokit.local")
    import sys
    QApplication(sys.argv[:1])


def bridge_dir() -> Path:
    _ensure_qt_app()
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
    path = root / "ai_bridge"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _log_path() -> Path:
    return bridge_dir() / "bridge.log"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def log(message: str) -> None:
    line = f"[{_now_iso()}] {message}\n"
    with _log_path().open("a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")


def _rect_norm(rect, cw: int, ch: int) -> dict[str, float]:
    return {
        "x": round(rect.x() / cw, 5),
        "y": round(rect.y() / ch, 5),
        "w": round(rect.width() / cw, 5),
        "h": round(rect.height() / ch, 5),
        "center_x": round((rect.x() + rect.width() / 2) / cw, 5),
        "center_y": round((rect.y() + rect.height() / 2) / ch, 5),
    }


def compute_device_layout(canvas, *, ref_w: int = REF_WIDTH, ref_h: int = REF_HEIGHT) -> dict[str, Any]:
    """在参考分辨率下计算手机 / Mac 机身与屏幕的归一化矩形。"""
    from .iphone import layout as iphone_layout
    from .mac import layout as mac_layout

    out: dict[str, Any] = {
        "ref_size": {"width": ref_w, "height": ref_h},
        "phone": None,
        "mac": None,
    }
    if canvas.device_mode in ("phone", "both") and canvas.show_iphone:
        body, screen = iphone_layout(
            ref_w, ref_h,
            canvas.iphone_model, canvas.iphone_theme,
            canvas.iphone_scale, canvas.iphone_pos,
        )
        out["phone"] = {
            "body": _rect_norm(body, ref_w, ref_h),
            "screen": _rect_norm(screen, ref_w, ref_h),
        }
    if canvas.device_mode in ("computer", "both") and canvas.show_mac:
        body, screen = mac_layout(
            ref_w, ref_h,
            canvas.mac_model, canvas.mac_theme,
            canvas.mac_scale, canvas.mac_pos,
        )
        out["mac"] = {
            "body": _rect_norm(body, ref_w, ref_h),
            "screen": _rect_norm(screen, ref_w, ref_h),
        }
    return out


def ratio_label(ratio: tuple[int, int]) -> str:
    rw, rh = ratio
    return f"{rw}:{rh}"


def build_snapshot(
    payload: dict[str, Any],
    canvas,
    *,
    preview_time: float = 0.0,
    export_duration: Optional[float] = None,
    export_fps: Optional[float] = None,
) -> dict[str, Any]:
    """合并 workflow payload 与运行时画布状态，供 Agent 读取。"""
    rw, rh = getattr(canvas, "output_ratio", (16, 9))
    layout = compute_device_layout(canvas)
    dur = export_duration
    if dur is None:
        dur = float(getattr(canvas, "effect_duration", 10.0))
    snap: dict[str, Any] = {
        "version": 1,
        "created_at": _now_iso(),
        "preview": {
            "time_sec": round(float(preview_time), 4),
            "ratio": ratio_label((rw, rh)),
            "ratio_tuple": [rw, rh],
        },
        "export": {
            "duration_sec": dur,
            "fps": export_fps if export_fps is not None else 30.0,
            "has_imported_video": canvas.has_imported_video(),
            "imported_video_duration_sec": canvas.imported_video_duration_sec(),
        },
        "device_mode": canvas.device_mode,
        "device_edit_target": canvas.device_edit_target,
        "layout": layout,
        "workflow": payload,
        "hints": {
            "effect_api": (
                "effects.code runs per frame with t, duration, breakpoints, zoom_region(x,y,w,h,scale). "
                "x,y,w,h are normalized 0..1 on the full frame. "
                "Use layout.phone.screen or layout.mac.screen for device focus regions."
            ),
            "patch_format": {
                "patch": {
                    "effects": {
                        "enabled": True,
                        "code": "# Python effect code",
                        "breakpoints": [3.0, 5.0],
                        "region_guide": False,
                    },
                    "export": {"duration": 10.0},
                }
            },
        },
    }
    if layout.get("phone", {}).get("screen") if layout.get("phone") else None:
        ps = layout["phone"]["screen"]
        snap["hints"]["example_focus_phone"] = (
            f"# smooth zoom to phone screen ~3s\n"
            f"px, py, pw, ph = {ps['x']}, {ps['y']}, {ps['w']}, {ps['h']}\n"
            f"if 3.0 <= t <= 4.0:\n"
            f"    p = (t - 3.0)\n"
            f"    zoom_region(px, py, pw, ph, 1.0 + 0.3 * p)\n"
        )
    return snap


def write_json(name: str, data: dict[str, Any]) -> Path:
    path = bridge_dir() / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_json(name: str) -> Optional[dict[str, Any]]:
    path = bridge_dir() / name
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
    except Exception:
        return None


def write_snapshot(snapshot: dict[str, Any]) -> Path:
    p = write_json("snapshot.json", snapshot)
    log(f"snapshot written → {p}")
    return p


def create_request(prompt: str, snapshot: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    req_id = str(uuid.uuid4())
    if snapshot is None:
        snapshot = read_json("snapshot.json") or {}
    req = {
        "id": req_id,
        "prompt": prompt.strip(),
        "created_at": _now_iso(),
        "status": "pending",
        "snapshot_id": snapshot.get("created_at"),
    }
    write_json("request.json", req)
    if snapshot:
        write_snapshot(snapshot)
    log(f"request {req_id[:8]}… created")
    log(f"  prompt: {prompt.strip()[:200]}{'…' if len(prompt.strip()) > 200 else ''}")
    log(f"  bridge: {bridge_dir()}")
    log("  → Agent: read snapshot.json + request.json, write response.json")
    return req


def read_response() -> Optional[dict[str, Any]]:
    return read_json("response.json")


def clear_response() -> bool:
    """删除 response.json（应用成功后无痕清理）。"""
    path = bridge_dir() / "response.json"
    if not path.is_file():
        return False
    path.unlink()
    log("response cleared")
    return True


def apply_patch_to_canvas(canvas, patch: dict[str, Any]) -> list[str]:
    """将 patch 合并到 Canvas；返回已应用字段说明列表。"""
    applied: list[str] = []
    if not isinstance(patch, dict):
        return applied

    eff = patch.get("effects")
    if isinstance(eff, dict):
        if "enabled" in eff:
            canvas.effect_enabled = bool(eff["enabled"])
            applied.append("effects.enabled")
        if "region_guide" in eff:
            canvas.region_guide_enabled = bool(eff["region_guide"])
            applied.append("effects.region_guide")
        if "code" in eff:
            canvas.effect_code = str(eff["code"])
            canvas._effect_code_cache_src = ""
            canvas._effect_code_cache_obj = None
            applied.append("effects.code")
        if "breakpoints" in eff:
            canvas.effect_breakpoints = [float(x) for x in eff["breakpoints"]]
            applied.append("effects.breakpoints")

    exp = patch.get("export")
    if isinstance(exp, dict):
        if "duration" in exp:
            d = float(exp["duration"])
            canvas.effect_duration = d
            applied.append("export.duration")

    content = patch.get("content")
    if isinstance(content, dict):
        for key, tgt in (("phone", "phone"), ("mac", "mac")):
            sub = content.get(key)
            if not isinstance(sub, dict):
                continue
            if "freeze_ranges" in sub and isinstance(sub["freeze_ranges"], list):
                parsed: list[tuple[float, float]] = []
                for it in sub["freeze_ranges"]:
                    if not isinstance(it, (list, tuple)) or len(it) < 2:
                        continue
                    try:
                        parsed.append((float(it[0]), float(it[1])))
                    except (TypeError, ValueError):
                        continue
                canvas.screen_slot(tgt).set_freeze_ranges(parsed)
                applied.append(f"content.{key}.freeze_ranges")

    return applied


def apply_response(
    canvas,
    response: Optional[dict[str, Any]] = None,
    *,
    on_ui_sync: Optional[Callable[[dict[str, Any], list[str]], None]] = None,
) -> tuple[list[str], Optional[str]]:
    """
    读取并应用 response.json。
    返回 (applied_fields, error_message)。
    on_ui_sync: GUI 回调，用于同步 effects 面板控件。
    """
    resp = response if response is not None else read_response()
    if resp is None:
        return [], "response.json not found"
    if resp.get("status") == "error":
        return [], str(resp.get("error", "response marked as error"))

    patch = resp.get("patch", resp)
    if not isinstance(patch, dict):
        return [], "invalid patch in response"

    applied = apply_patch_to_canvas(canvas, patch)
    if on_ui_sync is not None:
        on_ui_sync(patch, applied)

    req = read_json("request.json")
    if req and resp.get("request_id") and req.get("id") != resp.get("request_id"):
        log(f"warning: request_id mismatch ({req.get('id')} vs {resp.get('request_id')})")

    log(f"applied patch: {', '.join(applied) or '(empty)'}")
    clear_response()
    canvas.update()
    return applied, None


def bridge_status() -> dict[str, Any]:
    bd = bridge_dir()
    req = read_json("request.json")
    resp = read_response()
    snap = read_json("snapshot.json")
    return {
        "bridge_dir": str(bd),
        "log_file": str(_log_path()),
        "has_snapshot": snap is not None,
        "has_request": req is not None,
        "request": req,
        "has_response": resp is not None,
        "response_status": (resp or {}).get("status"),
        "response_summary": (resp or {}).get("summary"),
    }
