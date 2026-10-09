"""Manage activity titles: rename and merge similar titles under user control."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget

from app.core import formatting as fmt
from app.core.text import normalize_name
from app.services import lookup_service
from app.ui.dialogs.prompt_dialog import ChoiceDialog, NameDialog
from app.ui.events import notify, toast
from app.ui.widgets.common import IconButton
from app.ui.widgets.dialogs import BaseDialog, MessageDialog
from app.ui.widgets.display import EmptyState
from app.ui.widgets.inputs import SearchInput
from app.ui.widgets.table import Column, DataTable


class TitlesDialog(BaseDialog):
    def __init__(self, parent: QWidget | None):
        super().__init__(
            parent,
            "مدیریت عناوین فعالیت",
            "فعالیت‌های هم‌نام در گزارش‌ها با هم جمع می‌شوند. عناوین مشابه را می‌توانید ادغام کنید.",
            width=760,
        )
        self.search = SearchInput("جست‌وجوی عنوان", size="sm")
        self.search.search_changed.connect(lambda _: self._load())
        self.body.addWidget(self.search)

        self.table = DataTable(
            [
                Column("عنوان", lambda r: r.name, None),
                Column("تعداد ثبت", lambda r: fmt.fmt_int(r.usage), 110, "center"),
                Column("مجموع زمان", lambda r: fmt.fmt_clock(r.total_minutes), 110, "center",
                       tooltip=lambda r: fmt.fmt_duration(r.total_minutes)),
                Column("", width=100, actions=True),
            ],
            row_height=46,
        )
        self.table.set_row_widgets(self._row_actions)
        self.table.setMinimumHeight(380)
        self.empty = EmptyState("document", "عنوانی پیدا نشد", "با ثبت فعالیت، عناوین در این فهرست نمایش داده می‌شوند.")
        self.empty.hide()
        self.body.addWidget(self.table)
        self.body.addWidget(self.empty)
        close = self.add_button("بستن", "primary")
        close.clicked.connect(self.accept)
        self._all = []
        self._load(refetch=True)

    def _load(self, refetch: bool = False) -> None:
        if refetch:
            self._all = lookup_service.list_titles()
        key = normalize_name(self.search.text())
        rows = [r for r in self._all if key in normalize_name(r.name)] if key else self._all
        self.table.set_rows(rows)
        self.table.setVisible(bool(rows))
        self.empty.setVisible(not rows)

    def _row_actions(self, row) -> QWidget:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        rename = IconButton("edit", "تغییر نام", size=30, icon_px=16)
        rename.clicked.connect(lambda: self._rename(row))
        merge = IconButton("swap", "ادغام با عنوان دیگر", size=30, icon_px=16)
        merge.clicked.connect(lambda: self._merge(row))
        merge.setEnabled(len(self._all) > 1)
        layout.addWidget(rename)
        layout.addWidget(merge)
        return holder

    def _changed(self, message: str) -> None:
        notify("lookups")
        notify("activities")
        toast(message)
        self._load(refetch=True)

    def _rename(self, row) -> None:
        dialog = NameDialog(
            self, "تغییر نام عنوان", "عنوان جدید",
            lambda name, _c: lookup_service.rename_title(row.id, name),
            value=row.name, max_length=150,
            subtitle=f"نام همه {fmt.fmt_int(row.usage)} فعالیت ثبت‌شده با این عنوان تغییر می‌کند.",
        )
        if dialog.exec():
            self._changed("عنوان تغییر کرد.")

    def _merge(self, row) -> None:
        targets = [(t.name, t.id) for t in self._all if t.id != row.id]
        chosen = {}

        def do_merge(target_id):
            chosen["id"] = target_id

        dialog = ChoiceDialog(
            self, f"ادغام «{row.name}»", "ادغام در عنوان",
            targets, do_merge,
            subtitle="همه فعالیت‌های این عنوان به عنوان مقصد منتقل می‌شوند و این عنوان حذف می‌شود.",
            save_text="ادامه",
        )
        if not dialog.exec() or "id" not in chosen:
            return
        target = next((t for t in self._all if t.id == chosen["id"]), None)
        if target is None:
            return
        if not MessageDialog.confirm(
            self, "تأیید ادغام",
            f"{fmt.fmt_int(row.usage)} فعالیت از «{row.name}» به «{target.name}» منتقل می‌شوند. این کار قابل بازگشت نیست.",
            confirm_text="ادغام عناوین", danger=False,
        ):
            return
        try:
            lookup_service.merge_titles(row.id, target.id)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            self.show_error(exc)
            return
        self._changed("عناوین ادغام شدند.")
