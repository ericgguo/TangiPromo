"""
设备框 PNG 路径（相对 assets/iphone/third_party/Exports/iOS/）。

内层 dict 的 key 为稳定英文 theme_id（供逻辑与存储），界面文案由 i18n.theme_display_name 翻译。
"""
from __future__ import annotations

DEVICE_PNG: dict[str, dict[str, str]] = {
    "iPhone 17 Pro Max": {
        "cosmic_orange": "17 Pro Max/17 Pro Max - Cosmic Orange.png",
        "deep_blue": "17 Pro Max/17 Pro Max - Deep Blue.png",
        "silver": "17 Pro Max/17 Pro Max - Silver.png",
    },
    "iPhone 17 Pro": {
        "cosmic_orange": "17 Pro/17 Pro - Cosmic Orange.png",
        "deep_blue": "17 Pro/17 Pro - Deep Blue.png",
        "silver": "17 Pro/17 Pro - Silver.png",
    },
    "iPhone 16 Pro Max": {
        "black_titanium": "16 Pro Max/16 Pro Max - Black Titanium.png",
        "desert_titanium": "16 Pro Max/16 Pro Max - Desert Titanium.png",
        "natural_titanium": "16 Pro Max/16 Pro Max - Natural Titanium.png",
        "white_titanium": "16 Pro Max/16 Pro Max - White Titanium.png",
    },
    "iPhone 16 Pro": {
        "black_titanium": "16 Pro/16 Pro - Black Titanium.png",
        "desert_titanium": "16 Pro/16 Pro - Desert Titanium.png",
        "natural_titanium": "16 Pro/16 Pro - Natural Titanium.png",
        "white_titanium": "16 Pro/16 Pro - White Titanium.png",
    },
    "iPhone Air": {
        "cloud_white": "Air/Air - Cloud White.png",
        "light_gold": "Air/Air - Light Gold.png",
        "sky_blue": "Air/Air - Sky Blue.png",
        "space_black": "Air/Air - Space Black.png",
    },
    "iPhone 16 Plus": {
        "black": "16 Plus/16 Plus - Black.png",
        "pink": "16 Plus/16 Plus - Pink.png",
        "teal": "16 Plus/16 Plus - Teal.png",
        "ultramarine": "16 Plus/16 Plus - Ultramarine.png",
        "white": "16 Plus/16 Plus - White.png",
    },
    "iPhone 16": {
        "black": "16/16 - Black.png",
        "pink": "16/16 - Pink.png",
        "teal": "16/16 - Teal.png",
        "ultramarine": "16/16 - Ultramarine.png",
        "white": "16/16 - White.png",
    },
    "iPhone 15 Pro Max": {
        "black_titanium": "15 Pro Max/15 Pro Max - Black Titanium.png",
        "blue_titanium": "15 Pro Max/15 Pro Max - Blue Titanium.png",
        "natural_titanium": "15 Pro Max/15 Pro Max - Natural Titanium.png",
        "white_titanium": "15 Pro Max/15 Pro Max - White Titanium.png",
    },
    "iPhone 14 Pro Max": {
        "space_black": "14 Pro Max/14 Pro Max - Space Black.png",
        "silver": "14 Pro Max/14 Pro Max - Silver.png",
        "gold": "14 Pro Max/14 Pro Max - Gold.png",
        "deep_purple": "14 Pro Max/14 Pro Max - Deep Purple.png",
    },
    "iPhone 13 mini": {
        "midnight": "13 mini/13 mini - Black.png",
        "mini_blue": "13 mini/13 mini - Blue.png",
        "mini_pink": "13 mini/13 mini - Pink.png",
        "product_red": "13 mini/13 mini - Product (RED).png",
        "starlight": "13 mini/13 mini - Starlight.png",
    },
}

MODEL_ORDER: list[str] = list(DEVICE_PNG.keys())

_FALLBACK_THEME = "black_titanium"


def default_theme_for_model(model: str) -> str:
    themes = DEVICE_PNG.get(model, {})
    return next(iter(themes)) if themes else _FALLBACK_THEME


def rel_path_for(model: str, theme: str) -> str | None:
    m = DEVICE_PNG.get(model)
    if not m:
        return None
    return m.get(theme)
