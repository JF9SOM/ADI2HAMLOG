"""Regenerate packaging/icon/{icon.png,icon.icns,icon.ico}.

    pip install -e ".[gui]"   # PySide6 draws the icon; .icns needs macOS (iconutil)
    python packaging/make_icon.py
"""

from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontMetrics, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
)

OUT = Path(__file__).resolve().parent / "icon"
app = QGuiApplication(sys.argv)


def draw_icon() -> QImage:
    N = 1024
    img = QImage(N, N, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)

    # rounded-square background (macOS icon grid: ~824px square centered)
    m = 100
    rect = QRectF(m, m, N - 2 * m, N - 2 * m)
    g = QLinearGradient(0, rect.top(), 0, rect.bottom())
    g.setColorAt(0, QColor("#2b6cb0"))
    g.setColorAt(1, QColor("#1a365d"))
    path = QPainterPath()
    path.addRoundedRect(rect, 185, 185)
    p.fillPath(path, QBrush(g))

    # radio waves centered at the top
    p.setPen(QPen(QColor("#ffffff"), 30, Qt.SolidLine, Qt.RoundCap))
    cx, cy = N / 2, 400
    for i, r in enumerate((60, 125, 190)):
        p.setOpacity(1.0 - i * 0.25)
        p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 40 * 16, 100 * 16)
    p.setOpacity(1.0)
    p.setBrush(QColor("#ffffff"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx, cy), 32, 32)

    def fit(text, color, top, h, size, maxw):
        f = QFont("Helvetica Neue", size, QFont.Bold)
        while QFontMetrics(f).horizontalAdvance(text) > maxw:
            size -= 4
            f = QFont("Helvetica Neue", size, QFont.Bold)
        p.setFont(f)
        p.setPen(QColor(color))
        p.drawText(QRectF(m, top, N - 2 * m, h), Qt.AlignCenter, text)

    fit("ADI", "#ffffff", 540, 190, 190, 560)
    fit("→ HAMLOG", "#90cdf4", 735, 110, 100, 600)
    p.end()
    return img


def png_bytes(img: QImage, size: int) -> bytes:
    scaled = img.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    scaled.save(buf, "PNG")
    return bytes(ba)


def write_ico(img: QImage, path: Path) -> None:
    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [png_bytes(img, s) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for s, data in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    path.write_bytes(header + entries + b"".join(images))


def write_icns(img: QImage, path: Path) -> None:
    if sys.platform != "darwin":
        print("skip .icns (needs macOS iconutil)")
        return
    with tempfile.TemporaryDirectory() as t:
        iconset = Path(t) / "icon.iconset"
        iconset.mkdir()
        for base in (16, 32, 128, 256, 512):
            (iconset / f"icon_{base}x{base}.png").write_bytes(png_bytes(img, base))
            (iconset / f"icon_{base}x{base}@2x.png").write_bytes(png_bytes(img, base * 2))
        subprocess.check_call(["iconutil", "-c", "icns", str(iconset), "-o", str(path)])


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    image = draw_icon()
    (OUT / "icon.png").write_bytes(png_bytes(image, 1024))
    write_ico(image, OUT / "icon.ico")
    write_icns(image, OUT / "icon.icns")
    print("wrote", ", ".join(sorted(p.name for p in OUT.iterdir())))
