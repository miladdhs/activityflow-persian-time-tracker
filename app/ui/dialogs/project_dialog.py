from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QGridLayout, QWidget

from app.core import formatting as fmt
from app.core.errors import AppError, ValidationError
from app.services import project_service
from app.services.project_service import PROJECT_COLORS, STATUSES, ProjectInfo, ProjectInput
from app.ui.events import notify, toast
from app.ui.theme import tokens as t
from app.ui.widgets.date_picker import DateField
from app.ui.widgets.dialogs import BaseDialog, MessageDialog
from app.ui.widgets.display import ColorPicker
from app.ui.widgets.inputs import ComboBox, FormField, LineEdit, TextArea


class ProjectDialog(BaseDialog):
    def __init__(self, parent: QWidget | None, project: ProjectInfo | None = None):
        editing = project is not None
        super().__init__(
            parent,
            "ویرایش پروژه" if editing else "پروژه جدید",
            "نام، رنگ شناسایی و وضعیت پروژه را مشخص کنید.",
            width=560,
        )
        self.project = project

        self.name = LineEdit("مثلاً: تولید محتوای آموزشی", max_length=150)
        self.f_name = FormField("نام پروژه", self.name, required=True)
        self.name.textEdited.connect(lambda _: self.f_name.clear_error())
        self.description = TextArea("هدف یا توضیح کوتاهی درباره پروژه", 84)
        self.f_description = FormField("توضیحات", self.description, hint="اختیاری")
        self.colors = ColorPicker(PROJECT_COLORS)
        self.f_color = FormField("رنگ شناسایی", self.colors)
        self.start = DateField(None, allow_empty=True, placeholder="بدون تاریخ شروع", long_format=True)
        self.f_start = FormField("تاریخ شروع", self.start)
        self.status = ComboBox()
        self.status.set_items([(label, key) for key, label in STATUSES.items()])
        self.f_status = FormField("وضعیت", self.status)

        grid = QGridLayout()
        grid.setHorizontalSpacing(t.SPACE_4)
        grid.setVerticalSpacing(t.SPACE_4)
        grid.addWidget(self.f_name, 0, 0, 1, 2)
        grid.addWidget(self.f_start, 1, 0)
        grid.addWidget(self.f_status, 1, 1)
        grid.addWidget(self.f_color, 2, 0, 1, 2)
        grid.addWidget(self.f_description, 3, 0, 1, 2)
        self.body.addLayout(grid)

        if editing:
            self.name.setText(project.name)
            self.description.setPlainText(project.description)
            self.colors.set_color(project.color)
            self.start.set_date(project.start_date, emit=False)
            self.status.set_current_data(project.status)
        else:
            used = {p.color.upper() for p in project_service.all_projects()}
            self.colors.set_color(next((c for c in PROJECT_COLORS if c.upper() not in used), PROJECT_COLORS[0]))
            self.start.set_date(date.today(), emit=False)

        cancel = self.add_button("انصراف")
        cancel.clicked.connect(self.reject)
        save = self.add_button("ذخیره پروژه" if editing else "ساخت پروژه", "primary", "tick-square")
        save.clicked.connect(self._save)
        self.name.returnPressed.connect(self._save)
        self.name.setFocus()

    def _save(self) -> None:
        data = ProjectInput(
            name=self.name.text(),
            description=self.description.toPlainText(),
            color=self.colors.color(),
            start_date=self.start.date(),
            status=self.status.currentData(),
        )
        try:
            if self.project:
                project_service.update_project(self.project.id, data)
            else:
                project_service.create_project(data)
        except ValidationError as exc:
            target = {"description": self.f_description, "color": self.f_color, "status": self.f_status}.get(
                exc.field or "", self.f_name
            )
            target.set_error(exc.message)
            return
        except AppError as exc:
            self.f_name.set_error(exc.message)
            return
        notify("projects")
        toast("تغییرات ذخیره شد." if self.project else "پروژه ساخته شد.")
        self.accept()


def confirm_delete_project(parent: QWidget | None, project: ProjectInfo) -> bool:
    count = project.activity_count
    details = (
        f"{fmt.fmt_int(count)} فعالیت ثبت‌شده در این پروژه حذف نمی‌شوند و با عنوان «بدون پروژه» باقی می‌مانند."
        if count else "هیچ فعالیتی به این پروژه مرتبط نیست."
    )
    if not MessageDialog.confirm(
        parent,
        "حذف پروژه",
        f"پروژه «{project.name}» حذف می‌شود. اگر فقط می‌خواهید آن را از فهرست‌ها پنهان کنید، بایگانی را انتخاب کنید.",
        confirm_text="حذف پروژه",
        details=details,
    ):
        return False
    try:
        project_service.delete_project(project.id)
    except AppError as exc:
        MessageDialog.error(parent, exc.message)
        return False
    notify("projects")
    notify("activities")
    toast("پروژه حذف شد؛ سوابق فعالیت‌ها حفظ شدند.")
    return True
