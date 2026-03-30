"""
Export the canvas to high-quality PNG/JPG or MP4 video.

渲染管线（与预览几何一致、按目标像素精绘）：
  • 文字 / 手机框 / 水印 / 背景等均按 width×height 归一化布局，
    因此在「导出分辨率」下直接 render_frame(w, h, t)，与窗口里看到的构图一致，
    且为真分辨率输出，不会像「先按预览小图再放大」那样产生马赛克。

MP4：逐帧按时间轴 seek 导入视频；优先尝试 H.264(avc1)，失败则回退 mp4v。
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt, Signal, QThread
from PySide6.QtGui import QImage, QPainter

from .canvas import _decode_frame_at_time
from .i18n import tr


def _create_video_writer(path: str, fps: float, size: tuple[int, int]):
    """优先使用 avc1(H.264)，码流通常比 mp4v 更细、块效应更轻。"""
    import cv2

    w, h = size
    for tag in ("avc1", "H264", "mp4v"):
        fourcc = cv2.VideoWriter_fourcc(*tag)
        vw = cv2.VideoWriter(path, fourcc, fps, (w, h))
        if vw.isOpened():
            return vw
    return None


def _paint_export_frame(canvas, img: QImage, width: int, height: int, t: float) -> None:
    """在目标尺寸上绘制单帧，使用与预览相同的高质量选项。"""
    img.fill(Qt.GlobalColor.black)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    try:
        p.setRenderHint(QPainter.RenderHint.LosslessImageRendering)
    except AttributeError:
        pass
    canvas.render_frame(p, width, height, t)
    p.end()


class ExportWorker(QThread):
    """Background thread for video export."""

    progress = Signal(int)       # 0-100
    finished = Signal(str)       # output path
    error = Signal(str)

    def __init__(
        self,
        canvas,
        path: str,
        out_width: int,
        out_height: int,
        fps: float,
        duration: float,
        *,
        ensure_full_import_video: bool = False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.path = path
        self.out_width = out_width
        self.out_height = out_height
        self.fps = fps
        self.duration = duration
        self.ensure_full_import_video = ensure_full_import_video

    def run(self) -> None:
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.error.emit(tr("export.err.opencv"))
            return

        dur = float(self.duration)
        vd = self.canvas.imported_video_duration_sec()
        if self.ensure_full_import_video and vd is not None and vd > 0:
            dur = max(dur, vd)

        total = int(self.fps * dur)
        if total < 1:
            self.error.emit(tr("export.err.short"))
            return

        ow, oh = int(self.out_width), int(self.out_height)
        if ow < 1 or oh < 1:
            self.error.emit(tr("export.err.invalid_wh"))
            return

        # 独立 VideoCapture，避免与主线程预览共用同一解码器（防止 libav 断言崩溃）
        export_cap = None
        vpath = self.canvas.video_source_path()
        if vpath:
            export_cap = cv2.VideoCapture(vpath)
            if not export_cap.isOpened():
                export_cap.release()
                export_cap = None

        self.canvas.set_export_active(True)
        try:
            vw = _create_video_writer(self.path, self.fps, (ow, oh))
            if vw is None:
                self.error.emit(tr("export.err.writer", path=self.path))
                return

            src_fps = float(self.canvas.video_fps())
            src_dur = self.canvas.imported_video_duration_sec()

            def _clamp_src_time(tt: float) -> float:
                if src_dur is not None and src_dur > 0 and src_fps > 1e-6:
                    return min(max(0.0, tt), src_dur - 0.5 / src_fps)
                return max(0.0, tt)

            # When exporting a video, decoding by seeking for every frame
            # (CAP_PROP_POS_FRAMES + read) may land on the same/nearby frame,
            # especially on 4K sources/codecs. We sacrifice some speed and
            # decode sequentially after a single initial seek.
            current_idx: int | None = None
            current_pm = None
            eof = False

            if export_cap is not None and src_fps > 1e-6:
                # Initialize to the first output frame's nearest input frame.
                t0 = _clamp_src_time(0.0)
                idx0 = int(t0 * src_fps + 0.5)
                export_cap.set(cv2.CAP_PROP_POS_FRAMES, idx0)
                ret, frame = export_cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy()
                    h, w, c = frame_rgb.shape
                    img0 = QImage(
                        frame_rgb.data, w, h, w * c, QImage.Format.Format_RGB888
                    ).copy()
                    current_pm = QPixmap.fromImage(img0)
                    current_idx = idx0
                else:
                    eof = True
                    current_idx = idx0

            for i in range(total):
                t = i / self.fps

                if export_cap is not None and src_fps > 1e-6 and not eof:
                    tt = _clamp_src_time(t)
                    target_idx = int(tt * src_fps + 0.5)

                    # Decode forward until we reach the nearest frame.
                    while current_idx is not None and current_idx < target_idx:
                        ret, frame = export_cap.read()
                        if not ret:
                            eof = True
                            break
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy()
                        h, w, c = frame_rgb.shape
                        img = QImage(
                            frame_rgb.data, w, h, w * c, QImage.Format.Format_RGB888
                        ).copy()
                        current_pm = QPixmap.fromImage(img)
                        current_idx += 1

                    self.canvas.video_frame = current_pm
                elif export_cap is not None:
                    # Fallback (e.g. init failed): keep last frame (or None).
                    self.canvas.video_frame = current_pm

                img = QImage(ow, oh, QImage.Format.Format_RGB32)
                _paint_export_frame(self.canvas, img, ow, oh, t)

                img = img.convertToFormat(QImage.Format.Format_RGB888)
                iw, ih = img.width(), img.height()
                ptr = img.bits()
                try:
                    ptr.setsize(img.sizeInBytes())  # type: ignore[attr-defined]
                except Exception:
                    pass
                arr = np.frombuffer(ptr, dtype=np.uint8).reshape((ih, iw, 3))
                bgr = arr[:, :, ::-1].copy()
                vw.write(bgr)

                self.progress.emit(int((i + 1) / total * 100))

            vw.release()
            self.finished.emit(self.path)
        finally:
            if export_cap is not None:
                export_cap.release()
            self.canvas.set_export_active(False)


class Exporter:
    """Synchronous image export + async video export helper."""

    @staticmethod
    def export_image(
        canvas,
        path: str,
        width: int,
        height: int,
        quality: int = 95,
    ) -> str:
        """在目标分辨率下直接渲染（与预览同一套归一化布局，无放大插值模糊）。"""
        w, h = max(width, 1), max(height, 1)
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        try:
            p.setRenderHint(QPainter.RenderHint.LosslessImageRendering)
        except AttributeError:
            pass
        canvas.render_frame(p, w, h, canvas.time)
        p.end()

        ext = os.path.splitext(path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            flat = QImage(w, h, QImage.Format.Format_RGB32)
            flat.fill(Qt.GlobalColor.white)
            fp = QPainter(flat)
            fp.drawImage(0, 0, img)
            fp.end()
            flat.save(path, "JPEG", quality)
        else:
            img.save(path, "PNG")

        return path

    @staticmethod
    def start_video_export(
        canvas,
        path: str,
        width: int,
        height: int,
        fps: float,
        duration: float,
        *,
        ensure_full_import_video: bool = False,
        on_progress: Callable[[int], None] | None = None,
        on_finished: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> ExportWorker:
        """Start async video export.  Returns the worker thread."""
        worker = ExportWorker(
            canvas,
            path,
            width,
            height,
            fps,
            duration,
            ensure_full_import_video=ensure_full_import_video,
        )
        if on_progress:
            worker.progress.connect(on_progress)
        if on_finished:
            worker.finished.connect(on_finished)
        if on_error:
            worker.error.connect(on_error)
        worker.start()
        return worker


# 导出分辨率预设（与 main_window 下拉框一致）
RESOLUTIONS: dict[str, tuple[int, int]] = {
    "1080p (16:9)":  (1920, 1080),
    "2K (16:9)":     (2560, 1440),
    "4K (16:9)":     (3840, 2160),
    "1080p (9:16)":  (1080, 1920),
    "4K (9:16)":     (2160, 3840),
    "1080×1080":     (1080, 1080),
    "4K (1:1)":      (3840, 3840),
    "1080p (4:3)":   (1440, 1080),
    "1350×1080 (4:3)": (1350, 1080),
    "4K (4:3)":      (3840, 2880),
    "1080p (4:5)":   (864, 1080),
    "4K (4:5)":      (3072, 3840),
    "1080p (21:9)":  (2520, 1080),
    "4K (21:9)":     (3840, 1646),
    "自定义…":       (0, 0),
}