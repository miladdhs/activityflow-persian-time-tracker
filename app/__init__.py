"""ActivityFlow — offline Persian activity tracker & project manager.

Single source of truth for product metadata; packaging (pyproject, the
PyInstaller spec and the build script) reads these values from here.
"""

APP_NAME = "ActivityFlow"
APP_NAME_FA = "مدیریت فعالیت‌ها"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Offline Persian (Farsi) activity tracker, timesheet and project manager for Windows"
APP_AUTHOR = "Milad Dhs"
APP_ORGANIZATION = APP_NAME
APP_USER_MODEL_ID = f"{APP_NAME}.Desktop.1"
APP_COPYRIGHT = f"Copyright (c) 2026 {APP_AUTHOR}. MIT License."
APP_REPOSITORY = "https://github.com/miladdhs/activityflow-persian-time-tracker"
APP_ISSUES_URL = f"{APP_REPOSITORY}/issues"
APP_RELEASES_URL = f"{APP_REPOSITORY}/releases/latest"

__version__ = APP_VERSION
