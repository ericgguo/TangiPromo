"""
Mac / 电脑模式设备框配置。

• 简约窗口：红黄绿交通灯，程序绘制（无 PNG）
• 实体 MacBook：jamesjingyi/mockup-device-frames Exports/MacBook PNG（含刘海）
"""
from __future__ import annotations

# 简约窗口（程序绘制）
MINIMAL_MODELS: frozenset[str] = frozenset({"Window Dark", "Window Light"})

# 实体 MacBook PNG（相对 assets/mac/third_party/Exports/MacBook/）
DEVICE_PNG: dict[str, dict[str, str]] = {
    "MacBook Pro 14": {
        "default": "MacBook Pro 14.png",
        "menu_bar": "MacBook Pro 14 - Menu Bar.png",
    },
    "MacBook Pro 16": {
        "default": "MacBook Pro 16.png",
        "menu_bar": "MacBook Pro 16 - Menu Bar.png",
    },
    "MacBook Air 13": {
        "default": "MacBook Air 13.png",
        "menu_bar": "MacBook Air 13 - Menu Bar.png",
    },
    "MacBook Air 15": {
        "default": "MacBook Air 15.png",
        "menu_bar": "MacBook Air 15 - Menu Bar.png",
    },
}

MODEL_ORDER: list[str] = [
    "Window Dark",
    "Window Light",
    "MacBook Pro 14",
    "MacBook Pro 16",
    "MacBook Air 13",
    "MacBook Air 15",
]

_FALLBACK_THEME = "default"


def is_minimal_model(model: str) -> bool:
    return model in MINIMAL_MODELS


def default_theme_for_model(model: str) -> str:
    if is_minimal_model(model):
        return _FALLBACK_THEME
    themes = DEVICE_PNG.get(model, {})
    return next(iter(themes)) if themes else _FALLBACK_THEME


def rel_path_for(model: str, theme: str) -> str | None:
    if is_minimal_model(model):
        return None
    themes = DEVICE_PNG.get(model, {})
    if theme in themes:
        return themes[theme]
    return themes.get(_FALLBACK_THEME)
