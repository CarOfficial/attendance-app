"""Captures screenshots of the admin panel with headless Chrome.

Run after the API (port 8000) and Vite dev server (port 5173) are up.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
OUT = Path(__file__).resolve().parent
ADMIN_USER = "admin"
ADMIN_PASSWORD = "Admin-Demo-456"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1366, "height": 860}, locale="fa-IR")

        page.goto(f"{BASE}/login")
        page.get_by_label("نام کاربری").fill(ADMIN_USER)
        page.get_by_label("رمز عبور").fill(ADMIN_PASSWORD)
        page.screenshot(path=str(OUT / "01-login.png"))
        page.get_by_role("button", name="ورود").click()

        page.wait_for_url(f"{BASE}/", timeout=15000)
        page.wait_for_selector("text=داشبورد")
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "02-dashboard.png"), full_page=True)

        page.goto(f"{BASE}/attendance")
        page.wait_for_selector("text=حضور و غیاب")
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "03-attendance.png"), full_page=True)

        page.goto(f"{BASE}/employees")
        page.wait_for_selector("text=کارمندان")
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "04-employees.png"), full_page=True)

        page.get_by_role("button", name="+ کارمند جدید").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "04b-employee-create.png"), full_page=True)
        page.get_by_role("button", name="بستن فرم").click()

        page.goto(f"{BASE}/attendance")
        page.wait_for_selector("text=حضور و غیاب")
        page.wait_for_timeout(800)
        page.get_by_role("button", name="ویرایش").first.click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "03b-attendance-edit.png"))
        page.get_by_role("button", name="انصراف").click()

        page.goto(f"{BASE}/branches")
        page.get_by_role("button", name="+ دفتر جدید").click()
        page.wait_for_timeout(1500)
        # Click on the map a little north-west of the default center; the form should update.
        box = page.locator(".leaflet-container").bounding_box()
        page.mouse.click(box["x"] + box["width"] * 0.4, box["y"] + box["height"] * 0.4)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "05-branch-map.png"), full_page=True)

        browser.close()
        print("screenshots saved to", OUT)


if __name__ == "__main__":
    main()
