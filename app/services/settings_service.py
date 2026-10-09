"""Key/value application settings with an in-memory cache.

Keys and defaults live in :mod:`app.core.settings_keys`; a missing value falls
back to its registered default unless the caller passes an explicit one.
"""

from __future__ import annotations

from sqlalchemy import select

from app.core import formatting
from app.core.settings_keys import CALENDARS, DEFAULTS, Key
from app.database import read_session, write_session
from app.models import AppSetting

_cache: dict[str, str] | None = None
_MISSING = object()


def _load() -> dict[str, str]:
    global _cache
    if _cache is None:
        with read_session() as session:
            _cache = {row.key: row.value for row in session.scalars(select(AppSetting))}
    return _cache


def _raw(key: str) -> str | None:
    value = _load().get(key)
    return DEFAULTS.get(key) if value is None else value


def invalidate() -> None:
    global _cache
    _cache = None


def get(key: str, default=_MISSING) -> str:
    value = _raw(key)
    if value is None:
        return "" if default is _MISSING else default
    return value


def get_bool(key: str, default: bool = False) -> bool:
    value = _raw(key)
    return default if value is None else value == "1"


def get_int(key: str, default: int | None = None) -> int | None:
    value = _raw(key)
    try:
        return int(value) if value not in (None, "") else default
    except ValueError:
        return default


def set_many(values: dict[str, object]) -> None:
    with write_session() as session:
        for key, value in values.items():
            if isinstance(value, bool):
                text = "1" if value else "0"
            else:
                text = "" if value is None else str(value)
            row = session.get(AppSetting, key)
            if row is None:
                session.add(AppSetting(key=key, value=text))
            else:
                row.value = text
    invalidate()


def set(key: str, value: object) -> None:  # noqa: A001 - mirrors get()
    set_many({key: value})


def apply_display_prefs() -> None:
    formatting.prefs.persian_digits = get_bool(Key.PERSIAN_DIGITS)
    calendar = get(Key.CALENDAR)
    formatting.prefs.calendar = calendar if calendar in CALENDARS else CALENDARS[0]
