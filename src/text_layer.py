"""Text overlay layers that can be positioned anywhere on the canvas."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen,
)


@dataclass
class TextLayer:
    text: str = ""
    x: float = 0.5          # normalised 0-1
    y: float = 0.85         # normalised 0-1
    font_family: str = "Helvetica Neue"
    font_size_pt: int = 36  # at 1080px canvas height
    bold: bool = False
    italic: bool = False
    color: QColor = field(default_factory=lambda: QColor(255, 255, 255, 255))
    align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignHCenter
    shadow: bool = True
    shadow_color: QColor = field(default_factory=lambda: QColor(0, 0, 0, 160))
    shadow_offset: tuple[float, float] = (2.0, 3.0)
    outline: bool = False
    outline_color: QColor = field(default_factory=lambda: QColor(0, 0, 0, 200))
    outline_width: float = 2.0
    visible: bool = True
    name: str = ""

    # Runtime state (not serialised)
    _hit_rect: QRectF = field(default_factory=QRectF, repr=False, compare=False)

    def _make_font(self, canvas_h: int) -> QFont:
        scale = canvas_h / 1080.0
        pt = max(6, int(self.font_size_pt * scale))
        f = QFont(self.font_family, pt)
        f.setBold(self.bold)
        f.setItalic(self.italic)
        return f

    def render(self, painter: QPainter, canvas_w: int, canvas_h: int) -> None:
        if not self.visible or not self.text:
            return

        font = self._make_font(canvas_h)
        painter.setFont(font)
        fm = QFontMetricsF(font)

        lines = self.text.split("\n")
        line_h = fm.height()
        max_w = max(fm.horizontalAdvance(l) for l in lines)
        total_h = line_h * len(lines)

        cx = self.x * canvas_w
        cy = self.y * canvas_h

        bx = cx - max_w / 2
        by = cy - total_h / 2

        # Store hit rect for mouse picking
        self._hit_rect = QRectF(bx - 8, by - 4, max_w + 16, total_h + 8)

        for i, line in enumerate(lines):
            lw = fm.horizontalAdvance(line)
            if self.align == Qt.AlignmentFlag.AlignHCenter:
                lx = cx - lw / 2
            elif self.align == Qt.AlignmentFlag.AlignRight:
                lx = cx - lw
            else:
                lx = cx
            ly = by + i * line_h + fm.ascent()

            if self.outline:
                path = QPainterPath()
                path.addText(QPointF(lx, ly), font, line)
                scale = canvas_h / 1080.0
                pen = QPen(self.outline_color, self.outline_width * scale * 2)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.strokePath(path, pen)

            if self.shadow:
                sx = lx + self.shadow_offset[0]
                sy = ly + self.shadow_offset[1]
                painter.setPen(self.shadow_color)
                painter.drawText(QPointF(sx, sy), line)

            painter.setPen(self.color)
            painter.drawText(QPointF(lx, ly), line)

    def hit_test(self, nx: float, ny: float, canvas_w: int, canvas_h: int) -> bool:
        px = nx * canvas_w
        py = ny * canvas_h
        return self._hit_rect.contains(px, py)
