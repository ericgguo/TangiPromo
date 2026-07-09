#!/usr/bin/env python3
"""从 jamesjingyi/mockup-device-frames 下载设备框 PNG。"""
from __future__ import annotations

import argparse
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = (
    "https://raw.githubusercontent.com/jamesjingyi/mockup-device-frames/main/Exports"
)

IOS_FILES: list[str] = []  # iOS 按目录批量，见下方
MAC_FILES = [
    "MacBook Pro 14.png",
    "MacBook Pro 14 - Menu Bar.png",
    "MacBook Pro 16.png",
    "MacBook Pro 16 - Menu Bar.png",
    "MacBook Air 13.png",
    "MacBook Air 13 - Menu Bar.png",
    "MacBook Air 15.png",
    "MacBook Air 15 - Menu Bar.png",
]


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 0:
        print(f"  skip {dest.relative_to(ROOT)}")
        return
    print(f"  get  {dest.relative_to(ROOT)}")
    urllib.request.urlretrieve(url, dest)


def fetch_mac() -> None:
    out = ROOT / "assets" / "mac" / "third_party" / "Exports" / "MacBook"
    for name in MAC_FILES:
        url = f"{BASE_URL}/MacBook/{urllib.parse.quote(name)}"
        _download(url, out / name)


def fetch_ios_manifest_paths() -> None:
    """仅下载 iphone_manifest 中列出的 PNG（若本地缺失）。"""
    sys.path.insert(0, str(ROOT))
    from src.iphone_manifest import DEVICE_PNG

    out = ROOT / "assets" / "iphone" / "third_party" / "Exports" / "iOS"
    for _model, themes in DEVICE_PNG.items():
        for rel in themes.values():
            dest = out / rel
            if dest.is_file() and dest.stat().st_size > 0:
                continue
            parts = rel.split("/")
            url = f"{BASE_URL}/iOS/{'/'.join(urllib.parse.quote(p) for p in parts)}"
            _download(url, dest)


def main() -> int:
    parser = argparse.ArgumentParser(description="下载 mockup-device-frames PNG 资源")
    parser.add_argument("--ios", action="store_true", help="补全 iPhone PNG")
    parser.add_argument("--mac", action="store_true", help="下载 MacBook PNG")
    parser.add_argument("--all", action="store_true", help="iOS + MacBook")
    args = parser.parse_args()
    if not (args.ios or args.mac or args.all):
        args.mac = True

    if args.all or args.ios:
        print("iOS …")
        fetch_ios_manifest_paths()
    if args.all or args.mac:
        print("MacBook …")
        fetch_mac()
    print("完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
