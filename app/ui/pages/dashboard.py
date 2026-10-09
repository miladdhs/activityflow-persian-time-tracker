from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from app import APP_NAME
from app.core import formatting as fmt
from app.services import stats_service
from app.ui.dialogs.activity_dialog import ActivityDialog
from app.ui.pages.base import BasePage
from app.ui.theme import tokens as t
from app.ui.widgets.activity_row import ActivityListRow
from app.ui.widgets.charts import BarChart, BarPoint, DonutChart, Legend, Segment
from app.ui.widgets.common import IconTile, SectionCard, button, clear_layout, label
from app.ui.widgets.display import EmptyState, StatCard, delta_note


class DashboardPage(BasePage):
    key = "dashboard"
    title = "داشبورد"
    subtitle = "نگاهی سریع به فعالیت‌های امروز و این ماه"
    topics = {"activities", "projects", "lookups", "settings"}

    def __init__(self, window):
        super().__init__(window)

        # onboarding banner (only while there is no data)
        self.banner = QFrame()
        self.banner.setObjectName("Banner")
        b = QHBoxLayout(self.banner)
        b.setContentsMargins(24, 20, 24, 20)
        b.setSpacing(16)
        b.addWidget(IconTile("activity", t.ACCENT_PRIMARY, 48, 24))
        texts = QVBoxLayout()
        texts.setSpacing(4)
        texts.addWidget(label(f"به {APP_NAME} خوش آمدید", "h3"))
        texts.addWidget(label("هنوز فعالیتی ثبت نشده است. با ثبت اولین فعالیت، آمار و نمودارها اینجا جان می‌گیرند.", "secondary", wrap=True))
        b.addLayout(texts, 1)
        start = button("ثبت اولین فعالیت", "primary", "plus")
        start.clicked.connect(lambda: self.window_.open_entry())
        b.addWidget(start)
        self.layout_.addWidget(self.banner)

        # stat cards
        self.card_today = StatCard("زمان فعالیت امروز", "time-circle", t.ACCENT_PRIMARY)
        self.card_count = StatCard("فعالیت‌های ثبت‌شده", "paper", t.INFO)
        self.card_projects = StatCard("پروژه‌های فعال", "folder", t.SUCCESS)
        self.card_month = StatCard("زمان فعالیت این ماه", "calendar", t.WARNING)
        self.cards = [self.card_today, self.card_count, self.card_projects, self.card_month]
        self.cards_grid = QGridLayout()
        self.cards_grid.setSpacing(t.SPACE_4)
        self._cards_cols = 0
        self.layout_.addLayout(self.cards_grid)

        # charts row
        self.week_card = SectionCard("زمان فعالیت در ۷ روز گذشته", "مجموع مدت‌زمان ثبت‌شده برای هر روز")
        self.week_chart = BarChart(height=230)
        self.week_card.body.addWidget(self.week_chart, 1)

        self.projects_card = SectionCard("توزیع زمان بین پروژه‌ها", "")
        donut_row = QHBoxLayout()
        donut_row.setSpacing(t.SPACE_5)
        self.donut = DonutChart(170)
        self.legend = Legend()
        donut_row.addWidget(self.donut, 0, Qt.AlignmentFlag.AlignVCenter)
        donut_row.addWidget(self.legend, 1)
        self.projects_empty = label("در این ماه هنوز زمانی برای پروژه‌ها ثبت نشده است.", "muted", wrap=True)
        self.projects_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.projects_card.body.addLayout(donut_row, 1)
        self.projects_card.body.addWidget(self.projects_empty, 1)

        self.charts_row = QHBoxLayout()
        self.charts_row.setSpacing(t.SPACE_4)
        self.charts_row.addWidget(self.week_card, 3)
        self.charts_row.addWidget(self.projects_card, 2)
        self.layout_.addLayout(self.charts_row)

        # lists row
        self.recent_card = SectionCard("آخرین فعالیت‌های ثبت‌شده", "برای ویرایش روی هر مورد کلیک کنید", padding=16)
        all_btn = button("مشاهده همه", "ghost", "arrow-left", size="sm")
        all_btn.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        all_btn.clicked.connect(lambda: self.window_.go("history"))
        self.recent_card.add_action(all_btn)
        self.recent_list = QVBoxLayout()
        self.recent_list.setSpacing(2)
        self.recent_card.body.addLayout(self.recent_list)
        self.recent_card.body.addStretch(1)

        self.frequent_card = SectionCard("فعالیت‌های پرتکرار", "۳۰ روز گذشته — برای ثبت دوباره کلیک کنید", padding=16)
        self.frequent_list = QVBoxLayout()
        self.frequent_list.setSpacing(2)
        self.frequent_card.body.addLayout(self.frequent_list)
        self.frequent_card.body.addStretch(1)

        lists_row = QHBoxLayout()
        lists_row.setSpacing(t.SPACE_4)
        lists_row.addWidget(self.recent_card, 3)
        lists_row.addWidget(self.frequent_card, 2)
        self.layout_.addLayout(lists_row)
        self.layout_.addStretch(1)
        self._layout_cards()

    def header_actions(self) -> list[QWidget]:
        add = button("ثبت فعالیت", "primary", "plus", tooltip="Ctrl+N")
        add.clicked.connect(lambda: self.window_.open_entry())
        return [add]

    # responsive grid -------------------------------------------------------------

    def _layout_cards(self) -> None:
        cols = 4 if self.width() >= 980 or self.width() == 0 else 2
        if cols == self._cards_cols:
            return
        self._cards_cols = cols
        for card in self.cards:
            self.cards_grid.removeWidget(card)
        for i, card in enumerate(self.cards):
            self.cards_grid.addWidget(card, i // cols, i % cols)
        for c in range(4):
            self.cards_grid.setColumnStretch(c, 1 if c < cols else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_cards()

    # data ----------------------------------------------------------------------------

    def refresh(self) -> None:
        data = stats_service.dashboard()
        self.banner.setVisible(data.total_count == 0)

        self.card_today.set_duration(data.today_minutes)
        note, tone = delta_note(data.today_minutes, data.yesterday_minutes, "دیروز")
        self.card_today.set_note(note or f"{fmt.fmt_int(data.today_count)} فعالیت امروز", tone)

        self.card_count.set_number(fmt.fmt_int(data.total_count), "فعالیت")
        self.card_count.set_note(f"{fmt.fmt_int(data.month_count)} مورد در {data.month_label}", "accent" if data.month_count else None)

        self.card_projects.set_number(fmt.fmt_int(data.active_projects), "پروژه")
        paused = data.open_projects - data.active_projects
        self.card_projects.set_note(f"{fmt.fmt_int(paused)} پروژه متوقف" if paused else "همه پروژه‌های باز فعال هستند" if data.active_projects else "هنوز پروژه‌ای فعال نیست")

        self.card_month.set_duration(data.month_minutes)
        note, tone = delta_note(data.month_minutes, data.prev_month_minutes, "ماه قبل")
        self.card_month.set_note(note or data.month_label, tone)

        self.week_chart.set_data(
            [
                BarPoint(fmt.weekday_name(d) if i < 6 else "امروز", fmt.fmt_date_with_weekday(d), minutes, i == 6)
                for i, (d, minutes) in enumerate(data.week)
            ]
        )
        self.week_card.set_subtitle(f"مجموع هفته: {fmt.fmt_duration(sum(m for _, m in data.week))}")

        segments = [Segment(s.name, s.color, s.minutes) for s in data.projects]
        total = sum(s.value for s in segments)
        self.projects_card.set_subtitle(data.month_label)
        has_projects = total > 0
        self.donut.setVisible(has_projects)
        self.legend.setVisible(has_projects)
        self.projects_empty.setVisible(not has_projects)
        self.donut.set_data(segments, fmt.fmt_clock(total), "ساعت:دقیقه")
        self.legend.set_data(segments)

        clear_layout(self.recent_list)
        if data.recent:
            for row in data.recent:
                item = ActivityListRow(row)
                item.clicked.connect(lambda r: ActivityDialog.edit(self, r.id))
                self.recent_list.addWidget(item)
        else:
            self.recent_list.addWidget(EmptyState("paper", "هنوز فعالیتی ثبت نشده است.", "فعالیت‌های جدید اینجا نمایش داده می‌شوند."))

        clear_layout(self.frequent_list)
        if data.frequent:
            for item in data.frequent:
                self.frequent_list.addWidget(self._frequent_row(item))
        else:
            self.frequent_list.addWidget(label("پس از چند ثبت، فعالیت‌های پرتکرار اینجا برای ثبت سریع ظاهر می‌شوند.", "muted", wrap=True))

    def _frequent_row(self, item) -> QWidget:
        row = QFrame()
        row.setObjectName("ListRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(10)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        name = label(item.title)
        name.setStyleSheet("font-weight: 500;")
        texts.addWidget(name)
        texts.addWidget(label(f"{fmt.fmt_int(item.count)} بار  ·  مجموع {fmt.fmt_duration_short(item.minutes)}", "caption"))
        layout.addLayout(texts, 1)
        again = button("ثبت دوباره", "ghost", "plus", size="sm", tooltip="باز کردن فرم با همین عنوان و تنظیمات")
        again.clicked.connect(lambda: self.window_.open_entry(template={"title": item.title}))
        layout.addWidget(again)
        return row
