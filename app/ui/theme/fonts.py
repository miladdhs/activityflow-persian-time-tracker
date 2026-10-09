from __future__ import annotations

import logging

from PySide6.QtGui import QFont, QFontDatabase

from app.core.paths import resource_path
from app.ui.theme import tokens as t

log = logging.getLogger(__name__)

FONT_FILES = ["Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf", "Vazirmatn-SemiBold.ttf", "Vazirmatn-Bold.ttf"]


def load_fonts() -> bool:
    loaded = False
    for name in FONT_FILES:
        path = resource_path("fonts", name)
        if QFontDatabase.addApplicationFont(str(path)) == -1:
            log.warning("Could not load font %s", path)
        else:
            loaded = True
    return loaded


def app_font() -> QFont:
    font = QFont()
    font.setFamilies(t.FONT_FALLBACKS)
    font.setPixelSize(t.FONT_BODY)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def font(size: int = t.FONT_BODY, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = app_font()
    f.setPixelSize(size)
    f.setWeight(weight)
    return f
