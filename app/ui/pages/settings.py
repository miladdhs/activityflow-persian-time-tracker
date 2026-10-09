from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app import APP_ISSUES_URL, APP_NAME, APP_RELEASES_URL, APP_REPOSITORY, APP_VERSION
from app.core import formatting as fmt
from app.core.errors import AppError
from app.core.paths import backups_dir, data_dir, db_path
from app.core.settings_keys import CALENDARS, Key
from app.services import backup_service, lookup_service, settings_service
from app.services.project_service import PROJECT_COLORS
from app.ui import icons
from app.ui.dialogs.prompt_dialog import NameDialog
from app.ui.dialogs.titles_dialog import TitlesDialog
from app.ui.events import notify, toast
from app.ui.files import ask_open_path, ask_save_path, open_folder, reveal_file
from app.ui.pages.base import BasePage
from app.ui.theme import tokens as t
from app.ui.widgets.common import (
    ColorDot,
    IconButton,
    SectionCard,
    SegmentedControl,
    ToggleSwitch,
    button,
    clear_layout,
    label,
)
from app.ui.widgets.dialogs import MessageDialog


def _setting_row(title: str, description: str, control: QWidget) -> QFrame:
    row = QFrame()
    row.setObjectName("SettingRow")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 12, 0, 12)
    layout.setSpacing(16)
    texts = QVBoxLayout()
    texts.setSpacing(3)
    name = label(title)
    name.setStyleSheet("font-weight: 500;")
    texts.addWidget(name)
    if description:
        texts.addWidget(label(description, "caption", wrap=True))
    layout.addLayout(texts, 1)
    layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
    return row


def _file_size(size: int) -> str:
    if size < 1024 * 1024:
        return f"{fmt.fmt_decimal(round(size / 1024, 1))} کیلوبایت"
    return f"{fmt.fmt_decimal(round(size / (1024 * 1024), 1))} مگابایت"


