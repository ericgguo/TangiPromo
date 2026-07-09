"""
TangiPromo CLI — 命令行接口。

用法:
    python main.py <command> [options]
    tangipromo <command> [options]   # 安装后

命令:
    export-image      导出静态图片（PNG/JPEG）
    export-video      导出 MP4 视频
    save-workflow         保存当前参数为 workflow JSON 文件
    save-workflow-preset  保存到 workflow 预设库（与 GUI 共用）
    list-workflows        列出预设库中的 workflow
    delete-workflow       从预设库删除 workflow
    export-workflow       将预设库中的 workflow 导出为 JSON 文件
    workflow-import       从 JSON 文件导入到预设库
    gui               启动 GUI（等同于不带参数运行 main.py）
    list-backgrounds  列出所有可用背景名称及内部名称
    list-resolutions  列出所有分辨率预设
    list-iphones      列出所有 iPhone 型号及主题 ID
    list-macs         列出电脑模式设备（简约窗口 / MacBook）及主题 ID

示例:
    tangipromo list-backgrounds
    tangipromo list-iphones
    tangipromo export-image --background "极光" --ratio 9:16 \\
        --resolution 1080p --screen /path/to/shot.png out.png
    tangipromo export-image --background "霓虹光效" --ratio 9:16 --no-iphone \\
        --text "我的App" --text-color "#ff7c6bff" --text-size 48 \\
        --resolution 1080x1920 out.png
    tangipromo export-video --workflow my_preset.json --fps 30 --duration 8 out.mp4
    tangipromo export-video --background "星空粒子" --ratio 16:9 --no-iphone \\
        --duration 10 --fps 60 --effect-code fx.py out.mp4
    tangipromo save-workflow --background "霓虹光效" --ratio 9:16 \\
        --name "my_preset" workflow.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional


# ── 分辨率解析 ──────────────────────────────────────────────────────────────

# CLI 短名称 → 分辨率预设 key（宽松匹配）
_RES_ALIASES: dict[str, str] = {
    "1080p":     "1080p (16:9)",
    "2k":        "2K (16:9)",
    "4k":        "4K (16:9)",
    "1080":      "1080×1080",
    "1080x1080": "1080×1080",
}


def _parse_resolution(value: str) -> tuple[int, int]:
    """
    解析分辨率参数。支持：
      - 预设短名称: 1080p / 2k / 4k
      - 分辨率预设全名（与 RESOLUTIONS dict key 一致）
      - WxH 格式: 1920x1080 / 1080x1920
    """
    from .exporter import RESOLUTIONS

    # WxH 格式
    lower = value.lower().strip()
    if "x" in lower and not any(c.isalpha() and c != "x" for c in lower):
        parts = lower.split("x")
        if len(parts) == 2:
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                pass

    # 短名称别名
    key = _RES_ALIASES.get(lower)
    if key and key in RESOLUTIONS:
        w, h = RESOLUTIONS[key]
        if w > 0 and h > 0:
            return w, h

    # 全名精确匹配
    if value in RESOLUTIONS:
        w, h = RESOLUTIONS[value]
        if w > 0 and h > 0:
            return w, h

    # 大小写不敏感模糊匹配
    for k, (w, h) in RESOLUTIONS.items():
        if k.lower() == lower and w > 0 and h > 0:
            return w, h

    available = [k for k, v in RESOLUTIONS.items() if v[0] > 0]
    raise argparse.ArgumentTypeError(
        f"无法识别分辨率 {value!r}。\n"
        f"可用预设: {available}\n"
        f"或使用 WxH 格式，如: 1920x1080"
    )


# ── 公共参数构建 ─────────────────────────────────────────────────────────────

def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """export-image 和 export-video 共用的参数。"""
    parser.add_argument(
        "--workflow",
        metavar="PATH",
        help="加载 workflow JSON 文件（格式与 GUI「保存工作流」一致）",
    )
    parser.add_argument(
        "--workflow-preset",
        metavar="NAME",
        default=None,
        help="从预设库按名称加载 workflow（与 GUI 下拉框同名）",
    )
    parser.add_argument(
        "--workflow-id",
        metavar="UUID",
        default=None,
        help="从预设库按 id 加载 workflow（见 list-workflows --json）",
    )
    parser.add_argument(
        "--background", "-b",
        metavar="NAME",
        help='背景名称，如 "Aurora Flow"、"Neon Glow"、"Custom Code" 等（用 list-backgrounds 查看）',
    )
    parser.add_argument(
        "--bg-params",
        metavar="JSON",
        help='背景额外参数（JSON 格式），如 \'{"speed": 1.5}\'',
    )
    parser.add_argument(
        "--bg-speed",
        type=float,
        default=None,
        metavar="0-200",
        help="背景动画速度百分比（默认 100，即 1×）",
    )
    parser.add_argument(
        "--bg-code",
        metavar="PATH_OR_CODE",
        help="自定义背景代码：.py 文件路径，或直接传入代码字符串",
    )
    parser.add_argument(
        "--ratio", "-r",
        metavar="RATIO",
        default=None,
        help='输出比例，如 16:9 / 9:16 / 1:1 / 4:3 / 4:5 / 21:9',
    )
    parser.add_argument(
        "--device-mode",
        metavar="MODE",
        choices=["phone", "computer", "both"],
        default=None,
        help="设备模式：phone / computer / both（同时显示手机与 Mac）",
    )
    parser.add_argument(
        "--iphone",
        metavar="MODEL",
        default=None,
        help='iPhone 型号（如 "iPhone 17 Pro Max"）；传 none 关闭设备框',
    )
    parser.add_argument(
        "--iphone-theme",
        metavar="THEME",
        default=None,
        help='iPhone 主题 id（如 cosmic_orange / deep_blue / silver 等）',
    )
    parser.add_argument(
        "--iphone-scale",
        type=float,
        default=None,
        metavar="0-100",
        help="设备框缩放百分比（默认 72）",
    )
    parser.add_argument(
        "--iphone-x",
        type=float,
        default=None,
        metavar="0-100",
        help="设备框水平位置百分比（50=居中）",
    )
    parser.add_argument(
        "--iphone-y",
        type=float,
        default=None,
        metavar="0-100",
        help="设备框垂直位置百分比（50=居中）",
    )
    parser.add_argument(
        "--no-iphone",
        action="store_true",
        default=False,
        help="隐藏 iPhone 设备框（手机模式）",
    )
    parser.add_argument(
        "--mac",
        metavar="MODEL",
        default=None,
        help='电脑设备（如 "MacBook Pro 14"、"Window Dark"）；传 none 关闭设备框',
    )
    parser.add_argument(
        "--mac-theme",
        metavar="THEME",
        default=None,
        help='Mac 主题 id（如 default / menu_bar；简约窗口为 default）',
    )
    parser.add_argument(
        "--mac-scale",
        type=float,
        default=None,
        metavar="0-100",
        help="电脑设备框缩放百分比（默认 58）",
    )
    parser.add_argument(
        "--mac-x",
        type=float,
        default=None,
        metavar="0-100",
        help="电脑设备框水平位置百分比（50=居中）",
    )
    parser.add_argument(
        "--mac-y",
        type=float,
        default=None,
        metavar="0-100",
        help="电脑设备框垂直位置百分比（50=居中）",
    )
    parser.add_argument(
        "--no-mac",
        action="store_true",
        default=False,
        help="隐藏电脑设备框（电脑模式）",
    )
    parser.add_argument(
        "--screen", "-s",
        metavar="PATH",
        default=None,
        help="屏幕内容（当前设备模式下的主设备）",
    )
    parser.add_argument(
        "--screen-phone",
        metavar="PATH",
        default=None,
        help="iPhone 屏幕内容：图片或视频",
    )
    parser.add_argument(
        "--screen-mac",
        metavar="PATH",
        default=None,
        help="Mac / 电脑屏幕内容：图片或视频",
    )
    parser.add_argument(
        "--text",
        action="append",
        metavar="TEXT",
        default=None,
        help="文字图层内容（可多次使用，每次一个图层）",
    )
    parser.add_argument(
        "--text-y",
        action="append",
        type=float,
        metavar="0-1",
        default=None,
        help="对应 --text 的 Y 位置（归一化 0-1，可多次使用）",
    )
    parser.add_argument(
        "--watermark", "-w",
        metavar="PATH",
        default=None,
        help="水印图片路径（PNG）",
    )
    parser.add_argument(
        "--watermark-x",
        type=float,
        default=50.0,
        metavar="0-100",
        help="水印水平位置百分比（默认 50）",
    )
    parser.add_argument(
        "--watermark-y",
        type=float,
        default=50.0,
        metavar="0-100",
        help="水印垂直位置百分比（默认 50）",
    )
    parser.add_argument(
        "--watermark-width",
        type=float,
        default=14.0,
        metavar="0-100",
        help="水印宽度百分比（默认 14）",
    )
    parser.add_argument(
        "--effect-code",
        metavar="PATH_OR_CODE",
        default=None,
        help="效果后处理代码：.py 文件路径，或直接传入代码字符串",
    )
    parser.add_argument(
        "--effect-off",
        action="store_true",
        default=False,
        help="禁用效果（即使 workflow 中已启用）",
    )
    parser.add_argument(
        "--region-guide",
        action="store_true",
        default=False,
        help="启用效果区域参考线（effect region_guide，与 GUI 勾选框一致）",
    )
    parser.add_argument(
        "--breakpoints",
        metavar="T1,T2,...",
        default=None,
        help="时间轴断点（秒，逗号分隔，如 2.0,4.5,7.0）",
    )
    parser.add_argument(
        "--text-x",
        action="append",
        type=float,
        metavar="0-1",
        default=None,
        help="对应 --text 的 X 位置（归一化 0-1，默认 0.5 居中，可多次使用）",
    )
    parser.add_argument(
        "--text-font",
        action="append",
        metavar="FAMILY",
        default=None,
        help="对应 --text 的字体名称（可多次使用，如 'Helvetica Neue'）",
    )
    parser.add_argument(
        "--text-size",
        action="append",
        type=int,
        metavar="PT",
        default=None,
        help="对应 --text 的字体大小 pt（可多次使用，默认 36）",
    )
    parser.add_argument(
        "--text-color",
        action="append",
        metavar="#RRGGBB",
        default=None,
        help="对应 --text 的颜色（十六进制，可多次使用，默认 #ffffff）",
    )
    parser.add_argument(
        "--text-bold",
        action="store_true",
        default=False,
        help="所有 --text 图层粗体（若需单图层控制请用 --workflow）",
    )
    parser.add_argument(
        "--text-no-shadow",
        action="store_true",
        default=False,
        help="关闭所有 --text 图层的阴影",
    )
    parser.add_argument(
        "--watermark-color",
        metavar="#AARRGGBB",
        default=None,
        help="水印着色（十六进制 ARGB，如 #ffebebeb；默认白色半透明）",
    )
    parser.add_argument(
        "--resolution", "-R",
        metavar="PRESET_OR_WxH",
        default=None,
        help='导出分辨率：预设名称（1080p/2k/4k）或 WxH（如 1920x1080）；默认沿用 workflow，否则 1080p (16:9)',
    )
    parser.add_argument(
        "--time", "-t",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="渲染时间点（秒），默认 0.0",
    )


# ── 应用 CLI 参数到 session ──────────────────────────────────────────────────

def _apply_args_to_session(session, args: argparse.Namespace) -> tuple[int, int]:
    """
    将命令行参数应用到 PromoSession。
    返回 (width, height)。
    """
    # 1. 先加载 workflow（预设库和/或文件）
    if args.workflow_preset or args.workflow_id or args.workflow:
        from .workflow_cli import load_workflow_sources

        missing = load_workflow_sources(session, args)
        if missing:
            for p in missing:
                print(f"[警告] 文件不存在，已跳过: {p}", file=sys.stderr)

    # 2. 覆盖比例
    if args.ratio:
        session.set_ratio(args.ratio)

    # 3. 覆盖背景
    if args.background:
        bg_params = {}
        if args.bg_params:
            try:
                bg_params = json.loads(args.bg_params)
            except json.JSONDecodeError as e:
                print(f"[错误] --bg-params JSON 解析失败: {e}", file=sys.stderr)
                sys.exit(1)
        # --bg-speed 优先级高于 --bg-params 中的 speed
        if args.bg_speed is not None:
            bg_params["speed"] = args.bg_speed / 100.0
        session.set_background(args.background, **bg_params)

    if args.bg_code:
        code_val = args.bg_code
        if os.path.isfile(code_val):
            code_val = open(code_val, encoding="utf-8").read()
        session.set_background_code(code_val)

    # 4. 设备模式与框
    if args.device_mode:
        session.set_device_mode(args.device_mode)

    if args.no_iphone:
        session.set_iphone(visible=False)
    else:
        iphone_kwargs: dict = {}
        if args.iphone and args.iphone.lower() != "none":
            iphone_kwargs["model"] = args.iphone
        elif args.iphone and args.iphone.lower() == "none":
            session.set_iphone(visible=False)
        if args.iphone_theme:
            iphone_kwargs["theme"] = args.iphone_theme
        if args.iphone_scale is not None:
            iphone_kwargs["scale"] = args.iphone_scale
        if args.iphone_x is not None:
            iphone_kwargs["x"] = args.iphone_x
        if args.iphone_y is not None:
            iphone_kwargs["y"] = args.iphone_y
        if iphone_kwargs:
            session.set_iphone(**iphone_kwargs)

    if args.no_mac:
        session.set_mac(visible=False)
    else:
        mac_kwargs: dict = {}
        if args.mac and args.mac.lower() != "none":
            mac_kwargs["model"] = args.mac
        elif args.mac and args.mac.lower() == "none":
            session.set_mac(visible=False)
        if args.mac_theme:
            mac_kwargs["theme"] = args.mac_theme
        if args.mac_scale is not None:
            mac_kwargs["scale"] = args.mac_scale
        if args.mac_x is not None:
            mac_kwargs["x"] = args.mac_x
        if args.mac_y is not None:
            mac_kwargs["y"] = args.mac_y
        if mac_kwargs:
            session.set_mac(**mac_kwargs)

    # 5. 屏幕内容
    if args.screen_phone:
        session.set_screen(args.screen_phone, target="phone")
    if args.screen_mac:
        session.set_screen(args.screen_mac, target="mac")
    if args.screen:
        session.set_screen(args.screen)

    # 6. 文字图层
    if args.text:
        y_positions = args.text_y or []
        x_positions = args.text_x or []
        fonts = args.text_font or []
        sizes = args.text_size or []
        colors = args.text_color or []
        layers = []
        for i, text in enumerate(args.text):
            y = y_positions[i] if i < len(y_positions) else max(0.1, 0.85 - i * 0.08)
            x = x_positions[i] if i < len(x_positions) else 0.5
            d: dict = {"text": text, "x": x, "y": y}
            if i < len(fonts):
                d["font_family"] = fonts[i]
            if i < len(sizes):
                d["font_size_pt"] = sizes[i]
            if i < len(colors):
                d["color"] = colors[i]
            if args.text_bold:
                d["bold"] = True
            if args.text_no_shadow:
                d["shadow"] = False
            layers.append(d)
        session.set_text_layers(layers)

    # 7. 水印
    if args.watermark:
        wm_kwargs: dict = {
            "enabled": True,
            "center_x_pct": args.watermark_x,
            "center_y_pct": args.watermark_y,
            "width_pct": args.watermark_width,
        }
        if args.watermark_color:
            wm_kwargs["color"] = args.watermark_color
        session.add_watermark(args.watermark, **wm_kwargs)

    # 8. 效果代码
    if args.effect_code:
        code_val = args.effect_code
        if os.path.isfile(code_val):
            code_val = open(code_val, encoding="utf-8").read()
        session.set_effect(code_val, enabled=True)

    if args.effect_off:
        session.clear_effect()

    # 9. region_guide 和 breakpoints
    if args.region_guide:
        session.canvas.region_guide_enabled = True

    if args.breakpoints:
        try:
            bps = [float(x.strip()) for x in args.breakpoints.split(",") if x.strip()]
            session.set_timeline(session._export_duration, breakpoints=bps)
        except ValueError as e:
            print(f"[错误] --breakpoints 格式错误: {e}", file=sys.stderr)
            sys.exit(1)

    # 10. 解析分辨率（优先级：CLI 显式 > workflow 中的 resolution_key > 默认 1080p）
    res_arg = args.resolution
    if not res_arg and session._resolution_key:
        res_arg = session._resolution_key
    if not res_arg:
        res_arg = "1080p (16:9)"
    w, h = _parse_resolution(res_arg)
    return w, h


# ── 初始化 headless QApplication ─────────────────────────────────────────────

def _init_headless_app() -> None:
    """初始化 offscreen Qt 应用（不显示任何窗口）。"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    if QApplication.instance() is None:
        QApplication(sys.argv[:1])


