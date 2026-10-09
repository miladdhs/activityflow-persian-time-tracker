from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QWidget

from app import APP_NAME
from app.core import formatting as fmt
from app.core.errors import AppError
from app.core.settings_keys import DEFAULTS, PAGE_SIZES, Key
from app.reports.csv_export import export_records_csv
from app.services import activity_service, lookup_service, project_service, settings_service
from app.services.activity_service import NONE_ID, ActivityFilter
from app.ui.dialogs.activity_dialog import ActivityDialog, confirm_delete_activity
from app.ui.events import toast
from app.ui.files import ask_save_path, reveal_file
from app.ui.pages.base import BasePage
from app.ui.widgets.common import Card, IconButton, Menu, button, label, repolish
from app.ui.widgets.date_picker import DateField
from app.ui.widgets.dialogs import MessageDialog
from app.ui.widgets.display import EmptyState, Pager
from app.ui.widgets.inputs import ComboBox, SearchInput
from app.ui.widgets.table import Column, DataTable

ALL = -1  # combo value meaning "no filter"


def _quantity(row) -> str:
    return f"{fmt.fmt_decimal(row.quantity)} {row.unit_name}" if row.quantity is not None else "—"


def _time_tooltip(row) -> str:
    text = fmt.fmt_duration(row.duration_minutes) if row.duration_minutes else "بدون مدت‌زمان"
    if row.start_time and row.end_time:
        text += f"\nاز {fmt.fmt_time(row.start_time)} تا {fmt.fmt_time(row.end_time)}"
    return text


