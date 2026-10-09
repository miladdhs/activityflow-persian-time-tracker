"""Fill a database with realistic sample data (for demos and screenshots).

Usage (writes to a separate folder, never to your real data):
    $env:ACTIVITYFLOW_DATA_DIR = "$PWD\\demo-data"; python scripts/demo_data.py
"""

from __future__ import annotations

import random
import sys
from datetime import date, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import init_engine, initialize_database  # noqa: E402
from app.services import activity_service, lookup_service, project_service  # noqa: E402
from app.services.activity_service import ActivityInput  # noqa: E402
from app.services.project_service import ProjectInput  # noqa: E402

PROJECTS = [
    ("فروشگاه آنلاین کارنو", "#8B5CF6", "active", "طراحی و توسعه فروشگاه اینترنتی با پنل مدیریت و درگاه پرداخت."),
    ("اپلیکیشن سلامت", "#60A5FA", "active", "اپلیکیشن موبایل پیگیری خواب، تغذیه و فعالیت روزانه."),
    ("تولید محتوای اینستاگرام", "#F472B6", "active", "تولید کلیپ و پست برای صفحه رسمی برند."),
    ("دستیار هوش مصنوعی", "#34D399", "paused", "چت‌بات پاسخ‌گوی پشتیبانی مشتریان بر پایه مدل زبانی."),
    ("وب‌سایت شخصی", "#FBBF24", "completed", ""),
]

TEMPLATES = [
    # title, project index, category name, minutes range, quantity (unit, range) or None
    ("توسعه API سفارش‌ها", 0, "برنامه‌نویسی", (60, 180), None),
    ("طراحی صفحه محصول", 0, "طراحی", (45, 120), None),
    ("رفع باگ‌های پرداخت", 0, "پشتیبانی", (30, 90), None),
    ("جلسه هفتگی تیم", None, "جلسه", (30, 60), None),
    ("پیاده‌سازی صفحه داشبورد", 1, "برنامه‌نویسی", (90, 200), None),
    ("طراحی رابط کاربری", 1, "طراحی", (60, 150), None),
    ("ساخت کلیپ", 2, "طراحی", (40, 120), ("کلیپ", (1, 3))),
    ("عکاسی محصول", 2, "طراحی", (60, 120), ("عکس", (8, 30))),
    ("آموزش مدل زبانی", 3, "توسعه هوش مصنوعی", (60, 240), None),
    ("مطالعه مقاله", None, "آموزش", (20, 60), ("صفحه", (10, 40))),
    ("تحقیق بازار", None, "تحقیق و توسعه", (30, 90), None),
    ("ساخت کلیپ", 0, "طراحی", (30, 90), ("کلیپ", (1, 2))),
]


def seed(days: int = 75, seed_value: int = 7) -> None:
    rnd = random.Random(seed_value)
    init_engine()
    initialize_database()
    if activity_service.has_any_activity():
        print("Database already has activities; skipping.")
        return
    categories = {c.name: c.id for c in lookup_service.list_categories()}
    units = {u.name: u.id for u in lookup_service.list_units()}
    today = date.today()
    project_ids = []
    for i, (name, color, _status, desc) in enumerate(PROJECTS):
        project_ids.append(
            project_service.create_project(
                ProjectInput(name=name, color=color, status="active", description=desc,
                             start_date=today - timedelta(days=days + 10 - i * 7))
            )
        )
    for day_offset in range(days, -1, -1):
        day = today - timedelta(days=day_offset)
        if day.weekday() == 4 and rnd.random() < 0.7:  # Fridays are mostly off
            continue
        clock = 9 * 60 + rnd.choice([0, 15, 30])
        for _ in range(rnd.randint(1, 4)):
            title, p_idx, cat, (lo, hi), qty = rnd.choice(TEMPLATES)
            minutes = rnd.randrange(lo, hi + 1, 5)
            use_range = rnd.random() < 0.5 and clock + minutes < 23 * 60
            inp = ActivityInput(
                title=title,
                activity_date=day,
                project_id=project_ids[p_idx] if p_idx is not None else None,
                category_id=categories.get(cat),
                time_mode="range" if use_range else "duration",
                start_time=time(clock // 60, clock % 60) if use_range else None,
                end_time=time((clock + minutes) // 60, (clock + minutes) % 60) if use_range else None,
                duration_minutes=None if use_range else minutes,
                quantity=str(rnd.randint(*qty[1])) if qty else None,
                unit_id=units.get(qty[0]) if qty else None,
                notes="",
            )
            activity_service.create_activity(inp)
            clock += minutes + rnd.choice([15, 30, 45])
    for pid, (_, _, status, _) in zip(project_ids, PROJECTS, strict=True):
        if status != "active":
            project_service.set_status(pid, status)
    print("Demo data created.")


if __name__ == "__main__":
    seed()
