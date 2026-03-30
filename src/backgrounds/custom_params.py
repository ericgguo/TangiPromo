"""
自定义背景代码中可用的「物理 / 光学 / 色彩 / 质量 / 构图」参数默认值。

无需在面板配置；在自定义代码里直接使用变量名（可重新赋值），
或通过 exec 后的逻辑参与后处理（运动模糊、抖动、色散等）。

命名与含义见模块末尾 CUSTOM_BG_PARAM_REFERENCE。
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# 默认值（每一帧执行自定义代码前会注入到命名空间，用户可覆盖）
# ---------------------------------------------------------------------------

DEFAULT_CUSTOM_BG_PARAMS: dict[str, Any] = {
    # —— 1. 运动学与物理 Motion & Physics ——
    "Noise_Scale": 1.0,           # 噪声频率；小=平缓，大=破碎
    "Viscosity": 0.5,             # 黏度；高=厚重，低=稀薄
    "Vortex_Strength": 0.0,       # 涡流角向偏移强度
    "Jitter": 0.02,               # 高频震颤幅度（归一化坐标）

    # —— 2. 光学与材质 Optical & Material ——
    "Refraction_Index": 1.0,      # 折射 UV 偏移系数（配合 helpers）
    "Ambient_Occlusion": 0.3,     # 叠层暗边强度 0~1
    "Specular_Intensity": 0.5,    # 高光强度 0~1
    "Diffusion_Range": 1.0,       # 渐变衰减曲线；大=更实，小=更虚

    # —— 3. 色彩动力学 Color Dynamics ——
    "Color_Drift": 0.05,          # 色相/饱和度随 t 漂移量
    "Luminance_Threshold": 0.5,   # 亮度门控（叠色模式分界）
    "Chromatic_Aberration": 0.0,  # 边缘 RGB 分离强度 0~若干像素量级

    # —— 4. 渲染质量 Rendering Quality ——
    # 默认 0：后处理不参与画面，避免「未在代码里用到的参数」改变用户绘制结果
    "Dither_Amount": 0.0,         # 抗色带噪声强度（>0 时由管线加噪）
    "Sample_Density": 1.0,        # 场采样步长倒数；大=更细
    "Motion_Blur": 0.0,           # 与上一帧混合比例 0~1（需离屏管线）

    # —— 5. 构图 Compositional ——
    "Vignette_Weight": 0.0,       # 暗角强度 0~1
    "Aspect_Lock": True,          # 是否按宽高比统一噪声/涡流域
    "Safe_Zone_Offset": 0.1,      # 边缘安全区比例，剧烈效果可减弱
}


CUSTOM_BG_PARAM_REFERENCE = """
=== 时间与动画 ===
  t / time：从开始预览起累计的「秒」数（每帧约 +1/60）。若写 sin(t * 0.15)，约 40 秒才走完半周期，
  看起来会像「不流动」——请改为 sin(t * 2.0) 或提高 lights 里的 sp，或确认左侧未点「暂停」。
  Motion_Blur > 0 会与上一帧混合，过大时像拖影、动感变弱；不需要时请保持 0。

=== 自定义背景 · 变量（每帧注入默认值，可在代码中赋值覆盖）===

【运动学与物理 Motion & Physics】
  Noise_Scale — 噪声频率（Perlin/类 Perlin）；小=平缓，大=碎裂
  Viscosity — 黏度概念量，可与 viscosity_damp 等配合
  Vortex_Strength — 涡流角向偏移强度（见 vortex_offset）
  Jitter — 高频震颤幅度（见 jitter_xy）

【光学与材质 Optical & Material】
  Refraction_Index — UV 折射偏移（见 refract_uv）
  Ambient_Occlusion — 叠层暗边/遮蔽强度 0~1（逻辑自用在代码中）
  Specular_Intensity — 高光强度 0~1（逻辑自用）
  Diffusion_Range — 渐变衰减曲线（见 diffusion_curve）

【色彩动力学 Color Dynamics】
  Color_Drift — 色相/饱和度随 t 漂移（见 hsv_drift）
  Luminance_Threshold — 亮度门控 0~1（与 luminance_of、叠色逻辑配合）
  Chromatic_Aberration — 色散强度（后处理对 RGB 通道错位）

【渲染质量 Rendering Quality】
  Dither_Amount — 抖动抗色带（后处理加噪；默认 0，需在代码中赋值才启用）
  Sample_Density — 场采样密度（逻辑自用，如步长 = 1/Sample_Density）
  Motion_Blur — 与上一帧混合比例 0~1（后处理；默认 0）

【构图 Compositional】
  Vignette_Weight — 暗角权重 0~1（后处理）
  Aspect_Lock — 是否按画幅校正噪声域（见 aspect_aware_uv）
  Safe_Zone_Offset — 边缘安全区比例（见 safe_zone_factor）

【辅助函数】custom_helpers：perlin2, fbm2, vortex_offset, jitter_xy, hsv_drift,
  refract_uv, safe_zone_factor, luminance_of, apply_vignette_to_painter,
  aspect_aware_uv, diffusion_curve, viscosity_damp
"""
