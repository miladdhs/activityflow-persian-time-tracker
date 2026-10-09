"""Persian-aware text normalization.

``normalize_name`` produces the key used to detect same-named activities:
it unifies Arabic/Persian letter variants, digits, ZWNJ and whitespace, but
never merges genuinely different words.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation

_LETTER_MAP = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "\u0640": "",  # tatweel
    }
)

_DIGIT_MAP = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)

_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")
_SPACES = re.compile(r"[\s\u200c\u200d\u200e\u200f\u00a0\u2009\u202f]+")


def to_latin_digits(text: str) -> str:
    return text.translate(_DIGIT_MAP)


def clean_text(text: str | None) -> str:
    """Tidy user input for storage while keeping its visible shape."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text).translate(_LETTER_MAP)
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r" ?\u200c ?", "\u200c", text)
    return text.strip()


def clean_name(text: str | None) -> str:
    """A single-line display name (no line breaks, collapsed spaces)."""
    return clean_text(" ".join((text or "").split()))


def normalize_name(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_LETTER_MAP).translate(_DIGIT_MAP)
    text = _DIACRITICS.sub("", text)
    text = _SPACES.sub(" ", text)
    return text.strip().casefold()


def parse_decimal(text: str | None) -> Decimal | None:
    """Parse a user-entered number accepting Persian/Arabic digits and separators."""
    if text is None:
        return None
    raw = to_latin_digits(str(text)).strip()
    if not raw:
        return None
    raw = raw.replace("٫", ".").replace("/", ".").replace("٬", "").replace(",", "").replace(" ", "")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ValueError("invalid number") from None
    if not value.is_finite():
        raise ValueError("invalid number")
    return value
