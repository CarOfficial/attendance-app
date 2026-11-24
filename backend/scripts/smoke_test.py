"""End-to-end smoke test against a running server (http://127.0.0.1:8000)."""

import sys
from datetime import datetime, timedelta, timezone

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
IRAN = timezone(timedelta(hours=3, minutes=30))
LAT, LNG = 35.6996, 51.3380

ok = 0
fail = 0


def check(label, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  OK   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {extra}")


def main():
    c = httpx.Client(timeout=20)

    # 1) admin login (bootstrap -> must change password)
    r = c.post(f"{BASE}/auth/login", json={"username": "admin", "password": "Dev-Admin-Pass-1"})
    check("admin login", r.status_code == 200, r.text)
    tok = r.json()["access_token"]
    ah = {"Authorization": f"Bearer {tok}"}
    r = c.post(f"{BASE}/auth/change-password", headers=ah,
               json={"current_password": "Dev-Admin-Pass-1", "new_password": "Smoke-Admin-99"})
    check("admin change password", r.status_code == 200, r.text)
    ah = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 2) branch + schedule + dashboard
    r = c.post(f"{BASE}/admin/branches", headers=ah,
               json={"name": "دفتر تست", "latitude": LAT, "longitude": LNG, "radius_m": 150})
    check("create branch", r.status_code == 201, r.text)
    branch = r.json()

    r = c.get(f"{BASE}/admin/schedule", headers=ah)
    check("get schedule", r.status_code == 200 and r.json()["start_time"] == "08:00", r.text)

    r = c.patch(f"{BASE}/admin/schedule", headers=ah,
                json={"work_days": [0, 1, 2, 3, 4, 5, 6], "start_time": "08:00",
                      "end_time": "17:00", "late_grace_minutes": 15})
    check("update schedule", r.status_code == 200, r.text)

    # 3) employee
    r = c.post(f"{BASE}/admin/employees", headers=ah,
               json={"username": "smoke.emp", "full_name": "کارمند تست دود",
                     "password": "Initial-Pass-1", "branch_ids": [branch["id"]]})
    check("create employee", r.status_code == 201, r.text)
    emp_id = r.json()["id"]

    r = c.post(f"{BASE}/auth/login", json={"username": "smoke.emp", "password": "Initial-Pass-1"})
    check("employee login", r.status_code == 200, r.text)
    etok = r.json()["access_token"]
    eh = {"Authorization": f"Bearer {etok}"}
    r = c.post(f"{BASE}/auth/change-password", headers=eh,
               json={"current_password": "Initial-Pass-1", "new_password": "Smoke-Emp-11"})
    check("employee change password", r.status_code == 200, r.text)
    eh = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 4) check-in / check-out with description
    loc = {"latitude": LAT, "longitude": LNG, "accuracy_m": 8}
    r = c.post(f"{BASE}/attendance/check-in", headers=eh, json=loc)
    check("check-in", r.status_code == 201, r.text)
    rec = r.json()
    r = c.post(f"{BASE}/attendance/check-out", headers=eh,
               json={**loc, "work_description": "کارهای امروز: جلسه و پیگیری پروژه"})
    check("check-out with description", r.status_code == 200, r.text)
    check("hours_worked present", r.json()["hours_worked"] is not None, r.text)

    # check-out without description refused
    r = c.post(f"{BASE}/attendance/check-in", headers=eh, json=loc)
    check("second check-in refused", r.status_code == 409, r.text)

    # 5) week + summary
    r = c.get(f"{BASE}/attendance/week", headers=eh)
    check("employee week", r.status_code == 200 and len(r.json()["days"]) == 7, r.text)

    r = c.get(f"{BASE}/admin/summary?user_id={emp_id}", headers=ah)
    check("admin summary", r.status_code == 200 and "totals" in r.json(), r.text)

    # 6) leave flow
    start = (datetime.now(IRAN) + timedelta(days=5)).date()
    r = c.post(f"{BASE}/leaves", headers=eh,
               json={"start_date": start.isoformat(), "end_date": start.isoformat(),
                     "reason": "مرخصی شخصی"})
    check("create leave", r.status_code == 201, r.text)
    leave_id = r.json()["id"]
    r = c.patch(f"{BASE}/admin/leaves/{leave_id}", headers=ah, json={"decision": "approve"})
    check("approve leave", r.status_code == 200 and r.json()["status"] == "approved", r.text)
    r = c.get(f"{BASE}/attendance/week?start={start.isoformat()}", headers=eh)
    day = next(d for d in r.json()["days"] if d["date"] == start.isoformat())
    check("leave shows in week", day["status"] == "leave", str(day))

    # 7) forgotten check-out flow (fresh employee with an open check-in, moved to yesterday)
    r = c.post(f"{BASE}/admin/employees", headers=ah,
               json={"username": "smoke.late", "full_name": "کارمند فراموشکار",
                     "password": "Initial-Pass-1", "branch_ids": [branch["id"]]})
    check("create late employee", r.status_code == 201, r.text)
    r = c.post(f"{BASE}/auth/login", json={"username": "smoke.late", "password": "Initial-Pass-1"})
    ltok = r.json()["access_token"]
    lh = {"Authorization": f"Bearer {ltok}"}
    c.post(f"{BASE}/auth/change-password", headers=lh,
           json={"current_password": "Initial-Pass-1", "new_password": "Smoke-Late-22"})
    lh = {"Authorization": f"Bearer {c.post(f'{BASE}/auth/login', json={'username': 'smoke.late', 'password': 'Smoke-Late-22'}).json()['access_token']}"}
    r = c.post(f"{BASE}/attendance/check-in", headers=lh, json=loc)
    check("late employee check-in", r.status_code == 201, r.text)
    rec_id = r.json()["id"]
    yesterday = (datetime.now(IRAN) - timedelta(days=1)).date()
    r = c.patch(f"{BASE}/admin/attendance/{rec_id}", headers=ah,
                json={"check_in_at": f"{yesterday.isoformat()}T08:30:00+03:30"})
    check("move record to yesterday", r.status_code == 200, r.text)

    r = c.post(f"{BASE}/attendance/late-checkout", headers=lh,
               json={"work_date": yesterday.isoformat(), "check_out_time": "17:05",
                     "latitude": LAT, "longitude": LNG, "accuracy_m": 8,
                     "description": "کارهای دیروز شامل جلسه تیم"})
    check("submit late checkout", r.status_code == 201, r.text)
    late_id = r.json()["id"]
    r = c.get(f"{BASE}/admin/late-checkouts?status=pending", headers=ah)
    check("admin sees pending late", r.status_code == 200 and len(r.json()) >= 1, r.text)
    r = c.patch(f"{BASE}/admin/late-checkouts/{late_id}", headers=ah, json={"decision": "approve"})
    check("approve late checkout", r.status_code == 200 and r.json()["status"] == "approved", r.text)
    r = c.get(f"{BASE}/attendance/week?start={yesterday.isoformat()}", headers=lh)
    day = next(d for d in r.json()["days"] if d["date"] == yesterday.isoformat())
    check("yesterday present after approval", day["status"] == "present", str(day))

    # 8) dashboard
    r = c.get(f"{BASE}/admin/dashboard", headers=ah)
    body = r.json()
    check("dashboard counters", r.status_code == 200 and "pending_leaves" in body
          and "pending_late_checkouts" in body, r.text)

    # 9) excel exports
    today = datetime.now(IRAN).date()
    fr = (today - timedelta(days=7)).isoformat()
    r = c.get(f"{BASE}/admin/export/excel?user_id={emp_id}&from_date={fr}&to_date={today.isoformat()}",
              headers=ah)
    check("excel single", r.status_code == 200 and r.content[:2] == b"PK", r.text[:200])
    r = c.get(f"{BASE}/admin/export/excel?from_date={fr}&to_date={today.isoformat()}", headers=ah)
    check("excel all", r.status_code == 200 and r.content[:2] == b"PK", r.text[:200])

    # 10) record decision
    r = c.get(f"{BASE}/admin/attendance?user_id={emp_id}", headers=ah)
    checked_out = [x for x in r.json() if x["check_out_at"]]
    if checked_out:
        rid = checked_out[0]["id"]
        r = c.patch(f"{BASE}/admin/attendance/{rid}/decision", headers=ah,
                    json={"decision": "reject", "note": "تست"})
        check("reject record", r.status_code == 200 and r.json()["approval_status"] == "rejected", r.text)
        r = c.patch(f"{BASE}/admin/attendance/{rid}/decision", headers=ah, json={"decision": "approve"})
        check("re-approve record", r.status_code == 200, r.text)

    print(f"\n{ok} OK, {fail} FAIL")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
