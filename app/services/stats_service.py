"""Aggregates for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select

from app.core import formatting
from app.database import read_session
from app.models import Activity, ActivityTitle, Project
from app.services.activity_service import ActivityRow, recent_activities

NO_PROJECT_COLOR = "#5E5B73"
OTHERS_COLOR = "#45435A"


@dataclass
class Slice:
    key: int | None
    name: str
    color: str
    minutes: int
    count: int = 0


@dataclass
class FrequentItem:
    title: str
    count: int
    minutes: int


@dataclass
class DashboardData:
    today: date
    today_minutes: int = 0
    yesterday_minutes: int = 0
    today_count: int = 0
    total_count: int = 0
    month_count: int = 0
    active_projects: int = 0
    open_projects: int = 0
    month_minutes: int = 0
    prev_month_minutes: int = 0
    month_label: str = ""
    week: list[tuple[date, int]] = field(default_factory=list)
    projects: list[Slice] = field(default_factory=list)
    recent: list[ActivityRow] = field(default_factory=list)
    frequent: list[FrequentItem] = field(default_factory=list)


def _sum_minutes(session, start: date, end: date) -> tuple[int, int]:
    row = session.execute(
        select(func.coalesce(func.sum(Activity.duration_minutes), 0), func.count(Activity.id)).where(
            Activity.activity_date >= start, Activity.activity_date <= end
        )
    ).one()
    return int(row[0]), int(row[1])


def project_slices(session, start: date, end: date, top: int = 5) -> list[Slice]:
    rows = session.execute(
        select(
            Activity.project_id,
            Project.name,
            Project.color,
            func.coalesce(func.sum(Activity.duration_minutes), 0),
            func.count(Activity.id),
        )
        .select_from(Activity)
        .outerjoin(Project, Project.id == Activity.project_id)
        .where(Activity.activity_date >= start, Activity.activity_date <= end)
        .group_by(Activity.project_id)
        .order_by(func.sum(Activity.duration_minutes).desc())
    ).all()
    slices = [
        Slice(pid, name or "بدون پروژه", color or NO_PROJECT_COLOR, int(minutes), int(count))
        for pid, name, color, minutes, count in rows
        if minutes
    ]
    if len(slices) > top:
        rest = slices[top - 1:]
        slices = slices[: top - 1] + [
            Slice(None, "سایر پروژه‌ها", OTHERS_COLOR, sum(s.minutes for s in rest), sum(s.count for s in rest))
        ]
    return slices


def dashboard(today: date | None = None) -> DashboardData:
    today = today or date.today()
    data = DashboardData(today=today)
    year, month = formatting.current_year_month(today)
    month_start, month_end = formatting.month_range(year, month)
    prev_start, prev_end = formatting.month_range(*formatting.previous_month(year, month))
    data.month_label = formatting.fmt_month_year(year, month)

    with read_session() as session:
        data.today_minutes, data.today_count = _sum_minutes(session, today, today)
        yesterday = today - timedelta(days=1)
        data.yesterday_minutes, _ = _sum_minutes(session, yesterday, yesterday)
        data.month_minutes, data.month_count = _sum_minutes(session, month_start, month_end)
        # Only compare against the same number of elapsed days of the previous month.
        elapsed = (today - month_start).days
        data.prev_month_minutes, _ = _sum_minutes(session, prev_start, min(prev_end, prev_start + timedelta(days=elapsed)))
        data.total_count = int(session.scalar(select(func.count(Activity.id))) or 0)

        statuses = dict(
            session.execute(select(Project.status, func.count(Project.id)).group_by(Project.status)).all()
        )
        data.active_projects = int(statuses.get("active", 0))
        data.open_projects = int(statuses.get("active", 0) + statuses.get("paused", 0))

        week_start = today - timedelta(days=6)
        per_day = dict(
            session.execute(
                select(Activity.activity_date, func.sum(Activity.duration_minutes))
                .where(Activity.activity_date >= week_start, Activity.activity_date <= today)
                .group_by(Activity.activity_date)
            ).all()
        )
        data.week = [
            (week_start + timedelta(days=i), int(per_day.get(week_start + timedelta(days=i), 0) or 0))
            for i in range(7)
        ]

        data.projects = project_slices(session, month_start, month_end)

        frequent_start = today - timedelta(days=29)
        data.frequent = [
            FrequentItem(name, int(count), int(minutes or 0))
            for name, count, minutes in session.execute(
                select(ActivityTitle.name, func.count(Activity.id), func.sum(Activity.duration_minutes))
                .join(ActivityTitle, ActivityTitle.id == Activity.title_id)
                .where(Activity.activity_date >= frequent_start, Activity.activity_date <= today)
                .group_by(ActivityTitle.id)
                .order_by(func.count(Activity.id).desc(), func.sum(Activity.duration_minutes).desc())
                .limit(5)
            ).all()
        ]

    data.recent = recent_activities(6)
    return data


def day_summary(day: date) -> tuple[int, int]:
    with read_session() as session:
        return _sum_minutes(session, day, day)
