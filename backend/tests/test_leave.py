from datetime import timedelta

from conftest import BRANCH_LAT, BRANCH_LNG, auth_header, ready_employee_token
from helpers_late import _loc, _today


def _create_leave(client, token, start, end, reason="مرخصی استعلاجی"):
    return client.post(
        "/api/v1/leaves",
        headers=auth_header(token),
        json={"start_date": start.isoformat(), "end_date": end.isoformat(), "reason": reason},
    )


def test_leave_request_flow(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "leave.me", [branch["id"]])
    today = _today()
    start = today + timedelta(days=2)
    end = start + timedelta(days=1)

    r = _create_leave(client, token, start, end)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending"
    leave_id = body["id"]

    # duplicate overlapping request is refused
    r = _create_leave(client, token, start, end)
    assert r.status_code == 409

    # manager sees it and approves
    r = client.get("/api/v1/admin/leaves?status=pending", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.patch(f"/api/v1/admin/leaves/{leave_id}", headers=auth_header(admin_token),
                     json={"decision": "approve", "note": "موافقم"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # employee sees it in their list
    r = client.get("/api/v1/leaves/mine", headers=auth_header(token))
    assert r.status_code == 200
    assert r.json()[0]["status"] == "approved"

    # the day shows as leave in the weekly view
    r = client.get(f"/api/v1/attendance/week?start={start.isoformat()}", headers=auth_header(token))
    days = {d["date"]: d for d in r.json()["days"]}
    assert days[start.isoformat()]["status"] == "leave"
    assert days[(start + timedelta(days=1)).isoformat()]["status"] == "leave"


def test_leave_rejected_means_not_leave(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "leave.no", [branch["id"]])
    start = _today() + timedelta(days=3)
    r = _create_leave(client, token, start, start)
    assert r.status_code == 201
    leave_id = r.json()["id"]

    r = client.patch(f"/api/v1/admin/leaves/{leave_id}", headers=auth_header(admin_token),
                     json={"decision": "reject", "note": "کار فوری داریم"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    r = client.get(f"/api/v1/attendance/week?start={start.isoformat()}", headers=auth_header(token))
    days = {d["date"]: d for d in r.json()["days"]}
    # rejected leave: an unexcused past day would be absent; a future day stays future
    assert days[start.isoformat()]["status"] != "leave"


def test_check_in_blocked_on_approved_leave_today(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "leave.today", [branch["id"]])
    today = _today()
    r = _create_leave(client, token, today, today, "مرخصی امروز")
    assert r.status_code == 201
    client.patch(f"/api/v1/admin/leaves/{r.json()['id']}", headers=auth_header(admin_token),
                 json={"decision": "approve"})

    r = client.post("/api/v1/attendance/check-in", headers=auth_header(token),
                    json=_loc(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 409
    assert "leave" in r.json()["detail"]


def test_leave_validation(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "leave.bad", [branch["id"]])
    today = _today()

    # end before start
    r = _create_leave(client, token, today + timedelta(days=5), today + timedelta(days=2))
    assert r.status_code == 422

    # too far in the past
    r = _create_leave(client, token, today - timedelta(days=30), today - timedelta(days=29))
    assert r.status_code == 422

    # empty reason
    r = _create_leave(client, token, today + timedelta(days=9), today + timedelta(days=9), reason="x")
    assert r.status_code == 422
