import math
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QLinearGradient
from PySide6.QtCore import QPointF, QRectF, Qt
from .base import Background


class GeometricBackground(Background):
    """Animated geometric pattern: hexagonal grid with glowing pulses."""

    name = "几何脉冲"

    def __init__(self):
        self.speed = 1.0
        self.bg_color = QColor(8, 10, 20)
        self.line_color = (40, 80, 160)
        self.pulse_color = (100, 180, 255)
        self.cell_size = 60

    def render(self, painter: QPainter, width: int, height: int, t: float):
        painter.fillRect(0, 0, width, height, self.bg_color)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        tt = t * self.speed
        cell = self.cell_size
        h_cell = cell * math.sqrt(3) / 2

        cols = int(width / cell) + 3
        rows = int(height / h_cell) + 3

        lc = self.line_color
        pc = self.pulse_color

        for row in range(-1, rows):
            for col in range(-1, cols):
                cx = col * cell * 1.5 + (cell * 0.75 if row % 2 else 0)
                cy = row * h_cell
                dist_from_center = math.sqrt(
                    ((cx - width / 2) / width) ** 2 +
                    ((cy - height / 2) / height) ** 2
                )
                pulse = math.sin(tt * 1.5 - dist_from_center * 8.0) * 0.5 + 0.5
                fade = max(0, 1.0 - dist_from_center * 1.8)

                alpha_line = int(20 * fade + 40 * fade * pulse)
                alpha_node = int(60 * fade * pulse)

                # Hexagon outline
                path = self._hex_path(cx, cy, cell * 0.48)
                pen = QPen(QColor(lc[0], lc[1], lc[2], alpha_line))
                pen.setWidthF(0.8)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)

                # Center node glow
                if alpha_node > 8:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(pc[0], pc[1], pc[2], alpha_node))
                    r = 2 + 3 * pulse * fade
                    painter.drawEllipse(QPointF(cx, cy), r, r)

        # Bright scanning wave overlay
        wave_x = (math.sin(tt * 0.4) * 0.4 + 0.5) * width
        scan = QLinearGradient(wave_x - 60, 0, wave_x + 60, 0)
        scan.setColorAt(0, QColor(100, 180, 255, 0))
        scan.setColorAt(0.5, QColor(100, 180, 255, 18))
        scan.setColorAt(1, QColor(100, 180, 255, 0))
        painter.fillRect(0, 0, width, height, scan)

    @staticmethod
    def _hex_path(cx, cy, r):
        path = QPainterPath()
        for i in range(6):
            angle = math.pi / 3 * i + math.pi / 6
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        return path
