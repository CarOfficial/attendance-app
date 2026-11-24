from conftest import ADMIN_NEW_PASSWORD, ADMIN_PASSWORD, ADMIN_USER, auth_header, login


def test_bootstrap_admin_must_change_password(client):
    r = login(client, ADMIN_USER, ADMIN_PASSWORD)
    assert r.status_code == 200
    assert r.json()["must_change_password"] is True


def test_must_change_password_blocks_admin_endpoints(client):
    token = login(client, ADMIN_USER, ADMIN_PASSWORD).json()["access_token"]
    r = client.get("/api/v1/admin/employees", headers=auth_header(token))
    assert r.status_code == 403
    assert r.headers.get("X-Password-Change-Required") == "1"


def test_change_password_returns_new_token_and_revokes_old(client, admin_token):
    old = login(client, ADMIN_USER, ADMIN_NEW_PASSWORD).json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=auth_header(old)).status_code == 200

    r = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(old),
        json={"current_password": ADMIN_NEW_PASSWORD, "new_password": "Another-Pass-999"},
    )
    assert r.status_code == 200
    new = r.json()["access_token"]

    assert client.get("/api/v1/auth/me", headers=auth_header(new)).status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth_header(old)).status_code == 401


def test_wrong_current_password_rejected(client):
    token = login(client, ADMIN_USER, ADMIN_PASSWORD).json()["access_token"]
    r = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(token),
        json={"current_password": "wrong-password", "new_password": "Another-Pass-999"},
    )
    assert r.status_code == 400


def test_new_password_must_be_different_and_long_enough(client):
    token = login(client, ADMIN_USER, ADMIN_PASSWORD).json()["access_token"]
    short = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(token),
        json={"current_password": ADMIN_PASSWORD, "new_password": "short"},
    )
    assert short.status_code == 422
    same = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(token),
        json={"current_password": ADMIN_PASSWORD, "new_password": ADMIN_PASSWORD},
    )
    assert same.status_code == 422


def test_account_locks_after_repeated_failures(client):
    for _ in range(5):
        assert login(client, ADMIN_USER, "bad-password-x").status_code == 401
    # Even the correct password is refused while locked.
    r = login(client, ADMIN_USER, ADMIN_PASSWORD)
    assert r.status_code == 429


def test_unknown_user_gets_generic_401(client):
    r = login(client, "nobody", "whatever-123")
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid username or password"
