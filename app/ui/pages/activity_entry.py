from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from app.core import formatting as fmt
from app.services import activity_service
from app.ui.dialogs.activity_dialog import ActivityDialog
from app.ui.events import notify, toast
from app.ui.pages.base import BasePage
from app.ui.theme import tokens as t
from app.ui.widgets.activity_form import ActivityForm
from app.ui.widgets.activity_row import ActivityListRow
from app.ui.widgets.common import Card, Divider, IconTile, SectionCard, button, clear_layout, label

SHORTCUTS = [
    ("Ctrl + Enter", "ثبت فعالیت"),
    ("Ctrl + N", "فعالیت جدید از هر صفحه"),
    ("Up / Down", "تغییر ساعت یا تاریخ"),
    ("Tab", "رفتن به فیلد بعدی"),
]


class ActivityEntryPage(BasePage):
    key = "entry"
    title = "ثبت فعالیت"
    subtitle = "فعالیت انجام‌شده را با جزئیات دلخواه ثبت کنید"
    topics = {"activities", "projects", "lookups", "settings"}

    def __init__(self, window):
        super().__init__(window)
        row = QHBoxLayout()
        row.setSpacing(t.SPACE_5)

        # form card -------------------------------------------------------------------
        self.form_card = SectionCard("فعالیت جدید", "فیلدهای ستاره‌دار الزامی هستند؛ بقیه اختیاری‌اند.", padding=24)
        self.form = ActivityForm(mode="create")
        self.form.saved.connect(self._on_saved)
        self.form_card.body.addWidget(self.form)
        self.form_card.body.addWidget(Divider())
        footer = QHBoxLayout()
        footer.setSpacing(t.SPACE_3)
        self.save_btn = button("ثبت فعالیت", "primary", "tick-square", tooltip="Ctrl+Enter")
        self.save_btn.setMinimumWidth(150)
        self.save_btn.clicked.connect(self.form.submit)
        clear = button("پاک‌کردن فرم", "ghost", "close-square")
        clear.clicked.connect(lambda: (self.form.reset(keep_context=False), self.form.focus_title()))
        footer.addWidget(self.save_btn)
        footer.addWidget(clear)
        footer.addStretch(1)
        footer.addWidget(label("پروژه، نوع و واحد آخرین ثبت برای دفعه بعد به خاطر سپرده می‌شوند.", "caption"))
        self.form_card.body.addLayout(footer)
        row.addWidget(self.form_card, 3, Qt.AlignmentFlag.AlignTop)

        # side column ---------------------------------------------------------------
        side = QVBoxLayout()
        side.setSpacing(t.SPACE_4)

        self.today_card = SectionCard("امروز", "", padding=16)
        summary = QHBoxLayout()
        summary.setSpacing(12)
        summary.addWidget(IconTile("time-circle", t.ACCENT_PRIMARY, 44, 22))
        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.today_total = label("", "h2")
        self.today_caption = label("", "caption")
        texts.addWidget(self.today_total)
        texts.addWidget(self.today_caption)
        summary.addLayout(texts, 1)
        self.today_card.body.addLayout(summary)
        self.today_card.body.addWidget(Divider())
        self.today_list = QVBoxLayout()
        self.today_list.setSpacing(2)
        self.today_card.body.addLayout(self.today_list)
        side.addWidget(self.today_card)

        tips = Card(padding=16, spacing=10)
        tips.body.addWidget(label("میانبرهای صفحه‌کلید", "h3"))
        for keys, text in SHORTCUTS:
            line = QHBoxLayout()
            line.setSpacing(8)
            line.addWidget(label(text, "secondary"), 1)
            kbd = label(keys)
            kbd.setObjectName("Kbd")
            kbd.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            line.addWidget(kbd)
            tips.body.addLayout(line)
        tips.body.addWidget(Divider())
        tips.body.addWidget(
            label("فعالیت‌های هم‌نام در پروژه‌های مختلف، در گزارش‌ها زیر یک عنوان جمع می‌شوند.", "caption", wrap=True)
        )
        side.addWidget(tips)
        side.addStretch(1)

        side_holder = QWidget()
        side_holder.setLayout(side)
        side_holder.setMinimumWidth(300)
        side_holder.setMaximumWidth(420)
        row.addWidget(side_holder, 2)
        self.layout_.addLayout(row)
        self.layout_.addStretch(1)

    def header_actions(self) -> list[QWidget]:
        history = button("تاریخچه فعالیت‌ها", "secondary", "time-circle")
        history.clicked.connect(lambda: self.window_.go("history"))
        return [history]

    def on_show(self) -> None:
        super().on_show()
        self.form.focus_title()

    def refresh(self) -> None:
        self.form.refresh_choices()
        today = date.today()
        rows = activity_service.activities_on(today)
        minutes = sum(r.duration_minutes for r in rows)
        self.today_card.set_subtitle(fmt.fmt_date_long(today))
        self.today_total.setText(fmt.fmt_duration(minutes) if minutes else "بدون زمان ثبت‌شده")
        self.today_caption.setText(f"{fmt.fmt_int(len(rows))} فعالیت ثبت‌شده در امروز" if rows else "هنوز فعالیتی برای امروز ثبت نشده است.")
        clear_layout(self.today_list)
        for row in rows[:8]:
            item = ActivityListRow(row, show_day=False)
            item.clicked.connect(lambda r: ActivityDialog.edit(self, r.id))
            self.today_list.addWidget(item)
        if len(rows) > 8:
            more = button(f"مشاهده همه {fmt.fmt_int(len(rows))} فعالیت امروز", "ghost", size="sm")
            more.clicked.connect(lambda: self.window_.show_history(date_from=today, date_to=today))
            self.today_list.addWidget(more)
        if not rows:
            self.today_list.addWidget(label("فعالیت‌های امروز پس از ثبت اینجا نمایش داده می‌شوند.", "muted", wrap=True))

    # actions ---------------------------------------------------------------------

    def start_new(self, template: dict | None = None) -> None:
        if template:
            self.form.prefill(**template)
        self.form.focus_title()

    def _on_saved(self, _activity_id: int) -> None:
        toast("فعالیت با موفقیت ثبت شد.")
        self.form.reset(keep_context=True)
        notify("activities")
        self.form.focus_title()
