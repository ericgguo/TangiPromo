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
  - If you are not comfortable coding, share the built-in sample template **and** the **“Custom code: details for you and for AI assistants”** checklist below with any AI assistant, then paste the generated code into the editor—this avoids non-running snippets (e.g. OpenCV-only previews, uncalled `def`, wrong time variables).
  - Click **Apply** to compile and run; after you stop typing for a short moment, changes can also apply automatically (see the in-app tooltip).
  - **Save** / **Delete** named presets: snippets are stored locally as JSON under the app’s data directory (Qt `AppDataLocation` for TangiPromo).
- **Timeline (bottom-center player bar)** — When imported video exists or the current background is animated, the timeline appears under the canvas:
  - Play/Pause controls preview time and imported video playback together.
  - Drag-to-scrub seeks preview to an exact time point.
  - Add/Delete breakpoints and jump between them quickly.
  - Timeline length follows export duration; when loading a video, duration auto-initializes to video length and frame 0 is aligned.
- **Effects (right panel, export-consistent)** — Add post effects with Python code to the fully rendered frame (background + phone + text + watermarks), using the same render pipeline as export:
  - Useful for camera-like moves, region zoom, and time-window transitions.
  - Built-in helper `zoom_region(x, y, w, h, scale)` uses normalized coordinates.
  - `t`, `duration`, and `breakpoints` are available in effect code.
  - Region guide toggle overlays crosshair and normalized `(x, y)` under the mouse for precise targeting.

#### Custom code: details for you and for AI assistants

Paste the following into your AI prompt so generated code actually runs inside TangiPromo:

- **How it runs:** Each animation frame, TangiPromo **`exec`s your whole script** in a sandboxed namespace. It does **not** run `python yourfile.py`. There is **no** call to a function you define unless **you** call it from top-level code in the same snippet.
- **Output:** The app **ignores return values**. You must **draw on the injected `painter`** (or build a `QImage` and `painter.drawImage(...)`). Patterns that only **`return` a NumPy/OpenCV array** or use **`cv2.imshow` / Matplotlib `show()`** will not show as the background.
- **`if __name__ == "__main__":`** Often **does not run** in this embedded context, so preview loops there will never execute—keep the drawing logic at module level or behind an explicit function **that you call**.
- **Time variable:** Use the injected **`t`** (a float that increases over time, roughly seconds). Do **not** assume `frame_index` / `total_frames` exist unless you derive phase from **`t`** yourself (e.g. `sin(t * k)`).
- **Libraries:** **`np`** is available when NumPy is installed. **OpenCV (`cv2`)** is not required for backgrounds; if the model generates OpenCV-only preview code, ask it to **port to `painter` + Qt** (or NumPy → `QImage` → `drawImage`) using **`width`**, **`height`**, and **`t`**.
- **Minimal contract:** Valid custom code is any snippet that, when executed, uses **`painter`**, **`width`**, **`height`**, and **`t`** (and optional `time`) to paint the full frame.

**Other features**

- **iPhone** — Model and color, position and scale as % of the canvas; optional show/hide; **Center phone** snaps to the middle. Need another device frame? Add and integrate it yourself.
- **Screen content** — Load a still or a video into the device screen area.
- **Text layers** — Multiple layers, font, size, color, alignment, shadow/outline; drag on the canvas.
- **Watermarks** — One or more PNGs (transparency supported); drag to position.
- **Export** — Resolution presets, optional duration and FPS for video; behavior ties to loaded video when relevant.

### Requirements

- **Python 3.10+** (use a version that has compatible wheels for PySide6 on your OS).
- **ffmpeg (recommended, optional)** — Used for faster and more compatible `MP4` exports (especially 4K) by piping frames into ffmpeg (macOS uses hardware H.264 when available). If `ffmpeg` is not installed, the app falls back to OpenCV video writing.
  - macOS: `brew install ffmpeg`

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

用于制作类似 App Store 、X、instagram、小红书等等平台宣传物料的桌面工具，生成你需要宣传的workflow和功能，降低成本的同时极大加速你的宣发速度：动态背景、iPhone 外框、屏幕图片或视频、可拖拽的文字与品牌水印，以及多种比例下导出 PNG、JPEG 或 MP4。界面语言可在左侧 **English** / **中文** 之间切换。

### 功能说明

