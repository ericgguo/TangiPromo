# TangiPromo

Desktop app for creating App Store–style promo assets: combine animated backgrounds, iPhone device frames, screen content, text, and watermarks on a canvas, then export still images or video in multiple aspect ratios.

## Features

- Common output ratios (16:9, 9:16, 1:1, etc.)
- Built-in animated backgrounds plus custom Python drawing code and savable presets
- iPhone shell with screen image or video
- Text layers and PNG watermarks
- Export to PNG, JPEG, or MP4; UI in English or Chinese

## Requirements

- Python 3.10+ (use a version compatible with your PySide6 wheel)

## Install and run

```bash
cd TangiPromo
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Dependencies are listed in `requirements.txt` (PySide6, NumPy, Pillow, OpenCV, etc.).
