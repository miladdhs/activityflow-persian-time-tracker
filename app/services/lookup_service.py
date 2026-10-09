"""Activity types (categories), measurement units and activity titles."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from sqlalchemy import delete, func, select, update

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.text import clean_name, normalize_name
from app.database import read_session, write_session
from app.models import Activity, ActivityTitle, Category, Unit

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class CategoryInfo:
    id: int
    name: str
    color: str
    usage: int = 0


@dataclass(frozen=True)
class UnitInfo:
    id: int
    name: str
    usage: int = 0


@dataclass(frozen=True)
class TitleInfo:
    id: int
    name: str
    usage: int = 0
    total_minutes: int = 0


@dataclass(frozen=True)
class TitleUsage:
    """Values from the most recent activity with a given title, used to pre-fill forms."""

    project_id: int | None
    category_id: int | None
    unit_id: int | None


def _require_name(name: str, label: str, max_len: int) -> str:
    name = clean_name(name)
    if not name:
        raise ValidationError(f"{label} را وارد کنید.", "name")
    if len(name) > max_len:
        raise ValidationError(f"{label} حداکثر می‌تواند {max_len} نویسه باشد.", "name")
    return name


def _require_color(color: str) -> str:
    if not color or not _HEX.match(color):
        raise ValidationError("رنگ انتخاب‌شده معتبر نیست.", "color")
    return color.upper()


# --- categories --------------------------------------------------------------

def list_categories() -> list[CategoryInfo]:
    with read_session() as session:
        usage = (
            select(Activity.category_id, func.count(Activity.id).label("n"))
            .group_by(Activity.category_id)
            .subquery()
        )
        rows = session.execute(
            select(Category, func.coalesce(usage.c.n, 0))
            .outerjoin(usage, usage.c.category_id == Category.id)
            .order_by(Category.sort_order, Category.id)
        ).all()
        return [CategoryInfo(c.id, c.name, c.color, n) for c, n in rows]


def create_category(name: str, color: str) -> int:
    name = _require_name(name, "نام نوع فعالیت", 80)
    color = _require_color(color)
    key = normalize_name(name)
    with write_session() as session:
        if session.scalar(select(Category.id).where(Category.normalized_name == key)):
            raise ConflictError("این نوع فعالیت از قبل وجود دارد.")
        order = (session.scalar(select(func.max(Category.sort_order))) or 0) + 1
        category = Category(name=name, normalized_name=key, color=color, sort_order=order)
        session.add(category)
        session.flush()
        return category.id


def update_category(category_id: int, name: str, color: str) -> None:
    name = _require_name(name, "نام نوع فعالیت", 80)
    color = _require_color(color)
    key = normalize_name(name)
    with write_session() as session:
        category = session.get(Category, category_id)
        if category is None:
            raise NotFoundError("نوع فعالیت پیدا نشد.")
        clash = session.scalar(
            select(Category.id).where(Category.normalized_name == key, Category.id != category_id)
        )
        if clash:
            raise ConflictError("نوع فعالیت دیگری با همین نام وجود دارد.")
        category.name, category.normalized_name, category.color = name, key, color


def delete_category(category_id: int) -> int:
    """Delete a category; its activities are kept and become «بدون نوع»."""
    with write_session() as session:
        category = session.get(Category, category_id)
        if category is None:
            raise NotFoundError("نوع فعالیت پیدا نشد.")
        affected = session.scalar(
            select(func.count(Activity.id)).where(Activity.category_id == category_id)
        ) or 0
        session.execute(update(Activity).where(Activity.category_id == category_id).values(category_id=None))
        session.delete(category)
        return affected


# --- units -------------------------------------------------------------------

def list_units() -> list[UnitInfo]:
    with read_session() as session:
        usage = (
            select(Activity.unit_id, func.count(Activity.id).label("n"))
            .group_by(Activity.unit_id)
            .subquery()
        )
        rows = session.execute(
            select(Unit, func.coalesce(usage.c.n, 0))
            .outerjoin(usage, usage.c.unit_id == Unit.id)
            .order_by(Unit.id)
        ).all()
        return [UnitInfo(u.id, u.name, n) for u, n in rows]


def create_unit(name: str) -> int:
    name = _require_name(name, "نام واحد", 40)
    key = normalize_name(name)
    with write_session() as session:
        if session.scalar(select(Unit.id).where(Unit.normalized_name == key)):
            raise ConflictError("این واحد از قبل وجود دارد.")
        unit = Unit(name=name, normalized_name=key)
        session.add(unit)
        session.flush()
        return unit.id


def rename_unit(unit_id: int, name: str) -> None:
    name = _require_name(name, "نام واحد", 40)
    key = normalize_name(name)
    with write_session() as session:
        unit = session.get(Unit, unit_id)
        if unit is None:
            raise NotFoundError("واحد پیدا نشد.")
        if session.scalar(select(Unit.id).where(Unit.normalized_name == key, Unit.id != unit_id)):
            raise ConflictError("واحد دیگری با همین نام وجود دارد.")
        unit.name, unit.normalized_name = name, key


def delete_unit(unit_id: int) -> None:
    with write_session() as session:
        unit = session.get(Unit, unit_id)
        if unit is None:
            raise NotFoundError("واحد پیدا نشد.")
        used = session.scalar(select(func.count(Activity.id)).where(Activity.unit_id == unit_id)) or 0
        if used:
            raise ConflictError(
                f"این واحد در {used} فعالیت استفاده شده و قابل حذف نیست. "
                "برای حفظ دقت گزارش‌ها، ابتدا آن فعالیت‌ها را ویرایش کنید."
            )
        session.execute(
            update(ActivityTitle).where(ActivityTitle.default_unit_id == unit_id).values(default_unit_id=None)
        )
        session.delete(unit)


# --- activity titles --------------------------------------------------------

def list_titles() -> list[TitleInfo]:
    with read_session() as session:
        rows = session.execute(
            select(
                ActivityTitle.id,
                ActivityTitle.name,
                func.count(Activity.id),
                func.coalesce(func.sum(Activity.duration_minutes), 0),
            )
            .outerjoin(Activity, Activity.title_id == ActivityTitle.id)
            .group_by(ActivityTitle.id)
            .order_by(func.count(Activity.id).desc(), ActivityTitle.name)
        ).all()
        return [TitleInfo(i, n, c, m) for i, n, c, m in rows]


def title_names() -> list[str]:
    with read_session() as session:
        return list(session.scalars(select(ActivityTitle.name).order_by(ActivityTitle.name)))


def find_title(name: str) -> TitleInfo | None:
    key = normalize_name(name)
    if not key:
        return None
    with read_session() as session:
        row = session.execute(
            select(ActivityTitle.id, ActivityTitle.name).where(ActivityTitle.normalized_name == key)
        ).first()
        return TitleInfo(row[0], row[1]) if row else None


def similar_titles(name: str, limit: int = 3, cutoff: float = 0.6) -> list[str]:
    """Existing titles that look similar but are not identical (never merged automatically)."""
    key = normalize_name(name)
    if len(key) < 2:
        return []
    with read_session() as session:
        rows = session.execute(select(ActivityTitle.name, ActivityTitle.normalized_name)).all()
    scored = []
    for display, normalized in rows:
        if normalized == key:
            continue
        ratio = difflib.SequenceMatcher(None, key, normalized).ratio()
        if ratio >= cutoff or (len(key) >= 3 and (key in normalized or normalized in key)):
            scored.append((ratio, display))
    scored.sort(key=lambda item: -item[0])
    return [display for _, display in scored[:limit]]


def last_usage_for_title(name: str) -> TitleUsage | None:
    key = normalize_name(name)
    if not key:
        return None
    with read_session() as session:
        row = session.execute(
            select(Activity.project_id, Activity.category_id, Activity.unit_id, ActivityTitle.default_unit_id)
            .join(ActivityTitle, ActivityTitle.id == Activity.title_id)
            .where(ActivityTitle.normalized_name == key)
            .order_by(Activity.activity_date.desc(), Activity.id.desc())
            .limit(1)
        ).first()
        if row is None:
            return None
        return TitleUsage(row[0], row[1], row[2] or row[3])


def rename_title(title_id: int, name: str) -> None:
    name = _require_name(name, "عنوان فعالیت", 150)
    key = normalize_name(name)
    with write_session() as session:
        title = session.get(ActivityTitle, title_id)
        if title is None:
            raise NotFoundError("عنوان فعالیت پیدا نشد.")
        if session.scalar(
            select(ActivityTitle.id).where(ActivityTitle.normalized_name == key, ActivityTitle.id != title_id)
        ):
            raise ConflictError("عنوان دیگری با همین نام وجود دارد. برای یکی‌کردن آن‌ها از «ادغام» استفاده کنید.")
        title.name, title.normalized_name = name, key


def merge_titles(source_id: int, target_id: int) -> int:
    """Move every activity of ``source`` to ``target`` and remove ``source``."""
    if source_id == target_id:
        raise ValidationError("عنوان مبدأ و مقصد نباید یکسان باشند.")
    with write_session() as session:
        source = session.get(ActivityTitle, source_id)
        target = session.get(ActivityTitle, target_id)
        if source is None or target is None:
            raise NotFoundError("عنوان فعالیت پیدا نشد.")
        moved = session.execute(
            update(Activity).where(Activity.title_id == source_id).values(title_id=target_id)
        ).rowcount
        session.delete(source)
        return int(moved or 0)


def remove_orphan_titles(session) -> None:
    used = select(Activity.title_id).distinct()
    session.execute(delete(ActivityTitle).where(ActivityTitle.id.not_in(used)))
