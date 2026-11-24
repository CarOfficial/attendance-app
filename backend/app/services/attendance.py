from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.geo import haversine_m
from app.models import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    AttendanceRecord,
    Branch,
    LateCheckoutRequest,
    LeaveRequest,
    User,
)
from app.services.leave import approved_leaves_between
from app.services.schedule import get_schedule, is_work_day
from app.timeutil import (
    as_utc,
    at_local,
    end_of_local_day,
    local_date,
    local_tz,
    utcnow,
)

# A forgotten check-out may be filed until 24h after the end of that day.
SUBMIT_WINDOW_HOURS = 24
# The manager has until 48h after the end of that day (but at least 24h after the
# request was filed) to decide; after that the day is recorded as absent.
DECISION_GRACE_HOURS = 48
MANAGER_MIN_HOURS = 24


def _ensure_accuracy(accuracy_m: float) -> None:
    if accuracy_m > settings.max_gps_accuracy_m:
        raise HTTPException(
            status_code=422,
            detail=f"GPS accuracy too low ({accuracy_m:.0f} m). Move to an open area and try again.",
        )


def _today_record(db: Session, user: User, day: date) -> AttendanceRecord | None:
    return db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.user_id == user.id,
            AttendanceRecord.work_date == day,
        )
    )


def _open_record(db: Session, user: User) -> AttendanceRecord | None:
    return db.scalar(
        select(AttendanceRecord)
        .where(AttendanceRecord.user_id == user.id, AttendanceRecord.check_out_at.is_(None))
        .order_by(AttendanceRecord.check_in_at.desc())
    )


def _location_branch(db: Session, user: User, lat: float, lng: float) -> tuple[Branch, float]:
    """Pick the assigned branch the user is inside of (smallest distance wins)."""
    branches = [b for b in user.branches if b.is_active]
    if not branches:
        raise HTTPException(status_code=403, detail="No active branch is assigned to you")

    inside: list[tuple[Branch, float]] = []
    for b in branches:
        d = haversine_m(lat, lng, b.latitude, b.longitude)
        if d <= b.radius_m:
            inside.append((b, d))

    if not inside:
        nearest, nearest_d = min(
            ((b, haversine_m(lat, lng, b.latitude, b.longitude)) for b in branches),
            key=lambda x: x[1],
        )
        raise HTTPException(
            status_code=403,
            detail=f"You are outside the allowed area. Nearest branch: {nearest.name} (~{round(nearest_d)} m).",
        )
    return min(inside, key=lambda x: x[1])


def get_today_status(db: Session, user: User) -> tuple[str, AttendanceRecord | None]:
    rec = _today_record(db, user, local_date(utcnow()))
    if rec is None:
        return "not_checked_in", None
    if rec.check_out_at is None:
        return "checked_in", rec
    return "checked_out", rec


def check_in(db: Session, user: User, lat: float, lng: float, accuracy_m: float) -> AttendanceRecord:
    _ensure_accuracy(accuracy_m)

    now = utcnow()
    today = local_date(now)

    leave = db.scalar(
        select(LeaveRequest).where(
            LeaveRequest.user_id == user.id,
            LeaveRequest.status == STATUS_APPROVED,
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today,
        )
    )
    if leave is not None:
        raise HTTPException(status_code=409, detail="You have an approved leave for today")

    branch, distance = _location_branch(db, user, lat, lng)

    open_rec = _open_record(db, user)
    if open_rec is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Check-out for {open_rec.work_date} was never recorded. "
                "Use the forgotten check-out request to fix it."
            ),
        )

    if _today_record(db, user, today) is not None:
        raise HTTPException(status_code=409, detail="You have already checked in today")

    rec = AttendanceRecord(
        user_id=user.id,
        branch_id=branch.id,
        work_date=today,
        check_in_at=now,
        check_in_lat=lat,
        check_in_lng=lng,
        check_in_accuracy_m=accuracy_m,
        check_in_distance_m=distance,
    )
    db.add(rec)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You have already checked in today")
    db.refresh(rec)
    return rec


