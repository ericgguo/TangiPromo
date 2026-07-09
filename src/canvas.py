"""
Animated preview canvas.

• Runs at up to 60 FPS via QTimer.
• Maintains correct aspect ratio inside the widget.
• Supports drag-to-move for the device mockup and text layers.
• render_frame() is the single rendering entry-point shared with the exporter.
"""
from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from .iphone import IPhoneRenderer, MODEL_ORDER as IPHONE_MODEL_ORDER, layout as iphone_layout
from .iphone_manifest import default_theme_for_model as default_iphone_theme
from .mac import MacRenderer, MODEL_ORDER as MAC_MODEL_ORDER, layout as mac_layout
from .mac_manifest import default_theme_for_model as default_mac_theme
from .screen_slot import ScreenSlot
from .text_layer import TextLayer
from .watermark import (
    WatermarkState,
    compute_watermark_rect,
    default_watermark_states,
    render_watermarks,
)


_IPHONE_RENDERER = IPhoneRenderer()
_MAC_RENDERER = MacRenderer()

_DRAG_PHONE = object()
_DRAG_MAC = object()


class Canvas(QWidget):
    # Emitted when a text layer is clicked (passes layer index, or -1 for none)
    layer_selected = Signal(int)
    # Emitted when device position changes (phone or computer mode)
    iphone_moved = Signal(float, float)
    device_moved = iphone_moved
    device_edit_target_changed = Signal(str)
    # 水印索引（用于同步右侧输入框）
    watermark_moved = Signal(int)
    # 当前时间（秒）变化，用于时间轴 UI 跟随
    time_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(400, 280)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setMouseTracking(True)

        # ── Rendering state ──────────────────────────────────────────────
        self.background = None          # Background instance
        self.output_ratio: tuple[int, int] = (16, 9)

        _m0 = IPHONE_MODEL_ORDER[0] if IPHONE_MODEL_ORDER else "iPhone 17 Pro Max"
        self.device_mode: str = "phone"  # "phone" | "computer" | "both"
        self.device_edit_target: str = "phone"  # both 模式下侧栏编辑目标
        self.iphone_model: str = _m0
        self.iphone_theme: str = default_iphone_theme(_m0)
        self.iphone_scale: float = 0.72
        self.iphone_pos: tuple[float, float] = (0.5, 0.5)
        self.show_iphone: bool = True

        _mac0 = MAC_MODEL_ORDER[0] if MAC_MODEL_ORDER else "Window Dark"
        self.mac_model: str = _mac0
        self.mac_theme: str = default_mac_theme(_mac0)
        self.mac_scale: float = 0.58
        self.mac_pos: tuple[float, float] = (0.5, 0.5)
        self.show_mac: bool = True

        self.phone_screen = ScreenSlot()
        self.mac_screen = ScreenSlot()
        # 为 True 时主线程不再对 video_cap read，避免与导出线程争用解码器
        self._export_active: bool = False

        self.text_layers: list[TextLayer] = []
        self.selected_layer: int = -1

        self.watermark_states: list[WatermarkState] = default_watermark_states()
        self._wm_pix_cache: dict[tuple[str, int], QPixmap] = {}
        self.effect_enabled: bool = False
        self.effect_code: str = ""
        self.effect_duration: float = 10.0
        self.effect_breakpoints: list[float] = []
        self.effect_error: Optional[str] = None
        self._effect_code_cache_src: str = ""
        self._effect_code_cache_obj = None
        self.region_guide_enabled: bool = False
        self._region_hover_norm: tuple[float, float] | None = None

        # ── Animation ────────────────────────────────────────────────────
        self.time: float = 0.0
        self._paused: bool = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000 // 60)

        # ── Drag state ───────────────────────────────────────────────────
        self._drag_item = None            # _DRAG_PHONE | _DRAG_MAC | TextLayer
        self._drag_start_mouse: QPointF | None = None
        self._drag_start_pos: tuple[float, float] | None = None
        self._drag_watermark_idx: Optional[int] = None
        self._drag_start_wm_center: tuple[float, float] | None = None

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    def pause(self, paused: bool) -> None:
        self._paused = paused

    def reset_time(self) -> None:
        self.set_time(0.0)

    def screen_target(self, target: str | None = None) -> str:
        if target in ("phone", "mac"):
            return target
        if self.device_mode == "computer":
            return "mac"
        if self.device_mode == "both":
            return self.device_edit_target if self.device_edit_target in ("phone", "mac") else "phone"
        return "phone"

    def screen_slot(self, target: str | None = None) -> ScreenSlot:
        return self.mac_screen if self.screen_target(target) == "mac" else self.phone_screen

    # ── 兼容旧 API（指向当前模式下的主屏幕槽）────────────────────────────

    @property
    def screen_pixmap(self) -> Optional[QPixmap]:
        return self.screen_slot().screen_pixmap

    @screen_pixmap.setter
    def screen_pixmap(self, pix: Optional[QPixmap]) -> None:
        self.screen_slot().screen_pixmap = pix

    @property
    def video_cap(self):
        return self.screen_slot().video_cap

    @property
    def video_frame(self) -> Optional[QPixmap]:
        return self.screen_slot().video_frame

    @video_frame.setter
    def video_frame(self, pm: Optional[QPixmap]) -> None:
        self.screen_slot().video_frame = pm

    @property
    def _video_path(self) -> Optional[str]:
        return self.screen_slot()._video_path

    @property
    def _video_fps(self) -> float:
        return self.screen_slot()._video_fps

    @property
    def _video_duration_sec(self) -> Optional[float]:
        return self.screen_slot()._video_duration_sec

    def set_time(self, t: float) -> None:
        """设置当前预览时间（秒），并同步视频帧与画面刷新。"""
        self.time = max(0.0, float(t))
        if not self._export_active:
            for slot in (self.phone_screen, self.mac_screen):
                if slot.video_cap:
                    slot.reset_preview_sync()
                    slot.seek_to_time(self.time)
        self.time_changed.emit(self.time)
        self.update()

    def set_video(self, path: str, target: str | None = None) -> None:
        try:
            self.screen_slot(target).set_video(path)
            self.set_time(0.0)
        except ImportError:
            pass

    def clear_video(self, target: str | None = None) -> None:
        self.screen_slot(target).clear_video()

    def clear_screen(self, target: str | None = None) -> None:
        self.screen_slot(target).clear()

    def set_screen_image_path(self, path: str, target: str | None = None) -> None:
        self.screen_slot(target).set_image_path(path)

    def screen_image_path(self, target: str | None = None) -> Optional[str]:
        return self.screen_slot(target).image_path()

    def set_export_active(self, active: bool) -> None:
        """导出 MP4 时设为 True：主线程暂停对同一 VideoCapture 的读取，避免与解码线程冲突。"""
        self._export_active = bool(active)

    def video_fps(self) -> float:
        return max(
            (s.video_fps() for s in (self.phone_screen, self.mac_screen) if s.has_video()),
            default=30.0,
        )

    def video_source_path(self, target: str | None = None) -> Optional[str]:
        if target in ("phone", "mac"):
            return self.screen_slot(target).video_source_path()
        for slot in (self.phone_screen, self.mac_screen):
            p = slot.video_source_path()
            if p:
                return p
        return None

    def has_imported_video(self) -> bool:
        return self.phone_screen.has_video() or self.mac_screen.has_video()

    def imported_video_duration_sec(self) -> Optional[float]:
        durs = [
            d
            for s in (self.phone_screen, self.mac_screen)
            if (d := s.imported_video_duration_sec()) is not None and d > 0
        ]
        return max(durs) if durs else None

    def set_video_time_for_export(self, t: float) -> None:
        """[兼容] 导出管线已改为独立 VideoCapture。"""
        for slot in (self.phone_screen, self.mac_screen):
            if slot.video_cap:
                slot.seek_to_time(t)

    def preview_render_size(self) -> tuple[int, int]:
        """与 paintEvent 中 clip 的画布区域相同（眼睛看到的预览像素宽高）。"""
        return self._canvas_size()

    def center_iphone(self) -> None:
        """将设备置于画布正中央（归一化坐标 0.5, 0.5）。"""
        self.center_device()

    def center_device(self) -> None:
        """将当前编辑目标（或单模式设备）置于画布正中央。"""
        if self.device_mode == "both":
            if self.device_edit_target == "mac":
                self.mac_pos = (0.5, 0.5)
            else:
                self.iphone_pos = (0.5, 0.5)
        elif self.device_mode == "computer":
            self.mac_pos = (0.5, 0.5)
        else:
            self.iphone_pos = (0.5, 0.5)
        self.device_moved.emit(0.5, 0.5)
        self.update()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_frame(
        self,
        painter: QPainter,
        width: int,
        height: int,
        t: float,
    ) -> None:
        """Draw one complete frame.  Called both from paintEvent and exporter."""
        if self.effect_enabled and self.effect_code.strip():
            dev = painter.device()
            is_preview_paint = isinstance(dev, QWidget)
            dpr = self.devicePixelRatioF() if is_preview_paint else 1.0
            pw = max(1, int(round(width * dpr)))
            ph = max(1, int(round(height * dpr)))
            img = QImage(pw, ph, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.black)
            p2 = QPainter(img)
            p2.setRenderHint(QPainter.RenderHint.Antialiasing)
            p2.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            if dpr > 1.0:
                # Keep scene layout in logical coordinates while rasterizing at hi-DPI.
                p2.scale(dpr, dpr)
            self._render_scene(p2, width, height, t)
            p2.end()
            out = self._apply_effect_code(img, pw, ph, t)
            painter.drawImage(QRectF(0, 0, width, height), out, QRectF(0, 0, pw, ph))
            return
        self._render_scene(painter, width, height, t)

    def _render_scene(
        self, painter: QPainter, width: int, height: int, t: float
    ) -> None:
        # Background
        if self.background:
            self.background.render(painter, width, height, t)
        else:
            painter.fillRect(0, 0, width, height, QColor(15, 15, 30))

        # Device mockup(s)
        phone_content = self.phone_screen.current_content()
        mac_content = self.mac_screen.current_content()
        if self.device_mode in ("phone", "both") and self.show_iphone:
            _IPHONE_RENDERER.render(
                painter, width, height,
                self.iphone_model, self.iphone_theme,
                self.iphone_scale, self.iphone_pos,
                phone_content,
            )
        if self.device_mode in ("computer", "both") and self.show_mac:
            _MAC_RENDERER.render(
                painter, width, height,
                self.mac_model, self.mac_theme,
                self.mac_scale, self.mac_pos,
                mac_content,
            )

        # Text layers
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        for layer in self.text_layers:
            layer.render(painter, width, height)

        render_watermarks(
            painter, width, height, self.watermark_states, self._wm_pix_cache
        )

    def _apply_effect_code(
        self, img: QImage, width: int, height: int, t: float
    ) -> QImage:
        out = img
        self.effect_error = None
        src = self.effect_code
        if src != self._effect_code_cache_src:
            self._effect_code_cache_src = src
            self._effect_code_cache_obj = None
            try:
                self._effect_code_cache_obj = compile(src, "<effects>", "exec")
            except Exception as e:
                self.effect_error = str(e)
                return out

        def zoom_region(
            x: float, y: float, w: float, h: float, scale: float
        ) -> None:
            nonlocal out
            if scale <= 0.01:
                return
            x = max(0.0, min(1.0, x))
            y = max(0.0, min(1.0, y))
            w = max(0.001, min(1.0, w))
            h = max(0.001, min(1.0, h))
            pw = width * w
            ph = height * h
            cx = width * x
            cy = height * y
            tx = cx - pw * 0.5
            ty = cy - ph * 0.5
            target = QRectF(tx, ty, pw, ph)
            src_w = pw / scale
            src_h = ph / scale
            sx = cx - src_w * 0.5
            sy = cy - src_h * 0.5
            sx = max(0.0, min(width - src_w, sx))
            sy = max(0.0, min(height - src_h, sy))
            source = QRectF(sx, sy, src_w, src_h)
            src_img = out.copy()
            pz = QPainter(out)
            pz.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            pz.drawImage(target, src_img, source)
            pz.end()

        ns: dict[str, object] = {
            "__builtins__": __builtins__,
            "img": out,
            "width": width,
            "height": height,
            "t": t,
            "time": t,
            "duration": max(0.01, float(self.effect_duration)),
            "breakpoints": list(self.effect_breakpoints),
            "math": math,
            "QPainter": QPainter,
            "QImage": QImage,
            "QRectF": QRectF,
            "QColor": QColor,
            "Qt": Qt,
            "zoom_region": zoom_region,
        }
        try:
            if self._effect_code_cache_obj is not None:
                exec(self._effect_code_cache_obj, ns, ns)
        except Exception as e:
            self.effect_error = str(e)
        return out

    def clear_watermark_pixmap_cache(self) -> None:
        self._wm_pix_cache.clear()

    def grab_frame(self) -> QImage:
        """Return the current frame as a QImage (at preview / clip 区域分辨率)."""
        cw, ch = self.preview_render_size()
        img = QImage(cw, ch, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.black)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.render_frame(p, cw, ch, self.time)
        p.end()
        return img

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def paintEvent(self, _event) -> None:
        w, h = self.width(), self.height()
        cw, ch = self._canvas_size()
        ox = (w - cw) // 2
        oy = (h - ch) // 2

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Outer letterbox（与主窗口深色层次区分）
        p.fillRect(0, 0, w, h, QColor(10, 10, 12))

        p.save()
        p.translate(ox, oy)
        p.setClipRect(0, 0, cw, ch)
        self.render_frame(p, cw, ch, self.time)
        p.restore()

        p.setPen(QColor(255, 255, 255, 18))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(ox, oy, cw, ch, 6, 6)

        if self.region_guide_enabled and self._region_hover_norm is not None:
            nx, ny = self._region_hover_norm
            px = ox + int(round(nx * cw))
            py = oy + int(round(ny * ch))
            p.setPen(QColor(10, 132, 255, 170))
            p.drawLine(px, oy, px, oy + ch)
            p.drawLine(ox, py, ox + cw, py)
            p.setBrush(QColor(10, 132, 255, 210))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPoint(px, py), 4, 4)
            p.setPen(QColor(255, 255, 255, 235))
            p.setBrush(QColor(0, 0, 0, 170))
            label = f"x={nx:.3f}, y={ny:.3f}"
            tx = min(max(ox + 8, px + 10), ox + cw - 130)
            ty = min(max(oy + 8, py + 10), oy + ch - 22)
            p.drawRoundedRect(tx, ty, 122, 20, 4, 4)
            p.drawText(tx + 8, ty + 14, label)

        # Selection highlight
        if self.selected_layer >= 0:
            try:
                layer = self.text_layers[self.selected_layer]
                hr = layer._hit_rect.translated(ox, oy)
                pen = p.pen()
                from PySide6.QtGui import QPen
                sel_pen = QPen(QColor(10, 132, 255), 1.5, Qt.PenStyle.DashLine)
                p.setPen(sel_pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(hr)
            except IndexError:
                self.selected_layer = -1

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        nx, ny = self._to_norm(event.position())
        if nx is None:
            return

        cw, ch = self._canvas_size()
        px, py = nx * cw, ny * ch

        # 水印（最后绘制 = 最上层，优先命中）
        for i in range(len(self.watermark_states) - 1, -1, -1):
            st = self.watermark_states[i]
            if not st.enabled:
                continue
            r = compute_watermark_rect(st, cw, ch, self._wm_pix_cache)
            if r is not None and r.contains(QPointF(px, py)):
                self._drag_watermark_idx = i
                self._drag_start_mouse = QPointF(nx, ny)
                self._drag_start_wm_center = (st.center_x_pct, st.center_y_pct)
                self.selected_layer = -1
                self.layer_selected.emit(-1)
                self._drag_item = None
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.update()
                return

        # Hit-test text layers (reverse order = topmost first)
        for i in range(len(self.text_layers) - 1, -1, -1):
            layer = self.text_layers[i]
            if layer.hit_test(nx, ny, cw, ch):
                self.selected_layer = i
                self.layer_selected.emit(i)
                self._drag_item = layer
                self._drag_start_mouse = QPointF(nx, ny)
                self._drag_start_pos = (layer.x, layer.y)
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.update()
                return

        # Hit-test device bodies（Mac 后绘制，优先命中）
        hit = self._hit_device_at(nx, ny)
        if hit is not None:
            self.selected_layer = -1
            self.layer_selected.emit(-1)
            self._drag_item = _DRAG_MAC if hit == "mac" else _DRAG_PHONE
            self._drag_start_mouse = QPointF(nx, ny)
            self._drag_start_pos = self.mac_pos if hit == "mac" else self.iphone_pos
            if self.device_mode == "both":
                self.device_edit_target = hit
                self.device_edit_target_changed.emit(hit)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        # Deselect
        self.selected_layer = -1
        self.layer_selected.emit(-1)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        nx, ny = self._to_norm(event.position())
        if self.region_guide_enabled:
            if nx is None or ny is None:
                self._region_hover_norm = None
            else:
                self._region_hover_norm = (nx, ny)

        if self._drag_watermark_idx is not None:
            if nx is None:
                return
            i = self._drag_watermark_idx
            st = self.watermark_states[i]
            dx = nx - self._drag_start_mouse.x()
            dy = ny - self._drag_start_mouse.y()
            ocx, ocy = self._drag_start_wm_center or (st.center_x_pct, st.center_y_pct)
            st.center_x_pct = max(0.0, min(100.0, ocx + dx * 100.0))
            st.center_y_pct = max(0.0, min(100.0, ocy + dy * 100.0))
            self.watermark_moved.emit(i)
            self.update()
            return

        if self._drag_item is None:
            # Hover cursor
            if nx is not None and (
                self._hit_watermark(nx, ny)
                or self._hit_device_at(nx, ny) is not None
                or self._hit_any_layer(nx, ny)
            ):
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if nx is None:
            return

        dx = nx - self._drag_start_mouse.x()
        dy = ny - self._drag_start_mouse.y()

        if self._drag_item is _DRAG_PHONE:
            new_x = max(0.05, min(0.95, self._drag_start_pos[0] + dx))
            new_y = max(0.05, min(0.95, self._drag_start_pos[1] + dy))
            self.iphone_pos = (new_x, new_y)
            self.device_moved.emit(new_x, new_y)
        elif self._drag_item is _DRAG_MAC:
            new_x = max(0.05, min(0.95, self._drag_start_pos[0] + dx))
            new_y = max(0.05, min(0.95, self._drag_start_pos[1] + dy))
            self.mac_pos = (new_x, new_y)
            self.device_moved.emit(new_x, new_y)
        elif isinstance(self._drag_item, TextLayer):
            layer = self._drag_item
            layer.x = max(0.0, min(1.0, self._drag_start_pos[0] + dx))
            layer.y = max(0.0, min(1.0, self._drag_start_pos[1] + dy))

        self.update()

    def mouseReleaseEvent(self, _event) -> None:
        self._drag_item = None
        self._drag_start_mouse = None
        self._drag_start_pos = None
        self._drag_watermark_idx = None
        self._drag_start_wm_center = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, _event) -> None:
        if self.region_guide_enabled and self._region_hover_norm is not None:
            self._region_hover_norm = None
            self.update()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        if not self._paused:
            has_video = False
            if not self._export_active:
                for slot in (self.phone_screen, self.mac_screen):
                    if slot.video_cap:
                        has_video = True
            if has_video:
                fps = max(
                    (s.video_fps() for s in (self.phone_screen, self.mac_screen) if s.video_cap),
                    default=30.0,
                )
                self.time += 1.0 / max(fps, 1e-6)
                dur = self.imported_video_duration_sec()
                if dur is not None and dur > 0 and self.time >= dur:
                    self.time = self.time % dur
                if not self._export_active:
                    for slot in (self.phone_screen, self.mac_screen):
                        if slot.video_cap:
                            slot.sync_preview_at(self.time)
            else:
                self.time += 1.0 / 60.0
            self.time_changed.emit(self.time)
        self.update()

    def _canvas_size(self) -> tuple[int, int]:
        rw, rh = self.output_ratio
        ww, wh = self.width(), self.height()
        margin = 0.97
        if ww / wh > rw / rh:
            ch = int(wh * margin)
            cw = int(ch * rw / rh)
        else:
            cw = int(ww * margin)
            ch = int(cw * rh / rw)
        return max(cw, 1), max(ch, 1)

    def _canvas_offset(self) -> tuple[int, int]:
        cw, ch = self._canvas_size()
        return (self.width() - cw) // 2, (self.height() - ch) // 2

    def _to_norm(self, pos: QPointF) -> tuple[float | None, float | None]:
        """Convert widget coordinates to normalised canvas coordinates."""
        ox, oy = self._canvas_offset()
        cw, ch = self._canvas_size()
        px = pos.x() - ox
        py = pos.y() - oy
        if px < 0 or py < 0 or px > cw or py > ch:
            return None, None
        return px / cw, py / ch

    def _iphone_body_contains(self, nx: float, ny: float) -> bool:
        if not self.show_iphone or self.device_mode not in ("phone", "both"):
            return False
        cw, ch = self._canvas_size()
        body, _ = iphone_layout(
            cw, ch,
            self.iphone_model, self.iphone_theme,
            self.iphone_scale, self.iphone_pos,
        )
        px, py = nx * cw, ny * ch
        return body.contains(QPointF(px, py))

    def _mac_body_contains(self, nx: float, ny: float) -> bool:
        if not self.show_mac or self.device_mode not in ("computer", "both"):
            return False
        cw, ch = self._canvas_size()
        body, _ = mac_layout(
            cw, ch,
            self.mac_model, self.mac_theme,
            self.mac_scale, self.mac_pos,
        )
        px, py = nx * cw, ny * ch
        return body.contains(QPointF(px, py))

    def _hit_device_at(self, nx: float, ny: float) -> str | None:
        """返回 'mac' | 'phone' | None（Mac 优先）。"""
        if self._mac_body_contains(nx, ny):
            return "mac"
        if self._iphone_body_contains(nx, ny):
            return "phone"
        return None

    def _hit_device(self, nx: float, ny: float) -> bool:
        return self._hit_device_at(nx, ny) is not None

    def _hit_any_layer(self, nx: float, ny: float) -> bool:
        cw, ch = self._canvas_size()
        return any(l.hit_test(nx, ny, cw, ch) for l in self.text_layers)

    def _hit_watermark(self, nx: float, ny: float) -> bool:
        cw, ch = self._canvas_size()
        px, py = nx * cw, ny * ch
        for i in range(len(self.watermark_states) - 1, -1, -1):
            st = self.watermark_states[i]
            if not st.enabled:
                continue
            r = compute_watermark_rect(st, cw, ch, self._wm_pix_cache)
            if r is not None and r.contains(QPointF(px, py)):
                return True
        return False
