"""Aurora flow — NumPy-driven aurora background.

Two elegant palettes (deep emerald ↔ ethereal purple/cyan) crossfade over a
6-second period; fluid wave mask adds organic motion, with a subtle glimmer
boost at the crossfade peak.
"""
from __future__ import annotations

import math
from PySide6.QtGui import QPainter, QColor, QImage

from .base import Background

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


class AuroraFlowBackground(Background):
    """Aurora — emerald/violet dual-palette flow (numpy accelerated)."""

    name = "极光"

    PERIOD = 6.0
    TIME_FACTOR = 1.5

    def __init__(self) -> None:
        self.speed: float = 1.0

    def render(self, painter: QPainter, width: int, height: int, t: float) -> None:
        if not _HAS_NUMPY:
            self._render_fallback(painter, width, height)
            return

        tt = t * self.speed
        alpha = 0.5 * (1 + np.cos(2 * np.pi * tt / self.PERIOD + np.pi))
        active_t = tt * self.TIME_FACTOR

        x = np.linspace(0.0, 1.0, width, dtype=np.float32)
        y = np.linspace(0.0, 1.0, height, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)

        wave_base = np.sin(xx * 2.0 + active_t) * 0.5 + np.cos(yy * 2.5 - active_t * 0.7)
        wave_diag = np.sin((xx + yy) * 3.5 + active_t * 1.2)
        wave_detail = np.sin(xx * 15.0 - yy * 12.0 + active_t * 2.0) * 0.2
        combined = wave_base + wave_diag + wave_detail

        mask = np.clip((combined + 3.0) / 6.0, 0.0, 1.0)
        inv = 1.0 - mask

        # Deep emerald palette
        r_a = 5.0 * inv + 40.0 * mask
        g_a = 15.0 * inv + 200.0 * mask
        b_a = 25.0 * inv + 150.0 * mask

        # Ethereal purple / cyan palette
        r_b = 10.0 * inv + 130.0 * mask
        g_b = 10.0 * inv + 100.0 * mask
        b_b = 40.0 * inv + 255.0 * mask

        inv_a = 1.0 - alpha
        r = r_a * inv_a + r_b * alpha
        g = g_a * inv_a + g_b * alpha
        b = b_a * inv_a + b_b * alpha

        # Glimmer accent near crossfade midpoint
        glimmer = np.sin(math.pi * alpha) * (mask ** 4) * 50.0
        r = np.clip(r + glimmer, 0, 255)
        g = np.clip(g + glimmer * 1.2, 0, 255)
        b = np.clip(b + glimmer * 1.1, 0, 255)

        rgb = np.dstack((r, g, b)).astype(np.uint8)
        rgb = np.ascontiguousarray(rgb)

        h, w, _ = rgb.shape
        qimg = QImage(
            rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888
        ).copy()
        painter.drawImage(0, 0, qimg)

    @staticmethod
    def _render_fallback(painter: QPainter, width: int, height: int) -> None:
        painter.fillRect(0, 0, width, height, QColor(10, 18, 34))


__all__ = ["AuroraFlowBackground"]
