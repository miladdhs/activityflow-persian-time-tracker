"""Drill-down: the individual records that make up one report total."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget

from app.core import formatting as fmt
from app.services import report_service
from app.services.activity_service import ActivityFilter
from app.services.report_service import GROUP_BY, ReportGroup
from app.ui.dialogs.activity_dialog import ActivityDialog
from app.ui.widgets.common import Badge, label
from app.ui.widgets.dialogs import BaseDialog
from app.ui.widgets.table import Column, DataTable


class ReportDetailsDialog(BaseDialog):
    def __init__(self, parent: QWidget | None, f: ActivityFilter, group_by: str, group: ReportGroup):
        super().__init__(
            parent,
            f"جزئیات «{group.name}»",
            f"رکوردهای تشکیل‌دهنده این مجموع ({GROUP_BY[group_by]}) در بازه و فیلترهای انتخاب‌شده",
            width=1000,
        )
        self._filter, self._group_by, self._group = f, group_by, group

        summary = QHBoxLayout()
        summary.setSpacing(8)
        summary.addWidget(Badge(f"{fmt.fmt_int(group.count)} ثبت", "accent"))
        summary.addWidget(Badge(f"مجموع {fmt.fmt_duration(group.minutes)}", "info"))
        for unit, qty in group.quantities:
            summary.addWidget(Badge(f"{fmt.fmt_decimal(qty)} {unit}", "success"))
        summary.addStretch(1)
        summary.addWidget(label("برای ویرایش، روی ردیف دوبار کلیک کنید.", "caption"))
        self.body.addLayout(summary)

        self.table = DataTable(
            [
                Column("تاریخ", lambda r: fmt.fmt_date(r.activity_date), 110, "center",
                       tooltip=lambda r: fmt.fmt_date_with_weekday(r.activity_date)),
                Column("عنوان فعالیت", lambda r: r.title, None, tooltip=lambda r: r.notes or r.title),
                Column("پروژه", lambda r: r.project_name or "بدون پروژه", 200, color=lambda r: r.project_color,
                       muted=lambda r: r.project_id is None),
                Column("نوع", lambda r: r.category_name or "بدون نوع", 160, color=lambda r: r.category_color,
                       muted=lambda r: r.category_id is None),
                Column("مدت‌زمان", lambda r: fmt.fmt_clock(r.duration_minutes) if r.duration_minutes else "—", 90, "center",
                       tooltip=lambda r: fmt.fmt_duration(r.duration_minutes)),
                Column("مقدار", lambda r: f"{fmt.fmt_decimal(r.quantity)} {r.unit_name}" if r.quantity is not None else "—",
                       110, "center"),
            ],
            row_height=46,
        )
        self.table.setMinimumHeight(360)
        self.table.row_activated.connect(self._edit)
        self.body.addWidget(self.table)
        close = self.add_button("بستن", "primary")
        close.clicked.connect(self.accept)
        self._load()

    def _load(self) -> None:
        self.table.set_rows(report_service.group_records(self._filter, self._group_by, self._group.key))

    def _edit(self, row) -> None:
        if ActivityDialog.edit(self, row.id):
            self._load()
