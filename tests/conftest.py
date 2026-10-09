import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ACTIVITYFLOW_DATA_DIR", str(tmp_path))
    from app.core import formatting
    from app.database import dispose_engine, init_engine, initialize_database
    from app.services import settings_service

    formatting.prefs.persian_digits = True
    formatting.prefs.calendar = "jalali"
    init_engine()
    initialize_database()
    settings_service.invalidate()
    yield tmp_path
    dispose_engine()
    settings_service.invalidate()
