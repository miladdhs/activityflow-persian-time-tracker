from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from app import APP_NAME
from app.core import formatting as fmt
from app.core.errors import AppError
from app.reports.csv_export import export_groups_csv, export_records_csv
from app.services import activity_service, lookup_service, project_service, report_service
from app.services.activity_service import NONE_ID, ActivityFilter
from app.services.report_service import GROUP_BY, GROUP_SORTS, ReportResult
from app.ui.dialogs.report_details_dialog import ReportDetailsDialog
from app.ui.events import toast
from app.ui.files import ask_save_path, reveal_file
from app.ui.pages.base import BasePage
from app.ui.theme import tokens as t
from app.ui.widgets.charts import BarChart, BarPoint, DonutChart, HBarList, Legend, Segment
from app.ui.widgets.common import Card, IconButton, Menu, SectionCard, SegmentedControl, button, label
from app.ui.widgets.date_picker import DateField
from app.ui.widgets.dialogs import MessageDialog
from app.ui.widgets.display import EmptyState, StatCard
from app.ui.widgets.inputs import ComboBox, FormField
from app.ui.widgets.table import Column, DataTable

ALL = -1


def _quantities_text(quantities) -> str:
    return "  ·  ".join(f"{fmt.fmt_decimal(q)} {u}" for u, q in quantities) or "—"


