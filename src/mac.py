from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

from .device_content import draw_content_cover, load_pixmap, screen_norm_rect
from .mac_manifest import (
    DEVICE_PNG,
    MINIMAL_MODELS,
    MODEL_ORDER,
    default_theme_for_model,
    is_minimal_model,
    rel_path_for,
)

_ASSET_MAC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "mac", "third_party", "Exports", "MacBook")
)

# 简约窗口默认屏幕区（相对机身）
_MINIMAL_SCREEN_NORM = (0.012, 0.052, 0.976, 0.928)
# 实体 MacBook 检测失败时的回退
_HW_SCREEN_FALLBACK = (0.078, 0.062, 0.844, 0.838)

_TRAFFIC = (
    ("#FF5F57", "#E0443E"),
    ("#FEBC2E", "#D89E24"),
    ("#28C840", "#1AAB29"),
)

_MINIMAL_PALETTE = {
    "Window Dark": {
        "body": QColor(50, 50, 50),
        "title": QColor(43, 43, 43),
        "border": QColor(26, 26, 26),
        "shadow": QColor(0, 0, 0, 72),
    },
    "Window Light": {
        "body": QColor(245, 245, 245),
        "title": QColor(236, 236, 236),
        "border": QColor(208, 208, 208),
        "shadow": QColor(0, 0, 0, 48),
    },
}


def _abs_path_for(model: str, theme: str) -> str | None:
    rel = rel_path_for(model, theme)
    if not rel:
        rel = rel_path_for(model, default_theme_for_model(model))
    if not rel:
        return None
    return os.path.join(_ASSET_MAC, rel)


def device_aspect_ratio(model: str, theme: str) -> float:
    """机身宽 / 高。"""
    if is_minimal_model(model):
        return 1.6
    p = _abs_path_for(model, theme)
    if not p or not os.path.isfile(p):
        return 1.58
    pm = load_pixmap(p)
    if pm is None or pm.height() == 0:
        return 1.58
    return pm.width() / pm.height()


def layout(
    canvas_w: int,
    canvas_h: int,
    model_name: str,
    theme_name: str,
    scale: float,
    pos: tuple[float, float],
) -> tuple[QRectF, QRectF]:
    """返回画布坐标系下的 (机身矩形, 屏幕矩形)。"""
    if is_minimal_model(model_name):
        aspect = 1.6
        body_h = canvas_h * scale
        body_w = body_h * aspect
        cx = pos[0] * canvas_w
        cy = pos[1] * canvas_h
        body = QRectF(cx - body_w / 2, cy - body_h / 2, body_w, body_h)
        nx, ny, nw, nh = _MINIMAL_SCREEN_NORM
        scr = QRectF(
            body.x() + nx * body_w,
            body.y() + ny * body_h,
            nw * body_w,
            nh * body_h,
        )
        return body, scr

    p = _abs_path_for(model_name, theme_name)
    pm = load_pixmap(p) if p and os.path.isfile(p) else None
    if pm is None or pm.height() == 0:
        aspect = 1.58
        body_h = canvas_h * scale
        body_w = body_h * aspect
        cx = pos[0] * canvas_w
        cy = pos[1] * canvas_h
        body = QRectF(cx - body_w / 2, cy - body_h / 2, body_w, body_h)
        m = 0.06
        scr = QRectF(
            body.x() + body_w * m,
            body.y() + body_h * m,
            body_w * (1 - 2 * m),
            body_h * (1 - 2 * m),
        )
        return body, scr

    iw, ih = pm.width(), pm.height()
    body_h = canvas_h * scale
    body_w = body_h * (iw / ih)
    cx = pos[0] * canvas_w
    cy = pos[1] * canvas_h
    body = QRectF(cx - body_w / 2, cy - body_h / 2, body_w, body_h)

    nx, ny, nw, nh = screen_norm_rect(p, _HW_SCREEN_FALLBACK)
    scr = QRectF(
        body.x() + nx * body_w,
        body.y() + ny * body_h,
        nw * body_w,
        nh * body_h,
    )
    return body, scr


def _draw_traffic_lights(painter: QPainter, title_bar: QRectF) -> None:
    d = title_bar.height() * 0.38
    gap = d * 0.42
    x0 = title_bar.x() + title_bar.width() * 0.028
    cy = title_bar.center().y()
    for i, (fill, border) in enumerate(_TRAFFIC):
        cx = x0 + i * (d + gap) + d / 2
        painter.setPen(QPen(QColor(border), max(0.5, d * 0.06)))
        painter.setBrush(QBrush(QColor(fill)))
        painter.drawEllipse(QRectF(cx - d / 2, cy - d / 2, d, d))


def _render_minimal(
    painter: QPainter,
    body: QRectF,
    screen: QRectF,
    model_name: str,
    content: Optional[QPixmap],
) -> None:
    pal = _MINIMAL_PALETTE.get(model_name, _MINIMAL_PALETTE["Window Dark"])
    rad = min(body.width(), body.height()) * 0.018

    shadow = QRectF(body)
    shadow.translate(0, body.height() * 0.012)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(pal["shadow"])
    painter.drawRoundedRect(shadow, rad, rad)

    path = QPainterPath()
    path.addRoundedRect(body, rad, rad)

    grad = QLinearGradient(body.topLeft(), body.bottomLeft())
    grad.setColorAt(0, pal["title"])
    grad.setColorAt(min(0.12, 48 / max(body.height(), 1)), pal["title"])
    grad.setColorAt(0.13, pal["body"])
    grad.setColorAt(1, pal["body"])
    painter.setPen(QPen(pal["border"], max(1.0, body.width() * 0.0012)))
    painter.setBrush(QBrush(grad))
    painter.drawPath(path)

    title_h = screen.y() - body.y()
    title_bar = QRectF(body.x(), body.y(), body.width(), title_h)
    _draw_traffic_lights(painter, title_bar)

    scr_rad = rad * 0.55
    scr_path = QPainterPath()
    scr_path.addRoundedRect(screen, scr_rad, scr_rad)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0))
    painter.drawPath(scr_path)

    if content and not content.isNull():
        painter.save()
        painter.setClipPath(scr_path)
        draw_content_cover(painter, screen, content)
        painter.restore()


class MacRenderer:
    """电脑模式：简约窗口或实体 MacBook PNG 框。"""

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
        body, screen = layout(canvas_w, canvas_h, model_name, theme_name, scale, pos)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if is_minimal_model(model_name):
            _render_minimal(painter, body, screen, model_name, content)
            painter.restore()
            return

        p = _abs_path_for(model_name, theme_name)
        pm = load_pixmap(p) if p and os.path.isfile(p) else None

        if pm is None or pm.isNull():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(40, 40, 45))
            painter.drawRoundedRect(body, body.width() * 0.02, body.width() * 0.02)
            painter.setPen(QColor(150, 150, 155))
            painter.drawText(
                body.toRect(),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                "未找到 MacBook 框 PNG\n请运行: python scripts/fetch_mockups.py\n"
                "（从 jamesjingyi/mockup-device-frames 下载 Exports/MacBook）",
            )
            painter.restore()
            return

        rad = min(screen.width(), screen.height()) * 0.012
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

        painter.drawPixmap(body, pm, QRectF(0, 0, pm.width(), pm.height()))
        painter.restore()


MODELS = MODEL_ORDER

__all__ = [
    "MacRenderer",
    "MODELS",
    "MODEL_ORDER",
    "DEVICE_PNG",
    "MINIMAL_MODELS",
    "layout",
    "device_aspect_ratio",
    "default_theme_for_model",
    "is_minimal_model",
]
