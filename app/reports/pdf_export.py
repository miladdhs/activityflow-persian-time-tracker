"""PDF export rendered by Qt's text engine, which shapes Persian text correctly."""

from __future__ import annotations

from html import escape
from pathlib import Path

from app import APP_NAME
from app.core import formatting as fmt
from app.core.errors import StorageError
from app.reports.tables import quantity_text
from app.services.activity_service import ActivityRow
from app.services.report_service import GROUP_BY, ReportResult

ACCENT = "#6D46E0"
MUTED = "#6B6880"
LINE = "#E6E2F0"
HEAD_BG = "#F3F0FA"


def _cell(text: str, head: bool = False, align: str = "right") -> str:
    tag = "th" if head else "td"
    style = f"color:{'#2A2540' if head else '#1F1B2E'};" + ("font-weight:600;" if head else "")
    return f'<{tag} align="{align}" style="{style}">{escape(str(text))}</{tag}>'


def _rtl(cells: list[str]) -> str:
    # Qt's rich-text tables ignore dir="rtl", so the first logical column is emitted last (rightmost).
    return "".join(reversed(cells))


def _table(headers: list[str], rows: list[list[str]], numeric: set[int]) -> str:
    head = _rtl([_cell(h, True, "center" if i in numeric else "right") for i, h in enumerate(headers)])
    body = []
    for n, row in enumerate(rows):
        bg = ' bgcolor="#FAF9FD"' if n % 2 else ""
        cells = _rtl([_cell(v, False, "center" if i in numeric else "right") for i, v in enumerate(row)])
        body.append(f"<tr{bg}>{cells}</tr>")
    return (
        f'<table dir="rtl" width="100%" cellspacing="0" cellpadding="6" border="0" '
        f'style="border-collapse:collapse; border-bottom:1px solid {LINE};">'
        f'<tr bgcolor="{HEAD_BG}">{head}</tr>{"".join(body)}</table>'
    )


def build_html(result: ReportResult, records: list[ActivityRow], meta: list[tuple[str, str]]) -> str:
    meta_html = " &nbsp;·&nbsp; ".join(
        f'<span style="color:{MUTED}">{escape(k)}:</span> {escape(v)}' for k, v in meta
    )
    metrics = [
        ("مجموع زمان", fmt.fmt_duration_short(result.total_minutes)),
        ("تعداد فعالیت‌ها", fmt.fmt_int(result.count)),
        ("میانگین هر فعالیت", fmt.fmt_duration_short(result.avg_minutes)),
        ("روزهای فعال", fmt.fmt_int(result.active_days)),
    ]
    metric_cells = _rtl([
        f'<td width="25%" align="center" style="padding:10px;">'
        f'<p align="center" style="color:{MUTED}; font-size:9pt; margin:0;">{escape(k)}</p>'
        f'<p align="center" style="color:{ACCENT}; font-size:13pt; font-weight:700; margin:0;">{escape(v)}</p></td>'
        for k, v in metrics
    ])
    quantities = quantity_text(result.quantities, latin=False)

    group_rows = [
        [
            g.name,
            fmt.fmt_int(g.count),
            fmt.fmt_clock(g.minutes),
            fmt.fmt_clock(g.avg_minutes),
            fmt.fmt_percent(g.share),
            quantity_text(g.quantities, latin=False) or "—",
        ]
        for g in result.groups
    ]
    record_rows = [
        [
            fmt.fmt_date(r.activity_date),
            r.title,
            r.project_name or "بدون پروژه",
            r.category_name or "بدون نوع",
            fmt.fmt_clock(r.duration_minutes),
            f"{fmt.fmt_decimal(r.quantity)} {r.unit_name}" if r.quantity is not None else "—",
        ]
        for r in records
    ]

    return f"""
<html dir="rtl"><body dir="rtl" style="font-family:'Vazirmatn'; font-size:10pt; color:#1F1B2E;">
<p dir="rtl" align="right" style="font-size:18pt; font-weight:700; color:{ACCENT}; margin:0;">گزارش فعالیت‌ها</p>
<p dir="rtl" align="right" style="font-size:9pt; margin-top:4px;">{meta_html}</p>
<table dir="rtl" width="100%" cellspacing="6" cellpadding="0" bgcolor="{HEAD_BG}"><tr>{metric_cells}</tr></table>
{f'<p dir="rtl" align="right" style="margin-top:8px;"><span style="color:{MUTED}">مقادیر ثبت‌شده:</span> {escape(quantities)}</p>' if quantities else ''}
<p dir="rtl" align="right" style="font-size:12pt; font-weight:700; margin-top:16px;">گروه‌بندی بر اساس {escape(GROUP_BY.get(result.group_by, ''))}</p>
{_table([GROUP_BY.get(result.group_by, 'گروه'), 'تعداد', 'مجموع زمان', 'میانگین', 'سهم', 'مقادیر'], group_rows, {1, 2, 3, 4})}
<p dir="rtl" align="right" style="font-size:12pt; font-weight:700; margin-top:18px;">ریز فعالیت‌ها</p>
{_table(['تاریخ', 'عنوان فعالیت', 'پروژه', 'نوع فعالیت', 'مدت‌زمان', 'مقدار'], record_rows, {0, 4, 5})}
</body></html>
"""


def export_report_pdf(
    result: ReportResult, records: list[ActivityRow], meta: list[tuple[str, str]], path: Path
) -> Path:
    from PySide6.QtCore import QMarginsF, QSizeF, Qt
    from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPdfWriter, QTextDocument, QTextOption

    try:
        writer = QPdfWriter(str(path))
        writer.setResolution(300)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Unit.Millimeter)
        writer.setTitle("گزارش ActivityFlow")
        writer.setCreator(APP_NAME)

        doc = QTextDocument()
        doc.documentLayout().setPaintDevice(writer)
        font = QFont("Vazirmatn")
        font.setPointSizeF(10)
        doc.setDefaultFont(font)
        option = QTextOption()
        option.setTextDirection(Qt.LayoutDirection.RightToLeft)
        option.setAlignment(Qt.AlignmentFlag.AlignRight)
        doc.setDefaultTextOption(option)
        doc.setDocumentMargin(0)
        doc.setHtml(build_html(result, records, meta))
        # A valid page size stops print_() from adding its own 2cm margins and page numbers.
        doc.setPageSize(QSizeF(writer.width(), writer.height()))
        doc.print_(writer)
        del writer
    except Exception as exc:  # noqa: BLE001 - surfaced as a friendly storage error
        raise StorageError("ساخت فایل PDF با خطا مواجه شد. ممکن است فایل در برنامه دیگری باز باشد.") from exc
    if not Path(path).exists() or Path(path).stat().st_size == 0:
        raise StorageError("ساخت فایل PDF با خطا مواجه شد. ممکن است فایل در برنامه دیگری باز باشد.")
    return Path(path)
