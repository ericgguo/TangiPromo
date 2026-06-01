"""
PromoSession — headless / CLI 会话层。

在不打开任何窗口的情况下操控 Canvas 状态并导出图片/视频。
GUI 模式下不使用此模块（MainWindow 直接操作 Canvas）。
"""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import Qt, QEventLoop
from PySide6.QtGui import QColor, QPixmap


# ── 比例映射（与 MainWindow._RATIO_MAP 一致）─────────────────────────────────

RATIO_MAP: dict[str, tuple[int, int]] = {
    "16:9":  (16, 9),
    "9:16":  (9, 16),
    "1:1":   (1, 1),
    "4:3":   (4, 3),
    "4:5":   (4, 5),
    "21:9":  (21, 9),
}

RATIO_IDX: list[tuple[int, int]] = [
    (16, 9), (9, 16), (1, 1), (4, 3), (4, 5), (21, 9)
]


# ── 颜色工具（与 MainWindow 一致）────────────────────────────────────────────

def _color_to_hex(c: QColor) -> str:
    return c.name(QColor.NameFormat.HexArgb)


def _color_from_hex(s: str, fallback: QColor) -> QColor:
    c = QColor(s)
    return c if c.isValid() else fallback


# ── 序列化工具（与 MainWindow 保持一致，提取为独立函数）──────────────────────

def serialize_text_layer(layer) -> dict[str, Any]:
    return {
        "name": layer.name,
        "text": layer.text,
        "x": layer.x,
        "y": layer.y,
        "font_family": layer.font_family,
        "font_size_pt": layer.font_size_pt,
        "bold": layer.bold,
        "italic": layer.italic,
        "color": _color_to_hex(layer.color),
        "align": int(layer.align),
        "shadow": layer.shadow,
        "shadow_color": _color_to_hex(layer.shadow_color),
        "shadow_offset": list(layer.shadow_offset),
        "outline": layer.outline,
        "outline_color": _color_to_hex(layer.outline_color),
        "outline_width": layer.outline_width,
        "visible": layer.visible,
    }


def deserialize_text_layer(data: dict[str, Any]):
    from .text_layer import TextLayer
    layer = TextLayer()
    layer.name = str(data.get("name", ""))
    layer.text = str(data.get("text", ""))
    layer.x = float(data.get("x", 0.5))
    layer.y = float(data.get("y", 0.85))
    layer.font_family = str(data.get("font_family", layer.font_family))
    layer.font_size_pt = int(data.get("font_size_pt", layer.font_size_pt))
    layer.bold = bool(data.get("bold", False))
    layer.italic = bool(data.get("italic", False))
    layer.color = _color_from_hex(str(data.get("color", "")), layer.color)
    layer.align = Qt.AlignmentFlag(
        int(data.get("align", int(Qt.AlignmentFlag.AlignHCenter)))
    )
    layer.shadow = bool(data.get("shadow", True))
    layer.shadow_color = _color_from_hex(
        str(data.get("shadow_color", "")), layer.shadow_color
    )
    so = data.get("shadow_offset", list(layer.shadow_offset))
    if isinstance(so, list) and len(so) >= 2:
        layer.shadow_offset = (float(so[0]), float(so[1]))
    layer.outline = bool(data.get("outline", False))
    layer.outline_color = _color_from_hex(
        str(data.get("outline_color", "")), layer.outline_color
    )
    layer.outline_width = float(data.get("outline_width", layer.outline_width))
    layer.visible = bool(data.get("visible", True))
    return layer


def serialize_watermark(st) -> dict[str, Any]:
    return {
        "id": st.id,
        "title": st.title,
        "image_path": st.image_path,
        "enabled": st.enabled,
        "color": _color_to_hex(st.color),
        "center_x_pct": st.center_x_pct,
        "center_y_pct": st.center_y_pct,
        "width_pct": st.width_pct,
    }


def deserialize_watermark(data: dict[str, Any]):
    from .watermark import make_watermark_from_path
    st = make_watermark_from_path(str(data.get("image_path", "")))
    st.id = str(data.get("id", st.id))
    st.title = str(data.get("title", st.title))
    st.enabled = bool(data.get("enabled", st.enabled))
    st.color = _color_from_hex(str(data.get("color", "")), st.color)
    st.center_x_pct = float(data.get("center_x_pct", st.center_x_pct))
    st.center_y_pct = float(data.get("center_y_pct", st.center_y_pct))
    st.width_pct = float(data.get("width_pct", st.width_pct))
    return st


# ── PromoSession ──────────────────────────────────────────────────────────────

