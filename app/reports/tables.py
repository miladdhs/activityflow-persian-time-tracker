"""Tabular representations shared by every export format.

Numbers use Latin digits so spreadsheet programs treat them as numbers;
dates follow the user's calendar setting.
"""

from __future__ import annotations

from app.core import formatting as fmt
from app.services.activity_service import ActivityRow
from app.services.report_service import GROUP_BY, ReportGroup, ReportResult

RECORD_HEADERS = [
    "تاریخ", "روز هفته", "عنوان فعالیت", "پروژه", "نوع فعالیت", "ساعت شروع", "ساعت پایان",
    "مدت‌زمان (ساعت:دقیقه)", "مدت‌زمان (دقیقه)", "مقدار", "واحد", "توضیحات",
]


def quantity_text(quantities, latin: bool = True) -> str:
    return " · ".join(f"{fmt.fmt_decimal(q, latin=latin)} {unit}" for unit, q in quantities)


def _number(value) -> int | float | str:
    if value is None:
        return ""
    return int(value) if value == int(value) else float(value)


def record_row(row: ActivityRow) -> list:
    return [
        fmt.fmt_date(row.activity_date, latin=True),
        fmt.weekday_name(row.activity_date),
        row.title,
        row.project_name or "بدون پروژه",
        row.category_name or "بدون نوع",
        fmt.fmt_time(row.start_time, latin=True),
        fmt.fmt_time(row.end_time, latin=True),
        fmt.fmt_clock(row.duration_minutes, latin=True),
        row.duration_minutes,
        _number(row.quantity),
        row.unit_name or "",
        row.notes,
    ]


def group_headers(group_by: str) -> list[str]:
    return [
        GROUP_BY.get(group_by, "گروه"), "تعداد ثبت", "مجموع زمان (ساعت:دقیقه)", "مجموع زمان (دقیقه)",
        "میانگین هر فعالیت (دقیقه)", "سهم از کل (%)", "مقادیر", "آخرین فعالیت",
    ]


def group_row(group: ReportGroup) -> list:
    return [
        group.name,
        group.count,
        fmt.fmt_clock(group.minutes, latin=True),
        group.minutes,
        group.avg_minutes,
        round(group.share * 100, 1),
        quantity_text(group.quantities),
        fmt.fmt_date(group.last_date, latin=True),
    ]


def summary_rows(result: ReportResult) -> list[tuple[str, object]]:
    return [
        ("مجموع زمان فعالیت", fmt.fmt_clock(result.total_minutes, latin=True)),
        ("مجموع زمان (دقیقه)", result.total_minutes),
        ("تعداد فعالیت‌ها", result.count),
        ("میانگین زمان هر فعالیت (دقیقه)", result.avg_minutes),
        ("روزهای فعال", result.active_days),
        ("مقادیر ثبت‌شده", quantity_text(result.quantities) or "—"),
    ]
