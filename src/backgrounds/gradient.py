import math
from PySide6.QtGui import QPainter, QColor, QRadialGradient
from PySide6.QtCore import QPointF, Qt
from .base import Background


class MeshGradientBackground(Background):
    """Apple-style flowing mesh gradient with additive color blobs."""

    name = "网格渐变流动"

    # Each orb: (freq_x, freq_y, phase_x, phase_y, r, g, b)
    DEFAULT_ORBS = [
        (0.31, 0.37, 0.00, 0.00, 120,  80, 220),
        (0.47, 0.29, 1.57, 2.09, 220,  60, 180),
        (0.38, 0.53, 3.14, 1.05,  60, 200, 220),
        (0.23, 0.41, 5.24, 3.67, 220, 160,  60),
        (0.55, 0.19, 2.62, 4.71,  60, 220, 120),
    ]

    def __init__(self):
        self.orbs = list(self.DEFAULT_ORBS)
        self.speed = 1.0
        self.bg_color = QColor(10, 8, 30)
        self.radius_factor = 0.85

    def render(self, painter: QPainter, width: int, height: int, t: float):
        painter.fillRect(0, 0, width, height, self.bg_color)

        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Plus
        )
        radius = max(width, height) * self.radius_factor
        tt = t * self.speed

        for fx, fy, px, py, r, g, b in self.orbs:
            cx = (math.cos(tt * fx + px) * 0.38 + 0.5) * width
            cy = (math.sin(tt * fy + py) * 0.38 + 0.5) * height

            grad = QRadialGradient(QPointF(cx, cy), radius)
            center_color = QColor(r, g, b, 200)
            edge_color = QColor(r, g, b, 0)
            grad.setColorAt(0.0, center_color)
            grad.setColorAt(0.5, QColor(r // 2, g // 2, b // 2, 80))
            grad.setColorAt(1.0, edge_color)
            painter.fillRect(0, 0, width, height, grad)

        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )
