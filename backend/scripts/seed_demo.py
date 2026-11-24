"""Seeds a demo dataset through the public API (plus historical attendance rows).

Usage (with the API running and the same DATABASE_URL):
    python scripts/seed_demo.py --base http://127.0.0.1:8000 --admin-password Admin-Demo-123
"""

import argparse
import random
from datetime import datetime, time, timedelta

import httpx

from app.config import settings
from app.db import SessionLocal
from app.geo import haversine_m  # noqa: F401  (ensures app is importable)
from app.models import (
    STATUS_APPROVED,
    STATUS_PENDING,
    AttendanceRecord,
    LateCheckoutRequest,
    LeaveRequest,
    User,
)
from app.timeutil import local_date

TEHRAN = "+03:30"

BRANCHES = [
    {"name": "دفتر مرکزی - آزادی", "address": "تهران، میدان آزادی", "latitude": 35.6996, "longitude": 51.3380, "radius_m": 120},
    {"name": "شعبه غرب - سعادت‌آباد", "address": "تهران، سعادت‌آباد", "latitude": 35.7450, "longitude": 51.3700, "radius_m": 100},
]

EMPLOYEES = [
    ("sara.ahmadi", "سارا احمدی"),
    ("ali.rezaei", "علی رضایی"),
    ("mina.karimi", "مینا کریمی"),
    ("reza.moradi", "رضا مرادی"),
    ("neda.hosseini", "ندا حسینی"),
    ("amir.tavakoli", "امیر توکلی"),
    ("pwa.tester", "نیلوفر تستی"),  # used by the PWA end-to-end test
]

