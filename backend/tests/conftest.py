import os
import tempfile

# Must be set before the app (and its settings) is imported.
_db_dir = tempfile.mkdtemp(prefix="attendance-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_dir}/test.db"
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 40
os.environ["ADMIN_BOOTSTRAP_PASSWORD"] = "Admin-Pass-123"
os.environ["ENVIRONMENT"] = "development"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

ADMIN_USER = "admin"
ADMIN_PASSWORD = "Admin-Pass-123"
ADMIN_NEW_PASSWORD = "Admin-New-456"

# Tehran, Azadi area (used as the branch location in tests)
BRANCH_LAT = 35.6892
BRANCH_LNG = 51.3890


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as c:
        yield c


def login(client, username, password):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_token(client):
    """Logs in as the bootstrap admin, replaces the initial password, returns a ready token."""
    r = login(client, ADMIN_USER, ADMIN_PASSWORD)
    assert r.status_code == 200, r.text
    assert r.json()["must_change_password"] is True
    r = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(r.json()["access_token"]),
        json={"current_password": ADMIN_PASSWORD, "new_password": ADMIN_NEW_PASSWORD},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def branch(client, admin_token):
    r = client.post(
        "/api/v1/admin/branches",
        headers=auth_header(admin_token),
        json={"name": "دفتر مرکزی", "latitude": BRANCH_LAT, "longitude": BRANCH_LNG, "radius_m": 100},
    )
    assert r.status_code == 201, r.text
    return r.json()


def make_employee(client, admin_token, username, branch_ids, password="Initial-Pass-1"):
    r = client.post(
        "/api/v1/admin/employees",
        headers=auth_header(admin_token),
        json={
            "username": username,
            "full_name": "کارمند تست",
            "password": password,
            "branch_ids": branch_ids,
        },
    )
    return r


def ready_employee_token(client, admin_token, username, branch_ids, password="Initial-Pass-1"):
    """Creates an employee, logs in, changes the initial password, returns a ready token."""
    r = make_employee(client, admin_token, username, branch_ids, password)
    assert r.status_code == 201, r.text
    r = login(client, username, password)
    assert r.status_code == 200, r.text
    r = client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(r.json()["access_token"]),
        json={"current_password": password, "new_password": "Employee-Pass-789"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]
