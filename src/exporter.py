"""
Export the canvas to high-quality PNG/JPG or MP4 video.

Rendering pipeline (resolution-native, no upscale blur):
  render_frame(w, h, t) draws at full export resolution.

MP4 export prefers **ffmpeg** via stdin pipe for:
  • macOS hardware H.264 (h264_videotoolbox) — much faster on Apple Silicon / Intel Mac
  • proper bitrate / CRF / pixel format → plays in QuickTime, iOS, Android, browsers
  Falls back to OpenCV VideoWriter when ffmpeg is unavailable.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt, Signal, QThread
from PySide6.QtGui import QImage, QPainter, QPixmap

from .canvas import _decode_frame_at_time
from .i18n import tr


def _ffmpeg_path() -> Optional[str]:
    return shutil.which("ffmpeg")


def _build_ffmpeg_cmd(
    path: str, fps: float, width: int, height: int
) -> list[str]:
    """Build an ffmpeg command that reads raw RGB24 from stdin."""
    ffmpeg = _ffmpeg_path()
    if not ffmpeg:
        return []

    inp = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "pipe:0",
    ]

    is_mac = platform.system() == "Darwin"
    pixels = width * height

    if is_mac:
        # h264_videotoolbox: Apple hardware encoder.
        # realtime 0 = quality-first; allow_sw 1 = software fallback if HW busy.
        # profile high + level auto; bitrate scaled by resolution.
        if pixels <= 1920 * 1080:
            br = "8M"
        elif pixels <= 2560 * 1440:
            br = "16M"
        else:
            br = "30M"
        enc = [
            "-c:v", "h264_videotoolbox",
            "-b:v", br,
            "-profile:v", "high",
            "-level:v", "auto",
            "-realtime", "0",
            "-allow_sw", "1",
        ]
    else:
        # libx264 software: CRF 18 (visually lossless), medium preset.
        enc = [
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "medium",
            "-profile:v", "high",
            "-level:v", "4.2",
        ]

    out = [
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        path,
    ]
    return inp + enc + out


def _create_opencv_writer(path: str, fps: float, size: tuple[int, int]):
    """Fallback: OpenCV VideoWriter with avc1 → H264 → mp4v."""
    import cv2
    w, h = size
    for tag in ("avc1", "H264", "mp4v"):
        fourcc = cv2.VideoWriter_fourcc(*tag)
        vw = cv2.VideoWriter(path, fourcc, fps, (w, h))
        if vw.isOpened():
            return vw
    return None


def _paint_export_frame(canvas, img: QImage, width: int, height: int, t: float) -> None:
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

        export_cap = None
        vpath = self.canvas.video_source_path()
        if vpath:
            export_cap = cv2.VideoCapture(vpath)
            if not export_cap.isOpened():
                export_cap.release()
                export_cap = None

        # --- Choose writer: ffmpeg pipe (preferred) or OpenCV fallback ---
        ffmpeg_cmd = _build_ffmpeg_cmd(self.path, self.fps, ow, oh)
        ffmpeg_proc: Optional[subprocess.Popen] = None
        cv_writer = None
        use_ffmpeg = False

        if ffmpeg_cmd:
            try:
                ffmpeg_proc = subprocess.Popen(
                    ffmpeg_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                use_ffmpeg = True
            except Exception:
                ffmpeg_proc = None

        if not use_ffmpeg:
            cv_writer = _create_opencv_writer(self.path, self.fps, (ow, oh))
            if cv_writer is None:
                self.error.emit(tr("export.err.writer", path=self.path))
                return

        self.canvas.set_export_active(True)
        try:
            src_fps = float(self.canvas.video_fps())
            src_dur = self.canvas.imported_video_duration_sec()

            def _clamp_src_time(tt: float) -> float:
                if src_dur is not None and src_dur > 0 and src_fps > 1e-6:
                    return min(max(0.0, tt), src_dur - 0.5 / src_fps)
                return max(0.0, tt)

            current_idx: int | None = None
            current_pm: QPixmap | None = None
            eof = False

            if export_cap is not None and src_fps > 1e-6:
                t0 = _clamp_src_time(0.0)
                idx0 = int(t0 * src_fps + 0.5)
                export_cap.set(cv2.CAP_PROP_POS_FRAMES, idx0)
                ret, frame = export_cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy()
                    fh, fw, fc = frame_rgb.shape
                    img0 = QImage(
                        frame_rgb.data, fw, fh, fw * fc, QImage.Format.Format_RGB888
                    ).copy()
                    current_pm = QPixmap.fromImage(img0)
                    current_idx = idx0
                else:
                    eof = True
                    current_idx = idx0

            row_bytes = ow * 3

            for i in range(total):
                t = i / self.fps

                if export_cap is not None and src_fps > 1e-6 and not eof:
                    tt = _clamp_src_time(t)
                    target_idx = int(tt * src_fps + 0.5)

                    while current_idx is not None and current_idx < target_idx:
                        ret, frame = export_cap.read()
                        if not ret:
                            eof = True
                            break
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy()
                        fh, fw, fc = frame_rgb.shape
                        qimg = QImage(
                            frame_rgb.data, fw, fh, fw * fc, QImage.Format.Format_RGB888
                        ).copy()
                        current_pm = QPixmap.fromImage(qimg)
                        current_idx += 1

                    self.canvas.video_frame = current_pm
                elif export_cap is not None:
                    self.canvas.video_frame = current_pm

                img = QImage(ow, oh, QImage.Format.Format_RGB32)
                _paint_export_frame(self.canvas, img, ow, oh, t)

                img = img.convertToFormat(QImage.Format.Format_RGB888)

                if use_ffmpeg and ffmpeg_proc and ffmpeg_proc.stdin:
                    iw, ih = img.width(), img.height()
                    ptr = img.bits()
                    try:
                        ptr.setsize(img.sizeInBytes())  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    raw = bytes(ptr)
                    # Ensure each row is contiguous (no padding beyond 3*w)
                    stride = img.bytesPerLine()
                    if stride != row_bytes:
                        rows = []
                        for y in range(ih):
                            rows.append(raw[y * stride : y * stride + row_bytes])
                        raw = b"".join(rows)
                    try:
                        ffmpeg_proc.stdin.write(raw)
                    except BrokenPipeError:
                        stderr_out = ffmpeg_proc.stderr.read() if ffmpeg_proc.stderr else b""
                        self.error.emit(f"ffmpeg error: {stderr_out.decode(errors='replace')}")
                        return
                else:
                    iw, ih = img.width(), img.height()
                    ptr = img.bits()
                    try:
                        ptr.setsize(img.sizeInBytes())  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    arr = np.frombuffer(ptr, dtype=np.uint8).reshape((ih, iw, 3))
                    bgr = arr[:, :, ::-1].copy()
                    cv_writer.write(bgr)

                self.progress.emit(int((i + 1) / total * 100))

            # Finalize
            if use_ffmpeg and ffmpeg_proc:
                if ffmpeg_proc.stdin:
                    ffmpeg_proc.stdin.close()
                ffmpeg_proc.wait()
                if ffmpeg_proc.returncode != 0:
                    stderr_out = ffmpeg_proc.stderr.read() if ffmpeg_proc.stderr else b""
                    self.error.emit(f"ffmpeg exit {ffmpeg_proc.returncode}: {stderr_out.decode(errors='replace')}")
                    return
            elif cv_writer is not None:
                cv_writer.release()

            self.finished.emit(self.path)
        finally:
            if export_cap is not None:
                export_cap.release()
            if ffmpeg_proc is not None:
                try:
                    if ffmpeg_proc.stdin and not ffmpeg_proc.stdin.closed:
                        ffmpeg_proc.stdin.close()
                    ffmpeg_proc.kill()
                except Exception:
                    pass
            if cv_writer is not None:
                try:
                    cv_writer.release()
                except Exception:
                    pass
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
