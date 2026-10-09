"""CSV export — UTF-8 with BOM so Excel opens Persian text correctly."""

from __future__ import annotations

import csv
from pathlib import Path

from app.core.errors import StorageError
from app.reports.tables import RECORD_HEADERS, group_headers, group_row, record_row
from app.services.activity_service import ActivityRow
from app.services.report_service import ReportResult


def _write(path: Path, headers: list[str], rows: list[list]) -> Path:
    try:
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            writer.writerows(rows)
    except OSError as exc:
        raise StorageError("ذخیره فایل CSV با خطا مواجه شد. ممکن است فایل در برنامه دیگری باز باشد.") from exc
    return Path(path)


def export_records_csv(rows: list[ActivityRow], path: Path) -> Path:
    return _write(path, RECORD_HEADERS, [record_row(r) for r in rows])


def export_groups_csv(result: ReportResult, path: Path) -> Path:
    return _write(path, group_headers(result.group_by), [group_row(g) for g in result.groups])
