"""Local Iconly (Light) icons, recolored at runtime.

The SVG sources use a single placeholder color (``#200E32``); it is replaced
with any theme color so every icon shares one consistent stroke style.
"""

from __future__ import annotations

from functools import cache, lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from app.core.paths import cache_dir, resource_path
from app.ui.theme import tokens as t

_PLACEHOLDER = "#200E32"


@cache
def _source(name: str) -> str:
    return resource_path("icons", f"{name}.svg").read_text(encoding="utf-8")


def svg_data(name: str, color: str) -> bytes:
    return _source(name).replace(_PLACEHOLDER, color).encode("utf-8")


def _ratio() -> float:
    app = QGuiApplication.instance()
    screen = app.primaryScreen() if app else None
    return max(1.0, screen.devicePixelRatio() if screen else 1.0)


@lru_cache(maxsize=1024)
def pixmap(name: str, color: str = t.TEXT_SECONDARY, size: int = 20, ratio: float | None = None) -> QPixmap:
    ratio = ratio or _ratio()
    px = int(round(size * ratio))
    image = QPixmap(px, px)
    image.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg_data(name, color)))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, px, px))
    painter.end()
    image.setDevicePixelRatio(ratio)
    return image


def icon(
    name: str,
    color: str = t.TEXT_SECONDARY,
    size: int = 20,
    active: str | None = None,
    disabled: str = t.TEXT_MUTED,
) -> QIcon:
    result = QIcon()
    result.addPixmap(pixmap(name, color, size), QIcon.Mode.Normal, QIcon.State.Off)
    result.addPixmap(pixmap(name, active or color, size), QIcon.Mode.Active, QIcon.State.Off)
    result.addPixmap(pixmap(name, active or color, size), QIcon.Mode.Normal, QIcon.State.On)
    result.addPixmap(pixmap(name, disabled, size), QIcon.Mode.Disabled, QIcon.State.Off)
    return result


def icon_size(size: int = 20) -> QSize:
    return QSize(size, size)


def icon_file(name: str, color: str) -> str:
    """Write a recolored copy for use inside style sheets (``url(...)``)."""
    target = cache_dir() / f"{name}-{color.lstrip('#').lower()}.svg"
    data = svg_data(name, color)
    if not target.exists() or target.read_bytes() != data:
        target.write_bytes(data)
    return target.as_posix()


def logo_pixmap(size: int = 36) -> QPixmap:
    ratio = _ratio()
    px = int(round(size * ratio))
    image = QPixmap(px, px)
    image.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(str(resource_path("images", "logo.svg")))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, px, px))
    painter.end()
    image.setDevicePixelRatio(ratio)
    return image


def app_icon() -> QIcon:
    ico = resource_path("images", "app.ico")
    if Path(ico).exists():
        return QIcon(str(ico))
    result = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        image = QPixmap(size, size)
        image.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(str(resource_path("images", "logo.svg")))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        result.addPixmap(image)
    return result
