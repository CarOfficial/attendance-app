from conftest import BRANCH_LAT, BRANCH_LNG, auth_header, login, make_employee, ready_employee_token

# Roughly 0.0005 deg lat ~= 55 m; 0.02 deg lat ~= 2.2 km
NEAR_LAT = BRANCH_LAT + 0.0005
NEAR_LNG = BRANCH_LNG
FAR_LAT = BRANCH_LAT + 0.02
FAR_LNG = BRANCH_LNG


def _loc(lat, lng, acc=10):
    return {"latitude": lat, "longitude": lng, "accuracy_m": acc}


def _co(lat, lng, desc="کارهای روز شامل بررسی ایمیل‌ها و پیگیری پروژه", acc=10):
    return {"latitude": lat, "longitude": lng, "accuracy_m": acc, "work_description": desc}


def test_check_in_inside_radius_succeeds(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "in.radius", [branch["id"]])
    r = client.post("/api/v1/attendance/check-in", headers=auth_header(token),
                    json=_loc(NEAR_LAT, NEAR_LNG))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["branch_name"] == branch["name"]
    assert body["check_out_at"] is None


def test_check_in_outside_radius_rejected(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "out.radius", [branch["id"]])
    r = client.post("/api/v1/attendance/check-in", headers=auth_header(token),
                    json=_loc(FAR_LAT, FAR_LNG))
    assert r.status_code == 403
    assert "outside the allowed area" in r.json()["detail"]


def test_check_in_rejected_when_gps_accuracy_is_poor(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "poor.gps", [branch["id"]])
    r = client.post("/api/v1/attendance/check-in", headers=auth_header(token),
                    json=_loc(NEAR_LAT, NEAR_LNG, acc=500))
    assert r.status_code == 422


def test_no_branch_assigned_rejected(client, admin_token):
    token = ready_employee_token(client, admin_token, "no.branch", [])
    r = client.post("/api/v1/attendance/check-in", headers=auth_header(token),
                    json=_loc(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 403


def test_full_day_flow_and_duplicate_protection(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "full.day", [branch["id"]])
    h = auth_header(token)

    assert client.get("/api/v1/attendance/today", headers=h).json()["status"] == "not_checked_in"

    assert client.post("/api/v1/attendance/check-in", headers=h,
                       json=_loc(BRANCH_LAT, BRANCH_LNG)).status_code == 201
    assert client.get("/api/v1/attendance/today", headers=h).json()["status"] == "checked_in"

    # second check-in same day
    r = client.post("/api/v1/attendance/check-in", headers=h, json=_loc(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 409

    # check-out from far away is refused
    r = client.post("/api/v1/attendance/check-out", headers=h, json=_co(FAR_LAT, FAR_LNG))
    assert r.status_code == 403

    r = client.post("/api/v1/attendance/check-out", headers=h, json=_co(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 200
    body = r.json()
    assert body["check_out_at"] is not None
    assert body["work_description"].startswith("کارهای روز")
    assert body["check_out_source"] == "employee"
    assert body["hours_worked"] is not None
    assert client.get("/api/v1/attendance/today", headers=h).json()["status"] == "checked_out"

    # cannot check in again after checking out the same day
    r = client.post("/api/v1/attendance/check-in", headers=h, json=_loc(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 409

    # no open record left to check out
    r = client.post("/api/v1/attendance/check-out", headers=h, json=_co(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 409


def test_check_out_requires_work_description(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "no.desc", [branch["id"]])
    h = auth_header(token)
    client.post("/api/v1/attendance/check-in", headers=h, json=_loc(BRANCH_LAT, BRANCH_LNG))
    r = client.post("/api/v1/attendance/check-out", headers=h,
                    json={"latitude": BRANCH_LAT, "longitude": BRANCH_LNG, "accuracy_m": 10,
                          "work_description": "  "})
    assert r.status_code == 422


def test_check_out_without_check_in_rejected(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "no.checkin", [branch["id"]])
    r = client.post("/api/v1/attendance/check-out", headers=auth_header(token),
                    json=_co(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 409


def test_employee_must_change_password_before_attendance(client, admin_token, branch):
    make_employee(client, admin_token, "fresh.staff", [branch["id"]])
    token = login(client, "fresh.staff", "Initial-Pass-1").json()["access_token"]
    r = client.post("/api/v1/attendance/check-in", headers=auth_header(token),
                    json=_loc(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 403
    assert r.headers.get("X-Password-Change-Required") == "1"


def test_history_lists_own_records(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "history.user", [branch["id"]])
    h = auth_header(token)
    client.post("/api/v1/attendance/check-in", headers=h, json=_loc(BRANCH_LAT, BRANCH_LNG))
    r = client.get("/api/v1/attendance/history", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_admin_can_correct_a_record(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "forgot.checkout", [branch["id"]])
    h = auth_header(token)
    client.post("/api/v1/attendance/check-in", headers=h, json=_loc(BRANCH_LAT, BRANCH_LNG))

    records = client.get("/api/v1/admin/attendance", headers=auth_header(admin_token)).json()
    rec_id = records[0]["id"]
    r = client.patch(
        f"/api/v1/admin/attendance/{rec_id}",
        headers=auth_header(admin_token),
        json={"check_out_at": "2099-01-01T12:00:00+03:30"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["edited_by_admin"] is True
    assert r.json()["check_out_at"] is not None


def test_admin_dashboard_counts(client, admin_token, branch):
    ready_employee_token(client, admin_token, "dash.one", [branch["id"]])
    r = client.get("/api/v1/admin/dashboard", headers=auth_header(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["active_employees"] == 1
    assert body["present_today"] == 0
    assert body["absent_today"] == 1
