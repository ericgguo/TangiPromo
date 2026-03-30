# TangiPromo

桌面端 App 宣发素材工具：在画布上组合动态背景、iPhone 机型 mockup、屏幕截图、文字与水印，并按多种比例导出图片或视频。

## 功能概览

- 多种输出比例（如 16:9、9:16、1:1 等）
- 内置动态背景预设，支持自定义 Python 绘制代码与预设保存
- iPhone 外观与屏幕内容叠加
- 文字图层、水印 PNG
- 导出为静态图或视频；界面支持中文 / English

## 环境要求

- Python 3.10+（建议与当前系统已安装的 PySide6 兼容版本一致）

## 安装与运行

```bash
cd TangiPromo
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

依赖见项目根目录 `requirements.txt`（PySide6、NumPy、Pillow、OpenCV 等）。
