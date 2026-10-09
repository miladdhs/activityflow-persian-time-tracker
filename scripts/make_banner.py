"""Render the README hero / GitHub social-preview banner and a PNG logo.

    python scripts/screenshots.py    # first, so docs/screenshots/dashboard.png exists
    python scripts/make_banner.py    # -> docs/banner.png (1280x640), docs/logo.png (256x256)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DOCS = ROOT / "docs"
BANNER_SIZE = (1280, 640)  # GitHub social preview recommendation
LOGO_SIZE = 256
SCALE = 2  # rendered at 2x for crisp text on high-DPI screens

TAGLINE_FA = "ثبت و گزارش‌گیری فعالیت‌ها و پروژه‌ها"
TAGLINE_EN = "Offline Persian time tracker, timesheet & project manager"
CHIP_ROWS = (
    ("کاملاً آفلاین", "تقویم شمسی", "رابط فارسی راست‌چین"),
    ("گزارش Excel و PDF", "پشتیبان‌گیری خودکار", "رایگان و متن‌باز"),
)
FOOTER = "Windows  ·  Python  ·  PySide6  ·  SQLite"


def _font(family: str, px: int, weight):
    from PySide6.QtGui import QFont

    font = QFont(family)
    font.setPixelSize(px)
    font.setWeight(weight)
    return font


def _render_svg(path: Path, size: int):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(str(path)).render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def _glow(painter, center, radius: float, color: str, alpha: int) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QRadialGradient

    gradient = QRadialGradient(center, radius)
    inner = QColor(color)
    inner.setAlpha(alpha)
    outer = QColor(color)
    outer.setAlpha(0)
    gradient.setColorAt(0, inner)
    gradient.setColorAt(1, outer)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawEllipse(center, radius, radius)


def _screenshot_frame(painter, shot, rect) -> None:
    """Rounded, bordered screenshot with a soft layered shadow."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QPainterPath, QPen

    from app.ui.theme import tokens as t

    radius = 14 * SCALE
    painter.setPen(Qt.PenStyle.NoPen)
    for step in range(18, 0, -1):
        spread = step * 2.2 * SCALE
        shadow = QColor(0, 0, 0, 9)
        painter.setBrush(shadow)
        painter.drawRoundedRect(rect.adjusted(-spread, -spread * 0.6, spread, spread * 1.2), radius + spread, radius + spread)

    clip = QPainterPath()
    clip.addRoundedRect(rect, radius, radius)
    painter.save()
    painter.setClipPath(clip)
    scaled = shot.scaledToWidth(int(rect.width()), Qt.TransformationMode.SmoothTransformation)
    painter.drawImage(rect.topLeft(), scaled)
    painter.restore()

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(t.BORDER_STRONG), 1.5 * SCALE))
    painter.drawRoundedRect(QRectF(rect), radius, radius)


