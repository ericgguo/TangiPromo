# SKILL: TangiPromo CLI

> **For local AI agents (Hermes, OpenClaw, Cursor Agent, etc.)**
> This file tells you exactly how to drive TangiPromo from the command line — no GUI interaction needed.

---

## What TangiPromo does

TangiPromo is a local promo-asset generator. Given a set of parameters it renders an image or video frame-by-frame using an animated background, an optional iPhone device frame with screen content, text layers, and watermarks — then exports to **PNG / JPEG / MP4**.

---

## Step 0 — Prerequisites

```bash
cd /path/to/TangiPromo
# activate venv if used
source .venv/bin/activate
```

The entry point for all CLI commands is:

```bash
python main.py <command> [options]
```

---

## Step 1 — Always discover first

**Never guess names. Run these before any export:**

```bash
# All available background internal names (use exactly as shown with --background)
python main.py list-backgrounds

# All iPhone models and their theme IDs (use with --iphone and --iphone-theme)
python main.py list-iphones

# All resolution presets (use with --resolution)
python main.py list-resolutions
```

Example output of `list-backgrounds`:
```
可用背景:
  极光
  极光波浪
  流体波浪
  霓虹光效
  几何脉冲
  星空粒子
  自定义代码
```

Example output of `list-iphones` (abbreviated):
```
  --iphone "iPhone 17 Pro Max"
    主题(--iphone-theme): cosmic_orange  |  deep_blue  |  silver

  --iphone "iPhone 16 Pro"
    主题(--iphone-theme): black_titanium  |  desert_titanium  |  natural_titanium  |  white_titanium
```

---

## Step 2 — Commands

### `export-image` — Export a static PNG or JPEG

```bash
python main.py export-image [OPTIONS] OUTPUT
```

`OUTPUT` must end in `.png` or `.jpg` / `.jpeg`.

**Minimal example (no device frame):**
```bash
python main.py export-image \
  --background "霓虹光效" \
  --ratio 9:16 \
  --no-iphone \
  --resolution 1080x1920 \
  out.png
```

**With device frame + screen + text:**
```bash
python main.py export-image \
  --background "极光" \
  --ratio 9:16 \
  --iphone "iPhone 17 Pro Max" --iphone-theme cosmic_orange \
  --iphone-scale 75 --iphone-x 50 --iphone-y 45 \
  --screen /path/to/screenshot.png \
  --text "My App Name" --text-y 0.88 --text-size 48 --text-bold --text-color "#ffffffff" \
  --text "Download Now" --text-y 0.94 --text-size 24 --text-color "#ccffffff" \
  --resolution 1080x1920 \
  out.png
```

**At a specific animation time (for animated backgrounds):**
```bash
python main.py export-image --background "极光波浪" --ratio 16:9 --no-iphone \
  --time 3.5 --resolution 1920x1080 frame.png
```

---

### `export-video` — Export an MP4

```bash
python main.py export-video [OPTIONS] OUTPUT
```

`OUTPUT` must end in `.mp4`.

```bash
python main.py export-video \
  --background "星空粒子" \
  --ratio 9:16 \
  --iphone "iPhone 17 Pro Max" --iphone-theme deep_blue \
  --screen /path/to/screen_recording.mp4 \
  --text "TangiPromo" --text-y 0.88 --text-size 44 \
  --duration 8 --fps 30 \
  --resolution 1080x1920 \
  out.mp4
```

Add `--full-import-video` to automatically extend the video duration to cover the full imported screen video:
```bash
python main.py export-video --workflow preset.json \
  --screen /path/to/demo.mp4 --full-import-video \
  out.mp4
```

---

### `save-workflow` — Save current config as a reusable JSON

```bash
python main.py save-workflow [OPTIONS] OUTPUT.json
```

The saved file is 100% compatible with the GUI's "Save Workflow" button — you can load it back in the GUI, or pass it to `--workflow` in future CLI calls.

```bash
python main.py save-workflow \
  --background "霓虹光效" \
  --ratio 9:16 \
  --no-iphone \
  --name "neon_9x16" \
  neon_9x16.json
```

---

### `export-image` / `export-video` with `--workflow` as base

Load a workflow first, then CLI flags **override** individual fields:

```bash
# Load GUI-saved preset, override background and resolution
python main.py export-image \
  --workflow my_preset.json \
  --background "极光" \
  --resolution 4K \
  out_4k.png
```

---

## Step 3 — Full parameter reference

### Shared options (export-image, export-video, save-workflow)

