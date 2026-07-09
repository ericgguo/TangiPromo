"""单台设备（手机 / Mac）的屏幕内容：静态图或视频。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QImage, QPixmap


def _decode_frame_at_time(cap, t: float, fps: float, duration_sec: Optional[float]) -> Optional[QPixmap]:
    try:
        import cv2

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
        img = QImage(frame_rgb.data, w, h, w * c, QImage.Format.Format_RGB888).copy()
        return QPixmap.fromImage(img)
    except Exception:
        return None


class ScreenSlot:
    """一台设备 mockup 内的屏幕素材。"""

    def __init__(self) -> None:
        self.screen_pixmap: Optional[QPixmap] = None
        self._image_path: Optional[str] = None
        self.video_cap = None
        self.video_frame: Optional[QPixmap] = None
        self._video_path: Optional[str] = None
        self._video_fps: float = 30.0
        self._video_duration_sec: Optional[float] = None
        self._freeze_ranges: list[tuple[float, float]] = []
        self._preview_src_t: Optional[float] = None

    def reset_preview_sync(self) -> None:
        self._preview_src_t = None

    def current_content(self) -> Optional[QPixmap]:
        return self.video_frame or self.screen_pixmap

    def image_path(self) -> Optional[str]:
        return self._image_path

    def video_source_path(self) -> Optional[str]:
        return self._video_path

    def video_fps(self) -> float:
        return self._video_fps

    def imported_video_duration_sec(self) -> Optional[float]:
        return self._video_duration_sec

    def freeze_ranges(self) -> list[tuple[float, float]]:
        return list(self._freeze_ranges)

    def set_freeze_ranges(self, ranges: list[tuple[float, float]]) -> None:
        cleaned: list[tuple[float, float]] = []
        for start, end in ranges:
            s = float(start)
            e = float(end)
            if e <= s:
                continue
            cleaned.append((s, e))
        cleaned.sort(key=lambda x: x[0])
        merged: list[tuple[float, float]] = []
        for s, e in cleaned:
            if not merged:
                merged.append((s, e))
                continue
            ps, pe = merged[-1]
            if s <= pe:
                merged[-1] = (ps, max(pe, e))
            else:
                merged.append((s, e))
        self._freeze_ranges = merged
        self.reset_preview_sync()

    def video_time_at(self, timeline_t: float) -> float:
        """Map timeline time to source video time with freeze windows."""
        t = max(0.0, float(timeline_t))
        shift = 0.0
        for s, e in self._freeze_ranges:
            if t < s:
                break
            if s <= t <= e:
                return max(0.0, s - shift)
            shift += (e - s)
        return max(0.0, t - shift)

    def has_video(self) -> bool:
        return bool(self._video_path and self.video_cap is not None)

    def set_image_path(self, path: str) -> None:
        self._image_path = path or None

    def set_image(self, path: str, pix: QPixmap) -> None:
        self.clear_video()
        self._image_path = path
        self.screen_pixmap = pix

    def set_video(self, path: str) -> None:
        import cv2

        if self.video_cap:
            self.video_cap.release()
        self.video_cap = cv2.VideoCapture(path)
        self._video_path = path
        self.screen_pixmap = None
        self._image_path = None
        fps = float(self.video_cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self._video_fps = fps if fps > 1e-6 else 30.0
        fc = float(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
        if fc > 0 and self._video_fps > 0:
            self._video_duration_sec = fc / self._video_fps
        else:
            self._video_duration_sec = None
        self.reset_preview_sync()
        self.seek_to_time(0.0)

    def clear(self) -> None:
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        self._video_path = None
        self.video_frame = None
        self._video_fps = 30.0
        self._video_duration_sec = None
        self._freeze_ranges = []
        self.reset_preview_sync()
        self.screen_pixmap = None
        self._image_path = None

    def clear_video(self) -> None:
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        self._video_path = None
        self.video_frame = None
        self._video_fps = 30.0
        self._video_duration_sec = None
        self._freeze_ranges = []
        self.reset_preview_sync()

    def seek_to_time(self, t: float) -> None:
        if not self.video_cap:
            return
        src_t = self.video_time_at(t)
        pm = _decode_frame_at_time(
            self.video_cap, src_t, self._video_fps, self._video_duration_sec
        )
        if pm is not None:
            self.video_frame = pm
        self._preview_src_t = src_t

    def sync_preview_at(self, timeline_t: float) -> bool:
        """预览播放：冻结时复用当前帧，正常播放时顺序解码，跳转时才 seek。"""
        if not self.video_cap:
            return False
        src_t = self.video_time_at(timeline_t)
        step = 1.0 / max(self._video_fps, 1e-6)
        if self._preview_src_t is not None:
            if abs(src_t - self._preview_src_t) < 1e-6:
                return True
            if abs(src_t - (self._preview_src_t + step)) <= step * 0.6:
                if self.advance_video():
                    self._preview_src_t = src_t
                    return True
        self.seek_to_time(timeline_t)
        return True

    def advance_video(self) -> bool:
        if not self.video_cap:
            return False
        try:
            import cv2

            ret, frame = self.video_cap.read()
            if not ret:
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.video_cap.read()
            if not ret:
                return False
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, c = frame_rgb.shape
            img = QImage(frame_rgb.data, w, h, w * c, QImage.Format.Format_RGB888)
            self.video_frame = QPixmap.fromImage(img)
            return True
        except Exception:
            return False

    def to_content_dict(self) -> dict[str, str | None]:
        if self._video_path:
            return {
                "type": "video",
                "path": self._video_path,
                "freeze_ranges": [[s, e] for s, e in self._freeze_ranges],
            }
        if self._image_path:
            return {"type": "image", "path": self._image_path}
        return {"type": "none", "path": None}
