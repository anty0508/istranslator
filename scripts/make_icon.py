import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QBuffer, QByteArray, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication

SIZES = [16, 24, 32, 48, 64, 128, 256]


def render_png(size):
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    margin = size * 0.0625
    radius = size * 0.22
    p.setBrush(QColor(52, 120, 246))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(
        round(margin), round(margin),
        round(size - 2 * margin), round(size - 2 * margin),
        radius, radius,
    )

    font = QFont("Segoe UI", 1)
    font.setPixelSize(round(size * 0.42))
    font.setWeight(QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QColor(255, 255, 255))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "文A")
    p.end()

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    pix.save(buf, "PNG")
    buf.close()
    return bytes(ba.data())


def build_ico(path):
    images = [(s, render_png(s)) for s in SIZES]
    count = len(images)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + count * 16
    entries = b""
    blobs = b""
    for size, png in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
        blobs += png
    with open(path, "wb") as f:
        f.write(header + entries + blobs)
    print(f"wrote {path} with sizes {SIZES}, {os.path.getsize(path)} bytes")


if __name__ == "__main__":
    _app = QApplication([])  # keep a reference alive or QPixmap will fail
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.ico")
    build_ico(out)
