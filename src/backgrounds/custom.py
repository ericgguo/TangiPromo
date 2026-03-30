"""
自定义背景：exec 用户 Python 代码，直接在离屏 QImage 上绘制，
然后将结果 blit 到主画布。

设计原则：
  - 用户代码 = 一段纯粹的绘制脚本，和预设代码逻辑完全一样
  - 注入最小必要变量：painter, width, height, t
  - 额外提供常用 Qt 类 + math + numpy
  - 不注入任何"默认参数"干扰用户结果
  - 不做任何隐式后处理（用户若需要自己写）
"""
from __future__ import annotations

import math
import traceback
from typing import Any, Optional

from PySide6.QtGui import (
    QPainter,
    QColor,
    QImage,
    QLinearGradient,
    QRadialGradient,
    QPainterPath,
    QPen,
    QBrush,
    QFont,
)
from PySide6.QtCore import QPointF, QRectF, Qt

from .base import Background
from . import custom_helpers
from .custom_params import DEFAULT_CUSTOM_BG_PARAMS

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


def _build_ns(painter: QPainter, width: int, height: int, t: float) -> dict[str, Any]:
    """构建用户代码执行命名空间。

    注入内容：
      - 绘图上下文：painter / width / height / t
      - Qt 绘图类：QColor, QRadialGradient, QPainter, …
      - 常用模块：math, np（如已安装）
      - 辅助函数：fbm2, perlin2, vortex_offset, hsv_drift, …
      - 可选参数默认值：Vortex_Strength, Color_Drift, Noise_Scale 等
        （用户可在代码顶部直接赋值覆盖，与预设写法完全一致）
    """
    ns: dict[str, Any] = {
        # 绘图上下文
        "painter": painter,
        "width": width,
        "height": height,
        "t": t,
        "time": t,
        # 常用模块
        "math": math,
        # Qt 绘图类
        "QPainter": QPainter,
        "QColor": QColor,
        "QImage": QImage,
        "QLinearGradient": QLinearGradient,
        "QRadialGradient": QRadialGradient,
        "QPainterPath": QPainterPath,
        "QPen": QPen,
        "QBrush": QBrush,
        "QFont": QFont,
        "QPointF": QPointF,
        "QRectF": QRectF,
        "Qt": Qt,
    }
    # 可选参数默认值（用户代码中可直接使用，也可赋值覆盖）
    ns.update(DEFAULT_CUSTOM_BG_PARAMS)
    # 辅助函数（fbm2, perlin2, vortex_offset, hsv_drift 等）
    for name in custom_helpers.HELPER_EXPORTS:
        ns[name] = getattr(custom_helpers, name)
    if _HAS_NUMPY:
        ns["np"] = np
    return ns


class CustomCodeBackground(Background):
    """执行用户 Python 背景代码。

    用户代码直接操作 `painter`（离屏 QPainter），和预设背景的 render() 方法完全等价。
    代码里可以用 width, height, t 以及所有注入的 Qt 类和辅助函数。
    注入的 t / time 已与主窗口「动画速度」滑块一致（同预设背景的 t * speed）。
    """

    name = "自定义代码"

    def __init__(self) -> None:
        from ..i18n import default_custom_code

        self.speed: float = 1.0
        self.code: str = default_custom_code()
        self.error: str | None = None
        self._compiled = None
        self._last_code: str | None = None

    def render(self, painter: QPainter, width: int, height: int, t: float) -> None:
        # 默认填充背景色
        painter.fillRect(0, 0, width, height, QColor(15, 15, 25))

        code = self.code
        if not code.strip():
            return

        # 编译（有变化时才重新编译）
        if code != self._last_code:
            try:
                self._compiled = compile(code, "<custom_bg>", "exec")
                self._last_code = code
                self.error = None
            except SyntaxError as e:
                self.error = f"SyntaxError（第 {e.lineno} 行）: {e.msg}"
                return
            except Exception as e:
                self.error = f"编译错误: {e}"
                return

        # 离屏渲染：用户代码在独立的 QImage 上绘制
        img = QImage(width, height, QImage.Format.Format_RGB32)
        img.fill(QColor(15, 15, 25))

        p2 = QPainter(img)
        p2.setRenderHint(QPainter.RenderHint.Antialiasing)
        p2.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        ns = _build_ns(p2, width, height, t * self.speed)

        try:
            exec(self._compiled, ns)  # noqa: S102
            self.error = None
        except Exception:
            self.error = traceback.format_exc(limit=8)
        finally:
            # 确保合成模式复位后再 end，否则 end() 可能崩溃
            p2.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            p2.end()

        if self.error:
            return

        # 将离屏结果画到主 painter
        painter.drawImage(0, 0, img)


__all__ = ["CustomCodeBackground"]
