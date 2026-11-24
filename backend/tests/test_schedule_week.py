from conftest import auth_header, ready_employee_token
from helpers_late import _today


def test_default_schedule(client, admin_token):
    r = client.get("/api/v1/admin/schedule", headers=auth_header(admin_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["work_days"] == [0, 1, 2, 5, 6]  # Saturday..Wednesday
    assert body["start_time"] == "08:00"
    assert body["end_time"] == "17:00"
    assert body["late_grace_minutes"] == 15


def test_admin_can_update_schedule(client, admin_token):
    r = client.patch(
        "/api/v1/admin/schedule",
        headers=auth_header(admin_token),
        json={"work_days": [0, 1, 2, 3, 4, 5, 6], "start_time": "09:00",
              "end_time": "18:30", "late_grace_minutes": 10},
    )
    assert r.status_code == 200, r.text
    assert r.json()["start_time"] == "09:00"

    r = client.get("/api/v1/admin/schedule", headers=auth_header(admin_token))
    assert r.json()["work_days"] == [0, 1, 2, 3, 4, 5, 6]
    assert r.json()["end_time"] == "18:30"


def test_schedule_validation(client, admin_token):
    h = auth_header(admin_token)
    # end before start
    r = client.patch("/api/v1/admin/schedule", headers=h,
                     json={"work_days": [0, 1, 2], "start_time": "17:00",
                           "end_time": "08:00", "late_grace_minutes": 15})
    assert r.status_code == 422
    # empty days
    r = client.patch("/api/v1/admin/schedule", headers=h,
                     json={"work_days": [], "start_time": "08:00",
                           "end_time": "17:00", "late_grace_minutes": 15})
    assert r.status_code == 422
    # bad weekday number
    r = client.patch("/api/v1/admin/schedule", headers=h,
                     json={"work_days": [9], "start_time": "08:00",
                           "end_time": "17:00", "late_grace_minutes": 15})
    assert r.status_code == 422


def test_schedule_is_forbidden_for_employees(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "sched.emp", [branch["id"]])
    r = client.get("/api/v1/admin/schedule", headers=auth_header(token))
    assert r.status_code == 403
    # but employees can read it through their own week endpoint
    r = client.get("/api/v1/attendance/week", headers=auth_header(token))
    assert r.status_code == 200
    assert r.json()["schedule"]["start_time"] == "08:00"


def test_week_starts_on_saturday(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "week.start", [branch["id"]])
    r = client.get("/api/v1/attendance/week", headers=auth_header(token))
    assert r.status_code == 200, r.text
    body = r.json()
    from datetime import date, timedelta

    start = date.fromisoformat(body["start"])
    end = date.fromisoformat(body["end"])
    assert start.weekday() == 5  # Saturday
    assert end == start + timedelta(days=6)
    assert len(body["days"]) == 7


def test_week_statuses_absent_future(client, admin_token, branch):
    from datetime import timedelta

    r = client.patch("/api/v1/admin/schedule", headers=auth_header(admin_token),
                     json={"work_days": [0, 1, 2, 3, 4, 5, 6], "start_time": "08:00",
                           "end_time": "17:00", "late_grace_minutes": 15})
    assert r.status_code == 200

    token = ready_employee_token(client, admin_token, "week.abs", [branch["id"]])
    today = _today()
    r = client.get(f"/api/v1/attendance/week?start={(today - timedelta(days=3)).isoformat()}",
                   headers=auth_header(token))
    days = {d["date"]: d for d in r.json()["days"]}

    assert days[(today - timedelta(days=3)).isoformat()]["status"] == "absent"
    assert days[today.isoformat()] ["status"] == "absent"
    assert days[(today + timedelta(days=2)).isoformat()]["status"] == "future"


def test_non_working_day_is_not_absent(client, admin_token, branch):
    from datetime import timedelta

    # default schedule: Saturday..Wednesday -> Thursday/Friday are off
    token = ready_employee_token(client, admin_token, "week.off", [branch["id"]])
    today = _today()
    # find the next Thursday (weekday 3) after today
    d = today + timedelta(days=1)
    while d.weekday() != 3:
        d += timedelta(days=1)
    r = client.get(f"/api/v1/attendance/week?start={d.isoformat()}", headers=auth_header(token))
    days = {x["date"]: x for x in r.json()["days"]}
    assert days[d.isoformat()]["status"] == "non_working"
    assert days[d.isoformat()]["is_work_day"] is False


def test_admin_summary_totals(client, admin_token, branch):
    from conftest import auth_header as _ah
    from helpers_late import _co, _loc

    token = ready_employee_token(client, admin_token, "sum.emp", [branch["id"]])
    h = auth_header(token)
    client.post("/api/v1/attendance/check-in", headers=h, json=_loc(
        branch["latitude"], branch["longitude"]))
    client.post("/api/v1/attendance/check-out", headers=h, json=_co(
        branch["latitude"], branch["longitude"]))

    employees = client.get("/api/v1/admin/employees", headers=_ah(admin_token)).json()
    emp = next(e for e in employees if e["username"] == "sum.emp")

    r = client.get(f"/api/v1/admin/summary?user_id={emp['id']}", headers=_ah(admin_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_full_name"] == "کارمند تست"
    for key in ("present", "absent", "leave", "pending_checkout", "total_hours",
                "late_count", "early_leave_count"):
        assert key in body["totals"]
    assert body["totals"]["present"] >= 1
    assert len(body["days"]) >= 1


def test_dashboard_has_new_counters(client, admin_token, branch):
    r = client.get("/api/v1/admin/dashboard", headers=auth_header(admin_token))
    assert r.status_code == 200
    body = r.json()
    for key in ("pending_leaves", "pending_late_checkouts", "leave_today", "rejected_today"):
        assert key in body