def check_out(
    db: Session,
    user: User,
    lat: float,
    lng: float,
    accuracy_m: float,
    work_description: str,
) -> AttendanceRecord:
    _ensure_accuracy(accuracy_m)
    description = (work_description or "").strip()
    if len(description) < 3:
        raise HTTPException(status_code=422, detail="A short description of today's work is required")

    rec = _open_record(db, user)
    if rec is None:
        raise HTTPException(status_code=409, detail="No open check-in found")

    branch = rec.branch
    distance = haversine_m(lat, lng, branch.latitude, branch.longitude)
    if distance > branch.radius_m:
        raise HTTPException(
            status_code=403,
            detail=f"You must be at {branch.name} to check out (~{round(distance)} m away).",
        )

    rec.check_out_at = utcnow()
    rec.check_out_lat = lat
    rec.check_out_lng = lng
    rec.check_out_accuracy_m = accuracy_m
    rec.check_out_distance_m = distance
    rec.check_out_source = "employee"
    rec.work_description = description
    db.commit()
    db.refresh(rec)
    return rec


# ---------- forgotten check-out (late checkout) ----------


def late_decision_deadline(req: LateCheckoutRequest) -> datetime:
    """UTC moment after which an undecided request expires (day becomes absent)."""
    end_utc = end_of_local_day(req.work_date).astimezone(timezone.utc)
    return max(
        end_utc + timedelta(hours=DECISION_GRACE_HOURS),
        as_utc(req.requested_at) + timedelta(hours=MANAGER_MIN_HOURS),
    )


def late_submission_deadline(work_date: date) -> datetime:
    """UTC moment until which the employee may file the request (end of day + 24h)."""
    return end_of_local_day(work_date).astimezone(timezone.utc) + timedelta(hours=SUBMIT_WINDOW_HOURS)


def refresh_expired_late_requests(db: Session) -> int:
    """Mark pending requests past their decision deadline as expired. Returns count."""
    now = utcnow()
    changed = 0
    pending = db.scalars(select(LateCheckoutRequest).where(LateCheckoutRequest.status == STATUS_PENDING))
    for req in pending:
        if now > late_decision_deadline(req):
            req.status = "expired"
            changed += 1
    if changed:
        db.commit()
    return changed


def submit_late_checkout(
    db: Session,
    user: User,
    work_date: date,
    check_out_time: str,
    lat: float,
    lng: float,
    accuracy_m: float,
    description: str,
) -> LateCheckoutRequest:
    _ensure_accuracy(accuracy_m)
    refresh_expired_late_requests(db)

    now_utc = utcnow()
    now_local = now_utc.astimezone(local_tz())
    today = local_date(now_utc)
    description = (description or "").strip()
    if len(description) < 3:
        raise HTTPException(status_code=422, detail="A short description of the work is required")

    if work_date >= today:
        raise HTTPException(status_code=422, detail="work_date must be a past day")
    if now_utc > late_submission_deadline(work_date):
        raise HTTPException(
            status_code=422,
            detail="The 24-hour window for reporting this check-out has passed",
        )

    sched = get_schedule(db)
    if not is_work_day(sched, work_date):
        raise HTTPException(status_code=422, detail="That day is not a working day")

    rec = _today_record(db, user, work_date)
    if rec is None:
        raise HTTPException(status_code=409, detail=f"No check-in found for {work_date}")
    if rec.check_out_at is not None:
        raise HTTPException(status_code=409, detail="Check-out is already recorded for that day")

    existing = db.scalar(
        select(LateCheckoutRequest).where(
            LateCheckoutRequest.user_id == user.id,
            LateCheckoutRequest.work_date == work_date,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"A request for that day already exists ({existing.status})")

    branch, distance = _location_branch(db, user, lat, lng)

    try:
        hh, mm = check_out_time.split(":")
        claimed = datetime.combine(work_date, time(int(hh), int(mm)), tzinfo=local_tz())
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="check_out_time must be HH:MM")

    check_in_local = as_utc(rec.check_in_at).astimezone(local_tz())
    if claimed <= check_in_local:
        raise HTTPException(status_code=422, detail="Check-out time must be after check-in")
    if claimed > now_local:
        raise HTTPException(status_code=422, detail="Check-out time cannot be in the future")

    req = LateCheckoutRequest(
        user_id=user.id,
        record_id=rec.id,
        work_date=work_date,
        branch_id=branch.id,
        requested_at=now_utc,
        # Always stored as UTC so SQLite round-trips stay correct.
        check_out_at=claimed.astimezone(timezone.utc),
        latitude=lat,
        longitude=lng,
        accuracy_m=accuracy_m,
        distance_m=distance,
        description=description,
    )
    db.add(req)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A request for that day already exists")
    db.refresh(req)
    return req


