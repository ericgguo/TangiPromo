"""
Animated preview canvas.

• Runs at up to 60 FPS via QTimer.
• Maintains correct aspect ratio inside the widget.
• Supports drag-to-move for the iPhone mockup and text layers.
• render_frame() is the single rendering entry-point shared with the exporter.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from .iphone import IPhoneRenderer, MODEL_ORDER, layout
from .iphone_manifest import default_theme_for_model
from .text_layer import TextLayer
from .watermark import (
    WatermarkState,
    compute_watermark_rect,
    default_watermark_states,
    render_watermarks,
)


_RENDERER = IPhoneRenderer()

# Sentinel for "dragging the iPhone"
_DRAG_IPHONE = object()


def _decode_frame_at_time(
    cap,
    t: float,
    fps: float,
    duration_sec: Optional[float],
):
    """从已打开的 cv2.VideoCapture 按时间（秒）取一帧为 QPixmap；失败返回 None。"""
    try:
        import cv2
        from PySide6.QtGui import QImage, QPixmap
        if duration_sec is not None and duration_sec > 0:
            t = min(max(0.0, t), max(0.0, duration_sec - 0.5 / fps))
        else:
            t = max(0.0, t)
        idx = int(t * fps + 0.5)
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret and idx > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, idx - 1))
            ret, frame = cap.read()
        if not ret:
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy()
        h, w, c = frame_rgb.shape
        img = QImage(
            frame_rgb.data, w, h, w * c, QImage.Format.Format_RGB888
        ).copy()
        return QPixmap.fromImage(img)
    except Exception:
        return None


class Canvas(QWidget):
    # Emitted when a text layer is clicked (passes layer index, or -1 for none)
    layer_selected = Signal(int)
    # Emitted when iPhone position changes
    iphone_moved = Signal(float, float)
    # 水印索引（用于同步右侧输入框）
    watermark_moved = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(400, 280)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        # ── Rendering state ──────────────────────────────────────────────
        self.background = None          # Background instance
        self.output_ratio: tuple[int, int] = (16, 9)

        _m0 = MODEL_ORDER[0] if MODEL_ORDER else "iPhone 17 Pro Max"
        self.iphone_model: str = _m0
        self.iphone_theme: str = default_theme_for_model(_m0)
        self.iphone_scale: float = 0.72
        self.iphone_pos: tuple[float, float] = (0.5, 0.5)
        self.show_iphone: bool = True

        self.screen_pixmap: Optional[QPixmap] = None   # static image
        self.video_cap = None                           # cv2.VideoCapture
        self.video_frame: Optional[QPixmap] = None
        self._video_path: Optional[str] = None          # 源文件路径（导出线程可另开 capture）
        # 导入视频的元数据（用于导出 seek / 「完整包含片长」）
        self._video_fps: float = 30.0
        self._video_duration_sec: Optional[float] = None
        # 为 True 时主线程不再对 video_cap read，避免与导出线程争用解码器
        self._export_active: bool = False

        self.text_layers: list[TextLayer] = []
        self.selected_layer: int = -1

        self.watermark_states: list[WatermarkState] = default_watermark_states()
        self._wm_pix_cache: dict[tuple[str, int], QPixmap] = {}

        # ── Animation ────────────────────────────────────────────────────
        self.time: float = 0.0
        self._paused: bool = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000 // 60)

        # ── Drag state ───────────────────────────────────────────────────
        self._drag_item = None            # _DRAG_IPHONE or TextLayer
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
        self.time = 0.0

    def set_video(self, path: str) -> None:
        try:
            import cv2
            if self.video_cap:
                self.video_cap.release()
            self.video_cap = cv2.VideoCapture(path)
            self._video_path = path
            self.screen_pixmap = None
            fps = float(self.video_cap.get(cv2.CAP_PROP_FPS) or 0.0)
            self._video_fps = fps if fps > 1e-6 else 30.0
            fc = float(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
            if fc > 0 and self._video_fps > 0:
                self._video_duration_sec = fc / self._video_fps
            else:
                self._video_duration_sec = None
            self._advance_video()
        except ImportError:
            pass

    def clear_video(self) -> None:
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        self._video_path = None
        self.video_frame = None
        self._video_fps = 30.0
        self._video_duration_sec = None

    def set_export_active(self, active: bool) -> None:
        """导出 MP4 时设为 True：主线程暂停对同一 VideoCapture 的读取，避免与解码线程冲突。"""
        self._export_active = bool(active)

    def video_fps(self) -> float:
        return self._video_fps

    def video_source_path(self) -> Optional[str]:
        """已导入视频的本地路径；无视频时为 None。"""
        return self._video_path

    def preview_render_size(self) -> tuple[int, int]:
        """与 paintEvent 中 clip 的画布区域相同（眼睛看到的预览像素宽高）。"""
        return self._canvas_size()

    def imported_video_duration_sec(self) -> Optional[float]:
        """已导入视频的时长（秒）；无视频或未解析到时为 None。"""
        return self._video_duration_sec

    def set_video_time_for_export(self, t: float) -> None:
        """[兼容] 仍可用，但导出管线已改为独立 VideoCapture；优先不要用与主线程共用 cap。"""
        if not self.video_cap:
            return
        pm = _decode_frame_at_time(self.video_cap, t, self._video_fps, self._video_duration_sec)
        if pm is not None:
            self.video_frame = pm

    def center_iphone(self) -> None:
        """将设备置于画布正中央（归一化坐标 0.5, 0.5）。"""
        self.iphone_pos = (0.5, 0.5)
        self.iphone_moved.emit(0.5, 0.5)
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
        # Background
        if self.background:
            self.background.render(painter, width, height, t)
        else:
            painter.fillRect(0, 0, width, height, QColor(15, 15, 30))

        # iPhone
        if self.show_iphone:
            content = self.video_frame or self.screen_pixmap
            _RENDERER.render(
                painter, width, height,
                self.iphone_model, self.iphone_theme,
                self.iphone_scale, self.iphone_pos,
                content,
            )

        # Text layers
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        for layer in self.text_layers:
            layer.render(painter, width, height)

        render_watermarks(
            painter, width, height, self.watermark_states, self._wm_pix_cache
        )

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

        # Hit-test iPhone body
        if self.show_iphone and self._hit_iphone(nx, ny):
            self.selected_layer = -1
            self.layer_selected.emit(-1)
            self._drag_item = _DRAG_IPHONE
            self._drag_start_mouse = QPointF(nx, ny)
            self._drag_start_pos = self.iphone_pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        # Deselect
        self.selected_layer = -1
        self.layer_selected.emit(-1)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        nx, ny = self._to_norm(event.position())

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
                or self._hit_iphone(nx, ny)
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

        if self._drag_item is _DRAG_IPHONE:
            new_x = max(0.05, min(0.95, self._drag_start_pos[0] + dx))
            new_y = max(0.05, min(0.95, self._drag_start_pos[1] + dy))
            self.iphone_pos = (new_x, new_y)
            self.iphone_moved.emit(new_x, new_y)
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

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        if not self._paused:
            self.time += 1.0 / 60.0
        if self.video_cap and not self._export_active:
            self._advance_video()
        self.update()

    def _advance_video(self) -> None:
        try:
            import cv2
            import numpy as np
            ret, frame = self.video_cap.read()
            if not ret:
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.video_cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, c = frame_rgb.shape
                img = QImage(
                    frame_rgb.data, w, h, w * c, QImage.Format.Format_RGB888
                )
                self.video_frame = QPixmap.fromImage(img)
        except Exception:
            pass

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

    def _hit_iphone(self, nx: float, ny: float) -> bool:
        cw, ch = self._canvas_size()
        body, _ = layout(
            cw,
            ch,
            self.iphone_model,
            self.iphone_theme,
            self.iphone_scale,
            self.iphone_pos,
        )
        px, py = nx * cw, ny * ch
        return body.contains(QPointF(px, py))

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