# ── 子命令处理函数 ───────────────────────────────────────────────────────────

def cmd_list_backgrounds(_args: argparse.Namespace) -> int:
    _init_headless_app()
    from .backgrounds import ALL_BACKGROUNDS
    print("可用背景:")
    for cls in ALL_BACKGROUNDS:
        inst = cls()
        print(f"  {inst.name}")
    return 0


def cmd_list_resolutions(_args: argparse.Namespace) -> int:
    from .exporter import RESOLUTIONS
    print("可用分辨率预设:")
    for key, (w, h) in RESOLUTIONS.items():
        if w > 0 and h > 0:
            print(f"  {key!r:<28} {w}x{h}")
    print("\n也可使用 WxH 格式，如: --resolution 1920x1080")
    return 0


def cmd_list_iphones(_args: argparse.Namespace) -> int:
    from .iphone_manifest import DEVICE_PNG
    print("可用 iPhone 型号与主题:")
    for model, themes in DEVICE_PNG.items():
        theme_ids = "  |  ".join(themes.keys())
        print(f"\n  --iphone \"{model}\"")
        print(f"    主题(--iphone-theme): {theme_ids}")
    return 0


def cmd_list_macs(_args: argparse.Namespace) -> int:
    from .mac_manifest import DEVICE_PNG, MINIMAL_MODELS, MODEL_ORDER

    print("可用电脑模式设备:")
    for model in MODEL_ORDER:
        if model in MINIMAL_MODELS:
            print(f'\n  --mac "{model}"')
            print("    简约窗口（红黄绿交通灯，程序绘制）")
            continue
        themes = DEVICE_PNG.get(model, {})
        theme_ids = "  |  ".join(themes.keys())
        print(f'\n  --mac "{model}"')
        print(f"    主题(--mac-theme): {theme_ids}")
    return 0