| Parameter | Values / Format | Notes |
|-----------|----------------|-------|
| `--workflow PATH` | JSON file path | Load base config; CLI flags override |
| `--background NAME` | From `list-backgrounds` | e.g. `"霓虹光效"` |
| `--bg-speed PCT` | `0`–`300` (default `100`) | Animation speed percentage |
| `--bg-code PATH_OR_CODE` | File path or Python string | Activates Custom Code background |
| `--bg-params JSON` | `'{"speed": 1.5}'` | Extra background kwargs |
| `--ratio RATIO` | `16:9` `9:16` `1:1` `4:3` `4:5` `21:9` | Output aspect ratio |
| `--iphone "MODEL"` | From `list-iphones` | e.g. `"iPhone 17 Pro Max"` |
| `--iphone-theme ID` | From `list-iphones` | e.g. `cosmic_orange` |
| `--iphone-scale PCT` | `0`–`100` (default `72`) | Device scale % of canvas |
| `--iphone-x PCT` | `0`–`100` (default `50`) | Horizontal position % |
| `--iphone-y PCT` | `0`–`100` (default `50`) | Vertical position % |
| `--no-iphone` | flag | Hide device frame entirely |
| `--screen PATH` | Image or video file | Auto-detected by extension |
| `--text TEXT` | String (repeatable) | One layer per `--text` |
| `--text-y 0-1` | Float (repeatable) | Y position, 0=top, 1=bottom |
| `--text-x 0-1` | Float (repeatable) | X position, default `0.5` |
| `--text-font FAMILY` | String (repeatable) | e.g. `"Helvetica Neue"` |
| `--text-size PT` | Int (repeatable) | Font size in pt at 1080px height |
| `--text-color #HEX` | `#RRGGBB` or `#AARRGGBB` (repeatable) | Per-layer color |
| `--text-bold` | flag | Bold all `--text` layers |
| `--text-no-shadow` | flag | Disable shadow on all `--text` layers |
| `--watermark PATH` | PNG file | Single watermark |
| `--watermark-x PCT` | `0`–`100` (default `50`) | Center X % |
| `--watermark-y PCT` | `0`–`100` (default `50`) | Center Y % |
| `--watermark-width PCT` | `0`–`100` (default `14`) | Width % of canvas |
| `--watermark-color #HEX` | `#AARRGGBB` | Tint color, default white semi-transparent |
| `--effect-code PATH_OR_CODE` | File path or Python string | Post-process effect on full frame |
| `--effect-off` | flag | Disable effect (even if workflow has it) |
| `--region-guide` | flag | Overlay region crosshair (for effect targeting) |
| `--breakpoints T1,T2,...` | Comma-separated floats | e.g. `"2.0,5.0,8.0"` |
| `--resolution PRESET_OR_WxH` | See below | Export pixel dimensions |
| `--time SECONDS` | Float (default `0.0`) | Snapshot time for image export |

### Resolution shortcuts

| Short form | Full preset |
|------------|-------------|
| `1080p` | `1080p (16:9)` → 1920×1080 |
| `2k` | `2K (16:9)` → 2560×1440 |
| `4k` | `4K (16:9)` → 3840×2160 |
| `1080x1920` | Custom WxH — use for 9:16 |
| `WxH` | Any integer WxH, e.g. `864x1080` |

Note: when using `--ratio`, the **height** is kept from the resolution and the **width is recomputed** to match the ratio. So `--ratio 9:16 --resolution 1080p` gives 608×1080 (not 1920×1080).  
To get exactly 1080×1920, use `--resolution 1080x1920`.

### export-video only

| Parameter | Default | Notes |
|-----------|---------|-------|
| `--fps FPS` | `30` | Frame rate |
| `--duration SECONDS` | from workflow or `10` | Video length |
| `--full-import-video` | off | Extend to cover full imported screen video |

---

## Step 4 — Complex workflows via JSON

For rich text layers, per-layer colors, multiple watermarks, or effect code with breakpoints, the cleanest agent workflow is:

1. **Build a payload dict** matching the workflow format.
2. **Write it to a JSON file** with the structure below.
3. **Pass it via** `--workflow my.json`.

