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
        self.seek_to_time(0.0)

    def clear(self) -> None:
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        self._video_path = None
        self.video_frame = None
        self._video_fps = 30.0
        self._video_duration_sec = None
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

    def seek_to_time(self, t: float) -> None:
        if not self.video_cap:
            return
        pm = _decode_frame_at_time(self.video_cap, t, self._video_fps, self._video_duration_sec)
        if pm is not None:
            self.video_frame = pm

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
            return {"type": "video", "path": self._video_path}
        if self._image_path:
            return {"type": "image", "path": self._image_path}
        return {"type": "none", "path": None}
