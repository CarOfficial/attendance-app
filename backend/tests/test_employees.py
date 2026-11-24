from conftest import auth_header, login, make_employee, ready_employee_token


def test_create_employee_and_login_forces_password_change(client, admin_token, branch):
    r = make_employee(client, admin_token, "ali.rezaei", [branch["id"]])
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "ali.rezaei"
    assert body["branch_ids"] == [branch["id"]]
    assert body["must_change_password"] is True

    r = login(client, "ali.rezaei", "Initial-Pass-1")
    assert r.status_code == 200
    assert r.json()["must_change_password"] is True


def test_username_is_unique_case_insensitively(client, admin_token):
    assert make_employee(client, admin_token, "Sara", []).status_code == 201
    r = make_employee(client, admin_token, "sara", [])
    # "Sara" is normalized to "sara", so the second attempt must conflict.
    assert r.status_code == 409
    assert r.json()["detail"] == "Username already exists"


def test_username_format_is_validated(client, admin_token):
    r = make_employee(client, admin_token, "ab", [])
    assert r.status_code == 422
    r = make_employee(client, admin_token, "علی", [])
    assert r.status_code == 422


def test_invalid_branch_ids_rejected(client, admin_token):
    r = make_employee(client, admin_token, "bad.branch", [9999])
    assert r.status_code == 422


def test_admin_reset_password_revokes_sessions(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "reza.k", [branch["id"]])
    employee_id = client.get("/api/v1/auth/me", headers=auth_header(token)).json()["id"]

    r = client.post(
        f"/api/v1/admin/employees/{employee_id}/reset-password",
        headers=auth_header(admin_token),
        json={"new_password": "Reset-Pass-555"},
    )
    assert r.status_code == 204

    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 401
    r = login(client, "reza.k", "Reset-Pass-555")
    assert r.json()["must_change_password"] is True


def test_deactivated_employee_cannot_login(client, admin_token, branch):
    ready_employee_token(client, admin_token, "old.staff", [branch["id"]])
    employees = client.get("/api/v1/admin/employees", headers=auth_header(admin_token)).json()
    emp = next(e for e in employees if e["username"] == "old.staff")

    r = client.patch(
        f"/api/v1/admin/employees/{emp['id']}",
        headers=auth_header(admin_token),
        json={"is_active": False},
    )
    assert r.status_code == 200
    assert login(client, "old.staff", "Employee-Pass-789").status_code == 401


def test_employee_cannot_access_admin_routes(client, admin_token, branch):
    token = ready_employee_token(client, admin_token, "plain.user", [branch["id"]])
    r = client.get("/api/v1/admin/employees", headers=auth_header(token))
    assert r.status_code == 403
