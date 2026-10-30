#!/usr/bin/env python
"""Build a publishable source archive of the OP plugin.

The archive contains every git-tracked file plus untracked-but-not-ignored
files (so local work in progress is included), skips build outputs, and adds
a MANIFEST.txt with version, base commit and per-file SHA256.

Usage:
    python scripts/make_source_package.py                # dist/op-<ver>-src.zip
    python scripts/make_source_package.py --dry-run      # report only
    python scripts/make_source_package.py --format both   # zip + tar.gz
    python scripts/make_source_package.py --deterministic # fixed timestamps
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_HEADER = REPO_ROOT / "libop" / "base" / "AutomationModes.h"
SKIP_DIRS = {".git", "build", "bin", "dist", "__pycache__", ".vs", ".idea"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".obj", ".lib", ".pdb", ".ilk", ".exp"}
EXEC_SUFFIXES = {".sh", ".bash", ".command"}


def git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, check=False
    )
    if out.returncode != 0:
        raise SystemExit(
            "git %s failed: %s" % (" ".join(args), out.stderr.decode("utf-8", "replace").strip())
        )
    return out.stdout.decode("utf-8", "replace")


def read_version() -> str:
    text = VERSION_HEADER.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"#define\s+OP_VERSION\s+MAKE_OP_VERSION\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", text)
    if not m:
        raise SystemExit("cannot parse OP_VERSION from %s" % VERSION_HEADER)
    return ".".join(m.groups())


def is_skipped(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in SKIP_DIRS for p in parts[:-1]):
        return True
    if parts[0] in SKIP_DIRS:
        return True
    return Path(rel).suffix.lower() in SKIP_SUFFIXES


def collect_files(include_untracked: bool) -> list[str]:
    names = [n for n in git("ls-files", "-z").split("\0") if n]
    if include_untracked:
        names += [n for n in git("ls-files", "--others", "--exclude-standard", "-z").split("\0") if n]
    files = sorted({n for n in names if not is_skipped(n) and (REPO_ROOT / n).is_file()})
    return files


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(version: str, commit: str, dirty: list[str], files: list[str]) -> bytes:
    lines = [
        "OP plugin - source package",
        "=========================",
        "",
        "version      : %s" % version,
        "base commit  : %s" % commit,
        "packaged at  : %s" % time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "build host   : %s" % sys.platform,
        "file count   : %d" % len(files),
        "",
        "Build",
        "-----",
        "  Windows + VS2022 (MSVC v143) only.",
        "  python build.py            # x64 Release, bootstraps vcpkg + BlackBone + OpenCV",
        "  python build.py -a x86     # x86 Release (must bootstrap deps for x86 as well)",
        "  python build.py --no-tests # skip GoogleTest targets",
        "  Output: build/vs2022-<arch>-Release/libop/Release/op_<arch>.dll, bin/<arch>/",
        "  See README.md, README_EN.md and CLAUDE.md for details.",
        "",
        "Uncommitted changes included in this package",
        "-------------------------------------------",
    ]
    lines += ["  %s" % p for p in dirty] or ["  (none)"]
    lines += ["", "Files (sha256  size  path)", "--------------------------"]
    for rel in files:
        p = REPO_ROOT / rel
        lines.append("%s  %9d  %s" % (sha256_of(p), p.stat().st_size, rel))
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def write_zip(target: Path, root: str, files: list[str], manifest: bytes, deterministic: bool) -> int:
    fixed = (1980, 1, 1, 0, 0, 0)
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in files:
            src = REPO_ROOT / rel
            arc = "%s/%s" % (root, rel)
            if deterministic:
                info = zipfile.ZipInfo(arc, date_time=fixed)
            else:
                mtime = time.localtime(src.stat().st_mtime)[:6]
                info = zipfile.ZipInfo(arc, date_time=mtime)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if src.suffix.lower() in EXEC_SUFFIXES else 0o100644) << 16
            zf.writestr(info, src.read_bytes())
            count += 1
        info = zipfile.ZipInfo("%s/MANIFEST.txt" % root, date_time=fixed if deterministic else time.localtime()[:6])
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        zf.writestr(info, manifest)
        count += 1
    return count


def write_targz(target: Path, root: str, files: list[str], manifest: bytes, deterministic: bool) -> int:
    count = 0

    def add(tf: tarfile.TarFile, arc: str, data: bytes, mode: int, mtime: float) -> None:
        ti = tarfile.TarInfo(arc)
        ti.size = len(data)
        ti.mode = mode
        ti.mtime = 1 if deterministic else int(mtime)
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = ""
        tf.addfile(ti, io.BytesIO(data))

    with tarfile.open(target, "w:gz", format=tarfile.PAX_FORMAT) as tf:
        for rel in files:
            src = REPO_ROOT / rel
            mode = 0o755 if src.suffix.lower() in EXEC_SUFFIXES else 0o644
            add(tf, "%s/%s" % (root, rel), src.read_bytes(), mode, src.stat().st_mtime)
            count += 1
        add(tf, "%s/MANIFEST.txt" % root, manifest, 0o644, time.time())
        count += 1
    return count


def verify_zip(path: Path, expected: dict[str, str]) -> tuple[int, list[str]]:
    problems: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        for name in names:
            rel = name.split("/", 1)[1] if "/" in name else name
            want = expected.get(rel)
            if want is None:
                continue
            got = hashlib.sha256(zf.read(name)).hexdigest()
            if got != want:
                problems.append("hash mismatch: %s" % rel)
    return len(names), problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a publishable source archive of the OP plugin.")
    ap.add_argument("-o", "--output-dir", default="dist", help="output directory (default: dist)")
    ap.add_argument("--version", default=None, help="override version read from libop/base/AutomationModes.h")
    ap.add_argument("--format", choices=["zip", "tar.gz", "both"], default="zip")
    ap.add_argument("--no-untracked", action="store_true", help="include only git-tracked files")
    ap.add_argument("--deterministic", action="store_true", help="fixed timestamps for reproducible archives")
    ap.add_argument("--dry-run", action="store_true", help="list what would be packaged, write nothing")
    args = ap.parse_args()

    version = args.version or read_version()
    root = "op-%s-src" % version
    files = collect_files(include_untracked=not args.no_untracked)
    if not files:
        raise SystemExit("no files to package")

    commit = git("rev-parse", "--short", "HEAD").strip()
    dirty = sorted(l.split("\t", 1)[-1] for l in git("status", "--porcelain").splitlines() if l.strip())
    total = sum((REPO_ROOT / f).stat().st_size for f in files)

    print("OP source package")
    print("  version     : %s" % version)
    print("  root folder : %s/" % root)
    print("  base commit : %s (%d file(s) with uncommitted changes)" % (commit, len(dirty)))
    print("  files       : %d, %.2f MiB uncompressed" % (len(files), total / 1048576.0))
    if args.dry_run:
        for rel in files:
            print("    %s" % rel)
        print("dry run: nothing written")
        return 0

    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(version, commit, dirty, files)
    expected = {}
    for rel in files:
        expected[rel] = sha256_of(REPO_ROOT / rel)

    written: list[Path] = []
    if args.format in ("zip", "both"):
        target = out_dir / ("%s.zip" % root)
        write_zip(target, root, files, manifest, args.deterministic)
        entries, problems = verify_zip(target, expected)
        if problems:
            raise SystemExit("verification failed:\n  " + "\n  ".join(problems))
        print("  wrote       : %s (%d entries, %.2f MiB)" % (target, entries, target.stat().st_size / 1048576.0))
        written.append(target)
    if args.format in ("tar.gz", "both"):
        target = out_dir / ("%s.tar.gz" % root)
        n = write_targz(target, root, files, manifest, args.deterministic)
        print("  wrote       : %s (%d entries, %.2f MiB)" % (target, n, target.stat().st_size / 1048576.0))
        written.append(target)

    for target in written:
        digest = sha256_of(target)
        shafile = target.with_name(target.name + ".sha256")
        shafile.write_text("%s  %s\n" % (digest, target.name), encoding="utf-8", newline="\n")
        print("  sha256      : %s  (%s)" % (digest, shafile.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