def cmd_list_workflows(args: argparse.Namespace) -> int:
    _init_headless_app()
    from .workflow_cli import get_workflow_store, preset_to_jsonable
    from .workflow_preset_store import workflow_presets_path

    store = get_workflow_store()
    path = workflow_presets_path()
    if args.json:
        data = {
            "path": str(path),
            "presets": [preset_to_jsonable(p) for p in store.presets],
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print(f"Workflow 预设库: {path}")
    if not store.presets:
        print("  (空)")
        return 0
    for p in store.presets:
        print(f"  {p.name!r}  id={p.id}")
    return 0


def cmd_save_workflow_preset(args: argparse.Namespace) -> int:
    _init_headless_app()
    from .session import PromoSession
    from .workflow_cli import get_workflow_store
    from .workflow_preset_store import workflow_presets_path

    session = PromoSession()
    try:
        _apply_args_to_session(session, args)
    except (ValueError, FileNotFoundError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    name = (args.name or "cli_workflow").strip()
    if not name:
        print("[错误] 需要 --name", file=sys.stderr)
        return 1

    store = get_workflow_store()
    preset_id = args.preset_id.strip() if getattr(args, "preset_id", None) else None
    pr = store.upsert(name, session.collect_payload(), preset_id=preset_id)
    print(json.dumps({"ok": True, "id": pr.id, "name": pr.name, "path": str(workflow_presets_path())}))
    return 0


def cmd_delete_workflow(args: argparse.Namespace) -> int:
    _init_headless_app()
    from .workflow_cli import get_workflow_store, resolve_preset

    store = get_workflow_store()
    try:
        pr = resolve_preset(store, name=args.name, preset_id=args.preset_id)
    except ValueError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    if not store.delete(pr.id):
        print(f"[错误] 删除失败: {pr.id}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "deleted": pr.name, "id": pr.id}))
    return 0


def cmd_export_workflow(args: argparse.Namespace) -> int:
    _init_headless_app()
    from .workflow_cli import get_workflow_store, resolve_preset

    store = get_workflow_store()
    try:
        pr = resolve_preset(store, name=args.name, preset_id=args.preset_id)
    except ValueError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    out = args.output
    data = {"version": 1, "presets": [pr.to_dict()]}
    Path(out).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "name": pr.name, "id": pr.id, "output": out}))
    return 0


