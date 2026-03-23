from pathlib import Path
import sys

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPixmap


def render_icon(size: int, output_path: Path) -> None:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#1db954"))
    gradient.setColorAt(1.0, QColor("#0f3d27"))

    outer_rect = QRectF(0, 0, size, size)
    outer_path = QPainterPath()
    outer_path.addRoundedRect(outer_rect, size * 0.23, size * 0.23)
    painter.fillPath(outer_path, gradient)

    inner_rect = QRectF(size * 0.14, size * 0.14, size * 0.72, size * 0.72)
    inner_path = QPainterPath()
    inner_path.addRoundedRect(inner_rect, size * 0.16, size * 0.16)
    painter.fillPath(inner_path, QColor(255, 255, 255, 28))

    painter.setPen(QColor("#ffffff"))
    font = QFont("Helvetica Neue", int(size * 0.42))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(outer_rect, Qt.AlignmentFlag.AlignCenter, "H")

    painter.end()
    pixmap.save(str(output_path))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_app_icon.py <output-dir>")

    output_dir = Path(sys.argv[1])
    output_dir.mkdir(parents=True, exist_ok=True)

    app = QGuiApplication.instance() or QGuiApplication([])
    _ = app

    sizes = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]

    for filename, size in sizes:
        render_icon(size, output_dir / filename)


if __name__ == "__main__":
    main()
