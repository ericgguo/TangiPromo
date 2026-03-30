import math
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath
from PySide6.QtCore import Qt, QPointF
from .base import Background


class AbstractWavesBackground(Background):
    """Layered flowing wave bands — abstract liquid feel."""

    name = "流体波浪"

    LAYERS = [
        # (y_base, amplitude, freq, phase, speed_mult, r, g, b, alpha)
        (0.55, 0.10, 2.0, 0.00, 0.8, 102, 126, 234, 180),
        (0.60, 0.09, 2.5, 1.05, 1.0,  80, 200, 200, 150),
        (0.65, 0.08, 1.8, 2.10, 0.7, 200,  80, 200, 130),
        (0.70, 0.11, 3.0, 3.14, 1.2, 240, 147, 100, 120),
        (0.75, 0.07, 2.2, 4.20, 0.9, 100, 200, 100, 110),
        (0.80, 0.06, 1.5, 5.25, 0.6, 150, 100, 250, 100),
    ]

    def __init__(self):
        self.speed = 1.0
        self.bg_top = QColor(10, 12, 35)
        self.bg_bottom = QColor(20, 10, 40)

    def render(self, painter: QPainter, width: int, height: int, t: float):
        # Background gradient
        bg = QLinearGradient(0, 0, 0, height)
        bg.setColorAt(0, self.bg_top)
        bg.setColorAt(1, self.bg_bottom)
        painter.fillRect(0, 0, width, height, bg)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tt = t * self.speed
        steps = max(width // 3, 120)

        for y_base, amp, freq, phase, sm, r, g, b, a in self.LAYERS:
            path = QPainterPath()
            path.moveTo(-2, height + 2)

            xs = [i * width / steps for i in range(steps + 1)]
            ys = []
            for x in xs:
                w1 = math.sin(x / width * freq * math.pi * 2 + tt * sm + phase)
                w2 = math.sin(x / width * freq * 1.4 * math.pi * 2 - tt * sm * 0.7 + phase * 1.3)
                w3 = math.sin(x / width * freq * 0.6 * math.pi * 2 + tt * sm * 0.4 + phase * 0.5)
                y = (y_base + amp * (w1 * 0.5 + w2 * 0.3 + w3 * 0.2)) * height
                ys.append(y)

            path.lineTo(xs[0], ys[0])
            for i in range(1, len(xs)):
                path.lineTo(xs[i], ys[i])

            path.lineTo(width + 2, height + 2)
            path.closeSubpath()

            # Fill from wave top to bottom with gradient
            min_y = min(ys)
            wave_grad = QLinearGradient(0, min_y, 0, height)
            wave_grad.setColorAt(0.0, QColor(r, g, b, a))
            wave_grad.setColorAt(0.4, QColor(r // 2, g // 2, b // 2, a // 2))
            wave_grad.setColorAt(1.0, QColor(r // 4, g // 4, b // 4, a // 4))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(wave_grad)
            painter.drawPath(path)
