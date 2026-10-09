"""Names and default values of every persisted application setting."""

from __future__ import annotations


class Key:
    PERSIAN_DIGITS = "persian_digits"
    CALENDAR = "calendar"
    AUTO_BACKUP = "auto_backup"
    PAGE_SIZE = "page_size"
    SEEDED = "seeded"
    LAST_PROJECT = "last_project_id"
    LAST_CATEGORY = "last_category_id"
    LAST_UNIT = "last_unit_id"
    LAST_TIME_MODE = "last_time_mode"
    LAST_EXPORT_DIR = "last_export_dir"
    LAST_AUTO_BACKUP = "last_auto_backup"


CALENDARS = ("jalali", "gregorian")
TIME_MODES = ("duration", "range")
PAGE_SIZES = (10, 25, 50, 100)

# Written to the database on first run; also the fallback when a value is missing.
DEFAULTS: dict[str, str] = {
    Key.PERSIAN_DIGITS: "1",
    Key.CALENDAR: CALENDARS[0],
    Key.AUTO_BACKUP: "1",
    Key.PAGE_SIZE: "25",
    Key.LAST_TIME_MODE: TIME_MODES[0],
}