Minimal workflow JSON structure:
```json
{
  "version": 1,
  "presets": [{
    "id": "any-uuid",
    "name": "my_preset",
    "payload": {
      "ratio_idx": 1,
      "export": { "fps": 30, "duration": 10, "full_import_video": false },
      "background": { "key": "霓虹光效", "speed": 100, "custom_code": "" },
      "effects": { "enabled": false, "code": "", "breakpoints": [], "region_guide": false },
      "phone": { "model": "iPhone 17 Pro Max", "theme": "deep_blue", "show": true,
                 "scale": 72, "x": 50, "y": 50 },
      "content": { "type": "none", "path": null },
      "watermarks": [],
      "text_layers": [
        {
          "name": "layer1", "text": "Hello World",
          "x": 0.5, "y": 0.85,
          "font_family": "Helvetica Neue", "font_size_pt": 36,
          "bold": false, "italic": false,
          "color": "#ffffffff",
          "align": 4,
          "shadow": true, "shadow_color": "#a0000000", "shadow_offset": [2.0, 3.0],
          "outline": false, "outline_color": "#c8000000", "outline_width": 2.0,
          "visible": true
        }
      ]
    }
  }]
}
```

`ratio_idx` values: `0`=16:9, `1`=9:16, `2`=1:1, `3`=4:3, `4`=4:5, `5`=21:9

`align` values: `4`=center, `1`=left, `2`=right  
(These are Qt.AlignmentFlag int values: AlignHCenter=4, AlignLeft=1, AlignRight=2)

---

## Step 5 — Custom background / effect code contracts

### Background code (`--bg-code` or `background.custom_code`)

```python
# Injected: painter (QPainter), width, height, t (float seconds)
# Also injected: QColor, QLinearGradient, QRadialGradient, QPainterPath,
#                QPen, QBrush, QFont, QPointF, QRectF, Qt, math, np (numpy)
# Must: draw on painter. Return value is ignored.

import math
painter.fillRect(0, 0, width, height, QColor(10, 10, 20))
cx, cy = width / 2, height / 2
r = min(width, height) * 0.3 * (0.8 + 0.2 * math.sin(t * 2))
painter.setBrush(QColor(124, 107, 255, 160))
painter.setPen(Qt.PenStyle.NoPen)
painter.drawEllipse(QPointF(cx, cy), r, r)
```

### Effect code (`--effect-code` or `effects.code`)

```python
# Injected: img (QImage of full rendered frame), width, height,
#           t, time, duration, breakpoints, zoom_region()
# Also injected: QPainter, QImage, math
# Must: modify img in-place (QPainter on img) or call zoom_region().

zoom_region(0.1, 0.2, 0.8, 0.6, scale=1.0 + 0.3 * t / duration)
```

---

## Step 6 — Error handling & tips

- **Missing asset files**: CLI prints `[警告] 文件不存在，已跳过:` and continues. Always use **absolute paths** for `--screen`, `--watermark`, and workflow `content.path`.
- **Wrong background name**: CLI exits with `ValueError` listing all valid names. Run `list-backgrounds` first.
- **Resolution + ratio mismatch**: CLI recomputes width from height to match ratio. Use `WxH` format to control both dimensions explicitly.
- **No ffmpeg**: Video export falls back to OpenCV. Install ffmpeg for better quality: `brew install ffmpeg` (macOS).
- **Breakpoints format**: Must be comma-separated floats with no spaces: `"2.5,5.0,7.5"` ✓ — `"2.5, 5.0"` ✗.
- **Color format**: Accepts `#RRGGBB` (opaque) or `#AARRGGBB` (with alpha). For `--watermark-color`, alpha controls opacity: `#ffebebeb` = fully opaque near-white.

---

## Quick-reference cheatsheet

```bash
# Discover
python main.py list-backgrounds
python main.py list-iphones
python main.py list-resolutions

# Fast image export — no device, inline text
python main.py export-image \
  --background "霓虹光效" --ratio 9:16 --no-iphone \
  --text "App Name" --text-y 0.85 --text-size 48 --text-bold \
  --resolution 1080x1920 out.png

# Image with device frame
python main.py export-image \
  --background "极光" --ratio 9:16 \
  --iphone "iPhone 17 Pro Max" --iphone-theme cosmic_orange \
  --screen /abs/path/screenshot.png \
  --text "Feature Name" --text-y 0.88 \
  --resolution 1080x1920 out.png

# Video with screen recording
python main.py export-video \
  --background "星空粒子" --ratio 9:16 \
  --iphone "iPhone 17 Pro Max" --iphone-theme deep_blue \
  --screen /abs/path/demo.mp4 \
  --duration 10 --fps 30 --full-import-video \
  --resolution 1080x1920 out.mp4

# Save a workflow for reuse
python main.py save-workflow \
  --background "极光波浪" --ratio 16:9 --no-iphone \
  --name "aurora_16x9" aurora_16x9.json

# Export from saved workflow
python main.py export-image --workflow aurora_16x9.json out.png
python main.py export-video --workflow aurora_16x9.json --duration 8 out.mp4
```
