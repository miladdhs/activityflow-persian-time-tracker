"""End-to-end smoke test of the real main window (rendered offscreen)."""

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    from app.ui.theme import fonts
    from app.ui.theme.qss import build_stylesheet

    fonts.load_fonts()
    app.setStyleSheet(build_stylesheet())
    yield app


@pytest.fixture()
def window(qapp, db):
    from app.ui.main_window import MainWindow

    win = MainWindow()
    win.show()
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


def test_navigate_every_page(window, qapp):
    for key in ("dashboard", "entry", "history", "projects", "reports", "settings"):
        page = window.go(key, animate=False)
        qapp.processEvents()
        assert window.stack.currentWidget() is page
        assert window.header.title.text() == page.title


def test_entry_form_creates_activity_and_refreshes_pages(window, qapp):
    from app.services import activity_service

    window.open_entry()
    form = window.pages["entry"].form
    form.title.setText("ساخت کلیپ")
    form.set_duration(75)
    form.quantity.setText("3")
    form.unit.setCurrentIndex(1)
    assert form.submit() is not None
    qapp.processEvents()

    rows = activity_service.list_activities()
    assert len(rows) == 1
    assert rows[0].duration_minutes == 75 and str(rows[0].quantity) == "3"
    assert form.title.text() == ""  # form resets for the next entry

    history = window.go("history", animate=False)
    qapp.processEvents()
    assert len(history.table.rows()) == 1

    dashboard = window.go("dashboard", animate=False)
    qapp.processEvents()
    assert dashboard.banner.isHidden()


def test_entry_form_shows_inline_errors(window, qapp):
    window.open_entry()
    form = window.pages["entry"].form
    form.reset(keep_context=False)
    assert form.submit() is None
    assert form.f_title.error_label.isVisibleTo(form)


def test_history_filters_and_project_shortcut(window, qapp):
    from app.services import activity_service, project_service
    from app.services.activity_service import ActivityInput
    from app.services.project_service import ProjectInput

    pid = project_service.create_project(ProjectInput(name="پروژه آزمایشی"))
    activity_service.create_activity(ActivityInput("الف", date.today(), project_id=pid, duration_minutes=30))
    activity_service.create_activity(ActivityInput("ب", date.today(), duration_minutes=45))

    window.show_history(project_id=pid)
    qapp.processEvents()
    history = window.pages["history"]
    assert [r.title for r in history.table.rows()] == ["الف"]

    history.clear_filters()
    qapp.processEvents()
    assert len(history.table.rows()) == 2


def test_reports_and_settings_pages(window, qapp):
    from app.core import formatting
    from app.services import activity_service
    from app.services.activity_service import ActivityInput

    activity_service.create_activity(ActivityInput("گزارش", date.today(), duration_minutes=90))
    reports = window.go("reports", animate=False)
    qapp.processEvents()
    assert reports.result is not None and reports.result.count == 1
    reports.period.set_current("year", emit=True)
    qapp.processEvents()
    assert reports.result.count == 1

    settings = window.go("settings", animate=False)
    qapp.processEvents()
    settings.calendar.set_current("gregorian", emit=True)
    qapp.processEvents()
    assert formatting.prefs.calendar == "gregorian"
    settings.calendar.set_current("jalali", emit=True)
    qapp.processEvents()
    assert formatting.prefs.calendar == "jalali"
