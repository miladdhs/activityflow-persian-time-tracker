from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core import formatting as fmt
from app.core import jalali
from app.core.text import normalize_name, parse_decimal


@pytest.mark.parametrize(
    "a, b",
    [
        ("كليپ كاغذ", "کلیپ کاغذ"),
        ("  کلیپ    کاغذ ", "کلیپ کاغذ"),
        ("می\u200cروم", "می روم"),
        ("کلیپ ۱۰", "کلیپ 10"),
        ("Design", "design"),
    ],
)
def test_normalize_unifies_variants(a, b):
    assert normalize_name(a) == normalize_name(b)


def test_normalize_keeps_different_names_apart():
    assert normalize_name("کلیپ کاغذ") != normalize_name("کلیپ کاغذ تبلیغاتی")
    assert normalize_name("") == ""


def test_parse_decimal_accepts_persian_input():
    assert parse_decimal("۱۲٫۵") == Decimal("12.5")
    assert parse_decimal("1,250") == Decimal("1250")
    assert parse_decimal("  ") is None
    with pytest.raises(ValueError):
        parse_decimal("abc")


@pytest.mark.parametrize(
    "g, j",
    [
        (date(2024, 3, 20), (1403, 1, 1)),
        (date(2025, 3, 20), (1403, 12, 30)),
        (date(2025, 3, 21), (1404, 1, 1)),
        (date(2026, 10, 9), (1405, 7, 17)),
        (date(2000, 1, 1), (1378, 10, 11)),
    ],
)
def test_jalali_conversion(g, j):
    assert jalali.to_jalali(g) == j
    assert jalali.from_jalali(*j) == g


def test_jalali_round_trip_over_many_years():
    d = date(1990, 1, 1)
    while d < date(2040, 1, 1):
        assert jalali.from_jalali(*jalali.to_jalali(d)) == d
        d += timedelta(days=17)


def test_jalali_month_lengths():
    assert jalali.is_jalali_leap(1403)
    assert not jalali.is_jalali_leap(1404)
    assert jalali.jalali_month_length(1403, 12) == 30
    assert jalali.jalali_month_length(1404, 12) == 29
    start, end = jalali.jalali_month_range(1405, 7)
    assert start == date(2026, 9, 23) and end == date(2026, 10, 22)


def test_formatting_digits_and_durations():
    fmt.prefs.persian_digits = True
    fmt.prefs.calendar = "jalali"
    assert fmt.fmt_date(date(2026, 10, 9)) == "۱۴۰۵/۰۷/۱۷"
    assert fmt.fmt_date(date(2026, 10, 9), latin=True) == "1405/07/17"
    assert fmt.fmt_clock(135) == "۲:۱۵"
    assert fmt.fmt_duration(135) == "۲ ساعت و ۱۵ دقیقه"
    assert fmt.fmt_duration(45) == "۴۵ دقیقه"
    assert fmt.fmt_duration(120) == "۲ ساعت"
    assert fmt.fmt_int(12500) == "۱۲٬۵۰۰"
    assert fmt.fmt_decimal(Decimal("1250.5")) == "۱٬۲۵۰٫۵"
    fmt.prefs.persian_digits = False
    fmt.prefs.calendar = "gregorian"
    assert fmt.fmt_date(date(2026, 10, 9)) == "2026/10/09"
    assert fmt.fmt_decimal(Decimal("3.250")) == "3.25"
    fmt.prefs.persian_digits = True
    fmt.prefs.calendar = "jalali"
