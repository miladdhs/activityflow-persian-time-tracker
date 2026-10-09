"""Uniform display formatting for numbers, dates, times and durations.

All screens format values through this module so that digits (Persian or
Latin) and the calendar (Jalali or Gregorian) follow the user's settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import Decimal

from app.core import jalali

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


@dataclass
class DisplayPrefs:
    persian_digits: bool = True
    calendar: str = "jalali"  # "jalali" | "gregorian"

    @property
    def is_jalali(self) -> bool:
        return self.calendar == "jalali"


prefs = DisplayPrefs()


def digits(value: object, latin: bool = False) -> str:
    text = str(value)
    if latin or not prefs.persian_digits:
        return text
    return text.translate(_FA_DIGITS)


def fmt_int(value: int | None, latin: bool = False) -> str:
    value = int(value or 0)
    text = f"{value:,}"
    if not latin and prefs.persian_digits:
        text = text.replace(",", "٬")
    return digits(text, latin)


def fmt_decimal(value: Decimal | float | int | None, max_places: int = 3, latin: bool = False) -> str:
    if value is None:
        return ""
    value = Decimal(str(value)).quantize(Decimal(1).scaleb(-max_places))
    sign = "-" if value < 0 else ""
    value = abs(value)
    integer = int(value)
    fraction = format(value - integer, "f")[2:].rstrip("0") if value != integer else ""
    text = f"{integer:,}"
    use_fa = not latin and prefs.persian_digits
    if use_fa:
        text = text.replace(",", "٬")
    if fraction:
        text += ("٫" if use_fa else ".") + fraction
    return digits(sign + text, latin)


def fmt_percent(ratio: float, latin: bool = False) -> str:
    pct = round(ratio * 100)
    return digits(f"{pct}٪" if not latin and prefs.persian_digits else f"{pct}%", latin)


# --- dates -----------------------------------------------------------------

def date_parts(d: date) -> tuple[int, int, int]:
    return jalali.to_jalali(d) if prefs.is_jalali else (d.year, d.month, d.day)


def month_names() -> list[str]:
    return jalali.JALALI_MONTHS if prefs.is_jalali else jalali.GREGORIAN_MONTHS_FA


def month_name(month: int) -> str:
    return month_names()[month - 1]


def fmt_date(d: date | None, latin: bool = False) -> str:
    if d is None:
        return ""
    y, m, day = date_parts(d)
    return digits(f"{y:04d}/{m:02d}/{day:02d}", latin)


def fmt_date_long(d: date | None) -> str:
    if d is None:
        return ""
    y, m, day = date_parts(d)
    return digits(f"{day} {month_name(m)} {y}")


def fmt_date_with_weekday(d: date) -> str:
    return f"{weekday_name(d)}، {fmt_date_long(d)}"


def fmt_month_year(year: int, month: int) -> str:
    return digits(f"{month_name(month)} {year}")


def weekday_name(d: date) -> str:
    return jalali.WEEKDAYS_FA[d.weekday()]


def weekday_short(d: date) -> str:
    return jalali.WEEKDAYS_SHORT_FA[d.weekday()]


def relative_day(d: date, today: date | None = None) -> str:
    today = today or date.today()
    delta = (today - d).days
    if delta == 0:
        return "امروز"
    if delta == 1:
        return "دیروز"
    if 1 < delta < 7:
        return weekday_name(d)
    return fmt_date(d)


def current_year_month(today: date | None = None) -> tuple[int, int]:
    y, m, _ = date_parts(today or date.today())
    return y, m


def month_range(year: int, month: int) -> tuple[date, date]:
    if prefs.is_jalali:
        return jalali.jalali_month_range(year, month)
    start = date(year, month, 1)
    nxt = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, nxt - timedelta(days=1)


def year_range(year: int) -> tuple[date, date]:
    if prefs.is_jalali:
        return jalali.jalali_year_range(year)
    return date(year, 1, 1), date(year, 12, 31)


def month_range_of(d: date) -> tuple[date, date]:
    y, m, _ = date_parts(d)
    return month_range(y, m)


def previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


# --- times & durations -----------------------------------------------------

def fmt_time(t: time | None, latin: bool = False) -> str:
    if t is None:
        return ""
    return digits(f"{t.hour:02d}:{t.minute:02d}", latin)


def fmt_clock(minutes: int | None, latin: bool = False) -> str:
    """Duration as ``H:MM`` — compact and column-friendly."""
    minutes = max(0, int(minutes or 0))
    return digits(f"{minutes // 60}:{minutes % 60:02d}", latin)


def duration_parts(minutes: int | None) -> list[tuple[str, str]]:
    minutes = max(0, int(minutes or 0))
    hours, mins = divmod(minutes, 60)
    parts: list[tuple[str, str]] = []
    if hours:
        parts.append((fmt_int(hours), "ساعت"))
    if mins or not hours:
        parts.append((digits(mins), "دقیقه"))
    return parts


def fmt_duration(minutes: int | None) -> str:
    """Duration in words, e.g. «۲ ساعت و ۱۵ دقیقه»."""
    return " و ".join(f"{v} {u}" for v, u in duration_parts(minutes))


def fmt_duration_short(minutes: int | None) -> str:
    """Compact duration for tight spaces: «۴۵ دقیقه»، «۲ ساعت»، «۲:۱۵ ساعت»."""
    minutes = max(0, int(minutes or 0))
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{fmt_int(hours)}:{digits(f'{mins:02d}')} ساعت"
    if hours:
        return f"{fmt_int(hours)} ساعت"
    return f"{digits(mins)} دقیقه"
