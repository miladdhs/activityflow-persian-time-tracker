"""Design tokens — the single source of truth for colors, type, spacing and motion.

Values follow the ActivityFlow design system (docs/design-system.md).
"""

from __future__ import annotations

from PySide6.QtGui import QColor

# Backgrounds
BG_APP = "#0B0B10"
BG_SIDEBAR = "#0E0E15"
BG_SURFACE = "#13131C"
BG_SURFACE_HOVER = "#1A1A26"
BG_ELEVATED = "#1D1D2A"
BG_INPUT = "#101018"

# Borders
BORDER_SUBTLE = "#252533"
BORDER_STRONG = "#36364A"
FOCUS_RING = "#A78BFA"

# Text
TEXT_PRIMARY = "#F4F2FA"
TEXT_SECONDARY = "#AAA7BA"
TEXT_MUTED = "#777487"

# Brand accent
ACCENT_PRIMARY = "#8B5CF6"
ACCENT_HOVER = "#9D76FF"
ACCENT_PRESSED = "#7542E8"
ACCENT_SOFT = "#211833"
ACCENT_TEXT = "#C4B5FD"

# Semantic
SUCCESS = "#34D399"
WARNING = "#FBBF24"
DANGER = "#FB7185"
INFO = "#60A5FA"

# Typography
FONT_FAMILY = "Vazirmatn"
FONT_FALLBACKS = ["Vazirmatn", "Segoe UI", "Tahoma"]
FONT_DISPLAY = 30
FONT_H1 = 26
FONT_H2 = 21
FONT_H3 = 17
FONT_BODY = 14
FONT_SMALL = 12
FONT_CAPTION = 11
FONT_BUTTON = 13

# Spacing (4px grid)
SPACE_1, SPACE_2, SPACE_3, SPACE_4, SPACE_5, SPACE_6 = 4, 8, 12, 16, 20, 24
SPACE_8, SPACE_10, SPACE_12 = 32, 40, 48
PAGE_MARGIN = 28
CARD_PADDING = 20
FIELD_HEIGHT = 44
HEADER_HEIGHT = 72
SIDEBAR_WIDTH = 236

# Radius
RADIUS_SM = 6
RADIUS_MD = 9
RADIUS_LG = 12
RADIUS_XL = 16

# Motion (ms)
MOTION_HOVER = 120
MOTION_STATE = 160
MOTION_OPEN = 180


def qcolor(hex_color: str, alpha: float = 1.0) -> QColor:
    color = QColor(hex_color)
    color.setAlphaF(max(0.0, min(1.0, alpha)))
    return color


def rgba(hex_color: str, alpha: float) -> str:
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha:.3f})"
