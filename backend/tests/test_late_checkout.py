from datetime import timedelta

from conftest import BRANCH_LAT, BRANCH_LNG, auth_header, ready_employee_token
from helpers_late import (
    _co,
    _loc,
    _set_all_days_work_week,
    _submit,
    _today,
    _week_day,
    _yesterday,
    _yesterday_record,
)


def test_forgotten_checkout_approve_marks_day_present(client, admin_token, branch):
    _set_all_days_work_week(client, admin_token)
    token = ready_employee_token(client, admin_token, "late.ok", [branch["id"]])
    _yesterday_record(client, admin_token, token, branch)
    yesterday = _yesterday()

    r = _submit(client, token, yesterday)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["submission_deadline"] is not None
    assert body["decision_deadline"] > body["submission_deadline"]

    # duplicate request is refused
    r = _submit(client, token, yesterday)
    assert r.status_code == 409

    # manager sees it
    r = client.get("/api/v1/admin/late-checkouts?status=pending", headers=auth_header(admin_token))
    assert r.status_code == 200
    reqs = r.json()
    assert len(reqs) == 1
    req_id = reqs[0]["id"]
    assert reqs[0]["user_full_name"]

    # approve -> check-out recorded from the request, day becomes present
    r = client.patch(f"/api/v1/admin/late-checkouts/{req_id}", headers=auth_header(admin_token),
                     json={"decision": "approve", "note": "تایید شد"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    day = _week_day(client, token, yesterday)
    assert day["status"] == "present"
    assert day["approval_status"] == "approved"
    assert day["late_request_status"] == "approved"
    assert day["work_description"] == "کارهای دیروز شامل جلسه و کدنویسی"
    assert day["check_out_at"] is not None

    # now the employee can check in today
    r = client.post("/api/v1/attendance/check-in", headers=auth_header(token),
                    json=_loc(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 201, r.text


def test_forgotten_checkout_rejected_means_absent(client, admin_token, branch):
    _set_all_days_work_week(client, admin_token)
    token = ready_employee_token(client, admin_token, "late.no", [branch["id"]])
    _yesterday_record(client, admin_token, token, branch)
    yesterday = _yesterday()

    r = _submit(client, token, yesterday)
    assert r.status_code == 201, r.text
    req_id = r.json()["id"]

    r = client.patch(f"/api/v1/admin/late-checkouts/{req_id}", headers=auth_header(admin_token),
                     json={"decision": "reject", "note": "بدون مدرک"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"

    day = _week_day(client, token, yesterday)
    assert day["status"] == "rejected"  # counts as absent


def test_forgotten_checkout_outside_location_refused(client, admin_token, branch):
    _set_all_days_work_week(client, admin_token)
    token = ready_employee_token(client, admin_token, "late.far", [branch["id"]])
    _yesterday_record(client, admin_token, token, branch)
    r = _submit(client, token, _yesterday(), lat=BRANCH_LAT + 0.02, lng=BRANCH_LNG)
    assert r.status_code == 403


def test_forgotten_checkout_window_is_24h(client, admin_token, branch):
    _set_all_days_work_week(client, admin_token)
    token = ready_employee_token(client, admin_token, "late.old", [branch["id"]])
    _yesterday_record(client, admin_token, token, branch)

    from datetime import datetime, timedelta, timezone

    iran = timezone(timedelta(hours=3, minutes=30))
    three_days_ago = (datetime.now(iran) - timedelta(days=3)).date()
    r = client.patch(
        "/api/v1/admin/attendance/1",
        headers=auth_header(admin_token),
        json={"check_in_at": f"{three_days_ago.isoformat()}T08:30:00+03:30"},
    )
    assert r.status_code == 200, r.text

    r = _submit(client, token, three_days_ago)
    assert r.status_code == 422
    assert "24-hour window" in r.json()["detail"]


def test_forgotten_checkout_rejects_same_day(client, admin_token, branch):
    _set_all_days_work_week(client, admin_token)
    token = ready_employee_token(client, admin_token, "late.same", [branch["id"]])
    r = _submit(client, token, _today())
    assert r.status_code == 422


def test_check_in_blocked_while_previous_day_open(client, admin_token, branch):
    _set_all_days_work_week(client, admin_token)
    token = ready_employee_token(client, admin_token, "late.block", [branch["id"]])
    _yesterday_record(client, admin_token, token, branch)

    r = client.post("/api/v1/attendance/check-in", headers=auth_header(token),
                    json=_loc(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 409
    assert "forgotten check-out" in r.json()["detail"]


def test_missing_checkout_without_request_counts_absent(client, admin_token, branch):
    _set_all_days_work_week(client, admin_token)
    token = ready_employee_token(client, admin_token, "late.none", [branch["id"]])
    _yesterday_record(client, admin_token, token, branch)
    day = _week_day(client, token, _yesterday())
    assert day["status"] == "incomplete"


def test_admin_can_decide_on_normal_day_record(client, admin_token, branch):
    _set_all_days_work_week(client, admin_token)
    token = ready_employee_token(client, admin_token, "decide.me", [branch["id"]])
    h = auth_header(token)
    r = client.post("/api/v1/attendance/check-in", headers=h, json=_loc(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 201
    r = client.post("/api/v1/attendance/check-out", headers=h, json=_co(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 200
    rec_id = r.json()["id"]

    # rejecting a checked-out day is allowed
    r = client.patch(f"/api/v1/admin/attendance/{rec_id}/decision",
                     headers=auth_header(admin_token),
                     json={"decision": "reject", "note": "بدون تایید"})
    assert r.status_code == 200, r.text
    assert r.json()["approval_status"] == "rejected"

    day = _week_day(client, token, _today())
    assert day["status"] == "rejected"

    # approving flips it back
    r = client.patch(f"/api/v1/admin/attendance/{rec_id}/decision",
                     headers=auth_header(admin_token),
                     json={"decision": "approve"})
    assert r.status_code == 200
    day = _week_day(client, token, _today())
    assert day["status"] == "present"
