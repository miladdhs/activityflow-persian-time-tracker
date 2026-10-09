"""The activity form, shared by the «ثبت فعالیت» page and the edit dialog."""

from __future__ import annotations

from datetime import date, datetime, time

from PySide6.QtCore import QStringListModel, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCompleter,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core import formatting as fmt
from app.core.errors import AppError, ValidationError
from app.core.settings_keys import TIME_MODES, Key
from app.core.text import to_latin_digits
from app.services import activity_service, lookup_service, project_service, settings_service
from app.services.activity_service import ActivityInput, ActivityRow
from app.ui.theme import tokens as t
from app.ui.widgets.common import SegmentedControl, button, clear_layout, label
from app.ui.widgets.date_picker import DateField
from app.ui.widgets.inputs import ComboBox, FormField, LineEdit, NumberInput, TextArea, TimeInput

QUICK_DURATIONS = [(15, "۱۵ دقیقه"), (30, "۳۰ دقیقه"), (45, "۴۵ دقیقه"), (60, "۱ ساعت"), (90, "۱٫۵ ساعت"), (120, "۲ ساعت")]


class TitleHint(QWidget):
    """Explains how a title will be grouped and offers similar existing titles."""

    picked = Signal(str)

    def __init__(self):
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self.setMinimumHeight(26)

    def show_for(self, title: str) -> None:
        clear_layout(self._layout)
        text = title.strip()
        if not text:
            self._layout.addWidget(label("فعالیت‌های هم‌نام در گزارش‌ها خودکار با هم جمع می‌شوند.", "caption"))
            self._layout.addStretch(1)
            return
        existing = lookup_service.find_title(text)
        if existing:
            msg = label("", "caption")
            msg.setTextFormat(Qt.TextFormat.RichText)
            msg.setText(f'<span style="color:{t.SUCCESS};">●</span>&nbsp; به گروه موجود «{existing.name}» اضافه می‌شود')
            self._layout.addWidget(msg)
        else:
            similar = lookup_service.similar_titles(text)
            if similar:
                self._layout.addWidget(label("عنوان جدید است. شاید منظورتان این باشد:", "caption"))
                for name in similar:
                    chip = button(name, size=None)
                    chip.setProperty("chip", True)
                    chip.setProperty("variant", None)
                    chip.setToolTip("استفاده از این عنوان")
                    chip.clicked.connect(lambda _=False, n=name: self.picked.emit(n))
                    self._layout.addWidget(chip)
            else:
                self._layout.addWidget(label("عنوان جدید — یک گروه تازه در گزارش‌ها ساخته می‌شود.", "caption"))
        self._layout.addStretch(1)


