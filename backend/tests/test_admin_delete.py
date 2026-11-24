from datetime import datetime, timedelta, timezone

from conftest import BRANCH_LAT, BRANCH_LNG, auth_header, make_employee, ready_employee_token


def _today() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)).date().isoformat()


def _check_in(client, token):
    r = client.post(
        "/api/v1/attendance/check-in",
        headers=auth_header(token),
        json={"latitude": BRANCH_LAT, "longitude": BRANCH_LNG, "accuracy_m": 10},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_delete_branch_without_history(client, admin_token, branch):
    r = client.delete(f"/api/v1/admin/branches/{branch['id']}", headers=auth_header(admin_token))
    assert r.status_code == 204
    assert client.get("/api/v1/admin/branches", headers=auth_header(admin_token)).json() == []


def test_delete_branch_with_history_needs_force(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "ali.branch", [branch["id"]])
    _check_in(client, token)

    r = client.delete(f"/api/v1/admin/branches/{branch['id']}", headers=auth_header(admin_token))
    assert r.status_code == 409

    r = client.delete(
        f"/api/v1/admin/branches/{branch['id']}?force=true", headers=auth_header(admin_token)
    )
    assert r.status_code == 204
    assert client.get("/api/v1/admin/branches", headers=auth_header(admin_token)).json() == []


def test_delete_employee_with_history_needs_force(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "sara.del", [branch["id"]])
    _check_in(client, token)
    employees = client.get("/api/v1/admin/employees", headers=auth_header(admin_token)).json()
    emp = next(e for e in employees if e["username"] == "sara.del")

    r = client.delete(f"/api/v1/admin/employees/{emp['id']}", headers=auth_header(admin_token))
    assert r.status_code == 409

    r = client.delete(
        f"/api/v1/admin/employees/{emp['id']}?force=true", headers=auth_header(admin_token)
    )
    assert r.status_code == 204
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 401
    assert client.get("/api/v1/admin/employees", headers=auth_header(admin_token)).json() == []


def test_delete_attendance_record(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "reza.del", [branch["id"]])
    _check_in(client, token)
    rows = client.get("/api/v1/admin/attendance", headers=auth_header(admin_token)).json()
    assert len(rows) == 1

    r = client.delete(f"/api/v1/admin/attendance/{rows[0]['id']}", headers=auth_header(admin_token))
    assert r.status_code == 204
    assert client.get("/api/v1/admin/attendance", headers=auth_header(admin_token)).json() == []


def test_employee_cannot_delete(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "plain.del", [branch["id"]])
    r = client.delete(f"/api/v1/admin/branches/{branch['id']}", headers=auth_header(token))
    assert r.status_code == 403
