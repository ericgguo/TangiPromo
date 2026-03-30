"""
自定义背景用的辅助函数（不依赖 UI）。

可在自定义代码中直接调用；与 custom_params 中的变量配合使用。
"""
from __future__ import annotations

import math
import random
from typing import Tuple

from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtCore import QPointF, QRectF, Qt


# --- 平滑值噪声（类 Perlin 的平滑场，便于与 Noise_Scale 联用） ---
def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _hash21(ix: int, iy: int) -> float:
    n = math.sin(ix * 127.1 + iy * 311.7) * 43758.5453123
    return n - math.floor(n)


def perlin2(x: float, y: float) -> float:
    """
    双线性平滑值噪声，返回约 [0,1]，中心约 0.5。
    与 Noise_Scale 配合：对坐标使用 (x/Noise_Scale, y/Noise_Scale)。
    """
    x0 = math.floor(x)
    y0 = math.floor(y)
    xf = x - x0
    yf = y - y0
    u = _fade(xf)
    v = _fade(yf)
    n00 = _hash21(int(x0), int(y0))
    n10 = _hash21(int(x0 + 1), int(y0))
    n01 = _hash21(int(x0), int(y0 + 1))
    n11 = _hash21(int(x0 + 1), int(y0 + 1))
    nx0 = _lerp(n00, n10, u)
    nx1 = _lerp(n01, n11, u)
    return _lerp(nx0, nx1, v)


def fbm2(x: float, y: float, octaves: int = 4, persistence: float = 0.5) -> float:
    """分形布朗运动：多层 perlin2 叠加，返回约 [0,1]。"""
    s = 0.0
    a = 1.0
    f = 1.0
    norm = 0.0
    for _ in range(octaves):
        s += a * perlin2(x * f, y * f)
        norm += a
        a *= persistence
        f *= 2.0
    return s / max(norm, 1e-6)


def vortex_offset(
    x: float,
    y: float,
    cx: float,
    cy: float,
    strength: float,
    t: float,
) -> Tuple[float, float]:
    """
    涡流：对坐标施加角向偏移。strength 对应 Vortex_Strength。
    返回 (dx, dy) 加到原始 x,y 上。
    """
    if strength == 0.0:
        return 0.0, 0.0
    dx = x - cx
    dy = y - cy
    r2 = dx * dx + dy * dy + 1e-6
    r = math.sqrt(r2)
    # 垂直于径向的方向
    tx = -dy / r
    ty = dx / r
    mag = strength * (1.0 - math.exp(-r / (max(cx, cy) * 0.5 + 1))) * t * 0.1
    return tx * mag * 10.0, ty * mag * 10.0


def jitter_xy(x: float, y: float, t: float, amount: float, seed: int = 0) -> Tuple[float, float]:
    """确定性震颤（与 Jitter 参数配合）。"""
    if amount <= 0:
        return x, y
    rng = random.Random((seed, int(x * 1000), int(y * 1000), int(t * 60)))
    jx = (rng.random() - 0.5) * 2 * amount * max(x, y, 1)
    jy = (rng.random() - 0.5) * 2 * amount * max(x, y, 1)
    return x + jx, y + jy


def viscosity_damp(velocity: float, viscosity: float) -> float:
    """一维速度衰减，0<viscosity<=1 越高越黏。"""
    return velocity * (1.0 - min(1.0, max(0.0, viscosity)) * 0.1)


def hsv_drift(base: QColor, t: float, drift: float) -> QColor:
    """Color_Drift：在 HSV 空间微扰。"""
    h, s, v, a = base.getHsvF()
    h = (h + drift * math.sin(t * 0.7) * 0.02) % 1.0
    s = max(0.0, min(1.0, s + drift * math.cos(t * 0.5) * 0.05))
    c = QColor.fromHsvF(h, s, v, a)
    return c


def refract_uv(u: float, v: float, n: float) -> Tuple[float, float]:
    """
    Refraction_Index：简单 UV 折射偏移（模拟厚玻璃）。
    n 越大偏移越明显。
    """
    k = (n - 1.0) * 0.02
    return u + k * math.sin(v * 6.28), v + k * math.cos(u * 6.28)


def safe_zone_factor(px: float, py: float, w: float, h: float, offset: float) -> float:
    """
    Safe_Zone_Offset：距边缘越近因子越小（0~1），用于减弱背景剧烈变化。
    offset 为归一化边距比例。
    """
    if offset <= 0:
        return 1.0
    nx = px / w
    ny = py / h
    d = min(nx, ny, 1.0 - nx, 1.0 - ny)
    m = offset
    if d >= m:
        return 1.0
    return max(0.0, d / m)


def luminance_of(c: QColor) -> float:
    """相对亮度 0~1。"""
    return 0.299 * c.redF() + 0.587 * c.greenF() + 0.114 * c.blueF()


def apply_vignette_to_painter(
    painter: QPainter,
    width: int,
    height: int,
    weight: float,
) -> None:
    """Vignette_Weight：在已有内容上叠径向暗角。"""
    if weight <= 0:
        return
    cx, cy = width / 2, height / 2
    r = max(width, height) * 0.75
    g = QRadialGradient(QPointF(cx, cy), r)
    g.setColorAt(0.0, QColor(0, 0, 0, 0))
    g.setColorAt(1.0, QColor(0, 0, 0, int(255 * min(1.0, weight))))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    painter.fillRect(0, 0, width, height, g)


def aspect_aware_uv(
    u: float,
    v: float,
    width: int,
    height: int,
    aspect_lock: bool,
) -> Tuple[float, float]:
    """Aspect_Lock：为 True 时让噪声域在长宽比下保持圆度。"""
    if not aspect_lock or height <= 0:
        return u, v
    ar = width / height
    return u * ar, v


def diffusion_curve(t: float, diffusion_range: float) -> float:
    """Diffusion_Range：将线性 t 映射为指数衰减曲线。"""
    if diffusion_range <= 1e-6:
        return 1.0 if t < 1 else 0
    return 1.0 - math.pow(max(0.0, 1.0 - t), 1.0 / diffusion_range)


# 导出列表供 custom.py 批量注入
HELPER_EXPORTS = [
    "perlin2",
    "fbm2",
    "vortex_offset",
    "jitter_xy",
    "viscosity_damp",
    "hsv_drift",
    "refract_uv",
    "safe_zone_factor",
    "luminance_of",
    "apply_vignette_to_painter",
    "aspect_aware_uv",
    "diffusion_curve",
]