class PromoSession:
    """
    无头会话对象。封装 Canvas 所有状态，供 CLI 或脚本驱动。

    使用示例::

        session = PromoSession()
        session.set_background("Aurora Flow")
        session.set_ratio("9:16")
        session.set_screen("/path/to/screenshot.png")
        session.set_text_layers([{"text": "Hello", "y": 0.85}])
        session.export_image("/tmp/out.png", 1080, 1920)
    """

    def __init__(self) -> None:
        from .canvas import Canvas
        from .backgrounds import ALL_BACKGROUNDS
        from .iphone_manifest import default_theme_for_model
        from .iphone import MODEL_ORDER

        self._canvas = Canvas()
        # 停止 GUI 计时器（无头下不需要 60fps 刷新）
        self._canvas._timer.stop()

        # 初始化背景实例池
        self._bg_instances: dict[str, object] = {
            cls().name: cls() for cls in ALL_BACKGROUNDS
        }

        # 应用默认背景
        first_name = ALL_BACKGROUNDS[0]().name
        self._canvas.background = self._bg_instances[first_name]
        self._current_bg_name: str = first_name

        # 默认导出参数
        self._export_duration: float = 10.0
        self._export_fps: float = 30.0
        self._full_import_video: bool = False
        self._resolution_key: Optional[str] = None   # 来自 workflow 的分辨率预设 key

    # ------------------------------------------------------------------
    # 背景
    # ------------------------------------------------------------------

    def set_background(self, name: str, **params) -> None:
        """
        设置背景。name 为背景的 .name 属性（如 "Aurora Flow"、"Custom Code" 等）。
        params 可设置 speed 等属性。
        """
        from .backgrounds.custom import CustomCodeBackground
        bg = self._bg_instances.get(name)
        if bg is None:
            available = list(self._bg_instances.keys())
            raise ValueError(
                f"背景 {name!r} 不存在。可用: {available}"
            )
        for k, v in params.items():
            if hasattr(bg, k):
                setattr(bg, k, v)
        self._canvas.background = bg
        self._current_bg_name = name

    def set_background_code(self, code: str, speed: float = 1.0) -> None:
        """切换到自定义代码背景，并设置代码内容。"""
        from .backgrounds.custom import CustomCodeBackground
        custom_name = CustomCodeBackground().name
        bg = self._bg_instances.get(custom_name)
        if isinstance(bg, CustomCodeBackground):
            bg.code = code
            bg._last_code = None
            if hasattr(bg, "speed"):
                bg.speed = speed
        self._canvas.background = bg
        self._current_bg_name = custom_name

    def list_backgrounds(self) -> list[str]:
        """返回所有可用背景名称。"""
        return list(self._bg_instances.keys())

    # ------------------------------------------------------------------
    # 输出比例
    # ------------------------------------------------------------------

    def set_ratio(self, ratio: str) -> None:
        """
        设置输出比例。ratio 格式为 "16:9"、"9:16"、"1:1"、"4:3"、"4:5"、"21:9"。
        """
        if ratio not in RATIO_MAP:
            raise ValueError(f"比例 {ratio!r} 不支持。可用: {list(RATIO_MAP)}")
        self._canvas.output_ratio = RATIO_MAP[ratio]

    def set_ratio_by_index(self, idx: int) -> None:
        """按索引设置比例（与 workflow preset 的 ratio_idx 一致）。"""
        if 0 <= idx < len(RATIO_IDX):
            self._canvas.output_ratio = RATIO_IDX[idx]

    # ------------------------------------------------------------------
    # iPhone 设备框
    # ------------------------------------------------------------------

    def set_iphone(
        self,
        model: Optional[str] = None,
        theme: Optional[str] = None,
        scale: Optional[float] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        visible: Optional[bool] = None,
    ) -> None:
        """
        配置 iPhone 设备框。
        model: 型号字符串，如 "iPhone 17 Pro Max"
        theme: 主题 id，如 "cosmic_orange"
        scale: 缩放百分比（0-100）
        x, y: 位置百分比（0-100，50=居中）
        visible: 是否显示
        """
        from .iphone_manifest import default_theme_for_model
        if model is not None:
            self._canvas.iphone_model = model
            if theme is None:
                self._canvas.iphone_theme = default_theme_for_model(model)
        if theme is not None:
            self._canvas.iphone_theme = theme
        if scale is not None:
            self._canvas.iphone_scale = scale / 100.0
        if x is not None:
            px = x / 100.0
            py = self._canvas.iphone_pos[1]
            self._canvas.iphone_pos = (px, py)
        if y is not None:
            px = self._canvas.iphone_pos[0]
            py = y / 100.0
            self._canvas.iphone_pos = (px, py)
        if visible is not None:
            self._canvas.show_iphone = visible

    # ------------------------------------------------------------------
    # 屏幕内容（图片/视频）
    # ------------------------------------------------------------------

    def set_screen(self, path: str) -> None:
        """
        设置屏幕内容。自动判断图片或视频。
        path: 本地文件路径
        """
        if not path or not os.path.isfile(path):
            self._canvas.clear_video()
            self._canvas.set_screen_image_path("")
            self._canvas.screen_pixmap = None
            return
        ext = os.path.splitext(path)[1].lower()
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
        if ext in video_exts:
            self._canvas.set_video(path)
            self._canvas.set_screen_image_path("")
            vd = self._canvas.imported_video_duration_sec()
            if vd is not None and vd > 0:
                self._export_duration = max(self._export_duration, vd)
        else:
            pix = QPixmap(path)
            if pix.isNull():
                raise ValueError(f"无法加载图片: {path}")
            self._canvas.clear_video()
            self._canvas.set_screen_image_path(path)
            self._canvas.screen_pixmap = pix

    def clear_screen(self) -> None:
        self._canvas.clear_video()
        self._canvas.set_screen_image_path("")
        self._canvas.screen_pixmap = None

    # ------------------------------------------------------------------
    # 文字图层
    # ------------------------------------------------------------------

    def set_text_layers(self, layers: list[dict[str, Any]]) -> None:
        """
        设置文字图层列表。每个 dict 对应一个图层，字段与 workflow payload 一致。
        最简示例: [{"text": "Hello World", "y": 0.85}]
        """
        self._canvas.text_layers = [deserialize_text_layer(d) for d in layers]

    def add_text_layer(self, text: str, x: float = 0.5, y: float = 0.85, **kwargs) -> None:
        """快捷方法：追加一个文字图层。"""
        data = {"text": text, "x": x, "y": y, **kwargs}
        self._canvas.text_layers.append(deserialize_text_layer(data))

    def clear_text_layers(self) -> None:
        self._canvas.text_layers = []

    # ------------------------------------------------------------------
    # 水印
    # ------------------------------------------------------------------

    def set_watermarks(self, watermarks: list[dict[str, Any]]) -> None:
        """
        设置水印列表。每个 dict 需包含 image_path，其余字段可选。
        """
        states = []
        for item in watermarks:
            if not isinstance(item, dict):
                continue
            path = str(item.get("image_path", ""))
            if not path or not os.path.isfile(path):
                continue
            states.append(deserialize_watermark(item))
        self._canvas.watermark_states = states
        self._canvas._wm_pix_cache.clear()

    def add_watermark(
        self,
        image_path: str,
        *,
        enabled: bool = True,
        color: str = "#ffebebeb",
        center_x_pct: float = 50.0,
        center_y_pct: float = 50.0,
        width_pct: float = 14.0,
    ) -> None:
        """快捷方法：追加一个水印。"""
        from .watermark import make_watermark_from_path
        st = make_watermark_from_path(image_path)
        st.enabled = enabled
        st.color = _color_from_hex(color, st.color)
        st.center_x_pct = center_x_pct
        st.center_y_pct = center_y_pct
        st.width_pct = width_pct
        self._canvas.watermark_states.append(st)
        self._canvas._wm_pix_cache.clear()

    def clear_watermarks(self) -> None:
        self._canvas.watermark_states = []
        self._canvas._wm_pix_cache.clear()

    # ------------------------------------------------------------------
    # 效果（Effect）
    # ------------------------------------------------------------------

    def set_effect(
        self,
        code: str,
        enabled: bool = True,
        duration: Optional[float] = None,
        breakpoints: Optional[list[float]] = None,
    ) -> None:
        self._canvas.effect_code = code
        self._canvas.effect_enabled = enabled
        if duration is not None:
            self._canvas.effect_duration = duration
        if breakpoints is not None:
            self._canvas.effect_breakpoints = list(breakpoints)

    def clear_effect(self) -> None:
        self._canvas.effect_enabled = False
        self._canvas.effect_code = ""

    # ------------------------------------------------------------------
    # 时间轴
    # ------------------------------------------------------------------

    def set_timeline(self, duration: float, breakpoints: Optional[list[float]] = None) -> None:
        self._export_duration = max(0.1, float(duration))
        self._canvas.effect_duration = self._export_duration
        if breakpoints is not None:
            self._canvas.effect_breakpoints = list(breakpoints)

    def set_time(self, t: float) -> None:
        self._canvas.time = max(0.0, float(t))

    # ------------------------------------------------------------------
    # 加载 workflow preset
    # ------------------------------------------------------------------

    def load_workflow(self, source: "str | Path | dict[str, Any]") -> list[str]:
        """
        从 workflow payload（dict）或 JSON 文件路径加载整套工作流。
        payload 格式与 GUI「保存工作流」完全一致。
        返回缺失文件路径列表（不报错，由调用方决定如何处理）。
        """
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.is_file():
                raw = json.loads(path.read_text(encoding="utf-8"))
                # 支持两种格式：直接 payload dict 或 {"presets": [...]} 包装
                if isinstance(raw, dict) and "presets" in raw:
                    presets = raw["presets"]
                    if presets:
                        payload = presets[0].get("payload", presets[0])
                    else:
                        return []
                else:
                    payload = raw
            else:
                raise FileNotFoundError(f"找不到 workflow 文件: {source}")
        else:
            payload = source

        return self._apply_payload(payload)

    def _apply_payload(self, payload: dict[str, Any]) -> list[str]:
        from .backgrounds.custom import CustomCodeBackground
        missing: list[str] = []

        # 比例
        ratio_idx = int(payload.get("ratio_idx", 0))
        self.set_ratio_by_index(ratio_idx)

        # 导出参数
        exp = payload.get("export", {})
        if isinstance(exp, dict):
            self._export_fps = float(exp.get("fps", self._export_fps))
            self._export_duration = float(exp.get("duration", self._export_duration))
            self._full_import_video = bool(exp.get("full_import_video", False))
            res_key = exp.get("resolution_key")
            if res_key:
                self._resolution_key = str(res_key)

        # 背景
        bg = payload.get("background", {})
        if isinstance(bg, dict):
            bg_key = bg.get("key")
            if bg_key and bg_key in self._bg_instances:
                bg_inst = self._bg_instances[bg_key]
                speed = int(bg.get("speed", 100))
                if hasattr(bg_inst, "speed"):
                    bg_inst.speed = speed / 100.0
                custom_code = str(bg.get("custom_code", ""))
                if isinstance(bg_inst, CustomCodeBackground) and custom_code:
                    bg_inst.code = custom_code
                    bg_inst._last_code = None
                self._canvas.background = bg_inst
                self._current_bg_name = bg_key

        # 效果
        eff = payload.get("effects", {})
        if isinstance(eff, dict):
            self._canvas.effect_enabled = bool(eff.get("enabled", False))
            self._canvas.effect_code = str(eff.get("code", ""))
            self._canvas.effect_breakpoints = [
                float(x) for x in eff.get("breakpoints", [])
            ]
            self._canvas.region_guide_enabled = bool(eff.get("region_guide", False))

        # iPhone
        phone = payload.get("phone", {})
        if isinstance(phone, dict):
            from .iphone_manifest import default_theme_for_model
            model = phone.get("model")
            theme = phone.get("theme")
            if model:
                self._canvas.iphone_model = str(model)
                self._canvas.iphone_theme = (
                    str(theme) if theme else default_theme_for_model(str(model))
                )
            self._canvas.show_iphone = bool(phone.get("show", True))
            scale = float(phone.get("scale", 72))
            self._canvas.iphone_scale = scale / 100.0
            x = float(phone.get("x", 50)) / 100.0
            y = float(phone.get("y", 50)) / 100.0
            self._canvas.iphone_pos = (x, y)

        # 内容
        content = payload.get("content", {})
        if isinstance(content, dict):
            ctype = str(content.get("type", "none"))
            path = content.get("path")
            if path and isinstance(path, str):
                if os.path.isfile(path):
                    self.set_screen(path)
                else:
                    missing.append(path)
                    self.clear_screen()
            elif ctype == "none":
                self.clear_screen()

        # 水印
        wm_list = payload.get("watermarks", [])
        self._canvas.watermark_states = []
        self._canvas._wm_pix_cache.clear()
        for item in wm_list:
            if not isinstance(item, dict):
                continue
            p = str(item.get("image_path", ""))
            if not p or not os.path.isfile(p):
                if p:
                    missing.append(p)
                continue
            self._canvas.watermark_states.append(deserialize_watermark(item))

        # 文字图层
        self._canvas.text_layers = [
            deserialize_text_layer(item)
            for item in payload.get("text_layers", [])
            if isinstance(item, dict)
        ]

        # 同步 effect_duration
        self._canvas.effect_duration = self._export_duration

        return missing

    # ------------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------------

    def export_image(
        self,
        out_path: str,
        width: int,
        height: int,
        *,
        t: Optional[float] = None,
        quality: int = 95,
    ) -> str:
        """
        导出静态图片（PNG 或 JPEG）。
        t: 时间点（秒），默认使用当前 canvas.time。
        返回输出路径。
        """
        from .exporter import Exporter
        if t is not None:
            self._canvas.time = max(0.0, float(t))
        return Exporter.export_image(self._canvas, out_path, width, height, quality=quality)

    def export_video(
        self,
        out_path: str,
        width: int,
        height: int,
        *,
        fps: Optional[float] = None,
        duration: Optional[float] = None,
        ensure_full_import_video: bool = False,
        on_progress: Optional[Callable[[int], None]] = None,
    ) -> None:
        """
        导出 MP4 视频（同步阻塞直到完成）。
        on_progress: 接收 0-100 整数的回调。
        """
        from .exporter import Exporter
        from PySide6.QtCore import QEventLoop

        fps = float(fps) if fps is not None else self._export_fps
        duration = float(duration) if duration is not None else self._export_duration
        # 未显式指定时沿用 workflow 里的 full_import_video 设置
        if ensure_full_import_video is False:
            ensure_full_import_video = self._full_import_video

        errors: list[str] = []
        loop = QEventLoop()

        def _on_done(_path: str) -> None:
            loop.quit()

        def _on_err(msg: str) -> None:
            errors.append(msg)
            loop.quit()

        worker = Exporter.start_video_export(
            self._canvas,
            out_path,
            width,
            height,
            fps,
            duration,
            ensure_full_import_video=ensure_full_import_video,
            on_progress=on_progress,
            on_finished=_on_done,
            on_error=_on_err,
        )

        loop.exec()

        if errors:
            raise RuntimeError(errors[0])

    # ------------------------------------------------------------------
    # Workflow 保存
    # ------------------------------------------------------------------

    def save_workflow(
        self,
        out_path: "str | Path",
        name: str = "cli_export",
    ) -> None:
        """
        将当前会话状态保存为 workflow JSON 文件。
        文件格式与 GUI「保存工作流」完全兼容（可直接加载回 GUI）。
        """
        import uuid
        payload = self.collect_payload()
        preset = {
            "id": str(uuid.uuid4()),
            "name": name,
            "payload": payload,
        }
        data = {"version": 1, "presets": [preset]}
        Path(out_path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # 内省
    # ------------------------------------------------------------------

    def collect_payload(self) -> dict[str, Any]:
        """返回当前状态的 workflow payload（与 GUI 格式完全兼容）。"""
        content_path = None
        content_type = "none"
        if self._canvas.video_source_path():
            content_path = self._canvas.video_source_path()
            content_type = "video"
        elif self._canvas.screen_image_path():
            content_path = self._canvas.screen_image_path()
            content_type = "image"

        px, py = self._canvas.iphone_pos
        return {
            "ratio_idx": next(
                (i for i, r in enumerate(RATIO_IDX) if r == self._canvas.output_ratio),
                0,
            ),
            "export": {
                "format_idx": 2 if self._canvas.video_source_path() else 0,
                "resolution_key": self._resolution_key,
                "fps": self._export_fps,
                "duration": self._export_duration,
                "full_import_video": self._full_import_video,
            },
            "background": {
                "key": self._current_bg_name,
                "speed": int(
                    getattr(self._canvas.background, "speed", 1.0) * 100
                ),
                "custom_code": getattr(self._canvas.background, "code", ""),
            },
            "effects": {
                "enabled": self._canvas.effect_enabled,
                "region_guide": self._canvas.region_guide_enabled,
                "code": self._canvas.effect_code,
                "breakpoints": list(self._canvas.effect_breakpoints),
            },
            "phone": {
                "model": self._canvas.iphone_model,
                "theme": self._canvas.iphone_theme,
                "show": self._canvas.show_iphone,
                "scale": self._canvas.iphone_scale * 100.0,
                "x": px * 100.0,
                "y": py * 100.0,
            },
            "content": {"type": content_type, "path": content_path},
            "watermarks": [
                serialize_watermark(st) for st in self._canvas.watermark_states
            ],
            "text_layers": [
                serialize_text_layer(layer) for layer in self._canvas.text_layers
            ],
        }

    @property
    def canvas(self):
        """暴露底层 Canvas 实例（高级用途）。"""
        return self._canvas