- **输出比例** — 导出前可选择 16:9、9:16、1:1、4:3、4:5、21:9 等预设。
- **背景** — 内置多种动态预设（网格渐变、抽象波浪、极光、霓虹、几何、粒子等），也可用代码完全自定义画面。
- **用代码编辑背景** — 在背景预设列表中选择 **自定义代码**（英文界面下为 **Custom code**）。每帧会执行你的 Python 绘制脚本，与内置背景的渲染方式一致：
  - 脚本中可使用 **`painter`**（`QPainter`）、画布 **`width`** / **`height`**、时间 **`t`**（也可用 **`time`**）驱动动画。
  - 环境内注入常用 **Qt** 类型（`QColor`、`QLinearGradient`、`QRadialGradient`、`QPainterPath`、`QPen`、`QBrush`、`QFont`、`QPointF`、`QRectF`、`Qt` 等）、**`math`**、已安装时的 **`numpy`（`np`）**，以及 **`vortex_offset`**、噪声/类 FBM 等辅助函数和可在脚本顶部覆盖的默认参数（强度、漂移等）。
  - 如果你不会代码，请把内置示例模版、你的画面需求，以及**下文各条**（`exec`、`painter`、`t`、勿依赖 `__main__` 等）一并交给 AI，再把生成代码贴进编辑器——可避免出现只写 `def` 不调用、只用 `cv2.imshow`、`frame_index` 等与 TangiPromo 环境不符的代码。
  - 点击 **应用** 立即编译运行；停止编辑约片刻后也会自动应用（详见界面内提示）。
  - **保存** / **删除** 命名预设：代码会保存在本机应用数据目录下的 JSON 中（Qt 为 TangiPromo 分配的 `AppDataLocation`）。
  - **运行方式：** 每一帧 TangiPromo 会对你的整段脚本做一次 **`exec`**，**不是**执行 `python 某某.py`。只有你写在**同一脚本顶层**、或**自己调用**的函数里的代码才会跑；**仅定义** `def generate_...(): ...` **从不调用**时，背景不会有任何绘制。
  - **输出方式：** 程序**不会读取返回值**。必须在注入的 **`painter`** 上绘制（或拼好 **`QImage` 再 `painter.drawImage`**）。只 **`return` NumPy/OpenCV 图像**、只用 **`cv2.imshow`**、只用 **Matplotlib 弹窗** 都不会成为 TangiPromo 里的背景。
  - **`if __name__ == "__main__":`** 在嵌入执行时 **`__name__` 往往不等于 `"__main__"`**，里面的预览循环通常**根本不会执行**；请把绘制逻辑放在模块顶层，或在顶层**显式调用**你的函数。
  - **时间变量：** 请使用注入的 **`t`**（随时间递增的浮点数，量级接近秒）。环境里没有现成的 **`frame_index` / `total_frames`**；若需要循环相位，请用 **`t`** 自行换算（例如 `sin(t * k)`）。
  - **库：** 安装了 NumPy 时可用 **`np`**。背景**不依赖** OpenCV；若 AI 只给出 `cv2` + `imshow` 脚本，请要求它改为 **`painter` + Qt**（或 **NumPy → `QImage` → `drawImage`**），并明确使用 **`width`、`height`、`t`**。
  - **最低约定：** 合法自定义代码 = 执行后能用 **`painter`、`width`、`height`、`t`**（及可选 **`time`**）画满当前帧的片段。
- **时间轴（画布底部播放器）** — 当存在导入视频或当前背景为动画时，画布底部会显示时间轴：
  - 播放/暂停会同时控制预览时间与导入视频播放。
  - 可拖动定位到任意时间点预览。
  - 支持添加/删除断点并快速跳转。
  - 时间轴长度跟随导出时长；导入视频时默认自动同步为视频长度并对齐到第 0 帧。
- **Effects（右侧效果面板，导出一致）** — 可用 Python 代码对“整帧渲染结果”（背景 + 手机 + 文字 + 水印）做后处理，预览与导出使用同一渲染路径：
  - 适合做推镜、区域放大、时间窗转场等效果。
  - 内置 `zoom_region(x, y, w, h, scale)`（归一化坐标）。
  - 效果代码可直接使用 `t`、`duration`、`breakpoints`。
  - 可开启“画布区域指示器”显示鼠标位置十字线和归一化坐标，便于精确写效果参数。

**其余功能**

- **iPhone** — 机型与颜色、位置与缩放（画布百分比）、显示开关；**一键居中** 将手机置于画布中心。如果你需要其他设备的适配，请自行添加。
- **屏幕内容** — 为屏幕区域加载静态图或视频。
- **文字图层** — 多图层、字体、字号、颜色、对齐、阴影/描边；在画布上拖动摆放。
- **水印** — 支持多张 PNG（建议带透明）；在画布上拖动定位。
- **导出** — 分辨率预设、视频的帧率与时长等；若已加载视频，导出时长等行为与素材相关。

### 环境要求

- **Python 3.10+**（需与当前系统上 PySide6 的预编译包版本兼容）。
- **ffmpeg（建议安装，可选）** — 用于通过管道把帧交给 `ffmpeg` 来导出 `MP4`（速度更快、兼容性更好，尤其是 4K）。未安装时会自动回退到 OpenCV 的编码方式。
  - macOS：`brew install ffmpeg`

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
