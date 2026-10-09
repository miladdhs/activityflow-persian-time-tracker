import re

from app import APP_VERSION
from app.core.settings_keys import DEFAULTS, Key


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", APP_VERSION)


def test_defaults_are_seeded(db):
    from app.services import settings_service

    for key, value in DEFAULTS.items():
        assert settings_service.get(key) == value


def test_missing_value_falls_back_to_registered_default(db):
    from app.database import write_session
    from app.models import AppSetting
    from app.services import settings_service

    with write_session() as session:
        session.delete(session.get(AppSetting, Key.PAGE_SIZE))
    settings_service.invalidate()
    assert settings_service.get_int(Key.PAGE_SIZE) == int(DEFAULTS[Key.PAGE_SIZE])
    assert settings_service.get("unknown_key") == ""
    assert settings_service.get("unknown_key", "x") == "x"


def test_bool_and_int_roundtrip(db):
    from app.services import settings_service

    settings_service.set(Key.AUTO_BACKUP, False)
    assert settings_service.get_bool(Key.AUTO_BACKUP, True) is False
    settings_service.set(Key.LAST_PROJECT, None)
    assert settings_service.get_int(Key.LAST_PROJECT) is None
    settings_service.set(Key.LAST_PROJECT, 7)
    assert settings_service.get_int(Key.LAST_PROJECT) == 7


def test_display_prefs_ignore_invalid_calendar(db):
    from app.core import formatting
    from app.services import settings_service

    settings_service.set(Key.CALENDAR, "lunar")
    settings_service.apply_display_prefs()
    assert formatting.prefs.calendar == "jalali"
