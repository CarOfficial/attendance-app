"""Hourly leave: employee files it, manager approves it."""
from datetime import date, timedelta

from conftest import auth_header, make_employee, ready_employee_token


def _tomorrow() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


def _employee_id(client, admin_token, username):
    employees = client.get("/api/v1/admin/employees", headers=auth_header(admin_token)).json()
    return next(e for e in employees if e["username"] == username)["id"]


def test_employee_files_hourly_leave_and_admin_approves(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "hourly.one", [branch["id"]])
    headers = auth_header(token)

    r = client.post(
        "/api/v1/leaves/hourly",
        headers=headers,
        json={"date": _tomorrow(), "start_hour": 10, "end_hour": 12.5, "reason": "کار اداری"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["start_hour"] == 10
    assert body["end_hour"] == 12.5
    leave_id = body["id"]

    mine = client.get("/api/v1/leaves/hourly/mine", headers=headers)
    assert mine.status_code == 200, mine.text
    assert [x["id"] for x in mine.json()] == [leave_id]

    # Admin sees it and approves it.
    pending = client.get(
        "/api/v1/admin/hourly-leaves?status=pending", headers=auth_header(admin_token)
    ).json()
    assert leave_id in [x["id"] for x in pending]

    r = client.patch(
        f"/api/v1/admin/hourly-leaves/{leave_id}",
        headers=auth_header(admin_token),
        json={"decision": "approve"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # Deciding twice is refused.
    r = client.patch(
        f"/api/v1/admin/hourly-leaves/{leave_id}",
        headers=auth_header(admin_token),
        json={"decision": "reject"},
    )
    assert r.status_code == 409, r.text


def test_overlapping_hourly_leave_is_rejected(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "hourly.two", [branch["id"]])
    headers = auth_header(token)
    day = _tomorrow()

    first = client.post(
        "/api/v1/leaves/hourly",
        headers=headers,
        json={"date": day, "start_hour": 9, "end_hour": 11, "reason": "قرارداد"},
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/leaves/hourly",
        headers=headers,
        json={"date": day, "start_hour": 10, "end_hour": 11, "reason": "کار شخصی"},
    )
    assert second.status_code == 409, second.text

    # A non-overlapping range on the same day is fine.
    third = client.post(
        "/api/v1/leaves/hourly",
        headers=headers,
        json={"date": day, "start_hour": 13, "end_hour": 14, "reason": "کار شخصی"},
    )
    assert third.status_code == 201, third.text


def test_hourly_leave_validates_hours(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "hourly.three", [branch["id"]])
    headers = auth_header(token)

    r = client.post(
        "/api/v1/leaves/hourly",
        headers=headers,
        json={"date": _tomorrow(), "start_hour": 14, "end_hour": 14, "reason": "استراحت"},
    )
    assert r.status_code == 422, r.text

    r = client.post(
        "/api/v1/leaves/hourly",
        headers=headers,
        json={"date": _tomorrow(), "start_hour": 9, "end_hour": 25, "reason": "استراحت"},
    )
    assert r.status_code == 422, r.text


def test_admin_can_file_hourly_leave_for_employee(client, admin_token, branch):
    assert make_employee(client, admin_token, "hourly.four", [branch["id"]]).status_code == 201
    emp_id = _employee_id(client, admin_token, "hourly.four")

    r = client.post(
        "/api/v1/admin/hourly-leaves",
        headers=auth_header(admin_token),
        json={
            "user_id": emp_id,
            "date": _tomorrow(),
            "start_hour": 8,
            "end_hour": 9.5,
            "reason": "ثبت توسط مدیر",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["user_id"] == emp_id

    # user_id must be provided when an admin files it.
    r = client.post(
        "/api/v1/admin/hourly-leaves",
        headers=auth_header(admin_token),
        json={"date": _tomorrow(), "start_hour": 8, "end_hour": 9.5, "reason": "بدون کارمند"},
    )
    assert r.status_code == 422, r.text


def test_hourly_leave_endpoints_are_forbidden_for_non_admins(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "hourly.five", [branch["id"]])
    headers = auth_header(token)

    assert client.get("/api/v1/admin/hourly-leaves", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/v1/admin/hourly-leaves",
            headers=headers,
            json={
                "user_id": 1,
                "date": _tomorrow(),
                "start_hour": 8,
                "end_hour": 9,
                "reason": "تلاش غیرمجاز",
            },
        ).status_code
        == 403
    )
