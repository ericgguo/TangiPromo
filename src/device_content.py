"""设备框内屏幕内容绘制与 PNG 透明区域检测（iPhone / Mac 共用）。"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QPixmap

_screen_norm_cache: dict[str, tuple[float, float, float, float]] = {}


@lru_cache(maxsize=64)
def load_pixmap(abs_path: str) -> Optional[QPixmap]:
    p = QPixmap(abs_path)
    return p if not p.isNull() else None


def screen_norm_rect(abs_path: str, fallback: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """透明屏幕区域相对整图的归一化矩形 (x,y,w,h)，与中心连通域。"""
    if abs_path in _screen_norm_cache:
        return _screen_norm_cache[abs_path]
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


def draw_content_cover(painter: QPainter, screen: QRectF, pix: QPixmap) -> None:
    """等比放大铺满屏幕区域（cover）。"""
    pw, ph = pix.width(), pix.height()
    if pw == 0 or ph == 0:
        return
    sc = max(screen.width() / pw, screen.height() / ph)
    dw, dh = pw * sc, ph * sc
    dx = screen.x() + (screen.width() - dw) / 2
    dy = screen.y() + (screen.height() - dh) / 2
    painter.drawPixmap(QRectF(dx, dy, dw, dh), pix, QRectF(0, 0, pw, ph))