class ActivityForm(QWidget):
    saved = Signal(int)

    def __init__(self, mode: str = "create", parent: QWidget | None = None):
        super().__init__(parent)
        self.mode = mode
        self.activity_id: int | None = None
        self._editing_project: int | None = None
        self._touched: set[str] = set()
        self._last_end: time | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(t.SPACE_4)

        # title ------------------------------------------------------------------
        self.title = LineEdit("مثلاً: کلیپ کاغذ، طراحی صفحه اصلی، جلسه با تیم", max_length=150)
        self._completer_model = QStringListModel(self)
        completer = QCompleter(self._completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setMaxVisibleItems(8)
        popup = completer.popup()
        popup.setObjectName("CompleterPopup")
        popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        popup.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        completer.activated.connect(self._on_title_chosen)
        self.title.setCompleter(completer)
        self.f_title = FormField("عنوان فعالیت", self.title, required=True)
        self.title_hint = TitleHint()
        self.title_hint.picked.connect(self._on_title_chosen)
        self._hint_timer = QTimer(self)
        self._hint_timer.setSingleShot(True)
        self._hint_timer.setInterval(220)
        self._hint_timer.timeout.connect(lambda: self.title_hint.show_for(self.title.text()))
        self.title.textEdited.connect(lambda _: (self._hint_timer.start(), self.f_title.clear_error()))
        self.title.editingFinished.connect(lambda: self._apply_title_usage(self.title.text()))

        title_box = QVBoxLayout()
        title_box.setSpacing(6)
        title_box.addWidget(self.f_title)
        title_box.addWidget(self.title_hint)
        root.addLayout(title_box)

        grid = QGridLayout()
        grid.setHorizontalSpacing(t.SPACE_4)
        grid.setVerticalSpacing(t.SPACE_4)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self.project = ComboBox()
        self.project.activated.connect(lambda _: (self._touched.add("project"), self.f_project.clear_error()))
        self.f_project = FormField("پروژه", self.project)
        self.category = ComboBox()
        self.category.activated.connect(lambda _: (self._touched.add("category"), self.f_category.clear_error()))
        self.f_category = FormField("نوع فعالیت", self.category)
        grid.addWidget(self.f_project, 0, 0)
        grid.addWidget(self.f_category, 0, 1)

        self.date = DateField(date.today(), max_date=date.today(), long_format=True)
        self.date.date_changed.connect(lambda _: self.f_date.clear_error())
        self.f_date = FormField("تاریخ", self.date, required=True)
        self.time_mode = SegmentedControl([("duration", "مدت‌زمان"), ("range", "ساعت شروع و پایان")])
        self.time_mode.setFixedHeight(t.FIELD_HEIGHT)
        self.time_mode.changed.connect(self._on_mode)
        self.f_mode = FormField("نحوه ثبت زمان", self.time_mode)
        grid.addWidget(self.f_date, 1, 0)
        grid.addWidget(self.f_mode, 1, 1)

        # duration page
        self.hours = NumberInput("۰", max_digits=2)
        self.minutes = NumberInput("۰", max_digits=3)
        for w in (self.hours, self.minutes):
            w.value_edited.connect(self._update_duration_preview)
        self.f_hours = FormField("ساعت", self.hours)
        self.f_minutes = FormField("دقیقه", self.minutes)
        duration_page = QWidget()
        dp = QVBoxLayout(duration_page)
        dp.setContentsMargins(0, 0, 0, 0)
        dp.setSpacing(10)
        dp_row = QHBoxLayout()
        dp_row.setSpacing(t.SPACE_4)
        dp_row.addWidget(self.f_hours)
        dp_row.addWidget(self.f_minutes)
        dp.addLayout(dp_row)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        self._chips: list[tuple[QWidget, str]] = []
        for minutes, text in QUICK_DURATIONS:
            chip = button(self._chip_text(text))
            self._chips.append((chip, text))
            chip.setProperty("chip", True)
            chip.setProperty("variant", None)
            chip.setToolTip("تنظیم سریع مدت‌زمان")
            chip.clicked.connect(lambda _=False, m=minutes: self.set_duration(m))
            chips.addWidget(chip)
        chips.addStretch(1)
        dp.addLayout(chips)

        # range page
        self.start = TimeInput()
        self.end = TimeInput()
        for w in (self.start, self.end):
            w.time_edited.connect(self._update_duration_preview)
        self.f_start = FormField("ساعت شروع", self.start, required=True)
        now_btn = button("اکنون", "ghost", "time-circle", size="sm", tooltip="ساعت فعلی")
        now_btn.clicked.connect(lambda: self.end.set_time(datetime.now().time().replace(second=0, microsecond=0)))
        self.f_end = FormField("ساعت پایان", self.end, required=True)
        range_page = QWidget()
        rp = QVBoxLayout(range_page)
        rp.setContentsMargins(0, 0, 0, 0)
        rp.setSpacing(10)
        rp_row = QHBoxLayout()
        rp_row.setSpacing(t.SPACE_4)
        rp_row.addWidget(self.f_start)
        rp_row.addWidget(self.f_end)
        rp.addLayout(rp_row)
        rp_tools = QHBoxLayout()
        rp_tools.addWidget(now_btn)
        rp_tools.addStretch(1)
        rp.addLayout(rp_tools)

        self.time_stack = QStackedWidget()
        self.time_stack.addWidget(duration_page)
        self.time_stack.addWidget(range_page)
        grid.addWidget(self.time_stack, 2, 0, 1, 2)

        self.duration_preview = QLabel()
        self.duration_preview.setTextFormat(Qt.TextFormat.RichText)
        self.duration_preview.setProperty("role", "small")
        grid.addWidget(self.duration_preview, 3, 0, 1, 2)

        self.quantity = NumberInput("اختیاری، مثلاً ۱۲", decimals=3, max_digits=10)
        self.quantity.value_edited.connect(lambda: self.f_quantity.clear_error())
        self.f_quantity = FormField("مقدار", self.quantity, hint="اختیاری")
        self.unit = ComboBox()
        self.unit.activated.connect(lambda _: (self._touched.add("unit"), self.f_unit.clear_error()))
        self.f_unit = FormField("واحد", self.unit)
        grid.addWidget(self.f_quantity, 4, 0)
        grid.addWidget(self.f_unit, 4, 1)

        self.notes = TextArea("جزئیات، لینک یا نکته‌ای که بعداً به کارتان می‌آید", 88)
        self.f_notes = FormField("توضیحات", self.notes, hint="اختیاری")
        grid.addWidget(self.f_notes, 5, 0, 1, 2)
        root.addLayout(grid)

        self.fields = {
            "title": self.f_title, "project": self.f_project, "category": self.f_category,
            "date": self.f_date, "start": self.f_start, "end": self.f_end,
            "duration": self.f_hours, "quantity": self.f_quantity, "unit": self.f_unit, "notes": self.f_notes,
        }

        for seq in ("Ctrl+Return", "Ctrl+Enter", "Ctrl+S"):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(self.submit)

        self.refresh_choices()
        self._apply_defaults()

    # choices ---------------------------------------------------------------------

    @staticmethod
    def _chip_text(text: str) -> str:
        return text if fmt.prefs.persian_digits else to_latin_digits(text).replace("٫", ".")

    def refresh_choices(self) -> None:
        for chip, text in self._chips:
            chip.setText(self._chip_text(text))
        include = (self._editing_project,) if self._editing_project else ()
        projects = project_service.project_choices(include)
        self.project.set_items(
            [("بدون پروژه", None)]
            + [(p.name + ("" if p.status in project_service.OPEN_STATUSES else f" ({p.status_label})"), p.id, p.color) for p in projects]
        )
        self.category.set_items([("بدون نوع", None)] + [(c.name, c.id, c.color) for c in lookup_service.list_categories()])
        self.unit.set_items([("انتخاب واحد", None)] + [(u.name, u.id) for u in lookup_service.list_units()])
        self._completer_model.setStringList(lookup_service.title_names())

    def _apply_defaults(self) -> None:
        self.project.set_current_data(settings_service.get_int(Key.LAST_PROJECT))
        self.category.set_current_data(settings_service.get_int(Key.LAST_CATEGORY))
        self.unit.set_current_data(settings_service.get_int(Key.LAST_UNIT))
        mode = settings_service.get(Key.LAST_TIME_MODE)
        self.time_mode.set_current(mode if mode in TIME_MODES else TIME_MODES[0])
        self._on_mode(self.time_mode.current())
        self.title_hint.show_for("")

    # state helpers ---------------------------------------------------------------

    def _on_mode(self, mode: str) -> None:
        self.time_stack.setCurrentIndex(1 if mode == "range" else 0)
        for key in ("start", "end", "duration"):
            self.fields[key].clear_error()
        self._update_duration_preview()

    def set_duration(self, minutes: int) -> None:
        self.time_mode.set_current("duration")
        self._on_mode("duration")
        h, m = divmod(minutes, 60)
        self.hours.set_value(h if h else None)
        self.minutes.set_value(m if m or not h else None)
        self.f_hours.clear_error()
        self._update_duration_preview()

    def _duration_minutes(self) -> int | None:
        if self.time_mode.current() == "range":
            try:
                start, end = self.start.time(), self.end.time()
            except ValueError:
                return None
            if start is None or end is None:
                return None
            diff = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
            return diff if diff > 0 else None
        return self.hours.int_value() * 60 + self.minutes.int_value()

    def _update_duration_preview(self) -> None:
        minutes = self._duration_minutes()
        self.f_hours.clear_error()
        if self.time_mode.current() == "range":
            self.f_start.clear_error()
            self.f_end.clear_error()
        if minutes:
            self.duration_preview.setText(
                f'<span style="color:{t.TEXT_MUTED};">مدت‌زمان ثبت‌شده:</span> '
                f'<span style="color:{t.ACCENT_TEXT}; font-weight:600;">{fmt.fmt_duration(minutes)}</span>'
            )
        elif self.time_mode.current() == "range" and self.start.text() and self.end.text():
            self.duration_preview.setText(f'<span style="color:{t.WARNING};">ساعت پایان باید بعد از ساعت شروع باشد.</span>')
        else:
            self.duration_preview.setText(
                f'<span style="color:{t.TEXT_MUTED};">برای فعالیت‌هایی که فقط مقدار دارند، مدت‌زمان می‌تواند خالی بماند.</span>'
            )

    def _on_title_chosen(self, text: str) -> None:
        self.title.setText(text)
        self.f_title.clear_error()
        self.title_hint.show_for(text)
        self._apply_title_usage(text)

    def _apply_title_usage(self, text: str) -> None:
        """Pre-fill project/type/unit from the last activity with this title, unless chosen manually."""
        usage = lookup_service.last_usage_for_title(text)
        if usage is None:
            return
        if "project" not in self._touched and usage.project_id is not None:
            self.project.set_current_data(usage.project_id)
        if "category" not in self._touched and usage.category_id is not None:
            self.category.set_current_data(usage.category_id)
        if "unit" not in self._touched and usage.unit_id is not None:
            self.unit.set_current_data(usage.unit_id)

    # public API ------------------------------------------------------------------

    def load(self, row: ActivityRow) -> None:
        """Fill the form with an existing activity (for editing)."""
        self.activity_id = row.id
        self._editing_project = row.project_id
        self.refresh_choices()
        self.title.setText(row.title)
        self.title_hint.show_for(row.title)
        self.project.set_current_data(row.project_id)
        self.category.set_current_data(row.category_id)
        self.date.set_date(row.activity_date, emit=False)
        if row.time_mode == "range":
            self.time_mode.set_current("range")
            self.start.set_time(row.start_time)
            self.end.set_time(row.end_time)
        else:
            self.time_mode.set_current("duration")
            h, m = divmod(row.duration_minutes, 60)
            self.hours.set_value(h if h else None)
            self.minutes.set_value(m if m else None)
        self._on_mode(self.time_mode.current())
        self.quantity.set_value(row.quantity)
        self.unit.set_current_data(row.unit_id)
        self.notes.setPlainText(row.notes)
        self._touched = {"project", "category", "unit"}

    def prefill(self, title: str = "", project_id=..., category_id=..., unit_id=..., quantity=None,
                duration: int | None = None, notes: str = "") -> None:
        """Start a new entry from a template (repeat / duplicate). `...` keeps the current choice."""
        self.reset(keep_context=True)
        self.title.setText(title)
        self.title_hint.show_for(title)
        if title:
            self._apply_title_usage(title)
        if project_id is not ...:
            self.project.set_current_data(project_id)
        if category_id is not ...:
            self.category.set_current_data(category_id)
        if unit_id is not ...:
            self.unit.set_current_data(unit_id)
        if quantity is not None:
            self.quantity.set_value(quantity)
        if duration:
            self.set_duration(duration)
        self.notes.setPlainText(notes)
        self._touched = {"project", "category", "unit"}

    def reset(self, keep_context: bool = True) -> None:
        for field in self.fields.values():
            field.clear_error()
        self.title.clear()
        self.notes.clear()
        self.quantity.clear()
        self.hours.clear()
        self.minutes.clear()
        self.end.clear()
        self.start.set_time(self._last_end) if self._last_end else self.start.clear()
        self._touched = set()
        if not keep_context:
            self.date.set_date(date.today(), emit=False)
            self._apply_defaults()
        self.title_hint.show_for("")
        self._update_duration_preview()

    def focus_title(self) -> None:
        self.title.setFocus(Qt.FocusReason.OtherFocusReason)

    def collect(self) -> ActivityInput:
        mode = self.time_mode.current()
        start = end = None
        if mode == "range":
            try:
                start = self.start.time()
            except ValueError:
                raise ValidationError("ساعت شروع معتبر نیست؛ مثلاً ۰۹:۳۰ وارد کنید.", "start") from None
            try:
                end = self.end.time()
            except ValueError:
                raise ValidationError("ساعت پایان معتبر نیست؛ مثلاً ۱۷:۴۵ وارد کنید.", "end") from None
        return ActivityInput(
            title=self.title.text(),
            activity_date=self.date.date(),
            project_id=self.project.currentData(),
            category_id=self.category.currentData(),
            time_mode=mode,
            start_time=start,
            end_time=end,
            duration_minutes=self.hours.int_value() * 60 + self.minutes.int_value() if mode == "duration" else None,
            quantity=self.quantity.raw() or None,
            unit_id=self.unit.currentData(),
            notes=self.notes.toPlainText(),
        )

    def submit(self) -> int | None:
        for field in self.fields.values():
            field.clear_error()
        try:
            inp = self.collect()
            if self.activity_id is None:
                activity_id = activity_service.create_activity(inp)
            else:
                activity_service.update_activity(self.activity_id, inp)
                activity_id = self.activity_id
        except ValidationError as exc:
            field = self.fields.get(exc.field or "")
            if field is not None:
                field.set_error(exc.message)
                field.widget.setFocus()
            else:
                self.f_title.set_error(exc.message)
            return None
        except AppError as exc:
            from app.ui.widgets.dialogs import MessageDialog

            MessageDialog.error(self, exc.message)
            return None

        settings_service.set_many(
            {
                Key.LAST_PROJECT: inp.project_id,
                Key.LAST_CATEGORY: inp.category_id,
                Key.LAST_UNIT: inp.unit_id if inp.quantity else settings_service.get(Key.LAST_UNIT),
                Key.LAST_TIME_MODE: inp.time_mode,
            }
        )
        if inp.time_mode == "range":
            self._last_end = inp.end_time
        self.saved.emit(activity_id)
        return activity_id
