from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from app.core import formatting as fmt
from app.core.errors import AppError
from app.services import project_service
from app.services.project_service import STATUSES, ProjectInfo
from app.ui.dialogs.project_dialog import ProjectDialog, confirm_delete_project
from app.ui.events import notify, toast
from app.ui.pages.base import BasePage
from app.ui.theme import tokens as t
from app.ui.widgets.common import (
    STATUS_BADGE,
    Badge,
    Card,
    Divider,
    IconButton,
    IconTile,
    Menu,
    SegmentedControl,
    button,
    clear_layout,
    label,
)
from app.ui.widgets.dialogs import MessageDialog
from app.ui.widgets.display import EmptyState
from app.ui.widgets.inputs import SearchInput

CARD_MIN_WIDTH = 330


def _elide(text: str, limit: int = 110) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class ProjectCard(Card):
    open_requested = Signal(object)
    menu_requested = Signal(object, QPoint)

    def __init__(self, project: ProjectInfo):
        super().__init__(padding=20, spacing=14)
        self.project = project
        self.setProperty("interactive", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("برای مشاهده فعالیت‌های این پروژه کلیک کنید")
        self.setMinimumWidth(CARD_MIN_WIDTH - 40)

        head = QHBoxLayout()
        head.setSpacing(12)
        head.addWidget(IconTile("folder", project.color, 44, 22), 0, Qt.AlignmentFlag.AlignTop)
        titles = QVBoxLayout()
        titles.setSpacing(6)
        name = label(project.name, "h3")
        name.setToolTip(project.name)
        titles.addWidget(name)
        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)
        badge_row.addWidget(Badge(project.status_label, STATUS_BADGE.get(project.status, "neutral")))
        badge_row.addStretch(1)
        titles.addLayout(badge_row)
        head.addLayout(titles, 1)
        self.menu_btn = IconButton("more-circle", "گزینه‌ها", size=32, icon_px=18)
        self.menu_btn.clicked.connect(
            lambda: self.menu_requested.emit(self.project, self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height())))
        )
        head.addWidget(self.menu_btn, 0, Qt.AlignmentFlag.AlignTop)
        self.body.addLayout(head)

        desc = label(_elide(project.description) if project.description else "بدون توضیحات", "secondary" if project.description else "muted", wrap=True)
        desc.setMinimumHeight(40)
        desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeading)
        self.body.addWidget(desc)
        self.body.addWidget(Divider())

        stats = QHBoxLayout()
        stats.setSpacing(8)
        for caption, value in (
            ("مجموع زمان", fmt.fmt_duration_short(project.total_minutes) if project.total_minutes else "—"),
            ("فعالیت‌ها", fmt.fmt_int(project.activity_count)),
            ("آخرین فعالیت", fmt.relative_day(project.last_activity) if project.last_activity else "—"),
        ):
            col = QVBoxLayout()
            col.setSpacing(2)
            col.addWidget(label(caption, "caption"))
            v = label(value)
            v.setStyleSheet("font-weight: 600;")
            col.addWidget(v)
            stats.addLayout(col, 1)
        self.body.addLayout(stats)
        if project.start_date:
            self.body.addWidget(label(f"شروع: {fmt.fmt_date(project.start_date)}", "caption"))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.open_requested.emit(self.project)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.menu_requested.emit(self.project, event.globalPos())


