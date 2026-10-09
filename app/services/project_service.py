"""Projects: creation, editing, status changes and safe deletion."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select, update

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.text import clean_name, clean_text, normalize_name
from app.database import read_session, write_session
from app.models import Activity, Project

STATUSES: dict[str, str] = {
    "active": "فعال",
    "paused": "متوقف",
    "completed": "تکمیل‌شده",
    "archived": "بایگانی‌شده",
}

# Statuses that accept new activities.
OPEN_STATUSES = ("active", "paused")

PROJECT_COLORS = [
    "#8B5CF6", "#60A5FA", "#34D399", "#FBBF24", "#FB7185",
    "#F472B6", "#2DD4BF", "#A78BFA", "#FB923C", "#94A3B8",
]

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass
class ProjectInput:
    name: str
    description: str = ""
    color: str = PROJECT_COLORS[0]
    start_date: date | None = None
    status: str = "active"


@dataclass
class ProjectInfo:
    id: int
    name: str
    description: str
    color: str
    start_date: date | None
    status: str
    total_minutes: int = 0
    activity_count: int = 0
    last_activity: date | None = None
    extra: dict = field(default_factory=dict)

    @property
    def status_label(self) -> str:
        return STATUSES.get(self.status, self.status)


def _validate(data: ProjectInput) -> ProjectInput:
    name = clean_name(data.name)
    if not name:
        raise ValidationError("نام پروژه را وارد کنید.", "name")
    if len(name) > 150:
        raise ValidationError("نام پروژه حداکثر می‌تواند ۱۵۰ نویسه باشد.", "name")
    description = clean_text(data.description)
    if len(description) > 2000:
        raise ValidationError("توضیحات حداکثر می‌تواند ۲۰۰۰ نویسه باشد.", "description")
    if not data.color or not _HEX.match(data.color):
        raise ValidationError("رنگ انتخاب‌شده معتبر نیست.", "color")
    if data.status not in STATUSES:
        raise ValidationError("وضعیت پروژه معتبر نیست.", "status")
    return ProjectInput(name, description, data.color.upper(), data.start_date, data.status)


def _stats_subquery():
    return (
        select(
            Activity.project_id.label("pid"),
            func.count(Activity.id).label("cnt"),
            func.coalesce(func.sum(Activity.duration_minutes), 0).label("minutes"),
            func.max(Activity.activity_date).label("last"),
        )
        .group_by(Activity.project_id)
        .subquery()
    )


def _to_info(project: Project, cnt=0, minutes=0, last=None) -> ProjectInfo:
    return ProjectInfo(
        id=project.id,
        name=project.name,
        description=project.description or "",
        color=project.color,
        start_date=project.start_date,
        status=project.status,
        total_minutes=int(minutes or 0),
        activity_count=int(cnt or 0),
        last_activity=last,
    )


def list_projects(status: str | None = None, search: str = "") -> list[ProjectInfo]:
    stats = _stats_subquery()
    stmt = (
        select(Project, stats.c.cnt, stats.c.minutes, stats.c.last)
        .outerjoin(stats, stats.c.pid == Project.id)
    )
    if status:
        stmt = stmt.where(Project.status == status)
    key = normalize_name(search)
    if key:
        stmt = stmt.where(Project.normalized_name.contains(key))
    order = {"active": 0, "paused": 1, "completed": 2, "archived": 3}
    with read_session() as session:
        rows = session.execute(stmt).all()
    result = [_to_info(project, count, minutes, last) for project, count, minutes, last in rows]
    result.sort(key=lambda p: (order.get(p.status, 9), -(p.last_activity or date.min).toordinal(), p.name))
    return result


def status_counts() -> dict[str, int]:
    with read_session() as session:
        rows = session.execute(select(Project.status, func.count(Project.id)).group_by(Project.status)).all()
    counts = {key: 0 for key in STATUSES}
    counts.update({status: n for status, n in rows})
    return counts


def project_choices(include_ids: tuple[int, ...] = ()) -> list[ProjectInfo]:
    """Projects that can receive activities, plus any explicitly requested ids."""
    with read_session() as session:
        stmt = select(Project).where(
            Project.status.in_(OPEN_STATUSES) | Project.id.in_(include_ids or (-1,))
        ).order_by(Project.name)
        return [_to_info(p) for p in session.scalars(stmt)]


def all_projects() -> list[ProjectInfo]:
    with read_session() as session:
        return [_to_info(p) for p in session.scalars(select(Project).order_by(Project.name))]


def get_project(project_id: int) -> ProjectInfo:
    stats = _stats_subquery()
    with read_session() as session:
        row = session.execute(
            select(Project, stats.c.cnt, stats.c.minutes, stats.c.last)
            .outerjoin(stats, stats.c.pid == Project.id)
            .where(Project.id == project_id)
        ).first()
    if row is None:
        raise NotFoundError("پروژه پیدا نشد.")
    return _to_info(*row)


def create_project(data: ProjectInput) -> int:
    data = _validate(data)
    key = normalize_name(data.name)
    with write_session() as session:
        if session.scalar(select(Project.id).where(Project.normalized_name == key)):
            raise ConflictError("پروژه‌ای با این نام از قبل وجود دارد.")
        project = Project(
            name=data.name,
            normalized_name=key,
            description=data.description,
            color=data.color,
            start_date=data.start_date,
            status=data.status,
        )
        session.add(project)
        session.flush()
        return project.id


def update_project(project_id: int, data: ProjectInput) -> None:
    data = _validate(data)
    key = normalize_name(data.name)
    with write_session() as session:
        project = session.get(Project, project_id)
        if project is None:
            raise NotFoundError("پروژه پیدا نشد.")
        if session.scalar(select(Project.id).where(Project.normalized_name == key, Project.id != project_id)):
            raise ConflictError("پروژه دیگری با این نام وجود دارد.")
        project.name = data.name
        project.normalized_name = key
        project.description = data.description
        project.color = data.color
        project.start_date = data.start_date
        project.status = data.status


def set_status(project_id: int, status: str) -> None:
    if status not in STATUSES:
        raise ValidationError("وضعیت پروژه معتبر نیست.")
    with write_session() as session:
        project = session.get(Project, project_id)
        if project is None:
            raise NotFoundError("پروژه پیدا نشد.")
        project.status = status


def delete_project(project_id: int) -> int:
    """Delete the project only; its activities are kept as «بدون پروژه»."""
    with write_session() as session:
        project = session.get(Project, project_id)
        if project is None:
            raise NotFoundError("پروژه پیدا نشد.")
        detached = session.execute(
            update(Activity).where(Activity.project_id == project_id).values(project_id=None)
        ).rowcount
        session.delete(project)
        return int(detached or 0)
