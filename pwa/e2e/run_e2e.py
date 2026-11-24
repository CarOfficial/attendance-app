"""End-to-end check of the employee PWA on a mobile viewport with simulated GPS.

Requires:
  * API on :8000 and the PWA preview build on :4174 (``npm run build && npm run preview``)
  * demo data from ``backend/scripts/seed_demo.py`` in the same database the API uses
  * ``playwright`` installed (``python -m playwright install chromium``)

The tester account is reset to a clean first-login state before the run, so the
script can be repeated. Screenshots are written next to this file.

Environment overrides: E2E_BASE, E2E_DB, CHROME_PATH, E2E_CHANNEL (default: msedge,
because the bundled Chromium download is blocked on some networks).
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import bcrypt
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE = os.environ.get("E2E_BASE", "http://localhost:4174")
DB = Path(os.environ.get("E2E_DB", ROOT / "backend" / "smoke.db"))
OUT = Path(__file__).resolve().parent

USERNAME = "pwa.tester"
INITIAL = "Initial-Pass-1"
NEW_PASSWORD = "Tester-Pass-2026"
DESCRIPTION = "بررسی ایمیل‌ها و پاسخ به مشتریان"

INSIDE = (35.6996, 51.3380)   # دفتر مرکزی - آزادی (radius 120 m)
OUTSIDE = (35.7450, 51.3700)  # about 6 km away


def reset_tester() -> None:
    """Undo the previous run: initial password, forced change, no record for today."""
    if not DB.exists():
        sys.exit(f"database not found: {DB} (run backend/scripts/seed_demo.py first)")
    today = datetime.now(ZoneInfo("Asia/Tehran")).date().isoformat()
    password_hash = bcrypt.hashpw(INITIAL.encode(), bcrypt.gensalt(rounds=12)).decode()
    with sqlite3.connect(DB) as db:
        row = db.execute("SELECT id FROM users WHERE username = ?", (USERNAME,)).fetchone()
        if row is None:
            sys.exit(f"user {USERNAME} not found in {DB}; run seed_demo.py first")
        user_id = row[0]
        db.execute(
            "DELETE FROM late_checkout_requests WHERE record_id IN"
            " (SELECT id FROM attendance_records WHERE user_id = ? AND work_date = ?)",
            (user_id, today),
        )
        # Approved leave for today would block the check-in.
        db.execute(
            "DELETE FROM leave_requests WHERE user_id = ? AND start_date <= ? AND end_date >= ?",
            (user_id, today, today),
        )
        db.execute(
            "DELETE FROM attendance_records WHERE user_id = ? AND work_date = ?",
            (user_id, today),
        )
        db.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 1,"
            " failed_login_count = 0, locked_until = NULL, token_version = token_version + 1"
            " WHERE id = ?",
            (password_hash, user_id),
        )


def set_location(context, page, lat, lng) -> None:
    context.set_geolocation({"latitude": lat, "longitude": lng, "accuracy": 12})
    page.wait_for_timeout(200)


def main() -> None:
    reset_tester()

    with sync_playwright() as p:
        # An installed Chrome/Edge by default; CHROME_PATH points at a specific binary and
        # E2E_CHANNEL="" falls back to Playwright's bundled Chromium.
        chrome_path = os.environ.get("CHROME_PATH")
        channel = None if chrome_path else (os.environ.get("E2E_CHANNEL", "msedge") or None)
        browser = p.chromium.launch(executable_path=chrome_path or None, channel=channel)
        context = browser.new_context(
            **p.devices["iPhone 13"],
            locale="fa-IR",
            timezone_id="Asia/Tehran",
            permissions=["geolocation"],
            geolocation={"latitude": INSIDE[0], "longitude": INSIDE[1], "accuracy": 12},
            service_workers="block",  # the cached app shell would hide fresh code
        )
        page = context.new_page()

        # 1) Login with the initial password
        page.goto(f"{BASE}/login")
        page.get_by_label("نام کاربری").fill(USERNAME)
        page.get_by_label("رمز عبور").fill(INITIAL)
        page.screenshot(path=str(OUT / "01-login.png"))
        page.get_by_role("button", name="ورود").click()

        # 2) Forced password change on first login
        expect(page.get_by_text("تغییر رمز عبور")).to_be_visible(timeout=15000)
        page.get_by_label("رمز عبور فعلی (اولیه)").fill(INITIAL)
        page.get_by_label("رمز عبور جدید", exact=True).fill(NEW_PASSWORD)
        page.get_by_label("تکرار رمز عبور جدید").fill(NEW_PASSWORD)
        page.screenshot(path=str(OUT / "02-change-password.png"))
        page.get_by_role("button", name="ذخیره و ادامه").click()

        # 3) Home: not checked in yet
        expect(page.get_by_role("button", name="ثبت ورود")).to_be_visible(timeout=15000)
        expect(page.get_by_text("هنوز ورود نکرده‌اید")).to_be_visible()
        page.screenshot(path=str(OUT / "03-home-before.png"))

        # 4) Check-in from outside: refused with a Persian message, still not checked in
        set_location(context, page, *OUTSIDE)
        page.get_by_role("button", name="ثبت ورود").click()
        expect(page.get_by_text("خارج از محدوده‌ی مجاز هستید")).to_be_visible(timeout=15000)
        expect(page.get_by_text("هنوز ورود نکرده‌اید")).to_be_visible()
        page.screenshot(path=str(OUT / "04-outside-refused.png"))

        # 5) Check-in from inside: success
        set_location(context, page, *INSIDE)
        page.get_by_role("button", name="ثبت ورود").click()
        expect(page.get_by_text("ورود شما ثبت شد")).to_be_visible(timeout=15000)
        expect(page.get_by_role("button", name="ثبت خروج با تایید موقعیت مکانی")).to_be_visible()
        page.screenshot(path=str(OUT / "05-checked-in.png"))

        # 6) Check-out needs the daily work description, and is refused outside the branch.
        set_location(context, page, *OUTSIDE)
        page.get_by_role("button", name="ثبت خروج با تایید موقعیت مکانی").click()
        dialog = page.get_by_role("dialog", name="ثبت خروج")
        expect(dialog).to_be_visible()
        confirm = dialog.get_by_role("button", name="ثبت خروج", exact=True)
        expect(confirm).to_be_disabled()  # empty description is not accepted
        dialog.locator("textarea").fill(DESCRIPTION)
        confirm.click()
        expect(page.get_by_text("برای ثبت خروج باید در")).to_be_visible(timeout=15000)
        dialog.get_by_role("button", name="انصراف").click()

        # 7) Check-out from inside: success, then the day is closed
        set_location(context, page, *INSIDE)
        page.get_by_role("button", name="ثبت خروج با تایید موقعیت مکانی").click()
        expect(dialog).to_be_visible()
        dialog.locator("textarea").fill(DESCRIPTION)
        dialog.get_by_role("button", name="ثبت خروج", exact=True).click()
        expect(page.get_by_text("خروج شما ثبت شد")).to_be_visible(timeout=15000)
        expect(page.get_by_text("امروز تمام شد")).to_be_visible()
        expect(page.get_by_text(DESCRIPTION)).to_be_visible()
        page.screenshot(path=str(OUT / "06-checked-out.png"))

        # 8) Weekly view shows today's record with its description, then the 30-day history
        page.get_by_role("link", name="هفته کاری").click()
        expect(page.get_by_role("heading", name="هفته کاری")).to_be_visible()
        expect(page.get_by_text("ساعت کاری رسمی")).to_be_visible()
        expect(page.get_by_text("حاضر", exact=True).first).to_be_visible()
        expect(page.get_by_text(DESCRIPTION)).to_be_visible()
        page.screenshot(path=str(OUT / "07-week.png"))

        page.get_by_role("link", name="مشاهده سوابق ۳۰ روزه").click()
        expect(page.get_by_role("heading", name="سوابق حضور")).to_be_visible()
        expect(page.get_by_text("در حال بارگذاری…")).to_have_count(0)
        expect(page.get_by_text("سابقه‌ای ثبت نشده است.")).to_have_count(0)
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "08-history.png"), full_page=True)

        browser.close()
        print("E2E OK")


if __name__ == "__main__":
    main()
