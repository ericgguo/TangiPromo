import math
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath
from PySide6.QtCore import QPointF, Qt
from .base import Background


class AuroraBackground(Background):
    """Aurora borealis — layered sine wave bands with gradient fills."""

    name = "极光波浪"

    BANDS = [
        # (base_y_frac, amplitude, freq, phase_offset, color1, color2, alpha)
        (0.35, 0.12, 1.8, 0.00, (30, 200, 180),  (60, 100, 220),  90),
        (0.45, 0.10, 2.3, 1.20, (80, 220, 120),  (40, 180, 255),  70),
        (0.55, 0.08, 1.5, 2.40, (160, 80, 255),  (60, 220, 200),  60),
        (0.65, 0.09, 2.8, 0.80, (40, 200, 255),  (120, 60, 220),  50),
        (0.30, 0.06, 3.2, 3.60, (100, 255, 150), (50, 150, 255),  40),
    ]

    def __init__(self):
        self.speed = 1.0
        self.bg_top = QColor(2, 4, 18)
        self.bg_bottom = QColor(5, 15, 40)

    def render(self, painter: QPainter, width: int, height: int, t: float):
        # Sky gradient background
        sky = QLinearGradient(0, 0, 0, height)
        sky.setColorAt(0, self.bg_top)
        sky.setColorAt(1, self.bg_bottom)
        painter.fillRect(0, 0, width, height, sky)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tt = t * self.speed
        steps = max(width // 4, 80)

        for base_y, amp, freq, phase, c1, c2, alpha in self.BANDS:
            # Build the wave path
            path = QPainterPath()
            path.moveTo(0, height + 10)

            xs = [i * width / steps for i in range(steps + 1)]
            ys = []
            for x in xs:
                wave = math.sin(x / width * freq * math.pi * 2 + tt * 0.8 + phase)
                wave2 = math.sin(x / width * freq * 1.6 * math.pi * 2 - tt * 0.5 + phase)
                y = (base_y + amp * (wave * 0.6 + wave2 * 0.4)) * height
                ys.append(y)

            path.lineTo(xs[0], ys[0])
            for i in range(1, len(xs)):
                path.lineTo(xs[i], ys[i])

            # Band thickness varies with sine
            band_h = height * (amp * 1.8)
            for i in range(len(xs) - 1, -1, -1):
                x = xs[i]
                y = ys[i] + band_h * (0.7 + 0.3 * math.sin(xs[i] / width * math.pi + tt * 0.3))
                path.lineTo(x, y)

            path.closeSubpath()

            # Gradient fill along Y
            top_y = min(ys)
            bot_y = max(ys) + band_h
            grad = QLinearGradient(QPointF(0, top_y), QPointF(0, bot_y))
            grad.setColorAt(0.0, QColor(c1[0], c1[1], c1[2], alpha))
            grad.setColorAt(0.4, QColor(c2[0], c2[1], c2[2], alpha // 2))
            grad.setColorAt(1.0, QColor(c2[0], c2[1], c2[2], 0))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawPath(path)

        # Stars
        painter.setPen(Qt.PenStyle.NoPen)
        import random
        rng = random.Random(42)
        for _ in range(120):
            sx = rng.uniform(0, width)
            sy = rng.uniform(0, height * 0.55)
            twinkle = 0.4 + 0.6 * abs(math.sin(t * rng.uniform(0.5, 2.0) + rng.uniform(0, 6)))
            a = int(180 * twinkle)
            painter.setBrush(QColor(220, 230, 255, a))
            r = rng.uniform(0.5, 1.5)
            from PySide6.QtCore import QRectF
            painter.drawEllipse(QPointF(sx, sy), r, r)