def cmd_workflow_import(args: argparse.Namespace) -> int:
    _init_headless_app()
    from .workflow_cli import get_workflow_store, payload_from_workflow_file
    from .workflow_preset_store import workflow_presets_path

    name = args.name.strip()
    if not name:
        print("[错误] 需要 --name", file=sys.stderr)
        return 1
    try:
        payload = payload_from_workflow_file(args.input)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    store = get_workflow_store()
    preset_id = args.preset_id.strip() if args.preset_id else None
    pr = store.upsert(name, payload, preset_id=preset_id)
    print(json.dumps({"ok": True, "id": pr.id, "name": pr.name, "path": str(workflow_presets_path())}))
    return 0


def cmd_save_workflow(args: argparse.Namespace) -> int:
    _init_headless_app()
    from .session import PromoSession

    session = PromoSession()

    # save-workflow 重用 export-image 的所有共用参数
    try:
        _apply_args_to_session(session, args)
    except (ValueError, FileNotFoundError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    name = args.name or "cli_workflow"
    out = args.output
    session.save_workflow(out, name=name)
    print(f"已保存 workflow: {out}  (name={name!r})")
    return 0


def cmd_export_image(args: argparse.Namespace) -> int:
    _init_headless_app()
    from .session import PromoSession

    session = PromoSession()

    try:
        w, h = _apply_args_to_session(session, args)
    except (ValueError, FileNotFoundError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    out = args.output
    t = args.time

    # 根据比例调整分辨率
    rw, rh = session.canvas.output_ratio
    h_new = h
    w_new = int(round(h_new * rw / rh))
    w_final, h_final = max(1, w_new), max(1, h_new)
    # 偶数维度（H.264 兼容）
    w_final = w_final if w_final % 2 == 0 else w_final + 1
    h_final = h_final if h_final % 2 == 0 else h_final + 1

    print(f"导出图片: {out}  ({w_final}x{h_final}, t={t:.2f}s)")
    try:
        session.export_image(out, w_final, h_final, t=t)
        print(f"完成: {out}")
        return 0
    except Exception as e:
        print(f"[错误] 导出失败: {e}", file=sys.stderr)
        return 1


def cmd_export_video(args: argparse.Namespace) -> int:
    _init_headless_app()
    from .session import PromoSession

    session = PromoSession()

    try:
        w, h = _apply_args_to_session(session, args)
    except (ValueError, FileNotFoundError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    fps = args.fps
    duration = args.duration if args.duration is not None else session._export_duration
    out = args.output

    # 调整分辨率以匹配比例
    rw, rh = session.canvas.output_ratio
    h_new = h
    w_new = int(round(h_new * rw / rh))
    w_final, h_final = max(1, w_new), max(1, h_new)
    w_final = w_final if w_final % 2 == 0 else w_final + 1
    h_final = h_final if h_final % 2 == 0 else h_final + 1

    print(f"导出视频: {out}  ({w_final}x{h_final}, {fps}fps, {duration:.1f}s)")

    last_pct = [-1]

    def on_progress(pct: int) -> None:
        if pct != last_pct[0]:
            last_pct[0] = pct
            bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
            print(f"\r  [{bar}] {pct:3d}%", end="", flush=True)

    # --full-import-video 优先；否则沿用 workflow 里的值（session._full_import_video）
    full_import = getattr(args, "full_import_video", False) or session._full_import_video

    try:
        session.export_video(
            out,
            w_final,
            h_final,
            fps=fps,
            duration=duration,
            ensure_full_import_video=full_import,
            on_progress=on_progress,
        )
        print(f"\n完成: {out}")
        return 0
    except Exception as e:
        print(f"\n[错误] 导出失败: {e}", file=sys.stderr)
        return 1


def cmd_gui(_args: argparse.Namespace) -> int:
    """启动 GUI（等同于不带子命令运行 main.py）。"""
    # 直接用 sys.argv 覆写为无参数，再调用 main 的 run_gui
    import importlib
    main_mod = importlib.import_module("main")
    main_mod.run_gui()
    return 0


# ── 主入口 ───────────────────────────────────────────────────────────────────

def run_cli() -> None:
    """CLI 主入口，由 main.py 调用。"""
    parser = argparse.ArgumentParser(
        prog="tangipromo",
        description="TangiPromo — 宣发素材生成器命令行接口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # --- list-backgrounds ---
    subparsers.add_parser(
        "list-backgrounds",
        help="列出所有可用背景名称",
    )

    # --- list-resolutions ---
    subparsers.add_parser(
        "list-resolutions",
        help="列出所有分辨率预设",
    )

    # --- list-iphones ---
    subparsers.add_parser(
        "list-iphones",
        help="列出所有 iPhone 型号及对应主题 ID",
    )

    # --- list-macs ---
    subparsers.add_parser(
        "list-macs",
        help="列出电脑模式设备（简约窗口 / MacBook）及主题 ID",
    )

    # --- list-workflows ---
    p_lw = subparsers.add_parser(
        "list-workflows",
        help="列出 workflow 预设库（与 GUI 共用）",
    )
    p_lw.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON（含 id，供 --workflow-id 使用）",
    )

    # --- save-workflow-preset ---
    p_swp = subparsers.add_parser(
        "save-workflow-preset",
        help="将当前 CLI 参数保存到 workflow 预设库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(p_swp)
    p_swp.add_argument(
        "--name", "-n",
        required=True,
        metavar="NAME",
        help="预设名称（与 GUI 中显示一致）",
    )
    p_swp.add_argument(
        "--preset-id",
        default=None,
        metavar="UUID",
        help="更新已有预设的 id（省略则新建或按名称覆盖同名项需先 delete）",
    )

    # --- delete-workflow ---
    p_dw = subparsers.add_parser("delete-workflow", help="从预设库删除 workflow")
    g_dw = p_dw.add_mutually_exclusive_group(required=True)
    g_dw.add_argument("--name", "-n", metavar="NAME", help="预设名称")
    g_dw.add_argument("--preset-id", metavar="UUID", help="预设 id")

    # --- export-workflow ---
    p_ew = subparsers.add_parser(
        "export-workflow",
        help="将预设库中的 workflow 导出为 JSON 文件",
    )
    g_ew = p_ew.add_mutually_exclusive_group(required=True)
    g_ew.add_argument("--name", "-n", metavar="NAME", help="预设名称")
    g_ew.add_argument("--preset-id", metavar="UUID", help="预设 id")
    p_ew.add_argument(
        "output",
        metavar="OUTPUT.json",
        help="输出 JSON 路径",
    )

    # --- workflow-import ---
    p_wi = subparsers.add_parser(
        "workflow-import",
        help="从 workflow JSON 文件导入到预设库",
    )
    p_wi.add_argument("input", metavar="INPUT.json", help="workflow JSON 文件")
    p_wi.add_argument("--name", "-n", required=True, metavar="NAME", help="写入预设库的名称")
    p_wi.add_argument(
        "--preset-id",
        default=None,
        metavar="UUID",
        help="更新已有预设的 id",
    )

    # --- save-workflow ---
    p_sw = subparsers.add_parser(
        "save-workflow",
        help="将当前参数组合保存为 workflow JSON 文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(p_sw)
    p_sw.add_argument(
        "--name", "-n",
        default="cli_workflow",
        metavar="NAME",
        help="写入 JSON 内的预设名称（默认 cli_workflow）",
    )
    p_sw.add_argument(
        "output",
        metavar="OUTPUT.json",
        help="输出 JSON 文件路径",
    )

    # --- export-image ---
    p_img = subparsers.add_parser(
        "export-image",
        help="导出静态图片（PNG/JPEG）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(p_img)
    p_img.add_argument(
        "--quality",
        type=int,
        default=95,
        metavar="1-100",
        help="JPEG 质量（仅对 .jpg/.jpeg 有效，默认 95）",
    )
    p_img.add_argument(
        "output",
        metavar="OUTPUT",
        help="输出文件路径（.png 或 .jpg）",
    )

    # --- export-video ---
    p_vid = subparsers.add_parser(
        "export-video",
        help="导出 MP4 视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(p_vid)
    p_vid.add_argument(
        "--fps",
        type=float,
        default=30.0,
        metavar="FPS",
        help="帧率（默认 30）",
    )
    p_vid.add_argument(
        "--duration",
        type=float,
        default=None,
        metavar="SECONDS",
        help="视频时长（秒），默认与 workflow 一致或 10s",
    )
    p_vid.add_argument(
        "--full-import-video",
        action="store_true",
        default=False,
        dest="full_import_video",
        help="时长自动延长至完整覆盖导入视频（等同 GUI「完整包含导入视频」勾选框）",
    )
    p_vid.add_argument(
        "output",
        metavar="OUTPUT",
        help="输出文件路径（.mp4）",
    )

    # --- gui ---
    subparsers.add_parser(
        "gui",
        help="启动 GUI（等同于不带参数运行 main.py）",
    )

    args = parser.parse_args(sys.argv[1:])

    dispatch = {
        "list-backgrounds": cmd_list_backgrounds,
        "list-resolutions": cmd_list_resolutions,
        "list-iphones": cmd_list_iphones,
        "list-macs": cmd_list_macs,
        "list-workflows": cmd_list_workflows,
        "save-workflow": cmd_save_workflow,
        "save-workflow-preset": cmd_save_workflow_preset,
        "delete-workflow": cmd_delete_workflow,
        "export-workflow": cmd_export_workflow,
        "workflow-import": cmd_workflow_import,
        "export-image": cmd_export_image,
        "export-video": cmd_export_video,
        "gui": cmd_gui,
    }

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    sys.exit(handler(args))
