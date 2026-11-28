"""Approved hourly leave affects the day/hours, overtime on off days, and absence reasons."""
from datetime import timedelta

from conftest import auth_header, make_employee, ready_employee_token
from helpers_late import _today


def _employee_id(client, admin_token, username):
    employees = client.get("/api/v1/admin/employees", headers=auth_header(admin_token)).json()
    return next(e for e in employees if e["username"] == username)["id"]


def _set_all_days_work(client, admin_token):
    r = client.patch(
        "/api/v1/admin/schedule",
        headers=auth_header(admin_token),
        json={
            "work_days": [0, 1, 2, 3, 4, 5, 6],
            "start_time": "08:00",
            "end_time": "17:00",
            "late_grace_minutes": 15,
        },
    )
    assert r.status_code == 200, r.text


def _manual(client, admin_token, emp_id, branch_id, day, check_in, check_out):
    r = client.post(
        "/api/v1/admin/attendance/manual",
        headers=auth_header(admin_token),
        json={
            "user_id": emp_id,
            "branch_id": branch_id,
            "work_date": day.isoformat(),
            "check_in": check_in,
            "check_out": check_out,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _approve_hourly(client, admin_token, token, day, start, end):
    r = client.post(
        "/api/v1/leaves/hourly",
        headers=auth_header(token),
        json={"date": day.isoformat(), "start_hour": start, "end_hour": end, "reason": "کار شخصی"},
    )
    assert r.status_code == 201, r.text
    leave_id = r.json()["id"]
    r = client.patch(
        f"/api/v1/admin/hourly-leaves/{leave_id}",
        headers=auth_header(admin_token),
        json={"decision": "approve"},
    )
    assert r.status_code == 200, r.text


def _summary_day(client, admin_token, emp_id, day):
    r = client.get(
        f"/api/v1/admin/summary?user_id={emp_id}&from_date={day.isoformat()}&to_date={day.isoformat()}",
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_approved_hourly_leave_reduces_worked_hours(client, admin_token, branch):
    _set_all_days_work(client, admin_token)
    token = ready_employee_token(client, admin_token, "impact.one", [branch["id"]])
    emp_id = _employee_id(client, admin_token, "impact.one")
    today = _today()

    _manual(client, admin_token, emp_id, branch["id"], today, "08:00", "17:00")
    _approve_hourly(client, admin_token, token, today, 10, 12)

    body = _summary_day(client, admin_token, emp_id, today)
    day = body["days"][0]
    assert day["status"] == "present"
    assert day["hours_worked"] == 7.0
    assert day["hourly_leave_hours"] == 2.0
    assert body["totals"]["total_hours"] == 7.0

    # The admin attendance table shows the same adjusted hours plus the leave note.
    rows = client.get("/api/v1/admin/attendance", headers=auth_header(admin_token)).json()
    row = next(r for r in rows if r["work_date"] == today.isoformat())
    assert row["hours_worked"] == 7.0
    assert row["hourly_leave_hours"] == 2.0

    # The week view (what the employee sees) reports the same reduced day.
    r = client.get(f"/api/v1/attendance/week?start={today.isoformat()}", headers=auth_header(token))
    week_day = next(d for d in r.json()["days"] if d["date"] == today.isoformat())
    assert week_day["hours_worked"] == 7.0
    assert week_day["hourly_leave_hours"] == 2.0


def test_hourly_leave_without_record_marks_day_as_leave(client, admin_token, branch):
    _set_all_days_work(client, admin_token)
    token = ready_employee_token(client, admin_token, "impact.two", [branch["id"]])
    emp_id = _employee_id(client, admin_token, "impact.two")
    today = _today()

    _approve_hourly(client, admin_token, token, today, 9, 11)

    body = _summary_day(client, admin_token, emp_id, today)
    day = body["days"][0]
    assert day["status"] == "leave"
    assert day["hours_worked"] is None
    assert day["hourly_leave_hours"] == 2.0
    assert body["totals"]["leave"] == 1
    assert body["totals"]["absent"] == 0


def test_attendance_rows_report_late_and_overtime_minutes(client, admin_token, branch):
    _set_all_days_work(client, admin_token)
    token = ready_employee_token(client, admin_token, "impact.three", [branch["id"]])
    emp_id = _employee_id(client, admin_token, "impact.three")
    today = _today()

    created = _manual(client, admin_token, emp_id, branch["id"], today, "08:40", "19:10")
    assert created["check_in_edited"] is True
    assert created["check_out_edited"] is True

    rows = client.get("/api/v1/admin/attendance", headers=auth_header(admin_token)).json()
    row = next(r for r in rows if r["id"] == created["id"])
    assert row["late_minutes"] == 25  # 08:40 vs. 08:15 (08:00 + 15 min grace)
    assert row["overtime_minutes"] == 130  # 19:10 vs. 17:00


def test_non_working_day_attendance_counts_as_overtime(client, admin_token, branch):
    today = _today()
    other_days = [d for d in range(7) if d != today.weekday()]
    r = client.patch(
        "/api/v1/admin/schedule",
        headers=auth_header(admin_token),
        json={
            "work_days": other_days,
            "start_time": "08:00",
            "end_time": "17:00",
            "late_grace_minutes": 15,
        },
    )
    assert r.status_code == 200, r.text

    token = ready_employee_token(client, admin_token, "impact.four", [branch["id"]])
    emp_id = _employee_id(client, admin_token, "impact.four")

    _manual(client, admin_token, emp_id, branch["id"], today, "09:00", "13:00")

    body = _summary_day(client, admin_token, emp_id, today)
    day = body["days"][0]
    assert day["is_work_day"] is False
    assert day["status"] == "present"
    assert day["hours_worked"] == 4.0
    assert day["overtime_minutes"] == 240
    assert day["late_minutes"] == 0
    assert body["totals"]["overtime_minutes"] == 240


def test_employee_can_file_and_update_absence_reason(client, admin_token, branch):
    _set_all_days_work(client, admin_token)
    token = ready_employee_token(client, admin_token, "impact.five", [branch["id"]])
    emp_id = _employee_id(client, admin_token, "impact.five")
    headers = auth_header(token)
    today = _today()

    r = client.post(
        "/api/v1/attendance/absence-reason",
        headers=headers,
        json={"date": today.isoformat(), "reason": "بیماری و استراحت در منزل"},
    )
    assert r.status_code == 201, r.text

    # The admin sees the reason on the absent day in the reports.
    body = _summary_day(client, admin_token, emp_id, today)
    day = body["days"][0]
    assert day["status"] == "absent"
    assert day["absence_reason"] == "بیماری و استراحت در منزل"

    # Filing again for the same day updates the text instead of failing.
    r = client.post(
        "/api/v1/attendance/absence-reason",
        headers=headers,
        json={"date": today.isoformat(), "reason": "مرخصی بدون حقوق"},
    )
    assert r.status_code == 201, r.text
    listed = client.get(
        f"/api/v1/attendance/absence-reasons?from_date={today.isoformat()}&to_date={today.isoformat()}",
        headers=headers,
    ).json()
    assert len(listed) == 1
    assert listed[0]["reason"] == "مرخصی بدون حقوق"


def test_absence_reason_is_refused_for_a_recorded_day(client, admin_token, branch):
    _set_all_days_work(client, admin_token)
    token = ready_employee_token(client, admin_token, "impact.six", [branch["id"]])
    emp_id = _employee_id(client, admin_token, "impact.six")
    today = _today()

    _manual(client, admin_token, emp_id, branch["id"], today, "08:00", "17:00")

    r = client.post(
        "/api/v1/attendance/absence-reason",
        headers=auth_header(token),
        json={"date": today.isoformat(), "reason": "نباید پذیرفته شود"},
    )
    assert r.status_code == 409, r.text

    tomorrow = (today + timedelta(days=1)).isoformat()
    r = client.post(
        "/api/v1/attendance/absence-reason",
        headers=auth_header(token),
        json={"date": tomorrow, "reason": "روز آینده"},
    )
    assert r.status_code == 422, r.text


def test_employee_summary_endpoint_is_own_data_only(client, admin_token, branch):
    _set_all_days_work(client, admin_token)
    token = ready_employee_token(client, admin_token, "impact.seven", [branch["id"]])
    today = _today()

    r = client.get(
        f"/api/v1/attendance/summary?from_date={today.isoformat()}&to_date={today.isoformat()}",
        headers=auth_header(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_full_name"] == "کارمند تست"
    assert len(body["days"]) == 1
    assert "overtime_minutes" in body["totals"]
    assert "late_minutes" in body["totals"]

    # user_id in the query string cannot switch the report to someone else.
    other = client.get(
        f"/api/v1/attendance/summary?from_date={today.isoformat()}&to_date={today.isoformat()}&user_id=1",
        headers=auth_header(token),
    )
    assert other.status_code == 200, other.text
    assert other.json()["user_id"] == body["user_id"]


def test_morning_hourly_leave_does_not_count_as_late(client, admin_token, branch):
    _set_all_days_work(client, admin_token)
    token = ready_employee_token(client, admin_token, "impact.late", [branch["id"]])
    emp_id = _employee_id(client, admin_token, "impact.late")
    today = _today()

    # Approved leave from the start of the shift (08:00) until 10:00.
    _approve_hourly(client, admin_token, token, today, 8, 10)
    _manual(client, admin_token, emp_id, branch["id"], today, "10:05", "17:00")

    day = _summary_day(client, admin_token, emp_id, today)["days"][0]
    assert day["late_minutes"] == 0
    assert day["is_late"] is False
    rows = client.get("/api/v1/admin/attendance", headers=auth_header(admin_token)).json()
    row = next(r for r in rows if r["work_date"] == today.isoformat())
    assert row["late_minutes"] == 0

    # The threshold moves to leave end + grace (10:15), so a later arrival is late.
    _manual(client, admin_token, emp_id, branch["id"], today, "10:30", "17:00")
    day = _summary_day(client, admin_token, emp_id, today)["days"][0]
    assert day["late_minutes"] == 15
    assert day["is_late"] is True


def test_only_the_admin_changed_side_is_highlighted(client, admin_token, branch):
    _set_all_days_work(client, admin_token)
    token = ready_employee_token(client, admin_token, "impact.highlight", [branch["id"]])
    headers = auth_header(token)
    today = _today()

    # The employee checks in normally: neither side is highlighted.
    r = client.post(
        "/api/v1/attendance/check-in",
        headers=headers,
        json={"latitude": branch["latitude"], "longitude": branch["longitude"], "accuracy_m": 10},
    )
    assert r.status_code == 201, r.text
    record = r.json()
    assert record["check_in_edited"] is False
    assert record["check_out_edited"] is False

    # The manager changes only the check-out; the check-in must stay un-highlighted.
    from datetime import datetime, timedelta, timezone

    iran = timezone(timedelta(hours=3, minutes=30))
    checkout = (datetime.now(iran) + timedelta(hours=2)).replace(second=0, microsecond=0)
    r = client.patch(
        f"/api/v1/admin/attendance/{record['id']}",
        headers=auth_header(admin_token),
        json={"check_out_at": checkout.isoformat()},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["check_out_edited"] is True
    assert body["check_in_edited"] is False

    # A manual record with only a check-in highlights only the check-in.
    assert make_employee(client, admin_token, "impact.highlight2", [branch["id"]]).status_code == 201
    emp_id = _employee_id(client, admin_token, "impact.highlight2")
    created = _manual(client, admin_token, emp_id, branch["id"], today, "09:00", None)
    assert created["check_in_edited"] is True
    assert created["check_out_edited"] is False
