"""裁剪 build/ 与 bin/ 下的可重生成产物，降低本地编译占用。

只删除“下次构建可自动重建”的东西，绝不碰成品静态库：
  - 默认档：vcpkg 的 buildtrees/downloads、OpenCV 的中间构建目录与源码压缩包
  - --opencv-source：OpenCV 解压后的源码树（重编 OpenCV 时会自动重新下载）
  - --bin：bin/ 下的打包产物（build.py 会重新 install）
  - --tests：各构建树下的 tests 目录（配合 build.py --no-tests 使用）
  - --vcpkg-ports：vcpkg 的 ports/versions（删除后无法离线再装包）

保留：build/_deps/opencv/install、build/_deps/vcpkg/installed、BlackBone 产物、
build/vs20xx-* 构建树（删了等于全量重编）。

用法：
  python scripts/prune_build.py --dry-run
  python scripts/prune_build.py
  python scripts/prune_build.py --opencv-source --bin
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = REPO_ROOT / "build"
DEPS_DIR = BUILD_DIR / "_deps"
BIN_DIR = REPO_ROOT / "bin"
OPENCV_DIR = DEPS_DIR / "opencv"


def dir_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total


def ensure_inside(target: Path, *allowed_roots: Path) -> Path:
    """把 target 归一成绝对路径，并确认它落在允许删除的根目录内。"""
    resolved = Path(os.path.realpath(target))
    for root in allowed_roots:
        root_resolved = Path(os.path.realpath(root))
        if resolved == root_resolved or root_resolved in resolved.parents:
            return resolved
    raise SystemExit(
        f"[ERROR] refusing to delete {resolved}: outside {', '.join(str(r) for r in allowed_roots)}"
    )


def collect_default_targets() -> list[Path]:
    targets = [
        DEPS_DIR / "vcpkg" / "buildtrees",
        DEPS_DIR / "vcpkg" / "downloads",
        OPENCV_DIR / "build",
    ]
    targets.extend(sorted(OPENCV_DIR.glob("opencv-*.zip")))
    return targets


def collect_opencv_source_targets() -> list[Path]:
    return [p for p in sorted(OPENCV_DIR.glob("opencv-*")) if p.is_dir() and not p.name.endswith(".zip")]


def collect_tests_targets() -> list[Path]:
    return [p for p in sorted(BUILD_DIR.glob("*/tests")) if p.is_dir()]


def collect_vcpkg_ports_targets() -> list[Path]:
    return [
        DEPS_DIR / "vcpkg" / "ports",
        DEPS_DIR / "vcpkg" / "versions",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune regenerable build artifacts")
    parser.add_argument("--dry-run", action="store_true", help="Report only, delete nothing")
    parser.add_argument("--opencv-source", action="store_true", help="Also delete the extracted OpenCV source tree")
    parser.add_argument("--bin", action="store_true", help="Also delete bin/ packaging output")
    parser.add_argument("--vcpkg-ports", action="store_true", help="Also delete vcpkg ports/versions")
    parser.add_argument(
        "--tests",
        action="store_true",
        help="Delete build/*/tests trees (rebuilt by build.py without --no-tests)",
    )
    args = parser.parse_args()

    targets: list[Path] = collect_default_targets()
    allowed_roots = [DEPS_DIR]
    if args.opencv_source:
        targets.extend(collect_opencv_source_targets())
    if args.vcpkg_ports:
        targets.extend(collect_vcpkg_ports_targets())
    if args.tests:
        allowed_roots.append(BUILD_DIR)
        targets.extend(collect_tests_targets())
    if args.bin:
        allowed_roots.append(BIN_DIR)
        targets.append(BIN_DIR)

    existing: list[tuple[Path, int]] = []
    for target in targets:
        if not target.exists():
            continue
        existing.append((ensure_inside(target, *allowed_roots), dir_size(target)))

    if not existing:
        print("[INFO] Nothing to prune (already clean)")
        return 0

    total = 0
    for path, size in existing:
        total += size
        print(f"[{'DRY' if args.dry_run else 'DEL'}] {size / 1048576:9.1f} MB  {path}")

    if args.dry_run:
        print(f"[INFO] Would reclaim {total / 1073741824:.2f} GiB (dry run)")
        return 0

    for path, _size in existing:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    remaining = dir_size(BUILD_DIR)
    print(f"[INFO] Reclaimed {total / 1073741824:.2f} GiB")
    print(f"[INFO] build/ is now {remaining / 1048576:.0f} MB")
    print("[INFO] Static libs kept: build/_deps/opencv/install, build/_deps/vcpkg/installed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
