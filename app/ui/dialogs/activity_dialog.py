from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.core.errors import AppError
from app.services import activity_service
from app.ui.events import notify, toast
from app.ui.widgets.activity_form import ActivityForm
from app.ui.widgets.dialogs import BaseDialog, MessageDialog


class ActivityDialog(BaseDialog):
    """Edit an existing activity."""

    def __init__(self, parent: QWidget | None, activity_id: int):
        super().__init__(parent, "ویرایش فعالیت", "تغییرات بلافاصله در گزارش‌ها و آمار اعمال می‌شود.", width=640)
        self.form = ActivityForm(mode="edit")
        self.body.addWidget(self.form)
        self.form.load(activity_service.get_activity(activity_id))
        self.form.saved.connect(self._on_saved)

        cancel = self.add_button("انصراف")
        cancel.clicked.connect(self.reject)
        save = self.add_button("ذخیره تغییرات", "primary", "tick-square")
        save.setToolTip("Ctrl+Enter")
        save.clicked.connect(self.form.submit)
        save.setDefault(False)
        save.setAutoDefault(False)
        self.form.focus_title()

    def _on_saved(self, _id: int) -> None:
        notify("activities")
        toast("تغییرات ذخیره شد.")
        self.accept()

    @classmethod
    def edit(cls, parent: QWidget | None, activity_id: int) -> bool:
        try:
            dialog = cls(parent, activity_id)
        except AppError as exc:
            MessageDialog.error(parent, exc.message)
            notify("activities")
            return False
        return bool(dialog.exec())


def confirm_delete_activity(parent: QWidget | None, activity_id: int, title: str) -> bool:
    if not MessageDialog.confirm(
        parent,
        "حذف فعالیت",
        f"فعالیت «{title}» برای همیشه حذف می‌شود و مجموع‌ها در همه گزارش‌ها و آمارها به‌روز خواهند شد.",
        confirm_text="حذف فعالیت",
    ):
        return False
    try:
        activity_service.delete_activity(activity_id)
    except AppError as exc:
        MessageDialog.error(parent, exc.message)
        notify("activities")
        return False
    notify("activities")
    toast("فعالیت حذف شد.")
    return True