class ProjectsPage(BasePage):
    key = "projects"
    title = "پروژه‌ها"
    subtitle = "پروژه‌ها را بسازید، وضعیتشان را مدیریت کنید و زمان صرف‌شده را ببینید"
    topics = {"activities", "projects", "settings"}

    def __init__(self, window):
        super().__init__(window)
        self.status = "open"
        self._projects: list[ProjectInfo] = []
        self._cols = 0

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.segments = SegmentedControl(
            [("open", "جاری"), ("active", "فعال"), ("paused", "متوقف"), ("completed", "تکمیل‌شده"), ("archived", "بایگانی"), ("all", "همه")],
            "open",
        )
        self.segments.changed.connect(self._on_status)
        toolbar.addWidget(self.segments)
        toolbar.addStretch(1)
        self.search = SearchInput("جست‌وجوی پروژه", size="sm")
        self.search.setFixedWidth(260)
        self.search.search_changed.connect(lambda _: self.refresh_now())
        toolbar.addWidget(self.search)
        self.layout_.addLayout(toolbar)

        self.grid_holder = QWidget()
        self.grid = QGridLayout(self.grid_holder)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(t.SPACE_4)
        self.layout_.addWidget(self.grid_holder)

        self.empty = EmptyState("folder", "", "", "پروژه جدید")
        self.empty.action_clicked.connect(self.new_project)
        self.layout_.addWidget(self.empty)
        self.layout_.addStretch(1)

    def header_actions(self) -> list[QWidget]:
        add = button("پروژه جدید", "primary", "plus")
        add.clicked.connect(self.new_project)
        return [add]

    # data -------------------------------------------------------------------------------

    def _on_status(self, key: str) -> None:
        self.status = key
        self.refresh_now()

    def refresh(self) -> None:
        counts = project_service.status_counts()
        total = sum(counts.values())
        open_count = counts.get("active", 0) + counts.get("paused", 0)
        self.segments.set_label("open", f"جاری  {fmt.digits(open_count)}")
        for key, text in (("active", "فعال"), ("paused", "متوقف"), ("completed", "تکمیل‌شده"), ("archived", "بایگانی")):
            self.segments.set_label(key, f"{text}  {fmt.digits(counts.get(key, 0))}")
        self.segments.set_label("all", f"همه  {fmt.digits(total)}")

        status = None if self.status in ("all", "open") else self.status
        projects = project_service.list_projects(status, self.search.text())
        if self.status == "open":
            projects = [p for p in projects if p.status in project_service.OPEN_STATUSES]
        self._projects = projects
        self._cols = 0
        self._build_grid()

        has = bool(projects)
        self.grid_holder.setVisible(has)
        self.empty.setVisible(not has)
        if not has:
            if total == 0:
                self.empty.set_texts("هنوز پروژه‌ای نساخته‌اید", "پروژه‌ها به شما کمک می‌کنند زمان و فعالیت‌ها را دسته‌بندی و گزارش کنید.", "ساخت اولین پروژه")
            elif self.search.text().strip():
                self.empty.set_texts("پروژه‌ای پیدا نشد", "عبارت جست‌وجو را تغییر دهید.", "")
            else:
                self.empty.set_texts("پروژه‌ای در این وضعیت نیست", "وضعیت دیگری را انتخاب کنید یا یک پروژه جدید بسازید.", "پروژه جدید")

    def _columns(self) -> int:
        width = self.grid_holder.width() or (self.width() - 2 * t.PAGE_MARGIN)
        return max(1, min(4, (width + t.SPACE_4) // (CARD_MIN_WIDTH + t.SPACE_4)))

    def _build_grid(self) -> None:
        cols = self._columns()
        self._cols = cols
        clear_layout(self.grid)
        for c in range(6):
            self.grid.setColumnStretch(c, 0)
        for i, project in enumerate(self._projects):
            card = ProjectCard(project)
            card.open_requested.connect(self._open_activities)
            card.menu_requested.connect(self._menu)
            self.grid.addWidget(card, i // cols, i % cols)
        for c in range(cols):
            self.grid.setColumnStretch(c, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._projects and self._columns() != self._cols:
            self._build_grid()

    # actions -------------------------------------------------------------------------------

    def new_project(self) -> None:
        ProjectDialog(self).exec()

    def _open_activities(self, project: ProjectInfo) -> None:
        self.window_.show_history(project_id=project.id)

    def _menu(self, project: ProjectInfo, pos: QPoint) -> None:
        menu = Menu(self)
        menu.item("مشاهده فعالیت‌ها", lambda: self._open_activities(project), "time-circle")
        menu.item("ویرایش پروژه", lambda: ProjectDialog(self, project).exec(), "edit")
        status_menu = menu.submenu("تغییر وضعیت", "swap")
        for key, text in STATUSES.items():
            act = status_menu.item(text, lambda k=key: self._set_status(project, k), "tick-square" if key == project.status else None)
            act.setEnabled(key != project.status)
        menu.addSeparator()
        menu.item("حذف پروژه", lambda: confirm_delete_project(self, project), "delete", danger=True)
        menu.exec(pos)

    def _set_status(self, project: ProjectInfo, status: str) -> None:
        try:
            project_service.set_status(project.id, status)
        except AppError as exc:
            MessageDialog.error(self, exc.message)
            return
        notify("projects")
        toast(f"وضعیت «{project.name}» به «{STATUSES[status]}» تغییر کرد.")