class SettingsPage(BasePage):
    key = "settings"
    title = "تنظیمات"
    subtitle = "نمایش، انواع فعالیت، واحدها و پشتیبان‌گیری از اطلاعات"
    topics = {"activities", "lookups", "settings"}

    def __init__(self, window):
        super().__init__(window)
        columns = QHBoxLayout()
        columns.setSpacing(t.SPACE_5)
        right = QVBoxLayout()
        right.setSpacing(t.SPACE_5)
        left = QVBoxLayout()
        left.setSpacing(t.SPACE_5)

        # display ------------------------------------------------------------------------
        display = SectionCard("نمایش", "نحوه نمایش اعداد و تاریخ‌ها در کل برنامه")
        self.digits = SegmentedControl([("fa", "۱۲۳ فارسی"), ("en", "123 لاتین")])
        self.digits.changed.connect(lambda k: self._set_display(Key.PERSIAN_DIGITS, "1" if k == "fa" else "0"))
        self.calendar = SegmentedControl(list(zip(CALENDARS, ("شمسی", "میلادی"), strict=True)))
        self.calendar.changed.connect(lambda k: self._set_display(Key.CALENDAR, k))
        display.body.addWidget(_setting_row("ارقام", "ارقام فارسی یا لاتین در جدول‌ها، آمار و گزارش‌ها", self.digits))
        display.body.addWidget(_setting_row("تقویم", "تقویم مورد استفاده برای نمایش و انتخاب تاریخ", self.calendar))
        self.display_preview = label("", "caption")
        display.body.addWidget(self.display_preview)
        right.addWidget(display)

        # categories -----------------------------------------------------------------------
        self.categories_card = SectionCard("انواع فعالیت", "برای دسته‌بندی فعالیت‌ها و گزارش‌گیری به تفکیک نوع")
        add_cat = button("نوع جدید", "secondary", "plus", size="sm")
        add_cat.clicked.connect(self._add_category)
        self.categories_card.add_action(add_cat)
        self.categories_list = QVBoxLayout()
        self.categories_list.setSpacing(0)
        self.categories_card.body.addLayout(self.categories_list)
        right.addWidget(self.categories_card)

        # units ---------------------------------------------------------------------------------
        self.units_card = SectionCard("واحدهای مقدار", "مقادیر با واحدهای متفاوت هرگز با هم جمع نمی‌شوند")
        add_unit = button("واحد جدید", "secondary", "plus", size="sm")
        add_unit.clicked.connect(self._add_unit)
        self.units_card.add_action(add_unit)
        self.units_list = QVBoxLayout()
        self.units_list.setSpacing(0)
        self.units_card.body.addLayout(self.units_list)
        right.addWidget(self.units_card)
        right.addStretch(1)

        # data & backup -------------------------------------------------------------------
        backup = SectionCard("اطلاعات و پشتیبان‌گیری", "همه اطلاعات فقط روی همین رایانه ذخیره می‌شود")
        path_box = QFrame()
        path_box.setObjectName("SoftPanel")
        pl = QHBoxLayout(path_box)
        pl.setContentsMargins(14, 10, 8, 10)
        pl.setSpacing(10)
        db_icon = QLabel()
        db_icon.setPixmap(icons.pixmap("folder", t.ACCENT_TEXT, 20))
        pl.addWidget(db_icon)
        path_texts = QVBoxLayout()
        path_texts.setSpacing(2)
        path_texts.addWidget(label("محل ذخیره اطلاعات", "caption"))
        self.path_label = label(str(data_dir()), "small", selectable=True)
        self.path_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        path_texts.addWidget(self.path_label)
        pl.addLayout(path_texts, 1)
        open_btn = IconButton("show", "باز کردن پوشه اطلاعات", size=34, icon_px=18)
        open_btn.clicked.connect(lambda: open_folder(data_dir()))
        pl.addWidget(open_btn)
        backup.body.addWidget(path_box)

        self.auto_toggle = ToggleSwitch()
        self.auto_toggle.toggled.connect(self._set_auto_backup)
        backup.body.addWidget(
            _setting_row(
                "پشتیبان‌گیری خودکار روزانه",
                f"هنگام اجرای برنامه، روزی یک نسخه پشتیبان ساخته می‌شود و {fmt.digits(backup_service.KEEP_AUTO_BACKUPS)} نسخه آخر نگه داشته می‌شود.",
                self.auto_toggle,
            )
        )
        self.backup_info = label("", "small", wrap=True)
        backup.body.addWidget(self.backup_info)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        backup_btn = button("تهیه نسخه پشتیبان", "primary", "shield-done")
        backup_btn.clicked.connect(self._backup)
        restore_btn = button("بازیابی از فایل", "secondary", "upload")
        restore_btn.clicked.connect(self._restore)
        actions.addWidget(backup_btn)
        actions.addWidget(restore_btn)
        actions.addStretch(1)
        backup.body.addLayout(actions)
        extra = QHBoxLayout()
        extra.setSpacing(10)
        json_btn = button("خروجی JSON", "ghost", "paper-download", size="sm")
        json_btn.clicked.connect(self._export_json)
        folder_btn = button("پوشه پشتیبان‌ها", "ghost", "folder", size="sm")
        folder_btn.clicked.connect(lambda: open_folder(backups_dir()))
        extra.addWidget(json_btn)
        extra.addWidget(folder_btn)
        extra.addStretch(1)
        backup.body.addLayout(extra)
        left.addWidget(backup)

        # titles ------------------------------------------------------------------------------
        titles = SectionCard("عناوین فعالیت", "")
        self.titles_text = label("", "secondary", wrap=True)
        titles.body.addWidget(self.titles_text)
        manage = button("مدیریت و ادغام عناوین", "secondary", "edit-square")
        manage.clicked.connect(lambda: TitlesDialog(self).exec())
        row = QHBoxLayout()
        row.addWidget(manage)
        row.addStretch(1)
        titles.body.addLayout(row)
        left.addWidget(titles)

        # about -------------------------------------------------------------------------------
        about = SectionCard("درباره برنامه", "")
        head = QHBoxLayout()
        head.setSpacing(14)
        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(48))
        head.addWidget(logo)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        name = label(f"{APP_NAME}", "h3")
        name.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        texts.addWidget(name)
        texts.addWidget(label(f"نسخه {fmt.digits(APP_VERSION)}  ·  ثبت و تحلیل فعالیت‌ها، کاملاً آفلاین", "small"))
        head.addLayout(texts, 1)
        about.body.addLayout(head)
        about.body.addWidget(
            label("اطلاعات شما هیچ‌وقت به اینترنت ارسال نمی‌شود. برای جلوگیری از از دست رفتن داده‌ها، پشتیبان‌گیری خودکار را روشن نگه دارید.", "caption", wrap=True)
        )
        links = QHBoxLayout()
        links.setSpacing(10)
        for text, icon, url in (
            ("صفحه پروژه", "discovery", APP_REPOSITORY),
            ("نسخه‌های جدید", "download", APP_RELEASES_URL),
            ("گزارش مشکل", "danger", APP_ISSUES_URL),
        ):
            link = button(text, "ghost", icon, size="sm")
            link.setToolTip(url)
            link.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            links.addWidget(link)
        links.addStretch(1)
        about.body.addLayout(links)
        left.addWidget(about)
        left.addStretch(1)

        columns.addLayout(right, 1)
        columns.addLayout(left, 1)
        self.layout_.addLayout(columns)
        self.layout_.addStretch(1)

    # refresh -----------------------------------------------------------------------------------

    def refresh(self) -> None:
        self.digits.set_current("fa" if fmt.prefs.persian_digits else "en")
        self.calendar.set_current(fmt.prefs.calendar)
        self.display_preview.setText(f"پیش‌نمایش: {fmt.fmt_date_with_weekday(date.today())}  ·  {fmt.fmt_duration(135)}")
        self.auto_toggle.blockSignals(True)
        self.auto_toggle.setChecked(settings_service.get_bool(Key.AUTO_BACKUP))
        self.auto_toggle.blockSignals(False)
        self._refresh_lookups()
        self._refresh_backup_info()

    def _refresh_lookups(self) -> None:
        clear_layout(self.categories_list)
        categories = lookup_service.list_categories()
        for cat in categories:
            self.categories_list.addWidget(self._lookup_row(
                cat.name, cat.usage, cat.color,
                lambda c=cat: self._edit_category(c), lambda c=cat: self._delete_category(c),
            ))
        if not categories:
            self.categories_list.addWidget(label("هنوز نوعی تعریف نشده است.", "muted"))

        clear_layout(self.units_list)
        units = lookup_service.list_units()
        for unit in units:
            self.units_list.addWidget(self._lookup_row(
                unit.name, unit.usage, None,
                lambda u=unit: self._rename_unit(u), lambda u=unit: self._delete_unit(u),
            ))
        if not units:
            self.units_list.addWidget(label("هنوز واحدی تعریف نشده است.", "muted"))

        titles = lookup_service.list_titles()
        self.titles_text.setText(
            f"{fmt.fmt_int(len(titles))} عنوان فعالیت ثبت شده است. فعالیت‌های هم‌نام در همه پروژه‌ها با هم جمع می‌شوند؛ "
            "عناوین مشابه (مثلاً با املای متفاوت) را می‌توانید ادغام کنید."
        )

    def _lookup_row(self, name: str, usage: int, color: str | None, on_edit, on_delete) -> QWidget:
        row = QFrame()
        row.setObjectName("ListRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(10)
        if color:
            layout.addWidget(ColorDot(color, 10))
        layout.addWidget(label(name), 1)
        layout.addWidget(label(f"{fmt.fmt_int(usage)} فعالیت" if usage else "بدون استفاده", "caption"))
        edit = IconButton("edit", "ویرایش", size=30, icon_px=16)
        edit.clicked.connect(on_edit)
        delete = IconButton("delete", "حذف", tone="danger", size=30, icon_px=16)
        delete.clicked.connect(on_delete)
        layout.addWidget(edit)
        layout.addWidget(delete)
        return row

    def _refresh_backup_info(self) -> None:
        backups = backup_service.list_backups()
        db = db_path()
        size = _file_size(db.stat().st_size) if db.exists() else "—"
        if backups:
            last = backups[0]
            when = last.created
            day = fmt.relative_day(when.date())
            self.backup_info.setText(
                f"آخرین نسخه پشتیبان: {day} ساعت {fmt.digits(when.strftime('%H:%M'))}"
                f"  ·  {fmt.fmt_int(len(backups))} نسخه موجود  ·  حجم اطلاعات: {size}"
            )
        else:
            self.backup_info.setText(f"هنوز نسخه پشتیبانی تهیه نشده است.  ·  حجم اطلاعات: {size}")

    # display -------------------------------------------------------------------------------------

    def _set_display(self, key: str, value: str) -> None:
        settings_service.set(key, value)
        settings_service.apply_display_prefs()
        notify("settings")
        toast("تنظیمات نمایش اعمال شد.")

    def _set_auto_backup(self, checked: bool) -> None:
        settings_service.set(Key.AUTO_BACKUP, checked)
        toast("پشتیبان‌گیری خودکار روشن شد." if checked else "پشتیبان‌گیری خودکار خاموش شد.", "success" if checked else "warning")

    # categories & units -------------------------------------------------------------------------

    def _used_colors(self) -> set[str]:
        return {c.color.upper() for c in lookup_service.list_categories()}

    def _add_category(self) -> None:
        used = self._used_colors()
        color = next((c for c in PROJECT_COLORS if c.upper() not in used), PROJECT_COLORS[0])
        dialog = NameDialog(self, "نوع فعالیت جدید", "نام نوع", lambda n, c: lookup_service.create_category(n, c),
                            colors=PROJECT_COLORS, color=color, save_text="افزودن")
        if dialog.exec():
            notify("lookups")
            toast("نوع فعالیت اضافه شد.")

    def _edit_category(self, cat) -> None:
        dialog = NameDialog(self, "ویرایش نوع فعالیت", "نام نوع",
                            lambda n, c: lookup_service.update_category(cat.id, n, c),
                            value=cat.name, colors=PROJECT_COLORS, color=cat.color)
        if dialog.exec():
            notify("lookups")
            notify("activities")
            toast("نوع فعالیت ویرایش شد.")

    def _delete_category(self, cat) -> None:
        details = (f"{fmt.fmt_int(cat.usage)} فعالیت با این نوع حذف نمی‌شوند و «بدون نوع» خواهند شد."
                   if cat.usage else "هیچ فعالیتی از این نوع استفاده نمی‌کند.")
        if not MessageDialog.confirm(self, "حذف نوع فعالیت", f"نوع «{cat.name}» حذف شود؟",
                                     confirm_text="حذف نوع", details=details):
            return
        try:
            lookup_service.delete_category(cat.id)
        except AppError as exc:
            MessageDialog.error(self, exc.message)
            return
        notify("lookups")
        notify("activities")
        toast("نوع فعالیت حذف شد.")

    def _add_unit(self) -> None:
        dialog = NameDialog(self, "واحد جدید", "نام واحد", lambda n, _c: lookup_service.create_unit(n),
                            save_text="افزودن", max_length=30, subtitle="مثلاً: کلیپ، عکس، صفحه، کیلوگرم")
        if dialog.exec():
            notify("lookups")
            toast("واحد اضافه شد.")

    def _rename_unit(self, unit) -> None:
        dialog = NameDialog(self, "ویرایش واحد", "نام واحد", lambda n, _c: lookup_service.rename_unit(unit.id, n),
                            value=unit.name, max_length=30)
        if dialog.exec():
            notify("lookups")
            notify("activities")
            toast("واحد ویرایش شد.")

    def _delete_unit(self, unit) -> None:
        if unit.usage:
            MessageDialog.info(
                self, "حذف واحد ممکن نیست",
                f"واحد «{unit.name}» در {fmt.fmt_int(unit.usage)} فعالیت استفاده شده است. "
                "برای حفظ درستی گزارش‌ها، فقط واحدهای بدون استفاده قابل حذف هستند؛ می‌توانید نام آن را تغییر دهید.",
            )
            return
        if not MessageDialog.confirm(self, "حذف واحد", f"واحد «{unit.name}» حذف شود؟", confirm_text="حذف واحد"):
            return
        try:
            lookup_service.delete_unit(unit.id)
        except AppError as exc:
            MessageDialog.error(self, exc.message)
            return
        notify("lookups")
        toast("واحد حذف شد.")

    # backup -------------------------------------------------------------------------------------

    def _backup(self) -> None:
        name = f"{APP_NAME}-backup-{datetime.now():%Y-%m-%d-%H%M}.sqlite3"
        path = ask_save_path(self, "ذخیره نسخه پشتیبان", name, f"نسخه پشتیبان {APP_NAME} (*.sqlite3)")
        if path is None:
            return
        try:
            backup_service.create_backup(path)
            if path.parent.resolve() != backups_dir().resolve():
                backup_service.create_backup(prefix="backup-")
        except AppError as exc:
            MessageDialog.error(self, exc.message)
            return
        self._refresh_backup_info()
        toast("نسخه پشتیبان با موفقیت ذخیره شد.", action=("نمایش فایل", lambda: reveal_file(path)))

    def _restore(self) -> None:
        path = ask_open_path(self, "انتخاب فایل پشتیبان", backups_dir(), f"نسخه پشتیبان {APP_NAME} (*.sqlite3 *.db);;همه فایل‌ها (*.*)")
        if path is None:
            return
        try:
            backup_service.validate_backup_file(path)
        except AppError as exc:
            MessageDialog.error(self, exc.message, "فایل نامعتبر")
            return
        if not MessageDialog.confirm(
            self, "بازیابی اطلاعات",
            "همه اطلاعات فعلی با محتوای این نسخه پشتیبان جایگزین می‌شود.",
            confirm_text="بازیابی اطلاعات",
            details=f"قبل از بازیابی، یک نسخه پشتیبان ایمنی از اطلاعات فعلی در پوشه پشتیبان‌ها ساخته می‌شود.\n{path.name}",
        ):
            return
        try:
            backup_service.restore_backup(path)
        except AppError as exc:
            MessageDialog.error(self, exc.message)
            return
        settings_service.apply_display_prefs()
        notify("all")
        toast("اطلاعات با موفقیت بازیابی شد.")

    def _export_json(self) -> None:
        path = ask_save_path(self, "خروجی JSON", f"{APP_NAME}-data-{date.today():%Y-%m-%d}.json", "JSON (*.json)")
        if path is None:
            return
        try:
            backup_service.export_json(path)
        except AppError as exc:
            MessageDialog.error(self, exc.message)
            return
        toast("خروجی JSON ذخیره شد.", action=("نمایش فایل", lambda: reveal_file(path)))
