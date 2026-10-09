"""Render every page (with demo data) to PNG files for the docs and visual review.

    python scripts/screenshots.py                 # -> docs/screenshots
    python scripts/screenshots.py out_dir --empty # first-run (no data) screens
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA = Path(tempfile.gettempdir()) / "activityflow-shots"
shutil.rmtree(DATA, ignore_errors=True)
os.environ["ACTIVITYFLOW_DATA_DIR"] = str(DATA)

from PySide6.QtCore import QEventLoop, Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def pump(ms: int = 120) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


WINDOW_SIZE = (1440, 900)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=ROOT / "docs" / "screenshots")
    parser.add_argument("--empty", action="store_true", help="capture the first-run screens without demo data")
    args = parser.parse_args()
    out: Path = args.output
    out.mkdir(parents=True, exist_ok=True)
    empty = args.empty

    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    from app.ui.theme import fonts
    from app.ui.theme.qss import build_stylesheet

    fonts.load_fonts()
    app.setFont(fonts.app_font())
    app.setStyleSheet(build_stylesheet())

    from app.database import init_engine, initialize_database
    from app.services import settings_service

    init_engine()
    initialize_database()
    if not empty:
        from scripts.demo_data import seed

        seed()
    settings_service.apply_display_prefs()

    from app.ui.main_window import MainWindow

    window = MainWindow()
    window.resize(*WINDOW_SIZE)
    window.show()
    pump(300)
    prefix = "empty-" if empty else ""
    for key in ("dashboard", "entry", "history", "projects", "reports", "settings"):
        window.go(key, animate=False)
        pump(250)
        window.grab().save(str(out / f"{prefix}{key}.png"))
        print("saved", key)

    if not empty:
        from app.services import activity_service, project_service
        from app.ui.dialogs.activity_dialog import ActivityDialog
        from app.ui.dialogs.project_dialog import ProjectDialog

        row = activity_service.recent_activities(1)[0]
        dialog = ActivityDialog(window, row.id)
        dialog.show()
        pump(400)
        dialog.grab().save(str(out / "dialog-activity.png"))
        dialog.reject()
        pump(300)

        dialog = ProjectDialog(window, project_service.all_projects()[0])
        dialog.show()
        pump(400)
        dialog.grab().save(str(out / "dialog-project.png"))
        dialog.reject()
        pump(300)
        from app.ui.dialogs.report_details_dialog import ReportDetailsDialog
        from app.ui.dialogs.titles_dialog import TitlesDialog
        from app.ui.events import toast
        from app.ui.widgets.common import Menu
        from app.ui.widgets.dialogs import MessageDialog

        reports = window.go("reports", animate=False)
        pump(200)
        result = reports.result
        dialog = ReportDetailsDialog(window, result.filter, result.group_by, result.groups[0])
        dialog.show()
        pump(400)
        dialog.grab().save(str(out / "dialog-details.png"))
        dialog.reject()

        dialog = TitlesDialog(window)
        dialog.show()
        pump(400)
        dialog.grab().save(str(out / "dialog-titles.png"))
        dialog.reject()

        dialog = MessageDialog(window, "حذف فعالیت", "فعالیت «ساخت کلیپ» برای همیشه حذف می‌شود.", tone="danger",
                               confirm_text="حذف فعالیت", cancel_text="انصراف", confirm_variant="danger-solid",
                               details="مجموع‌ها در همه گزارش‌ها به‌روز خواهند شد.")
        dialog.show()
        pump(400)
        dialog.grab().save(str(out / "dialog-confirm.png"))
        dialog.reject()
        pump(300)

        entry = window.go("entry", animate=False)
        pump(200)
        entry.form.date.open_popup()
        pump(300)
        entry.form.date._popup.grab().save(str(out / "popup-calendar.png"))
        entry.form.date._popup.close()
        entry.form.project.showPopup()
        pump(300)
        entry.form.project.view().window().grab().save(str(out / "popup-combo.png"))
        entry.form.project.hidePopup()

        menu = Menu(window)
        menu.item("ویرایش فعالیت", lambda: None, "edit")
        menu.item("ثبت دوباره (کپی)", lambda: None, "paper-plus")
        menu.addSeparator()
        menu.item("حذف فعالیت", lambda: None, "delete", danger=True)
        menu.popup(window.mapToGlobal(window.rect().center()))
        pump(300)
        menu.grab().save(str(out / "popup-menu.png"))
        menu.close()

        window.go("history", animate=False)
        toast("فعالیت با موفقیت ثبت شد.")
        toast("خروجی گزارش ذخیره شد.", action=("نمایش فایل", lambda: None))
        pump(500)
        window.grab().save(str(out / "toast.png"))
        print("saved dialogs")
    window.close()


if __name__ == "__main__":
    main()
