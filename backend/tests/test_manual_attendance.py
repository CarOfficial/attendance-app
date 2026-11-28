"""Admin manual check-in/check-out (dashboard «ثبت دستی ورود/خروج»)."""
from datetime import date

from conftest import auth_header, make_employee


def _employee_id(client, admin_token, username):
    employees = client.get("/api/v1/admin/employees", headers=auth_header(admin_token)).json()
    return next(e for e in employees if e["username"] == username)["id"]


def test_admin_creates_record_manually(client, admin_token, branch):
    assert make_employee(client, admin_token, "manual.one", [branch["id"]]).status_code == 201
    emp_id = _employee_id(client, admin_token, "manual.one")

    r = client.post(
        "/api/v1/admin/attendance/manual",
        headers=auth_header(admin_token),
        json={
            "user_id": emp_id,
            "branch_id": branch["id"],
            "work_date": date.today().isoformat(),
            "check_in": "08:00",
            "check_out": "16:30",
            "work_description": "ثبت دستی توسط مدیر",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_id"] == emp_id
    assert body["check_out_at"] is not None
    assert body["edited_by_admin"] is True
    assert body["check_out_source"] == "admin"
    assert abs(body["hours_worked"] - 8.5) < 0.01

    rows = client.get("/api/v1/admin/attendance", headers=auth_header(admin_token)).json()
    assert [row["id"] for row in rows] == [body["id"]]


def test_admin_updates_existing_record_instead_of_duplicating(client, admin_token, branch):
    assert make_employee(client, admin_token, "manual.two", [branch["id"]]).status_code == 201
    emp_id = _employee_id(client, admin_token, "manual.two")
    headers = auth_header(admin_token)
    payload = {
        "user_id": emp_id,
        "branch_id": branch["id"],
        "work_date": date.today().isoformat(),
        "check_in": "09:00",
    }

    first = client.post("/api/v1/admin/attendance/manual", headers=headers, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["check_out_at"] is None

    payload["check_out"] = "17:00"
    second = client.post("/api/v1/admin/attendance/manual", headers=headers, json=payload)
    assert second.status_code == 200, second.text
    assert second.json()["id"] == first.json()["id"]

    rows = client.get("/api/v1/admin/attendance", headers=headers).json()
    assert len(rows) == 1


def test_manual_rejects_checkout_before_checkin(client, admin_token, branch):
    assert make_employee(client, admin_token, "manual.three", [branch["id"]]).status_code == 201
    emp_id = _employee_id(client, admin_token, "manual.three")

    r = client.post(
        "/api/v1/admin/attendance/manual",
        headers=auth_header(admin_token),
        json={
            "user_id": emp_id,
            "branch_id": branch["id"],
            "check_in": "17:00",
            "check_out": "09:00",
        },
    )
    assert r.status_code == 422, r.text


def test_manual_requires_hhmm_times(client, admin_token, branch):
    assert make_employee(client, admin_token, "manual.four", [branch["id"]]).status_code == 201
    emp_id = _employee_id(client, admin_token, "manual.four")

    r = client.post(
        "/api/v1/admin/attendance/manual",
        headers=auth_header(admin_token),
        json={"user_id": emp_id, "branch_id": branch["id"], "check_in": "8:00"},
    )
    assert r.status_code == 422, r.text


def test_manual_is_forbidden_for_employees(client, admin_token, branch):
    from conftest import ready_employee_token

    token = ready_employee_token(client, admin_token, "manual.emp", [branch["id"]])
    r = client.post(
        "/api/v1/admin/attendance/manual",
        headers=auth_header(token),
        json={"user_id": 1, "branch_id": branch["id"], "check_in": "08:00"},
    )
    assert r.status_code == 403