def decide_late_checkout(
    db: Session, admin: User, request_id: int, decision: str, note: str | None
) -> LateCheckoutRequest:
    refresh_expired_late_requests(db)
    req = db.get(LateCheckoutRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != STATUS_PENDING:
        raise HTTPException(status_code=409, detail=f"Request is already {req.status}")

    rec = db.get(AttendanceRecord, req.record_id)
    now = utcnow()

    if decision == "approve":
        if rec is None:
            raise HTTPException(status_code=409, detail="Attendance record not found")
        if rec.check_out_at is not None:
            raise HTTPException(status_code=409, detail="Check-out is already recorded for that day")
        rec.check_out_at = as_utc(req.check_out_at)
        rec.check_out_lat = req.latitude
        rec.check_out_lng = req.longitude
        rec.check_out_accuracy_m = req.accuracy_m
        rec.check_out_distance_m = req.distance_m
        rec.check_out_source = "late"
        rec.work_description = req.description
        rec.approval_status = STATUS_APPROVED
        rec.approval_note = note
        rec.approval_by = admin.id
        rec.approved_at = now
        req.status = STATUS_APPROVED
    else:
        req.status = STATUS_REJECTED
        if rec is not None:
            rec.approval_status = STATUS_REJECTED
            rec.approval_note = note
            rec.approval_by = admin.id
            rec.approved_at = now

    req.decided_at = now
    req.decided_by = admin.id
    req.decision_note = note
    db.commit()
    db.refresh(req)
    return req


def decide_record(
    db: Session, admin: User, record_id: int, decision: str, note: str | None
) -> AttendanceRecord:
    """Manager confirms/rejects a normal same-day record. Rejected days count as absent."""
    rec = db.get(AttendanceRecord, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if rec.check_out_at is None:
        raise HTTPException(
            status_code=422,
            detail="This day has no check-out; use the forgotten check-out request instead",
        )
    rec.approval_status = STATUS_APPROVED if decision == "approve" else STATUS_REJECTED
    rec.approval_note = note
    rec.approval_by = admin.id
    rec.approved_at = utcnow()
    db.commit()
    db.refresh(rec)
    return rec


# ---------- daily states / weekly view ----------

DAY_STATUSES = (
    "present",
    "working",
    "absent",
    "incomplete",
    "rejected",
    "leave",
    "pending_checkout",
    "non_working",
    "future",
)


def _day_state(
    d: date,
    *,
    sched,
    record: AttendanceRecord | None,
    late_req: LateCheckoutRequest | None,
    leave: LeaveRequest | None,
    pending_leave: bool,
    today: date,
) -> dict:
    is_work = is_work_day(sched, d)
    status = "future"
    hours = None
    is_late = False
    left_early = False

    if record is not None:
        ci = as_utc(record.check_in_at)
        co = as_utc(record.check_out_at)
        if co is not None:
            hours = round((co - ci).total_seconds() / 3600, 2)
            co_local = co.astimezone(local_tz())
            if co_local < at_local(d, sched.end_time):
                left_early = True
        ci_local = ci.astimezone(local_tz())
        late_after = at_local(d, sched.start_time) + timedelta(minutes=sched.late_grace_minutes)
        is_late = is_work and ci_local > late_after

        if record.approval_status == STATUS_REJECTED:
            status = "rejected"
        elif co is not None:
            status = "present"
        elif d >= today:
            status = "working"  # checked in and still at work today
        elif late_req is not None and late_req.status == STATUS_PENDING:
            status = "pending_checkout"
        else:
            # Checked in but never checked out and no approved request -> absent.
            status = "incomplete"
    elif leave is not None:
        status = "leave"
    elif not is_work:
        status = "non_working"
    elif d > today:
        status = "future"
    else:
        status = "absent"

    return {
        "date": d.isoformat(),
        "is_work_day": is_work,
        "status": status,
        "check_in_at": as_utc(record.check_in_at).isoformat() if record and record.check_in_at else None,
        "check_out_at": as_utc(record.check_out_at).isoformat() if record and record.check_out_at else None,
        "hours_worked": hours,
        "branch_name": record.branch.name if record else None,
        "work_description": record.work_description if record else None,
        "approval_status": record.approval_status if record else "none",
        "approval_note": record.approval_note if record else None,
        "late_request_status": late_req.status if late_req else None,
        "pending_leave": pending_leave,
        "is_late": is_late,
        "left_early": left_early,
    }


def day_states(
    db: Session,
    user_id: int,
    start: date,
    end: date,
    *,
    sched=None,
    refresh: bool = True,
) -> list[dict]:
    if refresh:
        refresh_expired_late_requests(db)
    sched = sched or get_schedule(db)
    today = local_date(utcnow())

    records = {
        r.work_date: r
        for r in db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.user_id == user_id,
                AttendanceRecord.work_date >= start,
                AttendanceRecord.work_date <= end,
            )
        )
    }
    late_reqs = {
        r.work_date: r
        for r in db.scalars(
            select(LateCheckoutRequest).where(
                LateCheckoutRequest.user_id == user_id,
                LateCheckoutRequest.work_date >= start,
                LateCheckoutRequest.work_date <= end,
            )
        )
    }
    leaves = approved_leaves_between(db, user_id, start, end)
    pending_leaves = list(
        db.scalars(
            select(LeaveRequest).where(
                LeaveRequest.user_id == user_id,
                LeaveRequest.status == STATUS_PENDING,
                LeaveRequest.start_date <= end,
                LeaveRequest.end_date >= start,
            )
        )
    )

    def _covers(items, d) -> bool:
        return any(l.start_date <= d <= l.end_date for l in items)

    states = []
    d = start
    while d <= end:
        states.append(
            _day_state(
                d,
                sched=sched,
                record=records.get(d),
                late_req=late_reqs.get(d),
                leave=next((l for l in leaves if l.start_date <= d <= l.end_date), None),
                pending_leave=_covers(pending_leaves, d) and d not in records,
                today=today,
            )
        )
        d += timedelta(days=1)
    return states


