from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.core.paths import logs_dir


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return logging.getLogger("activityflow")

    root.setLevel(level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    try:
        file_handler = RotatingFileHandler(
            logs_dir() / "activityflow.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        pass

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.WARNING)
    root.addHandler(console)
    return logging.getLogger("activityflow")
