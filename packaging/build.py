"""Build the standalone GUI with PyInstaller (run on the target OS; CI does this per OS).

    pip install -e ".[gui]" pyinstaller
    python packaging/build.py [--smoke]

Output: dist/adi2hamlog.app (macOS) or dist/adi2hamlog/ (Windows, Linux).
--smoke starts the built app headless for a few seconds and fails if it exits early.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def build() -> None:
    subprocess.check_call(
        [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--name", "adi2hamlog",
            "--paths", str(ROOT / "src"),
            "--add-data", f"{ROOT / 'src' / 'adi2hamlog' / 'data'}{os.pathsep}adi2hamlog/data",
            "--distpath", str(DIST), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build"),
            str(ROOT / "packaging" / "gui_launcher.py"),
        ],
        cwd=ROOT,
    )


def executable() -> Path:
    if sys.platform == "darwin":
        return DIST / "adi2hamlog.app" / "Contents" / "MacOS" / "adi2hamlog"
    exe = "adi2hamlog.exe" if sys.platform == "win32" else "adi2hamlog"
    return DIST / "adi2hamlog" / exe


def smoke(seconds: float = 8) -> None:
    exe = executable()
    if not exe.exists():
        sys.exit(f"smoke: {exe} not found")
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    proc = subprocess.Popen([str(exe)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(seconds)
    if proc.poll() is not None:
        out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
        sys.exit(f"smoke: app exited early with code {proc.returncode}\n{out}")
    proc.terminate()
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("smoke: app started and kept running")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    shutil.rmtree(DIST, ignore_errors=True)
    build()
    if args.smoke:
        smoke()
