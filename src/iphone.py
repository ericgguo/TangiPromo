
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap

from .iphone_manifest import (
    DEVICE_PNG,
    MODEL_ORDER,
    default_theme_for_model,
    rel_path_for,
)

# 项目内资源根：.../TangiPromo/assets/iphone/third_party/Exports/iOS/
_ASSET_IOS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "iphone", "third_party", "Exports", "iOS")
)

# 屏幕区域缓存：绝对路径 -> (nx, ny, nw, nh) 相对整图 0~1
_screen_norm_cache: dict[str, tuple[float, float, float, float]] = {}


def _abs_path_for(model: str, theme: str) -> str | None:
    rel = rel_path_for(model, theme)
    if not rel:
        # 主题不匹配时尝试默认色
        rel = rel_path_for(model, default_theme_for_model(model))
    if not rel:
        return None
    return os.path.join(_ASSET_IOS, rel)


@lru_cache(maxsize=64)
def _load_pixmap(abs_path: str) -> Optional[QPixmap]:
    p = QPixmap(abs_path)
    return p if not p.isNull() else None


def screen_norm_rect(abs_path: str) -> tuple[float, float, float, float]:
    """透明屏幕区域相对整图的归一化矩形 (x,y,w,h)，与中心连通域。"""
    if abs_path in _screen_norm_cache:
        return _screen_norm_cache[abs_path]
    fallback = (0.065, 0.033, 0.868, 0.935)
    if not os.path.isfile(abs_path):
        _screen_norm_cache[abs_path] = fallback
        return fallback
    try:
        import cv2
        import numpy as np
        img = cv2.imread(abs_path, cv2.IMREAD_UNCHANGED)
        if img is None or img.ndim < 3 or img.shape[2] < 4:
            _screen_norm_cache[abs_path] = fallback
            return fallback
        alpha = img[:, :, 3]
        h, w = alpha.shape
        mask = (alpha < 40).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)
        cx, cy = w // 2, h // 2
        lab = int(labels[cy, cx])
        if lab <= 0:
            _screen_norm_cache[abs_path] = fallback
            return fallback
        x, y, bw, bh, _area = stats[lab]
        t = (x / w, y / h, bw / w, bh / h)
        _screen_norm_cache[abs_path] = t
        return t
    except Exception:
        _screen_norm_cache[abs_path] = fallback
        return fallback


def device_aspect_ratio(model: str, theme: str) -> float:
    """机身宽 / 高（用于点击检测等）。"""
    p = _abs_path_for(model, theme)
    if not p or not os.path.isfile(p):
        return 0.48
    pm = _load_pixmap(p)
    if pm is None or pm.height() == 0:
        return 0.48
    return pm.width() / pm.height()


def layout(
    canvas_w: int,
    canvas_h: int,
    model_name: str,
    theme_name: str,
    scale: float,
    pos: tuple[float, float],
) -> tuple[QRectF, QRectF]:
    """
    返回画布坐标系下的 (机身矩形, 屏幕矩形)。
    scale：机身高度占画布高度比例。
    """
    p = _abs_path_for(model_name, theme_name)
    pm = _load_pixmap(p) if p and os.path.isfile(p) else None
    if pm is None or pm.height() == 0:
        # 占位：与旧版比例接近的竖屏手机
        bh = canvas_h * scale
        bw = bh * (77.6 / 163.0)
        cx = pos[0] * canvas_w
        cy = pos[1] * canvas_h
        body = QRectF(cx - bw / 2, cy - bh / 2, bw, bh)
        m = 0.04
        scr = QRectF(body.x() + bw * m, body.y() + bh * m, bw * (1 - 2 * m), bh * (1 - 2 * m))
        return body, scr

    iw, ih = pm.width(), pm.height()
    body_h = canvas_h * scale
    body_w = body_h * (iw / ih)
    cx = pos[0] * canvas_w
    cy = pos[1] * canvas_h
    body = QRectF(cx - body_w / 2, cy - body_h / 2, body_w, body_h)

    nx, ny, nw, nh = screen_norm_rect(p)
    scr = QRectF(
        body.x() + nx * body_w,
        body.y() + ny * body_h,
        nw * body_w,
        nh * body_h,
    )
    return body, scr


class IPhoneRenderer:
    """使用 PNG 框图：先画屏幕内容，再叠框图。"""

    def render(
        self,
        painter: QPainter,
        canvas_w: int,
        canvas_h: int,
        model_name: str,
        theme_name: str,
        scale: float,
        pos: tuple[float, float],
        content: Optional[QPixmap],
    ) -> None:
        p = _abs_path_for(model_name, theme_name)
        pm = _load_pixmap(p) if p and os.path.isfile(p) else None

        body, screen = layout(canvas_w, canvas_h, model_name, theme_name, scale, pos)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if pm is None or pm.isNull():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(40, 40, 45))
            painter.drawRoundedRect(body, body.width() * 0.08, body.width() * 0.08)
            painter.setPen(QColor(150, 150, 155))
            painter.drawText(
                body.toRect(),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                "未找到设备框 PNG\n请运行: python scripts/fetch_mockups.py\n"
                "（从 jamesjingyi/mockup-device-frames 下载 Exports/iOS）",
            )
            painter.restore()
            return

        # 屏幕圆角裁剪（与实物接近）
        rad = min(screen.width(), screen.height()) * 0.115
        path = QPainterPath()
        path.addRoundedRect(screen, rad, rad)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0))
        painter.drawPath(path)

        if content and not content.isNull():
            painter.save()
            painter.setClipPath(path)
            self._draw_content(painter, screen, content)
            painter.restore()

        # 框图压在最上层（透明区域露出已绘制内容）
        painter.drawPixmap(body, pm, QRectF(0, 0, pm.width(), pm.height()))

        painter.restore()

    @staticmethod
    def _draw_content(painter: QPainter, screen: QRectF, pix: QPixmap) -> None:
        pw, ph = pix.width(), pix.height()
        if pw == 0 or ph == 0:
            return
        sc = max(screen.width() / pw, screen.height() / ph)
        dw, dh = pw * sc, ph * sc
        dx = screen.x() + (screen.width() - dw) / 2
        dy = screen.y() + (screen.height() - dh) / 2
        painter.drawPixmap(QRectF(dx, dy, dw, dh), pix, QRectF(0, 0, pw, ph))


# 供 UI 使用（顺序与 manifest 一致）
MODELS = MODEL_ORDER

__all__ = [
    "IPhoneRenderer",
    "MODELS",
    "MODEL_ORDER",
    "DEVICE_PNG",
    "layout",
    "device_aspect_ratio",
    "default_theme_for_model",
]
