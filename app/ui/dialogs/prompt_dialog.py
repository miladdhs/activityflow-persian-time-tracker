from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QWidget

from app.core.errors import AppError
from app.ui.widgets.dialogs import BaseDialog
from app.ui.widgets.display import ColorPicker
from app.ui.widgets.inputs import ComboBox, FormField, LineEdit


class NameDialog(BaseDialog):
    """Ask for a name (and optionally a color); ``on_save`` performs the change."""

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        field_label: str,
        on_save: Callable[[str, str | None], None],
        value: str = "",
        colors: list[str] | None = None,
        color: str | None = None,
        subtitle: str = "",
        save_text: str = "ذخیره",
        max_length: int = 80,
    ):
        super().__init__(parent, title, subtitle, width=460)
        self._on_save = on_save
        self.input = LineEdit(max_length=max_length)
        self.input.setText(value)
        self.f_input = FormField(field_label, self.input, required=True)
        self.input.textEdited.connect(lambda _: self.f_input.clear_error())
        self.body.addWidget(self.f_input)
        self.picker = None
        if colors:
            self.picker = ColorPicker(colors, color)
            self.body.addWidget(FormField("رنگ", self.picker))
        cancel = self.add_button("انصراف")
        cancel.clicked.connect(self.reject)
        save = self.add_button(save_text, "primary", "tick-square")
        save.clicked.connect(self._save)
        self.input.returnPressed.connect(self._save)
        self.input.setFocus()
        self.input.selectAll()

    def _save(self) -> None:
        try:
            self._on_save(self.input.text(), self.picker.color() if self.picker else None)
        except AppError as exc:
            self.f_input.set_error(exc.message)
            return
        self.accept()


class ChoiceDialog(BaseDialog):
    """Pick one item from a list; ``on_save`` receives the chosen data."""

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        field_label: str,
        items: list[tuple[str, object]],
        on_save: Callable[[object], None],
        subtitle: str = "",
        save_text: str = "تأیید",
        danger: bool = False,
    ):
        super().__init__(parent, title, subtitle, width=480)
        self._on_save = on_save
        self.combo = ComboBox()
        self.combo.set_items(items, keep_current=False)
        self.field = FormField(field_label, self.combo, required=True)
        self.body.addWidget(self.field)
        cancel = self.add_button("انصراف")
        cancel.clicked.connect(self.reject)
        save = self.add_button(save_text, "danger-solid" if danger else "primary")
        save.clicked.connect(self._save)

    def _save(self) -> None:
        try:
            self._on_save(self.combo.currentData())
        except AppError as exc:
            self.field.set_error(exc.message)
            return
        self.accept()
