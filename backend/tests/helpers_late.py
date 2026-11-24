from datetime import timedelta

from conftest import BRANCH_LAT, BRANCH_LNG, auth_header


def _loc(lat, lng, acc=10):
    return {"latitude": lat, "longitude": lng, "accuracy_m": acc}


def _co(lat, lng, desc="جمع‌بندی کارهای امروز و پیگیری وظایف", acc=10):
    return {"latitude": lat, "longitude": lng, "accuracy_m": acc, "work_description": desc}


def _set_all_days_work_week(client, admin_token):
    r = client.patch(
        "/api/v1/admin/schedule",
        headers=auth_header(admin_token),
        json={"work_days": [0, 1, 2, 3, 4, 5, 6], "start_time": "08:00",
              "end_time": "17:00", "late_grace_minutes": 15},
    )
    assert r.status_code == 200, r.text


def _yesterday_record(client, admin_token, token, branch):
    """Employee checks in today; admin then moves that record to yesterday (still open)."""
    h = auth_header(token)
    r = client.post("/api/v1/attendance/check-in", headers=h, json=_loc(BRANCH_LAT, BRANCH_LNG))
    assert r.status_code == 201, r.text
    rec_id = r.json()["id"]

    from datetime import datetime, timedelta, timezone

    iran = timezone(timedelta(hours=3, minutes=30))
    yesterday = (datetime.now(iran) - timedelta(days=1)).strftime("%Y-%m-%dT08:30:00+03:30")
    r = client.patch(
        f"/api/v1/admin/attendance/{rec_id}",
        headers=auth_header(admin_token),
        json={"check_in_at": yesterday},
    )
    assert r.status_code == 200, r.text
    return rec_id


def _today():
    from datetime import datetime, timedelta, timezone

    iran = timezone(timedelta(hours=3, minutes=30))
    return datetime.now(iran).date()


def _yesterday():
    return _today() - timedelta(days=1)


def _submit(client, token, work_date, desc="کارهای دیروز شامل جلسه و کدنویسی",
            lat=BRANCH_LAT, lng=BRANCH_LNG, time="17:15"):
    return client.post(
        "/api/v1/attendance/late-checkout",
        headers=auth_header(token),
        json={"work_date": work_date.isoformat(), "check_out_time": time,
              "latitude": lat, "longitude": lng, "accuracy_m": 10, "description": desc},
    )


def _week_day(client, token, day):
    r = client.get(f"/api/v1/attendance/week?start={day.isoformat()}", headers=auth_header(token))
    assert r.status_code == 200, r.text
    for d in r.json()["days"]:
        if d["date"] == day.isoformat():
            return d
    raise AssertionError(f"{day} not found in week")