def totals_for_states(states: list[dict]) -> dict:
    totals = {
        "present": 0,
        "absent": 0,
        "leave": 0,
        "pending_checkout": 0,
        "non_working": 0,
        "future": 0,
        "total_hours": 0.0,
        "late_count": 0,
        "early_leave_count": 0,
    }
    for s in states:
        st = s["status"]
        if st in ("absent", "incomplete", "rejected"):
            totals["absent"] += 1
        elif st == "working":
            totals["present"] += 1
        elif st in totals:
            totals[st] += 1
        if s["hours_worked"]:
            totals["total_hours"] = round(totals["total_hours"] + s["hours_worked"], 2)
        if s["is_late"]:
            totals["late_count"] += 1
        if s["left_early"]:
            totals["early_leave_count"] += 1
    return totals


def admin_update_record(
    db: Session,
    rec: AttendanceRecord,
    *,
    branch_id: int | None,
    check_in_at,
    check_out_at,
) -> AttendanceRecord:
    if branch_id is not None:
        if db.get(Branch, branch_id) is None:
            raise HTTPException(status_code=422, detail="Branch not found")
        rec.branch_id = branch_id
    if check_in_at is not None:
        rec.check_in_at = as_utc(check_in_at)
    if check_out_at is not None:
        rec.check_out_at = as_utc(check_out_at)
        rec.check_out_source = "admin"

    ci = as_utc(rec.check_in_at)
    co = as_utc(rec.check_out_at)
    if co is not None and co < ci:
        raise HTTPException(status_code=422, detail="Check-out cannot be before check-in")

    rec.work_date = local_date(ci)
    rec.edited_by_admin = True
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Another record already exists for that day")
    db.refresh(rec)
    return rec


def default_history_range(today: date) -> tuple[date, date]:
    return today - timedelta(days=30), today


def current_week_start(today: date) -> date:
    """Weeks start on Saturday (Iranian week)."""
    return today - timedelta(days=(today.weekday() - 5) % 7)
