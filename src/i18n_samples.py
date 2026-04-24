"""自定义背景默认示例代码（中英注释），供 i18n 引用。"""
from __future__ import annotations

# 共享画面逻辑：NumPy 加速的极光流动背景，
# 两套优雅配色（深翠绿 ↔ 幻彩紫青）每 6s 交替交融。

_SHARED_BODY = """\
import numpy as np
from PySide6.QtGui import QImage

# --- 1. 时间与周期控制 ---
# 周期改为 6.0s
period = 6.0
# 使用 cos 映射到 0.0 - 1.0
# 这样在 t=0, 6, 12... 时 alpha 为 0
alpha = 0.5 * (1 + np.cos(2 * np.pi * t / period + np.pi))

# --- 2. 物理波动计算 (微调频率使波动更柔和) ---
time_factor = 1.5  # 稍微放慢波动速度，增加优雅感
active_t = t * time_factor

x = np.linspace(0, 1, width)
y = np.linspace(0, 1, height)
xx, yy = np.meshgrid(x, y)

# 增加一些非线性扰动，模拟极光的流体感
waveBase = np.sin(xx * 2.0 + active_t) * 0.5 + np.cos(yy * 2.5 - active_t * 0.7)
waveDiag = np.sin((xx + yy) * 3.5 + active_t * 1.2)
waveDetail = np.sin(xx * 15.0 - yy * 12.0 + active_t * 2.0) * 0.2
combined = waveBase + waveDiag + waveDetail

# 重新归一化 Mask，使其对比度更柔和
mask = (combined + 3.0) / 6.0
mask = np.clip(mask, 0, 1)

# --- 3. 颜色定义 (优雅极光色系) ---

# 方案 A：深邃翠绿 (Deep Emerald / Aurora Green)
# Dark: (5, 15, 25) | Light: (40, 200, 150)
r_a = 5 * (1 - mask) + 40 * mask
g_a = 15 * (1 - mask) + 200 * mask
b_a = 25 * (1 - mask) + 150 * mask

# 方案 B：幻彩紫青 (Ethereal Purple / Cyan)
# Dark: (10, 10, 40) | Light: (130, 100, 255)
r_b = 10 * (1 - mask) + 130 * mask
g_b = 10 * (1 - mask) + 100 * mask
b_b = 40 * (1 - mask) + 255 * mask

# --- 4. 颜色合成与增强 ---
# 在 A 和 B 之间插值
r = r_a * (1 - alpha) + r_b * alpha
g = g_a * (1 - alpha) + g_b * alpha
b = b_a * (1 - alpha) + b_b * alpha

# 进阶技巧：在 alpha 中间阶段注入一点"高光白"模拟极光最亮的中心
glimmer = np.sin(np.pi * alpha) * (mask ** 4) * 50
r = np.clip(r + glimmer, 0, 255)
g = np.clip(g + glimmer * 1.2, 0, 255)
b = np.clip(b + glimmer * 1.1, 0, 255)

# --- 5. 渲染输出 ---
rgb = np.dstack((r, g, b)).astype(np.uint8)
rgb = np.ascontiguousarray(rgb)

h, w, _ = rgb.shape
qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
painter.drawImage(0, 0, qimg)
"""

CODE_SAMPLE_ZH = _SHARED_BODY
CODE_SAMPLE_EN = _SHARED_BODY
