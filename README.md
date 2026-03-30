# TangiPromo

**Language / 语言:** [English](#english) · [中文](#中文)

---

<a id="english"></a>
## English

Desktop tool for promo assets on platforms like the App Store, X, Instagram, RedNote, and similar—build the workflows and feature shots you need for marketing, lower cost, and ship creatives much faster: animated backgrounds, iPhone frames, screen image or video, draggable text and **brand** watermarks, and export to PNG, JPEG, or MP4 in multiple aspect ratios. Switch **English** / **中文** in the left sidebar.

### What you can do

- **Output ratio** — Choose presets such as 16:9, 9:16, 1:1, 4:3, 4:5, 21:9 before exporting.
- **Backgrounds** — Pick built-in animated presets (mesh gradient, waves, aurora, neon, geometry, particles), or drive the canvas entirely with your own logic.
- **Custom background via Python** — In the background list, choose **Custom code** (中文界面下为 **自定义代码**). The editor runs a drawing script each frame, same idea as the built-in generators:
  - Your code receives **`painter`** (a `QPainter`), canvas **`width`** / **`height`**, and animation time **`t`** (also exposed as **`time`**).
  - Injected APIs include common **Qt** types (`QColor`, `QLinearGradient`, `QRadialGradient`, `QPainterPath`, `QPen`, `QBrush`, `QFont`, `QPointF`, `QRectF`, `Qt`, …), **`math`**, **`numpy` as `np`** when NumPy is installed, plus helpers such as **`vortex_offset`**, noise/FBM-style utilities, and tunable defaults (e.g. strength/drift parameters you can override at the top of your script).
  - If you are not comfortable coding, share the built-in sample template and your background/motion ideas with any AI assistant, then paste the generated code into the editor—you can get results quickly.
  - Click **Apply** to compile and run; after you stop typing for a short moment, changes can also apply automatically (see the in-app tooltip).
  - **Save** / **Delete** named presets: snippets are stored locally as JSON under the app’s data directory (Qt `AppDataLocation` for TangiPromo).
- **iPhone** — Model and color, position and scale as % of the canvas; optional show/hide; **Center phone** snaps to the middle. Need another device frame? Add and integrate it yourself.
- **Screen content** — Load a still or a video into the device screen area.
- **Text layers** — Multiple layers, font, size, color, alignment, shadow/outline; drag on the canvas.
- **Watermarks** — One or more PNGs (transparency supported); drag to position.
- **Export** — Resolution presets, optional duration and FPS for video; behavior ties to loaded video when relevant.

### Requirements

- **Python 3.10+** (use a version that has compatible wheels for PySide6 on your OS).

### Install and run

**Virtual environment: recommended.** A venv reduces conflicts with system or other projects. The app does **not** require a venv; any Python environment where you install the dependencies is fine.

**Option A — with a venv (recommended):**

```bash
cd TangiPromo
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Option B — without a venv** (user install or global `pip`, Conda, etc.):

```bash
cd TangiPromo
pip install -r requirements.txt   # or: pip install --user -r requirements.txt
python main.py
```

Use the **same** interpreter for `pip` and `python` so imports resolve. Dependencies: see `requirements.txt` (PySide6, NumPy, Pillow, OpenCV, etc.).

---

<a id="中文"></a>
## 中文

用于制作类似 App Store 、X、instagram、RedNote 等等平台宣传物料的桌面工具，生成你需要宣传的workflow和功能，降低成本的同时极大加速你的宣发速度：动态背景、iPhone 外框、屏幕图片或视频、可拖拽的文字与品牌水印，以及多种比例下导出 PNG、JPEG 或 MP4。界面语言可在左侧 **English** / **中文** 之间切换。

### 功能说明

- **输出比例** — 导出前可选择 16:9、9:16、1:1、4:3、4:5、21:9 等预设。
- **背景** — 内置多种动态预设（网格渐变、抽象波浪、极光、霓虹、几何、粒子等），也可用代码完全自定义画面。
- **用代码编辑背景** — 在背景预设列表中选择 **自定义代码**（英文界面下为 **Custom code**）。每帧会执行你的 Python 绘制脚本，与内置背景的渲染方式一致：
  - 脚本中可使用 **`painter`**（`QPainter`）、画布 **`width`** / **`height`**、时间 **`t`**（也可用 **`time`**）驱动动画。
  - 环境内注入常用 **Qt** 类型（`QColor`、`QLinearGradient`、`QRadialGradient`、`QPainterPath`、`QPen`、`QBrush`、`QFont`、`QPointF`、`QRectF`、`Qt` 等）、**`math`**、已安装时的 **`numpy`（`np`）**，以及 **`vortex_offset`**、噪声/类 FBM 等辅助函数和可在脚本顶部覆盖的默认参数（强度、漂移等）。
  - 如果你不会代码，把预设模版和你的背景动画需求交给任何AI，然后把它们生成的代码复制进对话框，很快就能搞定。
  - 点击 **应用** 立即编译运行；停止编辑约片刻后也会自动应用（详见界面内提示）。
  - **保存** / **删除** 命名预设：代码会保存在本机应用数据目录下的 JSON 中（Qt 为 TangiPromo 分配的 `AppDataLocation`）。
- **iPhone** — 机型与颜色、位置与缩放（画布百分比）、显示开关；**一键居中** 将手机置于画布中心。如果你需要其他设备的适配，请自行添加。
- **屏幕内容** — 为屏幕区域加载静态图或视频。
- **文字图层** — 多图层、字体、字号、颜色、对齐、阴影/描边；在画布上拖动摆放。
- **水印** — 支持多张 PNG（建议带透明）；在画布上拖动定位。
- **导出** — 分辨率预设、视频的帧率与时长等；若已加载视频，导出时长等行为与素材相关。

### 环境要求

- **Python 3.10+**（需与当前系统上 PySide6 的预编译包版本兼容）。

### 安装与运行

**虚拟环境：建议使用。** 使用 venv 可减少与系统或其它项目的依赖冲突；程序本身**不要求**必须用虚拟环境，只要在同一个 Python 环境里装好依赖即可。

**方式 A — 使用虚拟环境（推荐）：**

```bash
cd TangiPromo
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**方式 B — 不使用虚拟环境**（全局 pip、用户级 `pip install --user`、Conda 等均可）：

```bash
cd TangiPromo
pip install -r requirements.txt   # 或: pip install --user -r requirements.txt
python main.py
```

请保证 **`pip` 与 `python` 指向同一解释器**，以免找不到已安装的包。依赖列表见 `requirements.txt`（PySide6、NumPy、Pillow、OpenCV 等）。
