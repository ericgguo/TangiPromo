"""自定义背景默认示例代码（中英注释），供 i18n 引用。"""
from __future__ import annotations

CODE_SAMPLE_ZH = """\
# 自定义背景代码示例 —— 网格渐变风格（与「网格渐变流动」预设逻辑相同）
#
# 【可用变量】painter, width, height, t（秒）
# 【Qt 类】QColor, QRadialGradient, QLinearGradient, QPainterPath,
#          QPen, QBrush, QPointF, QRectF, Qt, QPainter, QFont
# 【可选默认参数】Vortex_Strength=0, Color_Drift=0.05, Noise_Scale=1,
#               Aspect_Lock=True, Vignette_Weight=0 等
#               → 在代码顶部直接赋值即可覆盖，例如：Vortex_Strength = 0.5
# 【辅助函数】vortex_offset(px,py,cx,cy,strength,t) → (dx,dy) 偏移量
#            fbm2(x,y), perlin2(x,y), hsv_drift(color,t,drift) 等
# 【numpy】np（已安装时可用）
#
# 注意：vortex_offset 返回的是「偏移量」(dx,dy)，用法：
#   vx, vy = vortex_offset(pos_x, pos_y, cx, cy, Vortex_Strength, t)
#   grad = QRadialGradient(QPointF(pos_x + vx, pos_y + vy), radius)

orbs = [
    (0.31, 0.37, 0.00, 0.00, 120,  80, 220),
    (0.47, 0.29, 1.57, 2.09, 220,  60, 180),
    (0.38, 0.53, 3.14, 1.05,  60, 200, 220),
    (0.23, 0.41, 5.24, 3.67, 220, 160,  60),
    (0.55, 0.19, 2.62, 4.71,  60, 220, 120),
]

painter.fillRect(0, 0, width, height, QColor(10, 8, 30))
painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
radius = max(width, height) * 0.85

for fx, fy, px, py, r, g, b in orbs:
    cx = (math.cos(t * fx + px) * 0.38 + 0.5) * width
    cy = (math.sin(t * fy + py) * 0.38 + 0.5) * height
    grad = QRadialGradient(QPointF(cx, cy), radius)
    grad.setColorAt(0.0, QColor(r, g, b, 200))
    grad.setColorAt(0.5, QColor(r // 2, g // 2, b // 2, 80))
    grad.setColorAt(1.0, QColor(r, g, b, 0))
    painter.fillRect(0, 0, width, height, grad)

painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
"""

CODE_SAMPLE_EN = """\
# Custom background sample — mesh gradient (same idea as the "Mesh gradient" preset)
#
# Variables: painter, width, height, t (seconds)
# Qt: QColor, QRadialGradient, QLinearGradient, QPainterPath,
#     QPen, QBrush, QPointF, QRectF, Qt, QPainter, QFont
# Optional params: Vortex_Strength, Color_Drift, Noise_Scale,
#                  Aspect_Lock, Vignette_Weight, … (override at top of script)
# Helpers: vortex_offset(px,py,cx,cy,strength,t) -> (dx,dy);
#          fbm2, perlin2, hsv_drift, …
# numpy: np when installed
#
# vortex_offset returns offsets (dx, dy), e.g.:
#   vx, vy = vortex_offset(pos_x, pos_y, cx, cy, Vortex_Strength, t)
#   grad = QRadialGradient(QPointF(pos_x + vx, pos_y + vy), radius)

orbs = [
    (0.31, 0.37, 0.00, 0.00, 120,  80, 220),
    (0.47, 0.29, 1.57, 2.09, 220,  60, 180),
    (0.38, 0.53, 3.14, 1.05,  60, 200, 220),
    (0.23, 0.41, 5.24, 3.67, 220, 160,  60),
    (0.55, 0.19, 2.62, 4.71,  60, 220, 120),
]

painter.fillRect(0, 0, width, height, QColor(10, 8, 30))
painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
radius = max(width, height) * 0.85

for fx, fy, px, py, r, g, b in orbs:
    cx = (math.cos(t * fx + px) * 0.38 + 0.5) * width
    cy = (math.sin(t * fy + py) * 0.38 + 0.5) * height
    grad = QRadialGradient(QPointF(cx, cy), radius)
    grad.setColorAt(0.0, QColor(r, g, b, 200))
    grad.setColorAt(0.5, QColor(r // 2, g // 2, b // 2, 80))
    grad.setColorAt(1.0, QColor(r, g, b, 0))
    painter.fillRect(0, 0, width, height, grad)

painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
"""
