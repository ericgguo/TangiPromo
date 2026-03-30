"""水印：用户自选 PNG 路径，着色后叠在画面最上层（仓库不捆绑任何品牌图）。"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap


def default_watermark_states() -> list["WatermarkState"]:
    return []


def make_watermark_from_path(image_path: str) -> "WatermarkState":
    """从用户选择的文件创建一条水印（绝对路径）。"""
    from .i18n import tr

    path = os.path.abspath(os.path.normpath(image_path))
    name = os.path.basename(path) or tr("wm.unnamed_file")
    return WatermarkState(
        id=uuid.uuid4().hex[:12],
        title=name,
        image_path=path,
        enabled=True,
    )


@dataclass
class WatermarkState:
    id: str
    title: str
    """界面分组标题，一般为文件名。"""
    image_path: str
    """本地 PNG 绝对路径。"""
    enabled: bool = False
    color: QColor = field(default_factory=lambda: QColor(255, 255, 255, 235))
    center_x_pct: float = 50.0
    center_y_pct: float = 50.0
    width_pct: float = 14.0


def tint_pixmap(src: QPixmap, color: QColor) -> QPixmap:
    """将非透明像素着色为 color（保留原 alpha 比例）。适用于黑/白图形 + 透明底。"""
    if src.isNull():
        return src
    out = QPixmap(src.size())
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.drawPixmap(0, 0, src)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(out.rect(), color)
    p.end()
    return out


def _tint_bgra_alpha_matte(path: str, color: QColor) -> QPixmap:
    """
    仅 Alpha 通道有信息、RGB 全 0 的 PNG（常见于导出的蒙版）。
    若用 SourceIn 在部分环境下整片同色，故用 Alpha 与目标色逐通道合成。
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        pm = QPixmap(path)
        return tint_pixmap(pm, color)

    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        return QPixmap()
    if im.ndim != 3 or im.shape[2] != 4:
        pm = QPixmap(path)
        return tint_pixmap(pm, color)

    b, g, r, a = cv2.split(im)
    if int(r.max()) > 0 or int(g.max()) > 0 or int(b.max()) > 0:
        pm = QPixmap(path)
        return tint_pixmap(pm, color)

    cr, cg, cb, ca = color.getRgb()
    nr = (np.float32(cr) * a / 255.0).astype(np.uint8)
    ng = (np.float32(cg) * a / 255.0).astype(np.uint8)
    nb = (np.float32(cb) * a / 255.0).astype(np.uint8)
    na = (np.float32(a) * (ca / 255.0)).astype(np.uint8)
    merged = cv2.merge([nb, ng, nr, na])
    rgba = cv2.cvtColor(merged, cv2.COLOR_BGRA2RGBA)
    h, w = rgba.shape[:2]
    qimg = QImage(
        rgba.data, w, h, w * 4, QImage.Format.Format_RGBA8888
    )
    return QPixmap.fromImage(qimg.copy())


def get_tinted_cached(
    path: str,
    color: QColor,
    cache: dict[tuple[str, int], QPixmap],
) -> QPixmap:
    key = (path, color.rgba())
    if key not in cache:
        if os.path.isfile(path):
            pm_try = _tint_bgra_alpha_matte(path, color)
            if not pm_try.isNull():
                cache[key] = pm_try
            else:
                pm = QPixmap(path)
                cache[key] = tint_pixmap(pm, color) if not pm.isNull() else QPixmap()
        else:
            cache[key] = QPixmap()
    return cache[key]


def compute_watermark_rect(
    st: WatermarkState,
    cw: int,
    ch: int,
    cache: dict[tuple[str, int], QPixmap],
) -> Optional[QRectF]:
    """画布坐标系下的水印外接矩形（用于点击检测）。"""
    if not st.enabled or cw <= 0 or ch <= 0:
        return None
    path = st.image_path
    if not os.path.isfile(path):
        return None
    pix = get_tinted_cached(path, st.color, cache)
    if pix.isNull():
        return None
    pw, ph = pix.width(), pix.height()
    if pw <= 0 or ph <= 0:
        return None
    draw_w = cw * (st.width_pct / 100.0)
    draw_h = ph * (draw_w / pw)
    cx = cw * (st.center_x_pct / 100.0)
    cy = ch * (st.center_y_pct / 100.0)
    x = cx - draw_w / 2.0
    y = cy - draw_h / 2.0
    return QRectF(x, y, draw_w, draw_h)


def render_watermarks(
    painter: QPainter,
    width: int,
    height: int,
    states: list[WatermarkState],
    cache: dict[tuple[str, int], QPixmap],
) -> None:
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    for st in states:
        if not st.enabled:
            continue
        path = st.image_path
        if not os.path.isfile(path):
            continue
        pix = get_tinted_cached(path, st.color, cache)
        if pix.isNull():
            continue
        pw, ph = pix.width(), pix.height()
        if pw <= 0 or ph <= 0:
            continue
        draw_w = width * (st.width_pct / 100.0)
        draw_h = ph * (draw_w / pw)
        cx = width * (st.center_x_pct / 100.0)
        cy = height * (st.center_y_pct / 100.0)
        x = cx - draw_w / 2.0
        y = cy - draw_h / 2.0
        painter.drawPixmap(
            QRectF(x, y, draw_w, draw_h),
            pix,
            QRectF(0, 0, pw, ph),
        )
