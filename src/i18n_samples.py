"""自定义背景默认示例代码（中英注释），供 i18n 引用。"""
from __future__ import annotations

# 共享画面逻辑：5 个柔和的流动色球 + 顶层微噪点网格，营造"现代简约"渐变流光感。
# 配色遵循现代 UI（indigo / violet / teal / amber），无高饱和纯色，
# 避免"花哨"但保留动感。

_SHARED_BODY = """\
# Soft orbs (fx, fy, phase_x, phase_y, R, G, B)
orbs = [
    (0.22, 0.28, 0.00, 0.00, 124, 108, 255),   # indigo
    (0.31, 0.19, 1.57, 2.09, 168, 132, 255),   # violet
    (0.17, 0.35, 3.14, 1.05,  90, 210, 220),   # teal
    (0.27, 0.24, 5.24, 3.67, 255, 176, 120),   # amber
    (0.20, 0.32, 2.62, 4.71, 255, 128, 168),   # rose
]

# Deep neutral base — avoid pure black for softer feel.
painter.fillRect(0, 0, width, height, QColor(11, 11, 16))

# Additive orbs create a calm, modern color wash.
painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
radius = max(width, height) * 0.78

for fx, fy, px, py, r, g, b in orbs:
    cx = (math.cos(t * fx + px) * 0.32 + 0.5) * width
    cy = (math.sin(t * fy + py) * 0.32 + 0.5) * height
    grad = QRadialGradient(QPointF(cx, cy), radius)
    grad.setColorAt(0.0, QColor(r, g, b, 150))
    grad.setColorAt(0.45, QColor(r // 2, g // 2, b // 2, 55))
    grad.setColorAt(1.0, QColor(r, g, b, 0))
    painter.fillRect(0, 0, width, height, grad)

painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

# Subtle top-down vignette to ground the composition.
vignette = QLinearGradient(0, 0, 0, height)
vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
vignette.setColorAt(1.0, QColor(0, 0, 0, 90))
painter.fillRect(0, 0, width, height, vignette)
"""

CODE_SAMPLE_ZH = """\
# 自定义背景示例 —— 现代柔和流光（Indigo · Violet · Teal · Amber · Rose）
#
# 可用变量：painter, width, height, t（秒）
# Qt 类：QColor, QRadialGradient, QLinearGradient, QPainterPath,
#        QPen, QBrush, QPointF, QRectF, Qt, QPainter, QFont
# 可选参数：Vortex_Strength, Color_Drift, Noise_Scale,
#           Aspect_Lock, Vignette_Weight 等（顶部直接赋值即可覆盖）
# 辅助函数：vortex_offset, fbm2, perlin2, hsv_drift …
# numpy：np（若已安装）
#
# 用法提示：
#   vx, vy = vortex_offset(px, py, cx, cy, Vortex_Strength, t)
#   grad = QRadialGradient(QPointF(px + vx, py + vy), radius)

""" + _SHARED_BODY

CODE_SAMPLE_EN = """\
# Custom background — modern soft flow (Indigo · Violet · Teal · Amber · Rose)
#
# Variables: painter, width, height, t (seconds)
# Qt: QColor, QRadialGradient, QLinearGradient, QPainterPath,
#     QPen, QBrush, QPointF, QRectF, Qt, QPainter, QFont
# Optional params: Vortex_Strength, Color_Drift, Noise_Scale,
#                  Aspect_Lock, Vignette_Weight, … (override at top of file)
# Helpers: vortex_offset, fbm2, perlin2, hsv_drift, …
# numpy: np when installed
#
# Usage:
#   vx, vy = vortex_offset(px, py, cx, cy, Vortex_Strength, t)
#   grad = QRadialGradient(QPointF(px + vx, py + vy), radius)

""" + _SHARED_BODY