WORK_NOTES = [
    "بررسی ایمیل‌ها و پاسخ به درخواست‌های مشتریان",
    "جلسه برنامه‌ریزی هفتگی تیم و مرور پیشرفت پروژه",
    "توسعه قابلیت جدید پنل و رفع باگ‌های گزارش‌شده",
    "پیگیری اسناد مالی و بایگانی قراردادها",
    "کدنویسی ماژول گزارش‌گیری و نوشتن تست",
    "پشتیبانی تلفنی و ثبت تیکت‌های کاربران",
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://127.0.0.1:8000")
    p.add_argument("--admin-password", required=True)
    p.add_argument("--new-admin-password", help="optional: rotate the admin password after login")
    args = p.parse_args()
    api = f"{args.base}/api/v1"

    with httpx.Client(timeout=20) as c:
        r = c.post(f"{api}/auth/login", json={"username": settings.admin_bootstrap_username, "password": args.admin_password})
        r.raise_for_status()
        token = r.json()["access_token"]
        if args.new_admin_password:
            r = c.post(f"{api}/auth/change-password", headers={"Authorization": f"Bearer {token}"},
                       json={"current_password": args.admin_password, "new_password": args.new_admin_password})
            r.raise_for_status()
            token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        branch_ids = []
        for b in BRANCHES:
            r = c.post(f"{api}/admin/branches", headers=h, json=b)
            r.raise_for_status()
            branch_ids.append(r.json()["id"])

        emp_ids = []
        for i, (username, full_name) in enumerate(EMPLOYEES):
            assigned = branch_ids if i == 0 else [branch_ids[i % 2]]
            r = c.post(f"{api}/admin/employees", headers=h, json={
                "username": username,
                "full_name": full_name,
                "password": "Initial-Pass-1",
                "branch_ids": assigned,
            })
            r.raise_for_status()
            emp_ids.append(r.json()["id"])

    # Historical attendance (past 6 workdays) and today's activity, written directly to the DB.
    random.seed(7)
    today = local_date(datetime.now().astimezone())
    with SessionLocal() as db:
        users = {u.id: u for u in db.query(User).filter(User.id.in_(emp_ids)).all()}
        for offset in range(1, 7):
            day = today - timedelta(days=offset)
            if day.weekday() == 4:  # Friday weekend in Iran
                continue
            for i, uid in enumerate(emp_ids):
                if random.random() < 0.12:  # occasional absence
                    continue
                branch_id = branch_ids[0] if i == 0 else branch_ids[i % 2]
                in_t = time(8, random.randint(0, 25))
                out_t = time(16 + random.randint(0, 2), random.randint(0, 50))
                check_in = datetime.combine(day, in_t, tzinfo=_tehran())
                check_out = datetime.combine(day, out_t, tzinfo=_tehran())
                db.add(AttendanceRecord(
                    user_id=uid, branch_id=branch_id, work_date=day,
                    check_in_at=check_in, check_in_lat=35.7, check_in_lng=51.35,
                    check_in_accuracy_m=8, check_in_distance_m=12,
                    check_out_at=check_out, check_out_lat=35.7, check_out_lng=51.35,
                    check_out_accuracy_m=9, check_out_distance_m=15,
                    check_out_source="employee",
                    work_description=random.choice(WORK_NOTES),
                ))

        now = datetime.now().astimezone()
        open_rec = None
        for i, uid in enumerate(emp_ids[:4]):
            branch_id = branch_ids[0] if i == 0 else branch_ids[i % 2]
            in_at = now - timedelta(hours=random.choice([3, 4, 5]))
            out_at = None if i < 2 else now - timedelta(minutes=random.randint(10, 60))
            rec = AttendanceRecord(
                user_id=uid, branch_id=branch_id, work_date=today,
                check_in_at=in_at, check_in_lat=35.7, check_in_lng=51.35,
                check_in_accuracy_m=7, check_in_distance_m=10,
                check_out_at=out_at, check_out_lat=35.7 if out_at else None,
                check_out_lng=51.35 if out_at else None,
                check_out_accuracy_m=8 if out_at else None,
                check_out_distance_m=14 if out_at else None,
                check_out_source="employee" if out_at else None,
                work_description=random.choice(WORK_NOTES) if out_at else None,
            )
            db.add(rec)
            if out_at is None and open_rec is None:
                open_rec = rec
        db.commit()

        # --- demo leave requests ---
        yday = today - timedelta(days=1)
        db.add(LeaveRequest(
            user_id=emp_ids[1], start_date=today + timedelta(days=3),
            end_date=today + timedelta(days=4), reason="مرخصی شخصی",
            status=STATUS_PENDING,
        ))
        db.add(LeaveRequest(
            user_id=emp_ids[2], start_date=yday - timedelta(days=2),
            end_date=yday - timedelta(days=1), reason="مرخصی استعلاجی",
            status=STATUS_APPROVED, decided_at=now, decided_by=1,
        ))

        # --- demo forgotten check-out: yesterday's record without a check-out ---
        yesterday = today - timedelta(days=1)
        if yesterday.weekday() != 4:  # not Friday
            emp_id = emp_ids[3]
            branch_id = branch_ids[0]
            check_in = datetime.combine(yesterday, time(8, 12), tzinfo=_tehran())
            rec = AttendanceRecord(
                user_id=emp_id, branch_id=branch_id, work_date=yesterday,
                check_in_at=check_in, check_in_lat=35.7, check_in_lng=51.35,
                check_in_accuracy_m=8, check_in_distance_m=12,
            )
            db.add(rec)
            db.flush()
            db.add(LateCheckoutRequest(
                user_id=emp_id, record_id=rec.id, work_date=yesterday,
                branch_id=branch_id, requested_at=now,
                check_out_at=datetime.combine(yesterday, time(17, 20), tzinfo=_tehran()),
                latitude=35.7, longitude=51.35, accuracy_m=9, distance_m=14,
                description="پایان پروژه گزارش ماهانه و تحویل به واحد مالی",
                status=STATUS_PENDING,
            ))
        db.commit()

    print(f"seeded {len(branch_ids)} branches, {len(emp_ids)} employees")


def _tehran():
    from zoneinfo import ZoneInfo
    return ZoneInfo(settings.timezone)


if __name__ == "__main__":
    main()