class ReportsPage(BasePage):
    key = "reports"
    title = "گزارش‌ها"
    subtitle = "تحلیل زمان و مقدار فعالیت‌ها بر اساس بازه، پروژه، نوع و عنوان"
    topics = {"activities", "projects", "lookups", "settings"}

    def __init__(self, window):
        super().__init__(window)
        self.result: ReportResult | None = None
        self._loading = False
        self._range_initialized = False

        # filters ---------------------------------------------------------------------
        filters = Card(padding=18, spacing=14)
        period_row = QHBoxLayout()
        period_row.setSpacing(10)
        self.period = SegmentedControl([("month", "ماهانه"), ("year", "سالانه"), ("custom", "بازه دلخواه")], "month")
        self.period.changed.connect(self._on_period)
        period_row.addWidget(self.period)
        period_row.addSpacing(6)

        self.prev_btn = IconButton("arrow-right", "دوره قبل", size=40, icon_px=18)
        self.prev_btn.clicked.connect(lambda: self._step(-1))
        self.next_btn = IconButton("arrow-left", "دوره بعد", size=40, icon_px=18)
        self.next_btn.clicked.connect(lambda: self._step(1))
        self.month = ComboBox(min_width=130)
        self.year = ComboBox(min_width=100)
        self.month.currentIndexChanged.connect(lambda _: self._changed())
        self.year.currentIndexChanged.connect(lambda _: self._changed())
        self.date_from = DateField(placeholder="از تاریخ")
        self.date_to = DateField(placeholder="تا تاریخ")
        self.date_from.date_changed.connect(lambda _: self._changed())
        self.date_to.date_changed.connect(lambda _: self._changed())
        self.range_dash = label("تا", "muted")
        for w in (self.prev_btn, self.month, self.year, self.next_btn, self.date_from, self.range_dash, self.date_to):
            period_row.addWidget(w)
        period_row.addStretch(1)
        self.period_label = label("", "secondary")
        period_row.addWidget(self.period_label)
        filters.body.addLayout(period_row)

        combos = QHBoxLayout()
        combos.setSpacing(12)
        self.project = ComboBox()
        self.category = ComboBox()
        self.unit = ComboBox()
        self.group_by = ComboBox()
        for key, text in GROUP_BY.items():
            self.group_by.addItem(text, key)
        self.sort = ComboBox()
        for key, text in GROUP_SORTS.items():
            self.sort.addItem(text, key)
        for title, combo in (
            ("پروژه", self.project), ("نوع فعالیت", self.category), ("واحد مقدار", self.unit),
            ("گروه‌بندی بر اساس", self.group_by), ("مرتب‌سازی", self.sort),
        ):
            combo.currentIndexChanged.connect(lambda _: self._changed())
            combos.addWidget(FormField(title, combo), 1)
        filters.body.addLayout(combos)
        self.layout_.addWidget(filters)

        # results ---------------------------------------------------------------------
        self.results = QWidget()
        results = QVBoxLayout(self.results)
        results.setContentsMargins(0, 0, 0, 0)
        results.setSpacing(t.SPACE_6)

        cards = QHBoxLayout()
        cards.setSpacing(t.SPACE_4)
        self.card_time = StatCard("مجموع زمان", "time-circle", t.ACCENT_PRIMARY)
        self.card_count = StatCard("تعداد فعالیت", "paper", t.INFO)
        self.card_avg = StatCard("میانگین هر روز فعال", "activity", t.SUCCESS)
        self.card_qty = StatCard("مقادیر ثبت‌شده", "graph", t.WARNING)
        for c in (self.card_time, self.card_count, self.card_avg, self.card_qty):
            cards.addWidget(c, 1)
        results.addLayout(cards)

        self.trend_card = SectionCard("روند زمان فعالیت", "")
        self.trend = BarChart(height=220)
        self.trend_card.body.addWidget(self.trend)
        results.addWidget(self.trend_card)

        charts = QHBoxLayout()
        charts.setSpacing(t.SPACE_4)
        self.project_card = SectionCard("سهم پروژه‌ها از زمان", "")
        donut_row = QHBoxLayout()
        donut_row.setSpacing(t.SPACE_5)
        self.donut = DonutChart(160)
        self.legend = Legend()
        donut_row.addWidget(self.donut, 0, Qt.AlignmentFlag.AlignVCenter)
        donut_row.addWidget(self.legend, 1)
        self.project_card.body.addLayout(donut_row)
        self.project_empty = label("زمانی برای نمایش ثبت نشده است.", "muted")
        self.project_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.project_card.body.addWidget(self.project_empty, 1)
        self.category_card = SectionCard("زمان به تفکیک نوع فعالیت", "")
        self.category_bars = HBarList()
        self.category_card.body.addWidget(self.category_bars)
        self.category_card.body.addStretch(1)
        charts.addWidget(self.project_card, 1)
        charts.addWidget(self.category_card, 1)
        results.addLayout(charts)

        self.groups_card = SectionCard("", "برای دیدن رکوردهای هر ردیف، روی آن دوبار کلیک کنید", padding=0)
        self.groups_card.body.setContentsMargins(0, 18, 0, 6)
        self.groups_card.head.setContentsMargins(20, 0, 20, 0)
        self.groups_table = DataTable(
            [
                Column("نام", lambda g: g.name, None, color=lambda g: g.color, tooltip=lambda g: g.name),
                Column("تعداد ثبت", lambda g: fmt.fmt_int(g.count), 100, "center"),
                Column("مجموع زمان", lambda g: fmt.fmt_duration_short(g.minutes) if g.minutes else "—", 130, "center",
                       tooltip=lambda g: fmt.fmt_duration(g.minutes)),
                Column("سهم از زمان", lambda g: fmt.fmt_percent(g.share) if g.minutes else "—", 100, "center"),
                Column("میانگین هر ثبت", lambda g: fmt.fmt_duration_short(g.avg_minutes) if g.avg_minutes else "—", 130, "center"),
                Column("مقدار", lambda g: _quantities_text(g.quantities), 170, "center",
                       tooltip=lambda g: _quantities_text(g.quantities)),
                Column("آخرین فعالیت", lambda g: fmt.fmt_date(g.last_date) if g.last_date else "—", 120, "center"),
            ],
            row_height=48,
        )
        self.groups_table.row_activated.connect(self._drilldown)
        self.groups_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.groups_card.body.addWidget(self.groups_table)
        results.addWidget(self.groups_card)

        self.empty = EmptyState("chart", "در این بازه فعالیتی ثبت نشده است.", "بازه زمانی یا فیلترها را تغییر دهید.")
        empty_card = Card(padding=0)
        empty_card.body.addWidget(self.empty)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.results)
        self.stack.addWidget(empty_card)
        self.layout_.addWidget(self.stack)
        self.layout_.addStretch(1)

        self._fill_periods()
        self._on_period("month", refresh=False)

    def header_actions(self) -> list[QWidget]:
        self.export_btn = button("خروجی گزارش", "primary", "download")
        self.export_btn.clicked.connect(self._export_menu)
        return [self.export_btn]

    # periods -----------------------------------------------------------------------------

    def _fill_periods(self) -> None:
        self._loading = True
        year, month = fmt.current_year_month()
        first = activity_service.first_activity_date()
        first_year = fmt.date_parts(first)[0] if first else year
        current_year = self.year.currentData() or year
        self.year.clear()
        for y in range(year, min(first_year, year - 2) - 1, -1):
            self.year.addItem(fmt.digits(y), y)
        self.year.set_current_data(current_year)
        current_month = self.month.currentData() or month
        self.month.clear()
        for i, name in enumerate(fmt.month_names(), start=1):
            self.month.addItem(name, i)
        self.month.set_current_data(current_month)
        if not self._range_initialized:
            self._range_initialized = True
            self.date_from.set_date(date.today() - timedelta(days=29), emit=False)
            self.date_to.set_date(date.today(), emit=False)
        self._loading = False

    def _on_period(self, key: str, refresh: bool = True) -> None:
        month, custom = key == "month", key == "custom"
        self.month.setVisible(month)
        self.year.setVisible(not custom)
        self.prev_btn.setVisible(not custom)
        self.next_btn.setVisible(not custom)
        for w in (self.date_from, self.range_dash, self.date_to):
            w.setVisible(custom)
        if refresh:
            self._changed()

    def _step(self, delta: int) -> None:
        year, month = self.year.currentData(), self.month.currentData()
        if self.period.current() == "month":
            month += delta
            if month < 1:
                year, month = year - 1, 12
            elif month > 12:
                year, month = year + 1, 1
        else:
            year += delta
        if self.year.index_of(year) < 0:
            return
        self._loading = True
        self.year.set_current_data(year)
        self.month.set_current_data(month)
        self._loading = False
        self._changed()

    def _date_range(self) -> tuple[date, date, str]:
        mode = self.period.current()
        year = self.year.currentData()
        if mode == "month":
            month = self.month.currentData()
            start, end = fmt.month_range(year, month)
            return start, end, fmt.fmt_month_year(year, month)
        if mode == "year":
            start, end = fmt.year_range(year)
            return start, end, f"سال {fmt.digits(year)}"
        start, end = self.date_from.date(), self.date_to.date()
        if start > end:
            start, end = end, start
        return start, end, f"{fmt.fmt_date(start)} تا {fmt.fmt_date(end)}"

    # filters ---------------------------------------------------------------------------------

    def _reload_choices(self) -> None:
        self._loading = True
        self.project.set_items(
            [("همه پروژه‌ها", ALL), ("بدون پروژه", NONE_ID)] + [(p.name, p.id, p.color) for p in project_service.all_projects()]
        )
        self.category.set_items(
            [("همه انواع", ALL), ("بدون نوع", NONE_ID)] + [(c.name, c.id, c.color) for c in lookup_service.list_categories()]
        )
        self.unit.set_items([("همه واحدها", ALL)] + [(u.name, u.id) for u in lookup_service.list_units()])
        self._loading = False

    def _filter(self) -> ActivityFilter:
        start, end, _ = self._date_range()

        def pick(combo):
            value = combo.currentData()
            return None if value in (None, ALL) else value

        return ActivityFilter(
            project_id=pick(self.project), category_id=pick(self.category), unit_id=pick(self.unit),
            date_from=start, date_to=end,
        )

    def _changed(self) -> None:
        if not self._loading:
            self.refresh_now()

    # data -----------------------------------------------------------------------------------

    def refresh(self) -> None:
        self._fill_periods()
        self._reload_choices()
        start, end, period_text = self._date_range()
        f = self._filter()
        group_by = self.group_by.currentData()
        result = report_service.build_report(f, group_by, self.sort.currentData())
        self.result = result
        days = (end - start).days + 1
        self.period_label.setText(f"{period_text}  ·  {fmt.fmt_int(days)} روز")
        if self.period.current() != "custom":
            by_month = self.period.current() == "month"
            current = (self.year.currentData(), self.month.currentData() if by_month else 1)
            first_year = self.year.itemData(self.year.count() - 1)
            today_year, today_month = fmt.current_year_month()
            self.prev_btn.setEnabled(current > (first_year, 1))
            self.next_btn.setEnabled(current < (today_year, today_month if by_month else 1))

        if not result.count:
            self.stack.setCurrentIndex(1)
            self.empty.set_texts(
                "در این بازه فعالیتی ثبت نشده است.",
                f"برای {period_text} با فیلترهای انتخاب‌شده رکوردی وجود ندارد. بازه یا فیلترها را تغییر دهید.",
            )
            return
        self.stack.setCurrentIndex(0)

        self.card_time.set_duration(result.total_minutes)
        self.card_time.set_note(f"در {fmt.fmt_int(result.active_days)} روز فعال از {fmt.fmt_int(days)} روز", "accent")
        self.card_count.set_number(fmt.fmt_int(result.count), "ثبت")
        self.card_count.set_note(f"میانگین هر ثبت: {fmt.fmt_duration_short(result.avg_minutes)}" if result.avg_minutes else "بدون مدت‌زمان")
        per_day = round(result.total_minutes / result.active_days) if result.active_days else 0
        self.card_avg.set_duration(per_day)
        self.card_avg.set_note(f"میانگین روزانه کل بازه: {fmt.fmt_duration_short(round(result.total_minutes / days))}" if result.total_minutes else "")
        if result.quantities:
            unit, qty = result.quantities[0]
            self.card_qty.set_number(fmt.fmt_decimal(qty), unit)
            rest = result.quantities[1:]
            self.card_qty.set_note(_quantities_text(rest) if rest else "واحدهای مختلف جداگانه جمع می‌شوند")
        else:
            self.card_qty.set_number("—")
            self.card_qty.set_note("مقداری در این بازه ثبت نشده است")

        unit_text = "روزانه" if result.trend_unit == "day" else "ماهانه"
        self.trend_card.set_subtitle(f"مجموع زمان {unit_text} در {period_text}")
        self.trend.set_data([BarPoint(p.label, p.tooltip, p.minutes, False) for p in result.trend])

        segments = [Segment(s.name, s.color, s.minutes) for s in result.by_project]
        has_time = bool(sum(s.value for s in segments))
        self.donut.setVisible(has_time)
        self.legend.setVisible(has_time)
        self.project_empty.setVisible(not has_time)
        self.donut.set_data(segments, fmt.fmt_clock(result.total_minutes), "ساعت:دقیقه")
        self.legend.set_data(segments)
        self.category_bars.set_data([Segment(s.name, s.color, s.minutes) for s in result.by_category if s.minutes])

        self.groups_card.title_label.setText(f"گزارش بر اساس {GROUP_BY[group_by]}")
        self.groups_table.columns[0].title = GROUP_BY[group_by]
        self.groups_table.set_rows(result.groups)
        self.groups_table.fit_height()

    def _drilldown(self, group) -> None:
        if self.result is None:
            return
        ReportDetailsDialog(self, self.result.filter, self.result.group_by, group).exec()

    # export ----------------------------------------------------------------------------------

    def _meta(self) -> list[tuple[str, str]]:
        _, _, period_text = self._date_range()
        return [
            ("بازه زمانی", period_text),
            ("پروژه", self.project.currentText()),
            ("نوع فعالیت", self.category.currentText()),
            ("واحد", self.unit.currentText()),
            ("گروه‌بندی", self.group_by.currentText()),
            ("تاریخ تهیه", fmt.fmt_date(date.today())),
        ]

    def _export_menu(self) -> None:
        menu = Menu(self)
        has = bool(self.result and self.result.count)
        menu.item("فایل Excel (کامل)", lambda: self._export("xlsx"), "document", enabled=has)
        menu.item("فایل PDF (قابل چاپ)", lambda: self._export("pdf"), "paper", enabled=has)
        menu.addSeparator()
        menu.item("CSV ردیف‌های گزارش", lambda: self._export("groups"), "paper-download", enabled=has)
        menu.item("CSV همه رکوردها", lambda: self._export("records"), "paper-download", enabled=has)
        btn = self.export_btn
        pos = btn.mapToGlobal(QPoint(0, btn.height() + 6))
        menu.exec(pos)

    def _export(self, kind: str) -> None:
        if not self.result or not self.result.count:
            MessageDialog.info(self, "خروجی گزارش", "در این بازه داده‌ای برای خروجی وجود ندارد.")
            return
        stamp = f"{date.today():%Y-%m-%d}"
        specs = {
            "xlsx": ("ذخیره گزارش Excel", f"{APP_NAME}-report-{stamp}.xlsx", "Excel (*.xlsx)"),
            "pdf": ("ذخیره گزارش PDF", f"{APP_NAME}-report-{stamp}.pdf", "PDF (*.pdf)"),
            "groups": ("ذخیره ردیف‌های گزارش", f"{APP_NAME}-summary-{stamp}.csv", "CSV (*.csv)"),
            "records": ("ذخیره رکوردهای گزارش", f"{APP_NAME}-records-{stamp}.csv", "CSV (*.csv)"),
        }
        title, name, file_filter = specs[kind]
        path = ask_save_path(self, title, name, file_filter)
        if path is None:
            return
        try:
            records = activity_service.list_activities(self.result.filter) if kind != "groups" else []
            if kind == "xlsx":
                from app.reports.excel_export import export_report_xlsx

                export_report_xlsx(self.result, records, self._meta(), path)
            elif kind == "pdf":
                from app.reports.pdf_export import export_report_pdf

                export_report_pdf(self.result, records, self._meta(), path)
            elif kind == "groups":
                export_groups_csv(self.result, path)
            else:
                export_records_csv(records, path)
        except AppError as exc:
            MessageDialog.error(self, exc.message)
            return
        toast("خروجی گزارش ذخیره شد.", action=("نمایش فایل", lambda: reveal_file(path)))
