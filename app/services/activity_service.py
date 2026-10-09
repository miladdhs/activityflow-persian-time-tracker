"""Activities: validation, persistence, filtering and pagination."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Select, and_, func, or_, select

from app.core.errors import NotFoundError, ValidationError
from app.core.text import clean_name, clean_text, normalize_name, parse_decimal
from app.database import read_session, write_session
from app.models import Activity, ActivityTitle, Category, Project, Unit
from app.services.lookup_service import remove_orphan_titles
from app.services.project_service import OPEN_STATUSES

NONE_ID = 0  # filter value meaning «بدون پروژه» / «بدون نوع»
MAX_MINUTES = 24 * 60
MAX_QUANTITY = Decimal("1000000000")
MIN_DATE = date(2000, 1, 1)


@dataclass
class ActivityInput:
    title: str
    activity_date: date | None
    project_id: int | None = None
    category_id: int | None = None
    time_mode: str = "duration"  # "range" | "duration"
    start_time: time | None = None
    end_time: time | None = None
    duration_minutes: int | None = None
    quantity: str | Decimal | None = None
    unit_id: int | None = None
    notes: str = ""


@dataclass
class ActivityRow:
    id: int
    title_id: int
    title: str
    project_id: int | None
    project_name: str | None
    project_color: str | None
    category_id: int | None
    category_name: str | None
    category_color: str | None
    activity_date: date
    start_time: time | None
    end_time: time | None
    duration_minutes: int
    quantity: Decimal | None
    unit_id: int | None
    unit_name: str | None
    notes: str
    created_at: datetime

    @property
    def time_mode(self) -> str:
        return "range" if self.start_time and self.end_time else "duration"


@dataclass
class ActivityFilter:
    search: str = ""
    project_id: int | None = None
    category_id: int | None = None
    title_id: int | None = None
    unit_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None

    def is_empty(self) -> bool:
        return not (
            self.search.strip() or self.project_id is not None or self.category_id is not None
            or self.title_id is not None or self.unit_id is not None
            or self.date_from or self.date_to
        )


@dataclass
class ActivityPage:
    rows: list[ActivityRow]
    total: int
    total_minutes: int
    page: int
    page_count: int


SORTS = {
    "date_desc": (Activity.activity_date.desc(), Activity.start_time.desc(), Activity.id.desc()),
    "date_asc": (Activity.activity_date.asc(), Activity.start_time.asc(), Activity.id.asc()),
    "duration_desc": (Activity.duration_minutes.desc(), Activity.activity_date.desc(), Activity.id.desc()),
    "duration_asc": (Activity.duration_minutes.asc(), Activity.activity_date.desc(), Activity.id.desc()),
}


def quantity_from_milli(value: int | None) -> Decimal | None:
    if value is None:
        return None
    return (Decimal(value) / 1000).normalize() if value % 1000 else Decimal(value // 1000)


# --- validation ----------------------------------------------------------------

@dataclass
class _Clean:
    title: str
    activity_date: date
    start_time: time | None
    end_time: time | None
    duration: int
    quantity_milli: int | None
    unit_id: int | None
    notes: str


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def validate(inp: ActivityInput, today: date | None = None) -> _Clean:
    today = today or date.today()
    title = clean_name(inp.title)
    if not title:
        raise ValidationError("عنوان فعالیت را وارد کنید.", "title")
    if len(title) > 150:
        raise ValidationError("عنوان فعالیت حداکثر می‌تواند ۱۵۰ نویسه باشد.", "title")

    if inp.activity_date is None:
        raise ValidationError("تاریخ فعالیت را انتخاب کنید.", "date")
    if inp.activity_date > today:
        raise ValidationError("تاریخ فعالیت نمی‌تواند بعد از امروز باشد.", "date")
    if inp.activity_date < MIN_DATE:
        raise ValidationError("تاریخ واردشده معتبر نیست.", "date")

    start = end = None
    if inp.time_mode == "range":
        if inp.start_time is None:
            raise ValidationError("ساعت شروع را وارد کنید.", "start")
        if inp.end_time is None:
            raise ValidationError("ساعت پایان را وارد کنید.", "end")
        start = inp.start_time.replace(second=0, microsecond=0)
        end = inp.end_time.replace(second=0, microsecond=0)
        duration = _minutes(end) - _minutes(start)
        if duration <= 0:
            raise ValidationError("ساعت پایان باید بعد از ساعت شروع باشد.", "end")
    else:
        duration = int(inp.duration_minutes or 0)
        if duration < 0 or duration > MAX_MINUTES:
            raise ValidationError("مدت‌زمان باید بین ۰ تا ۲۴ ساعت باشد.", "duration")

    quantity_milli = None
    unit_id = None
    raw_quantity = inp.quantity
    if raw_quantity not in (None, ""):
        try:
            quantity = parse_decimal(str(raw_quantity))
        except ValueError:
            raise ValidationError("مقدار واردشده عدد معتبری نیست.", "quantity") from None
        if quantity is not None:
            if quantity <= 0:
                raise ValidationError("مقدار باید بزرگ‌تر از صفر باشد.", "quantity")
            if quantity > MAX_QUANTITY:
                raise ValidationError("مقدار واردشده بیش از حد بزرگ است.", "quantity")
            if quantity.normalize().as_tuple().exponent < -3:
                raise ValidationError("حداکثر سه رقم اعشار مجاز است.", "quantity")
            if inp.unit_id is None:
                raise ValidationError("واحد مقدار را انتخاب کنید.", "unit")
            quantity_milli = int(quantity * 1000)
            unit_id = inp.unit_id

    if duration == 0 and quantity_milli is None:
        raise ValidationError("مدت‌زمان یا مقدار فعالیت را وارد کنید.", "duration")

    notes = clean_text(inp.notes)
    if len(notes) > 4000:
        raise ValidationError("توضیحات حداکثر می‌تواند ۴۰۰۰ نویسه باشد.", "notes")

    return _Clean(title, inp.activity_date, start, end, duration, quantity_milli, unit_id, notes)


def _check_references(session, inp: ActivityInput, clean: _Clean, current_project: int | None) -> None:
    if inp.project_id is not None:
        project = session.get(Project, inp.project_id)
        if project is None:
            raise ValidationError("پروژه انتخاب‌شده پیدا نشد.", "project")
        if project.status not in OPEN_STATUSES and project.id != current_project:
            raise ValidationError("این پروژه بسته یا بایگانی شده و فعالیت جدید نمی‌پذیرد.", "project")
    if inp.category_id is not None and session.get(Category, inp.category_id) is None:
        raise ValidationError("نوع فعالیت انتخاب‌شده پیدا نشد.", "category")
    if clean.unit_id is not None and session.get(Unit, clean.unit_id) is None:
        raise ValidationError("واحد انتخاب‌شده پیدا نشد.", "unit")


def _title_for(session, name: str, unit_id: int | None) -> ActivityTitle:
    key = normalize_name(name)
    title = session.scalar(select(ActivityTitle).where(ActivityTitle.normalized_name == key))
    if title is None:
        title = ActivityTitle(name=name, normalized_name=key, default_unit_id=unit_id)
        session.add(title)
        session.flush()
    elif unit_id is not None:
        title.default_unit_id = unit_id
    return title


# --- commands ----------------------------------------------------------------------

def create_activity(inp: ActivityInput) -> int:
    clean = validate(inp)
    with write_session() as session:
        _check_references(session, inp, clean, None)
        title = _title_for(session, clean.title, clean.unit_id)
        activity = Activity(
            title_id=title.id,
            project_id=inp.project_id,
            category_id=inp.category_id,
            activity_date=clean.activity_date,
            start_time=clean.start_time,
            end_time=clean.end_time,
            duration_minutes=clean.duration,
            quantity_milli=clean.quantity_milli,
            unit_id=clean.unit_id,
            notes=clean.notes,
        )
        session.add(activity)
        session.flush()
        return activity.id


def update_activity(activity_id: int, inp: ActivityInput) -> None:
    clean = validate(inp)
    with write_session() as session:
        activity = session.get(Activity, activity_id)
        if activity is None:
            raise NotFoundError("این فعالیت پیدا نشد؛ ممکن است قبلاً حذف شده باشد.")
        _check_references(session, inp, clean, activity.project_id)
        title = _title_for(session, clean.title, clean.unit_id)
        activity.title_id = title.id
        activity.project_id = inp.project_id
        activity.category_id = inp.category_id
        activity.activity_date = clean.activity_date
        activity.start_time = clean.start_time
        activity.end_time = clean.end_time
        activity.duration_minutes = clean.duration
        activity.quantity_milli = clean.quantity_milli
        activity.unit_id = clean.unit_id
        activity.notes = clean.notes
        session.flush()
        remove_orphan_titles(session)


def delete_activity(activity_id: int) -> None:
    with write_session() as session:
        activity = session.get(Activity, activity_id)
        if activity is None:
            raise NotFoundError("این فعالیت پیدا نشد؛ ممکن است قبلاً حذف شده باشد.")
        session.delete(activity)
        session.flush()
        remove_orphan_titles(session)


# --- queries --------------------------------------------------------------------

def with_joins(stmt: Select) -> Select:
    """Join the lookup tables used by filters and display columns."""
    return (
        stmt.join(ActivityTitle, ActivityTitle.id == Activity.title_id)
        .outerjoin(Project, Project.id == Activity.project_id)
        .outerjoin(Category, Category.id == Activity.category_id)
        .outerjoin(Unit, Unit.id == Activity.unit_id)
    )


def base_select() -> Select:
    return with_joins(
        select(
            Activity,
            ActivityTitle.name,
            Project.name,
            Project.color,
            Category.name,
            Category.color,
            Unit.name,
        ).select_from(Activity)
    )


def _id_condition(column, value: int | None):
    if value is None:
        return None
    return column.is_(None) if value == NONE_ID else column == value


def apply_filter(stmt: Select, f: ActivityFilter) -> Select:
    conditions = []
    for column, value in (
        (Activity.project_id, f.project_id),
        (Activity.category_id, f.category_id),
        (Activity.title_id, f.title_id),
        (Activity.unit_id, f.unit_id),
    ):
        cond = _id_condition(column, value)
        if cond is not None:
            conditions.append(cond)
    if f.date_from:
        conditions.append(Activity.activity_date >= f.date_from)
    if f.date_to:
        conditions.append(Activity.activity_date <= f.date_to)
    text = f.search.strip()
    if text:
        key = normalize_name(text)
        conditions.append(
            or_(
                ActivityTitle.normalized_name.contains(key, autoescape=True),
                Project.normalized_name.contains(key, autoescape=True),
                Category.normalized_name.contains(key, autoescape=True),
                Activity.notes.contains(clean_text(text), autoescape=True),
            )
        )
    return stmt.where(and_(*conditions)) if conditions else stmt


def _row(result) -> ActivityRow:
    a, title, p_name, p_color, c_name, c_color, u_name = result
    return ActivityRow(
        id=a.id,
        title_id=a.title_id,
        title=title,
        project_id=a.project_id,
        project_name=p_name,
        project_color=p_color,
        category_id=a.category_id,
        category_name=c_name,
        category_color=c_color,
        activity_date=a.activity_date,
        start_time=a.start_time,
        end_time=a.end_time,
        duration_minutes=a.duration_minutes,
        quantity=quantity_from_milli(a.quantity_milli),
        unit_id=a.unit_id,
        unit_name=u_name,
        notes=a.notes or "",
        created_at=a.created_at,
    )


def query_activities(
    f: ActivityFilter, sort: str = "date_desc", page: int = 1, page_size: int = 25
) -> ActivityPage:
    page_size = max(1, min(int(page_size), 500))
    with read_session() as session:
        stats_stmt = apply_filter(
            with_joins(
                select(func.count(Activity.id), func.coalesce(func.sum(Activity.duration_minutes), 0))
                .select_from(Activity)
            ),
            f,
        )
        total, total_minutes = (int(v) for v in session.execute(stats_stmt).one())
        page_count = max(1, -(-total // page_size))
        page = max(1, min(page, page_count))
        stmt = (
            apply_filter(base_select(), f)
            .order_by(*SORTS.get(sort, SORTS["date_desc"]))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = [_row(r) for r in session.execute(stmt)]
    return ActivityPage(rows, total, total_minutes, page, page_count)


def list_activities(f: ActivityFilter | None = None, sort: str = "date_desc", limit: int | None = None) -> list[ActivityRow]:
    with read_session() as session:
        stmt = apply_filter(base_select(), f or ActivityFilter()).order_by(*SORTS.get(sort, SORTS["date_desc"]))
        if limit:
            stmt = stmt.limit(limit)
        return [_row(r) for r in session.execute(stmt)]


def get_activity(activity_id: int) -> ActivityRow:
    with read_session() as session:
        result = session.execute(base_select().where(Activity.id == activity_id)).first()
    if result is None:
        raise NotFoundError("این فعالیت پیدا نشد؛ ممکن است قبلاً حذف شده باشد.")
    return _row(result)


def has_any_activity() -> bool:
    with read_session() as session:
        return session.scalar(select(Activity.id).limit(1)) is not None


def first_activity_date() -> date | None:
    with read_session() as session:
        return session.scalar(select(func.min(Activity.activity_date)))


def recent_activities(limit: int = 6) -> list[ActivityRow]:
    with read_session() as session:
        stmt = base_select().order_by(Activity.created_at.desc(), Activity.id.desc()).limit(limit)
        return [_row(r) for r in session.execute(stmt)]


def activities_on(day: date) -> list[ActivityRow]:
    return list_activities(ActivityFilter(date_from=day, date_to=day), sort="date_desc")
