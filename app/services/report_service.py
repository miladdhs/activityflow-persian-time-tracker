"""Report aggregation.

Activities can be grouped by title (same-named activities across every
project), by project or by activity type. Quantities are always summed per
unit, so «۱۰ عدد» and «۲ کیلوگرم» are never added together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.core import formatting
from app.database import read_session
from app.models import Activity, ActivityTitle, Category, Project, Unit
from app.services.activity_service import (
    NONE_ID,
    ActivityFilter,
    ActivityRow,
    apply_filter,
    list_activities,
    quantity_from_milli,
    with_joins,
)
from app.services.stats_service import NO_PROJECT_COLOR, Slice

GROUP_BY = {
    "title": "عنوان فعالیت",
    "project": "پروژه",
    "category": "نوع فعالیت",
}

GROUP_SORTS = {
    "minutes": "بیشترین زمان",
    "count": "بیشترین دفعات ثبت",
    "quantity": "بیشترین مقدار",
    "recent": "جدیدترین فعالیت",
    "name": "نام",
}

NO_CATEGORY_COLOR = "#5E5B73"
TITLE_COLOR = "#A78BFA"


@dataclass
class ReportGroup:
    key: int | None
    name: str
    color: str
    count: int
    minutes: int
    last_date: date | None
    quantities: list[tuple[str, Decimal]] = field(default_factory=list)
    share: float = 0.0

    @property
    def avg_minutes(self) -> int:
        return round(self.minutes / self.count) if self.count else 0

    @property
    def max_quantity(self) -> Decimal:
        return max((q for _, q in self.quantities), default=Decimal(0))


@dataclass
class TrendPoint:
    label: str
    tooltip: str
    start: date
    minutes: int


@dataclass
class ReportResult:
    filter: ActivityFilter
    group_by: str
    total_minutes: int = 0
    count: int = 0
    active_days: int = 0
    quantities: list[tuple[str, Decimal]] = field(default_factory=list)
    groups: list[ReportGroup] = field(default_factory=list)
    by_project: list[Slice] = field(default_factory=list)
    by_category: list[Slice] = field(default_factory=list)
    trend: list[TrendPoint] = field(default_factory=list)
    trend_unit: str = "day"

    @property
    def avg_minutes(self) -> int:
        return round(self.total_minutes / self.count) if self.count else 0


def _group_columns(group_by: str):
    if group_by == "project":
        return Activity.project_id, Project.name, Project.color
    if group_by == "category":
        return Activity.category_id, Category.name, Category.color
    return Activity.title_id, ActivityTitle.name, None


def _empty_name(group_by: str) -> str:
    return {"project": "بدون پروژه", "category": "بدون نوع"}.get(group_by, "—")


def _empty_color(group_by: str) -> str:
    return NO_PROJECT_COLOR if group_by == "project" else NO_CATEGORY_COLOR


def _aggregate_select(*columns):
    return with_joins(select(*columns).select_from(Activity))


def _quantities(session, f: ActivityFilter, key_col=None) -> dict:
    columns = [Unit.name, func.sum(Activity.quantity_milli)]
    group = [Activity.unit_id]
    if key_col is not None:
        columns.insert(0, key_col)
        group.insert(0, key_col)
    stmt = apply_filter(_aggregate_select(*columns), f).where(Activity.quantity_milli.is_not(None))
    stmt = stmt.group_by(*group).order_by(func.sum(Activity.quantity_milli).desc())
    result: dict = {}
    for row in session.execute(stmt):
        if key_col is not None:
            key, unit, total = row
        else:
            key, (unit, total) = None, row
        result.setdefault(key, []).append((unit, quantity_from_milli(int(total))))
    return result


def _slices(session, f: ActivityFilter, group_by: str) -> list[Slice]:
    key_col, name_col, color_col = _group_columns(group_by)
    stmt = apply_filter(
        _aggregate_select(
            key_col, name_col, color_col if color_col is not None else name_col,
            func.coalesce(func.sum(Activity.duration_minutes), 0), func.count(Activity.id),
        ),
        f,
    ).group_by(key_col).order_by(func.sum(Activity.duration_minutes).desc())
    return [
        Slice(key, name or _empty_name(group_by), (color if color_col is not None else None) or _empty_color(group_by),
              int(minutes), int(count))
        for key, name, color, minutes, count in session.execute(stmt)
    ]


def _trend(session, f: ActivityFilter) -> tuple[list[TrendPoint], str]:
    per_day = dict(
        session.execute(
            apply_filter(_aggregate_select(Activity.activity_date, func.sum(Activity.duration_minutes)), f)
            .group_by(Activity.activity_date)
        ).all()
    )
    if not f.date_from or not f.date_to:
        if not per_day:
            return [], "day"
        start, end = min(per_day), max(per_day)
    else:
        start, end = f.date_from, f.date_to
        # Days after today can never hold activities; don't draw empty future bars.
        if start <= date.today() < end:
            end = date.today()

    span = (end - start).days + 1
    if span <= 62:
        points = []
        for i in range(span):
            day = start + timedelta(days=i)
            _, _, d = formatting.date_parts(day)
            points.append(
                TrendPoint(formatting.digits(d), formatting.fmt_date_with_weekday(day), day, int(per_day.get(day, 0) or 0))
            )
        return points, "day"

    points: list[TrendPoint] = []
    y, m, _ = formatting.date_parts(start)
    while True:
        m_start, m_end = formatting.month_range(y, m)
        if m_start > end:
            break
        minutes = sum(int(v or 0) for d, v in per_day.items() if m_start <= d <= m_end)
        label = formatting.month_name(m)
        points.append(TrendPoint(label, formatting.fmt_month_year(y, m), m_start, minutes))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return points, "month"


def build_report(f: ActivityFilter, group_by: str = "title", sort: str = "minutes") -> ReportResult:
    group_by = group_by if group_by in GROUP_BY else "title"
    result = ReportResult(filter=f, group_by=group_by)
    key_col, name_col, color_col = _group_columns(group_by)

    with read_session() as session:
        totals = session.execute(
            apply_filter(
                _aggregate_select(
                    func.count(Activity.id),
                    func.coalesce(func.sum(Activity.duration_minutes), 0),
                    func.count(func.distinct(Activity.activity_date)),
                ),
                f,
            )
        ).one()
        result.count, result.total_minutes, result.active_days = (int(v or 0) for v in totals)
        if result.count == 0:
            return result

        result.quantities = _quantities(session, f).get(None, [])
        group_quantities = _quantities(session, f, key_col)

        stmt = apply_filter(
            _aggregate_select(
                key_col,
                name_col,
                color_col if color_col is not None else name_col,
                func.count(Activity.id),
                func.coalesce(func.sum(Activity.duration_minutes), 0),
                func.max(Activity.activity_date),
            ),
            f,
        ).group_by(key_col)

        for key, name, color, count, minutes, last in session.execute(stmt):
            result.groups.append(
                ReportGroup(
                    key=key,
                    name=name or _empty_name(group_by),
                    color=(color if color_col is not None else TITLE_COLOR) or _empty_color(group_by),
                    count=int(count),
                    minutes=int(minutes),
                    last_date=last,
                    quantities=group_quantities.get(key, []),
                )
            )

        for group in result.groups:
            if result.total_minutes:
                group.share = group.minutes / result.total_minutes
            else:
                group.share = group.count / result.count

        result.by_project = _slices(session, f, "project")
        result.by_category = _slices(session, f, "category")
        result.trend, result.trend_unit = _trend(session, f)

    sorters = {
        "minutes": lambda g: (-g.minutes, -g.count, g.name),
        "count": lambda g: (-g.count, -g.minutes, g.name),
        "quantity": lambda g: (-g.max_quantity, -g.minutes, g.name),
        "recent": lambda g: (-(g.last_date or date.min).toordinal(), g.name),
        "name": lambda g: g.name,
    }
    result.groups.sort(key=sorters.get(sort, sorters["minutes"]))
    return result


def group_filter(f: ActivityFilter, group_by: str, key: int | None) -> ActivityFilter:
    """The filter that selects exactly the records behind one report group."""
    value = NONE_ID if key is None else key
    narrowed = ActivityFilter(**vars(f))
    if group_by == "project":
        narrowed.project_id = value
    elif group_by == "category":
        narrowed.category_id = value
    else:
        narrowed.title_id = value
    return narrowed


def group_records(f: ActivityFilter, group_by: str, key: int | None) -> list[ActivityRow]:
    return list_activities(group_filter(f, group_by, key))
