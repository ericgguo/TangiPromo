import math
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen, QPainterPath
from PySide6.QtCore import QPointF, Qt
from .base import Background


class NeonGlowBackground(Background):
    """Dark background with animated neon light blobs and grid lines."""

    name = "霓虹光效"

    GLOWS = [
        (0.28, 0.35, 0.22, 0.18, (255,  60, 120)),
        (0.72, 0.65, 0.18, 0.22, ( 60, 180, 255)),
        (0.50, 0.50, 0.20, 0.20, (180,  60, 255)),
        (0.20, 0.70, 0.15, 0.25, (255, 200,  40)),
        (0.80, 0.30, 0.25, 0.15, ( 40, 255, 180)),
    ]

    def __init__(self):
        self.speed = 1.0
        self.bg_color = QColor(4, 4, 12)
        self.show_grid = True

    def render(self, painter: QPainter, width: int, height: int, t: float):
        painter.fillRect(0, 0, width, height, self.bg_color)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tt = t * self.speed

        # Perspective grid
        if self.show_grid:
            self._draw_grid(painter, width, height, tt)

        # Glowing blobs
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Plus
        )
        for i, (bx, by, rx, ry, color) in enumerate(self.GLOWS):
            cx = (bx + rx * math.cos(tt * 0.37 + i * 1.3)) * width
            cy = (by + ry * math.sin(tt * 0.29 + i * 2.1)) * height
            radius = max(width, height) * 0.45

            grad = QRadialGradient(QPointF(cx, cy), radius)
            r, g, b = color
            grad.setColorAt(0.0, QColor(r, g, b, 180))
            grad.setColorAt(0.3, QColor(r // 2, g // 2, b // 2, 80))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(0, 0, width, height, grad)

        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )

        # Neon scan line
        scan_y = int((math.sin(tt * 0.7) * 0.4 + 0.5) * height)
        scan_grad = QRadialGradient(QPointF(width / 2, scan_y), width * 0.6)
        scan_grad.setColorAt(0.0, QColor(140, 220, 255, 60))
        scan_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(0, scan_y - 2, width, 4, scan_grad)

    def _draw_grid(self, painter, width, height, t):
        vp_x = width / 2
        vp_y = height * 0.62
        alpha_base = 35
        pen = QPen(QColor(60, 120, 180, alpha_base))
        pen.setWidthF(0.7)
        painter.setPen(pen)

        cols = 16
        for i in range(cols + 1):
            fx = i / cols
            bx = fx * width
            path = QPainterPath()
            path.moveTo(bx, height)
            path.lineTo(vp_x, vp_y)
            painter.drawPath(path)

        rows = 10
        for j in range(rows + 1):
            fy = j / rows
            py = vp_y + (height - vp_y) * fy
            t_factor = fy
            lx = vp_x * (1 - t_factor)
            rx = vp_x + (width - vp_x) * t_factor
            a = int(alpha_base * fy * 1.5)
            pen2 = QPen(QColor(60, 120, 180, min(a, 80)))
            pen2.setWidthF(0.5)
            painter.setPen(pen2)
            painter.drawLine(QPointF(lx, py), QPointF(rx, py))
