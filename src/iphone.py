
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap

from .device_content import draw_content_cover, load_pixmap, screen_norm_rect
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

_IPHONE_SCREEN_FALLBACK = (0.065, 0.033, 0.868, 0.935)


def _abs_path_for(model: str, theme: str) -> str | None:
    rel = rel_path_for(model, theme)
    if not rel:
        # 主题不匹配时尝试默认色
        rel = rel_path_for(model, default_theme_for_model(model))
    if not rel:
        return None
    return os.path.join(_ASSET_IOS, rel)


def device_aspect_ratio(model: str, theme: str) -> float:
    """机身宽 / 高（用于点击检测等）。"""
    p = _abs_path_for(model, theme)
    if not p or not os.path.isfile(p):
        return 0.48
    pm = load_pixmap(p)
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
    pm = load_pixmap(p) if p and os.path.isfile(p) else None
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

    nx, ny, nw, nh = screen_norm_rect(p, _IPHONE_SCREEN_FALLBACK)
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
        pm = load_pixmap(p) if p and os.path.isfile(p) else None

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
            draw_content_cover(painter, screen, content)
            painter.restore()

        # 框图压在最上层（透明区域露出已绘制内容）
        painter.drawPixmap(body, pm, QRectF(0, 0, pm.width(), pm.height()))

        painter.restore()

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
