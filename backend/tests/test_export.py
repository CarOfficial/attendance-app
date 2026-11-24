from datetime import timedelta

from conftest import auth_header, ready_employee_token
from helpers_late import _co, _loc, _today

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _employee_id(client, admin_token, username):
    employees = client.get("/api/v1/admin/employees", headers=auth_header(admin_token)).json()
    return next(e["id"] for e in employees if e["username"] == username)


def test_export_all_employees(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "xls.all", [branch["id"]])
    h = auth_header(token)
    client.post("/api/v1/attendance/check-in", headers=h,
                json=_loc(branch["latitude"], branch["longitude"]))
    client.post("/api/v1/attendance/check-out", headers=h,
                json=_co(branch["latitude"], branch["longitude"]))

    today = _today()
    r = client.get(
        f"/api/v1/admin/export/excel?from_date={(today - timedelta(days=7)).isoformat()}"
        f"&to_date={today.isoformat()}",
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(XLSX)
    assert r.content[:2] == b"PK"  # zip/xlsx magic
    assert "attachment" in r.headers["content-disposition"]


def test_export_single_employee(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "xls.one", [branch["id"]])
    h = auth_header(token)
    client.post("/api/v1/attendance/check-in", headers=h,
                json=_loc(branch["latitude"], branch["longitude"]))
    client.post("/api/v1/attendance/check-out", headers=h,
                json=_co(branch["latitude"], branch["longitude"]))

    emp_id = _employee_id(client, admin_token, "xls.one")
    today = _today()
    r = client.get(
        f"/api/v1/admin/export/excel?user_id={emp_id}"
        f"&from_date={(today - timedelta(days=7)).isoformat()}&to_date={today.isoformat()}",
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200, r.text
    assert r.content[:2] == b"PK"
    assert f"attendance-{emp_id}" in r.headers["content-disposition"]


def test_export_unknown_employee_404(client, admin_token):
    r = client.get("/api/v1/admin/export/excel?user_id=99999", headers=auth_header(admin_token))
    assert r.status_code == 404


def test_export_range_too_large(client, admin_token):
    r = client.get(
        "/api/v1/admin/export/excel?from_date=2020-01-01&to_date=2026-01-01",
        headers=auth_header(admin_token),
    )
    assert r.status_code == 422


def test_export_requires_admin(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "xls.emp", [branch["id"]])
    r = client.get("/api/v1/admin/export/excel", headers=auth_header(token))
    assert r.status_code == 403


def test_export_requires_auth(client):
    r = client.get("/api/v1/admin/export/excel")
    assert r.status_code in (401, 403)
