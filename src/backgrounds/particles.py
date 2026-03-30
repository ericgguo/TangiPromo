import math
import random
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen
from PySide6.QtCore import QPointF, Qt
from .base import Background


class Particle:
    def __init__(self, w, h):
        self.reset(w, h, initial=True)

    def reset(self, w, h, initial=False):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h) if initial else h + 10
        speed = random.uniform(15, 60)
        angle = random.uniform(-math.pi / 8, math.pi / 8) - math.pi / 2
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.size = random.uniform(1.5, 5.0)
        self.alpha = random.uniform(100, 220)
        self.color = random.choice([
            (100, 180, 255),
            (180, 100, 255),
            (255, 150, 100),
            (100, 255, 180),
            (255, 220, 100),
        ])
        self.life = random.uniform(0.5, 1.0)
        self.age = 0.0 if not initial else random.uniform(0, self.life)


class ParticleConstellationBackground(Background):
    """Floating glowing particles with connecting lines."""

    name = "星空粒子"

    def __init__(self):
        self.particles: list[Particle] = []
        self.count = 80
        self.speed = 1.0
        self.connect_dist = 120
        self.bg_color = QColor(5, 8, 20)
        self._last_size = (0, 0)

    def _init_particles(self, w, h):
        self.particles = [Particle(w, h) for _ in range(self.count)]
        self._last_size = (w, h)

    def render(self, painter: QPainter, width: int, height: int, t: float):
        painter.fillRect(0, 0, width, height, self.bg_color)

        if (width, height) != self._last_size or not self.particles:
            self._init_particles(width, height)

        dt = 1.0 / 60.0 * self.speed

        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.age += dt
            if p.y < -20 or p.x < -20 or p.x > width + 20:
                p.reset(width, height)

        # Draw connecting lines
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, a in enumerate(self.particles):
            for b in self.particles[i + 1:]:
                dx = a.x - b.x
                dy = a.y - b.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < self.connect_dist:
                    alpha = int(120 * (1 - dist / self.connect_dist))
                    r = (a.color[0] + b.color[0]) // 2
                    g = (a.color[1] + b.color[1]) // 2
                    bl = (a.color[2] + b.color[2]) // 2
                    pen = QPen(QColor(r, g, bl, alpha))
                    pen.setWidthF(0.6)
                    painter.setPen(pen)
                    painter.drawLine(QPointF(a.x, a.y), QPointF(b.x, b.y))

        # Draw glowing particles
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            life_frac = min(p.age / p.life, 1.0) if p.life > 0 else 1.0
            fade = math.sin(life_frac * math.pi)
            r, g, b = p.color
            alpha = int(p.alpha * fade)
            if alpha < 5:
                continue
            size = p.size * (0.5 + 0.5 * fade)

            # Glow
            grad = QRadialGradient(QPointF(p.x, p.y), size * 4)
            grad.setColorAt(0.0, QColor(r, g, b, alpha))
            grad.setColorAt(0.4, QColor(r, g, b, alpha // 3))
            grad.setColorAt(1.0, QColor(r, g, b, 0))
            painter.setBrush(grad)
            painter.drawEllipse(QPointF(p.x, p.y), size * 4, size * 4)

            # Core
            painter.setBrush(QColor(min(r + 60, 255), min(g + 60, 255), min(b + 60, 255), alpha))
            painter.drawEllipse(QPointF(p.x, p.y), size, size)