class HistoryPage(BasePage):
    key = "history"
    title = "تاریخچه فعالیت‌ها"
    subtitle = "جست‌وجو، فیلتر، ویرایش و حذف فعالیت‌های ثبت‌شده"
    topics = {"activities", "projects", "lookups", "settings"}
    scrollable = False

    def __init__(self, window):
        super().__init__(window)
        self.sort = "date_desc"
        self.page = 1
        size = settings_service.get_int(Key.PAGE_SIZE)
        self.page_size = size if size in PAGE_SIZES else int(DEFAULTS[Key.PAGE_SIZE])
        self._total = 0

        # filters -------------------------------------------------------------------
        filters = Card(padding=14, spacing=0)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.search = SearchInput("جست‌وجو در عنوان، پروژه، نوع یا توضیحات")
        self.search.search_changed.connect(lambda _: self._filters_changed())
        row.addWidget(self.search, 1)
        self.project = ComboBox(min_width=170)
        self.project.currentIndexChanged.connect(lambda _: self._filters_changed())
        row.addWidget(self.project)
        self.category = ComboBox(min_width=150)
        self.category.currentIndexChanged.connect(lambda _: self._filters_changed())
        row.addWidget(self.category)
        self.date_from = DateField(allow_empty=True, placeholder="از تاریخ", max_date=None)
        self.date_from.date_changed.connect(lambda _: self._filters_changed())
        self.date_to = DateField(allow_empty=True, placeholder="تا تاریخ", max_date=None)
        self.date_to.date_changed.connect(lambda _: self._filters_changed())
        row.addWidget(self.date_from)
        row.addWidget(self.date_to)
        self.clear_btn = IconButton("close-square", "پاک‌کردن همه فیلترها", size=40, icon_px=20)
        self.clear_btn.clicked.connect(self.clear_filters)
        row.addWidget(self.clear_btn)
        filters.body.addLayout(row)
        self.layout_.addWidget(filters)

        # table -----------------------------------------------------------------------
        self.table_card = Card(padding=0, spacing=0)
        head = QHBoxLayout()
        head.setContentsMargins(20, 16, 20, 12)
        head.setSpacing(12)
        head.addWidget(label("فعالیت‌ها", "h3"))
        self.summary = label("", "small")
        head.addWidget(self.summary)
        head.addStretch(1)
        self.table_card.body.addLayout(head)

        self.table = DataTable(
            [
                Column("عنوان فعالیت", lambda r: r.title, None, tooltip=lambda r: r.notes or r.title),
                Column("پروژه", lambda r: r.project_name or "بدون پروژه", 180,
                       color=lambda r: r.project_color, muted=lambda r: r.project_id is None),
                Column("نوع فعالیت", lambda r: r.category_name or "بدون نوع", 160,
                       color=lambda r: r.category_color, muted=lambda r: r.category_id is None),
                Column("تاریخ", lambda r: fmt.fmt_date(r.activity_date), 120, "center",
                       tooltip=lambda r: fmt.fmt_date_with_weekday(r.activity_date), sort_key="date"),
                Column("مدت‌زمان", lambda r: fmt.fmt_duration_short(r.duration_minutes) if r.duration_minutes else "—",
                       130, "center", tooltip=_time_tooltip, muted=lambda r: not r.duration_minutes, sort_key="duration"),
                Column("مقدار", _quantity, 120, "center", muted=lambda r: r.quantity is None),
                Column("", width=96, actions=True),
            ]
        )
        self.table.set_row_widgets(self._row_actions)
        self.table.row_activated.connect(lambda r: self._edit(r))
        self.table.context_requested.connect(self._context_menu)
        self.table.sort_requested.connect(self._on_sort)

        self.empty = EmptyState("paper", "هنوز فعالیتی ثبت نشده است.", "", "ثبت فعالیت")
        self.empty.action_clicked.connect(self._empty_action)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.empty)
        self.table_card.body.addWidget(self.stack, 1)

        pager_holder = QWidget()
        pager_layout = QHBoxLayout(pager_holder)
        pager_layout.setContentsMargins(20, 12, 20, 14)
        self.pager = Pager(PAGE_SIZES)
        self.pager.set_page_size(self.page_size)
        self.pager.page_changed.connect(self._go_page)
        self.pager.page_size_changed.connect(self._on_page_size)
        pager_layout.addWidget(self.pager)
        self.pager_holder = pager_holder
        self.table_card.body.addWidget(pager_holder)
        self.layout_.addWidget(self.table_card, 1)
        self._loading = False

    def header_actions(self) -> list[QWidget]:
        export = button("خروجی CSV", "secondary", "download", tooltip="ذخیره فعالیت‌های فیلترشده در فایل CSV")
        export.clicked.connect(self.export_csv)
        add = button("ثبت فعالیت", "primary", "plus", tooltip="Ctrl+N")
        add.clicked.connect(lambda: self.window_.open_entry())
        return [export, add]

    # filters -------------------------------------------------------------------------

    def _reload_choices(self) -> None:
        self._loading = True
        self.project.set_items(
            [("همه پروژه‌ها", ALL), ("بدون پروژه", NONE_ID)]
            + [(p.name, p.id, p.color) for p in project_service.all_projects()]
        )
        self.category.set_items(
            [("همه انواع", ALL), ("بدون نوع", NONE_ID)]
            + [(c.name, c.id, c.color) for c in lookup_service.list_categories()]
        )
        self._loading = False

    def current_filter(self) -> ActivityFilter:
        project = self.project.currentData()
        category = self.category.currentData()
        return ActivityFilter(
            search=self.search.text(),
            project_id=None if project in (None, ALL) else project,
            category_id=None if category in (None, ALL) else category,
            date_from=self.date_from.date(),
            date_to=self.date_to.date(),
        )

    def set_filter(self, project_id: int | None = None, category_id: int | None = None,
                   date_from: date | None = None, date_to: date | None = None, search: str = "") -> None:
        """Called by other pages (e.g. «مشاهده فعالیت‌ها» on a project card)."""
        self._reload_choices()
        self._loading = True
        self.search.blockSignals(True)
        self.search.setText(search)
        self.search.blockSignals(False)
        self.project.set_current_data(ALL if project_id is None else project_id)
        self.category.set_current_data(ALL if category_id is None else category_id)
        self.date_from.set_date(date_from, emit=False)
        self.date_to.set_date(date_to, emit=False)
        self._loading = False
        self.page = 1
        self._dirty = True

    def clear_filters(self) -> None:
        self.set_filter()
        self.refresh_now()

    def _filters_changed(self) -> None:
        if self._loading:
            return
        self.page = 1
        self.refresh_now()

    # data --------------------------------------------------------------------------------

    def refresh(self) -> None:
        self._reload_choices()
        f = self.current_filter()
        bad_range = bool(f.date_from and f.date_to and f.date_from > f.date_to)
        self.date_to.setProperty("error", bad_range)
        self.date_to.setToolTip("تاریخ پایان نباید قبل از تاریخ شروع باشد." if bad_range else "")
        repolish(self.date_to)

        result = activity_service.query_activities(f, self.sort, self.page, self.page_size)
        if result.page != self.page:
            self.page = result.page
        self._total = result.total
        self.table.set_rows(result.rows)
        self.table.set_sort_indicator(self.sort.split("_")[0], self.sort.endswith("desc"))
        self.clear_btn.setVisible(not f.is_empty())

        if result.total:
            self.stack.setCurrentWidget(self.table)
            self.summary.setText(
                f"{fmt.fmt_int(result.total)} فعالیت  ·  مجموع {fmt.fmt_duration(result.total_minutes)}"
                if result.total_minutes else f"{fmt.fmt_int(result.total)} فعالیت"
            )
        else:
            self.stack.setCurrentWidget(self.empty)
            self.summary.setText("")
            if f.is_empty():
                self.empty.set_texts("هنوز فعالیتی ثبت نشده است.", "اولین فعالیت خود را ثبت کنید تا اینجا نمایش داده شود.", "ثبت فعالیت")
            else:
                self.empty.set_texts("نتیجه‌ای پیدا نشد", "هیچ فعالیتی با این فیلترها مطابقت ندارد. فیلترها را تغییر دهید یا پاک کنید.", "پاک‌کردن فیلترها")
        self.pager_holder.setVisible(result.total > 0)
        self.pager.update_state(result.page, result.page_count, result.total, self.page_size)

    def _empty_action(self) -> None:
        if self.current_filter().is_empty():
            self.window_.open_entry()
        else:
            self.clear_filters()

    def _go_page(self, page: int) -> None:
        self.page = max(1, page)
        self.refresh_now()
        self.table.scrollToTop()

    def _on_page_size(self, size: int) -> None:
        self.page_size = size
        self.page = 1
        settings_service.set(Key.PAGE_SIZE, size)
        self.refresh_now()

    def _on_sort(self, key: str) -> None:
        current_key, direction = self.sort.split("_")
        if key == current_key:
            direction = "asc" if direction == "desc" else "desc"
        else:
            direction = "desc"
        self.sort = f"{key}_{direction}"
        self.page = 1
        self.refresh_now()

    # row actions -------------------------------------------------------------------------

    def _row_actions(self, row) -> QWidget:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        edit = IconButton("edit", "ویرایش", size=32, icon_px=17)
        edit.clicked.connect(lambda: self._edit(row))
        delete = IconButton("delete", "حذف", tone="danger", size=32, icon_px=17)
        delete.clicked.connect(lambda: confirm_delete_activity(self, row.id, row.title))
        layout.addWidget(edit)
        layout.addWidget(delete)
        return holder

    def _edit(self, row) -> None:
        ActivityDialog.edit(self, row.id)

    def _duplicate(self, row) -> None:
        self.window_.open_entry(
            template={
                "title": row.title,
                "project_id": row.project_id,
                "category_id": row.category_id,
                "unit_id": row.unit_id,
                "quantity": row.quantity,
                "duration": row.duration_minutes or None,
                "notes": row.notes,
            }
        )

    def _context_menu(self, row, pos) -> None:
        menu = Menu(self)
        menu.item("ویرایش فعالیت", lambda: self._edit(row), "edit")
        menu.item("ثبت دوباره (کپی)", lambda: self._duplicate(row), "paper-plus")
        menu.addSeparator()
        menu.item("حذف فعالیت", lambda: confirm_delete_activity(self, row.id, row.title), "delete", danger=True)
        menu.exec(pos)

    # export -------------------------------------------------------------------------------

    def export_csv(self) -> None:
        f = self.current_filter()
        rows = activity_service.list_activities(f, self.sort)
        if not rows:
            MessageDialog.info(self, "خروجی CSV", "فعالیتی برای خروجی گرفتن وجود ندارد.")
            return
        path = ask_save_path(self, "ذخیره خروجی CSV", f"{APP_NAME}-history-{date.today():%Y-%m-%d}.csv", "CSV (*.csv)")
        if path is None:
            return
        try:
            export_records_csv(rows, path)
        except AppError as exc:
            MessageDialog.error(self, exc.message)
            return
        toast(f"{fmt.fmt_int(len(rows))} فعالیت در فایل CSV ذخیره شد.", action=("نمایش فایل", lambda: reveal_file(path)))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            row = self.table.current_row()
            if row is not None:
                confirm_delete_activity(self, row.id, row.title)
                return
        super().keyPressEvent(event)

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()
