"""Application bootstrap: logging, Qt setup, database, theme and the main window."""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
import traceback

from PySide6.QtCore import QLibraryInfo, QLocale, QLockFile, Qt, QTimer, QTranslator
from PySide6.QtWidgets import QApplication

from app import APP_NAME, APP_ORGANIZATION, APP_USER_MODEL_ID, APP_VERSION
from app.core.errors import AppError
from app.core.logging_setup import setup_logging
from app.core.paths import data_dir

log = logging.getLogger("activityflow")


def _set_app_user_model_id() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except (AttributeError, OSError):
            pass


def _install_translations(app: QApplication) -> None:
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name in ("qtbase_fa", "qt_fa"):
        translator = QTranslator(app)
        if translator.load(name, path):
            app.installTranslator(translator)


def _install_exception_hook() -> None:
    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        log.error("Unhandled exception:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
        from app.ui.widgets.dialogs import MessageDialog

        app = QApplication.instance()
        if app is None:
            return
        message = exc.message if isinstance(exc, AppError) else "یک خطای پیش‌بینی‌نشده رخ داد. اطلاعات شما حفظ شده است."
        try:
            MessageDialog.error(app.activeWindow(), message)
        except Exception:  # noqa: BLE001 - never let the hook itself crash the app
            pass

    sys.excepthook = hook
    threading.excepthook = lambda args: hook(args.exc_type, args.exc_value, args.exc_traceback)


def run() -> int:
    _set_app_user_model_id()
    setup_logging()
    log.info("Starting %s %s", APP_NAME, APP_VERSION)

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORGANIZATION)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    QLocale.setDefault(QLocale(QLocale.Language.Persian, QLocale.Country.Iran))
    _install_translations(app)

    from app.ui import icons
    from app.ui.theme import fonts
    from app.ui.theme.qss import build_stylesheet
    from app.ui.widgets.dialogs import MessageDialog

    fonts.load_fonts()
    app.setFont(fonts.app_font())
    app.setWindowIcon(icons.app_icon())
    app.setStyleSheet(build_stylesheet())

    lock = QLockFile(str(data_dir() / "activityflow.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        MessageDialog.info(None, "برنامه در حال اجراست", f"{APP_NAME} هم‌اکنون باز است. لطفاً از پنجره باز استفاده کنید.")
        return 0

    from app.database import init_engine, initialize_database
    from app.services import backup_service, settings_service

    try:
        init_engine()
        initialize_database()
        settings_service.apply_display_prefs()
    except Exception as exc:  # noqa: BLE001 - shown to the user, details in the log
        log.exception("Database initialisation failed")
        message = exc.message if isinstance(exc, AppError) else "پایگاه داده برنامه باز نشد."
        MessageDialog.error(None, f"{message}\nمسیر اطلاعات: {data_dir()}", "خطا در راه‌اندازی")
        return 1

    _install_exception_hook()

    from app.ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    def background_backup() -> None:
        try:
            backup_service.auto_backup_if_due()
        except AppError as exc:
            log.warning("Automatic backup failed: %s", exc.message)
        except Exception:  # noqa: BLE001
            log.exception("Automatic backup failed")

    QTimer.singleShot(1500, background_backup)
    code = app.exec()

    from app.database import dispose_engine

    dispose_engine()
    lock.unlock()
    log.info("Exited with code %s", code)
    return code