def build_banner(screenshot: Path):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QPen

    from app import APP_NAME
    from app.ui.theme import tokens as t

    width, height = BANNER_SIZE[0] * SCALE, BANNER_SIZE[1] * SCALE
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(t.BG_APP))
    p = QPainter(image)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing | QPainter.RenderHint.SmoothPixmapTransform)

    # background: brand glows + dotted grid
    _glow(p, QPointF(width * 0.05, height * 0.1), 620 * SCALE, t.ACCENT_PRIMARY, 70)
    _glow(p, QPointF(width * 0.95, height * 1.05), 520 * SCALE, t.INFO, 40)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 14))
    step = 28 * SCALE
    for x in range(step // 2, width, step):
        for y in range(step // 2, height, step):
            p.drawEllipse(QPointF(x, y), 1.1 * SCALE, 1.1 * SCALE)

    # product screenshot, bleeding off the left edge
    shot = QImage(str(screenshot))
    if not shot.isNull():
        shot_w = 660 * SCALE
        shot_h = shot_w * shot.height() / shot.width()
        _screenshot_frame(p, shot, QRectF(-60 * SCALE, 92 * SCALE, shot_w, shot_h))

    # text column (right-aligned, RTL)
    right = width - 64 * SCALE
    column = 520 * SCALE
    left = right - column

    logo_px = 76 * SCALE
    logo = _render_svg(ROOT / "app" / "resources" / "images" / "logo.svg", logo_px)
    top = 118 * SCALE
    p.drawImage(QPointF(right - logo_px, top), logo)

    name_font = _font(t.FONT_FAMILY, 60 * SCALE, QFont.Weight.Bold)
    p.setFont(name_font)
    name_rect = QRectF(left, top - 4 * SCALE, column - logo_px - 20 * SCALE, logo_px + 8 * SCALE)
    gradient = QLinearGradient(name_rect.topLeft(), name_rect.bottomRight())
    gradient.setColorAt(0, QColor("#FFFFFF"))
    gradient.setColorAt(1, QColor(t.ACCENT_TEXT))
    p.setPen(QPen(gradient, 1))
    p.drawText(name_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, APP_NAME)

    y = top + logo_px + 30 * SCALE
    p.setFont(_font(t.FONT_FAMILY, 30 * SCALE, QFont.Weight.DemiBold))
    p.setPen(QColor(t.TEXT_PRIMARY))
    tagline_rect = QRectF(left - 40 * SCALE, y, column + 40 * SCALE, 100 * SCALE)
    bounds = p.boundingRect(tagline_rect, int(Qt.AlignmentFlag.AlignRight | Qt.TextFlag.TextWordWrap), TAGLINE_FA)
    p.drawText(tagline_rect, int(Qt.AlignmentFlag.AlignRight | Qt.TextFlag.TextWordWrap), TAGLINE_FA)
    y += bounds.height() + 12 * SCALE

    p.setFont(_font(t.FONT_FAMILY, 19 * SCALE, QFont.Weight.Normal))
    p.setPen(QColor(t.TEXT_SECONDARY))
    p.drawText(QRectF(left - 60 * SCALE, y, column + 60 * SCALE, 30 * SCALE), Qt.AlignmentFlag.AlignRight, TAGLINE_EN)
    y += 62 * SCALE

    # feature chips, laid out right-to-left
    chip_font = _font(t.FONT_FAMILY, 15 * SCALE, QFont.Weight.Medium)
    metrics = QFontMetricsF(chip_font)
    p.setFont(chip_font)
    chip_h, pad, gap = 36 * SCALE, 15 * SCALE, 10 * SCALE
    for row in CHIP_ROWS:
        x = right
        for chip in row:
            chip_w = metrics.horizontalAdvance(chip) + pad * 2
            rect = QRectF(x - chip_w, y, chip_w, chip_h)
            p.setPen(QPen(QColor(t.ACCENT_PRIMARY), 1.2 * SCALE))
            p.setBrush(QColor(t.ACCENT_SOFT))
            p.drawRoundedRect(rect, chip_h / 2, chip_h / 2)
            p.setPen(QColor(t.ACCENT_TEXT))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, chip)
            x -= chip_w + gap
        y += chip_h + gap

    p.setFont(_font(t.FONT_FAMILY, 16 * SCALE, QFont.Weight.Normal))
    p.setPen(QColor(t.TEXT_MUTED))
    p.drawText(QRectF(left, height - 74 * SCALE, column, 30 * SCALE), Qt.AlignmentFlag.AlignRight, FOOTER)
    p.end()
    return image.scaled(BANNER_SIZE[0], BANNER_SIZE[1], Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)


def main() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv[:1])  # noqa: F841 - fonts and painting need an application object
    from app.ui.theme import fonts

    fonts.load_fonts()
    DOCS.mkdir(exist_ok=True)

    screenshot = DOCS / "screenshots" / "dashboard.png"
    if not screenshot.exists():
        print(f"warning: {screenshot} not found; run scripts/screenshots.py first", file=sys.stderr)
    build_banner(screenshot).save(str(DOCS / "banner.png"), "PNG")
    _render_svg(ROOT / "app" / "resources" / "images" / "logo.svg", LOGO_SIZE).save(str(DOCS / "logo.png"), "PNG")
    print(f"Wrote {DOCS / 'banner.png'} and {DOCS / 'logo.png'}")


if __name__ == "__main__":
    main()
