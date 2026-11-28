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
    AbsenceReason,
    AttendanceRecord,
    Branch,
    HourlyLeaveRequest,
    LateCheckoutRequest,
    LeaveRequest,
    User,
)
from app.schemas import AttendanceOut
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


def _mark_admin_edited(rec: AttendanceRecord, *fields: str) -> None:
    """Remembers exactly which sides of the record the manager changed."""
    current = {f for f in (rec.admin_edited_fields or "").split(",") if f}
    current.update(fields)
    rec.admin_edited_fields = ",".join(sorted(current))


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
    hourly_leaves: list,
    absence_reason: str | None,
    today: date,
) -> dict:
    is_work = is_work_day(sched, d)
    status = "future"
    hours = None
    is_late = False
    left_early = False
    hourly_hours = 0.0
    late_minutes = 0
    overtime_minutes = 0

    if record is not None:
        ci = as_utc(record.check_in_at)
        co = as_utc(record.check_out_at)
        if co is not None:
            hours = round((co - ci).total_seconds() / 3600, 2)
            co_local = co.astimezone(local_tz())
            # An approved hourly leave during the day reduces the worked hours.
            ci_local_h = ci.astimezone(local_tz())
            ci_hour = ci_local_h.hour + ci_local_h.minute / 60
            co_hour = co_local.hour + co_local.minute / 60
            for item in hourly_leaves:
                overlap = max(0.0, min(item.end_hour, co_hour) - max(item.start_hour, ci_hour))
                hourly_hours += overlap
            if hourly_hours:
                hours = round(max(0.0, hours - hourly_hours), 2)
            if co_local < at_local(d, sched.end_time):
                left_early = True
        late_minutes, overtime_minutes = record_metrics(record, sched, hourly_leaves)
        is_late = late_minutes > 0

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
    elif hourly_leaves and is_work and d <= today:
        # Approved hourly leave without any attendance record: the day is excused.
        status = "leave"
        hourly_hours = round(sum(item.end_hour - item.start_hour for item in hourly_leaves), 2)
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
        "hourly_leave_hours": round(hourly_hours, 2),
        "late_minutes": late_minutes,
        "overtime_minutes": overtime_minutes,
        "absence_reason": absence_reason,
    }


def record_metrics(rec: AttendanceRecord, sched, leaves=()) -> tuple[int, int]:
    """(late minutes after the grace period, overtime minutes) for one record.

    On a non-working day any time at the office counts as overtime.
    An approved hourly leave at the start of the day pushes the late threshold
    to the end of that leave (plus the usual grace), so arriving afterwards is
    not late.
    """
    if rec.check_in_at is None:
        return 0, 0
    ci = as_utc(rec.check_in_at).astimezone(local_tz())
    co = as_utc(rec.check_out_at).astimezone(local_tz()) if rec.check_out_at else None
    work_day = is_work_day(sched, rec.work_date)
    late = 0
    if work_day:
        shift_start = at_local(rec.work_date, sched.start_time)
        grace_h = sched.late_grace_minutes / 60
        threshold = shift_start.hour + shift_start.minute / 60 + grace_h
        for item in sorted(leaves, key=lambda x: x.start_hour):
            if item.start_hour <= threshold and item.end_hour > threshold:
                threshold = item.end_hour + grace_h
        ci_hour = ci.hour + ci.minute / 60
        if ci_hour > threshold + 1e-9:
            late = int(round((ci_hour - threshold) * 60))
    if co is None:
        return late, 0
    if not work_day:
        return late, max(0, int((co - ci).total_seconds() // 60))
    shift_end = at_local(rec.work_date, sched.end_time)
    overtime = max(0, int((co - shift_end).total_seconds() // 60))
    return late, overtime


def hourly_leave_hours_for_record(rec: AttendanceRecord, leaves: list) -> float:
    """Hours of approved hourly leave that fall inside this record's presence."""
    if not leaves or rec.check_out_at is None:
        return 0.0
    ci = as_utc(rec.check_in_at).astimezone(local_tz())
    co = as_utc(rec.check_out_at).astimezone(local_tz())
    ci_hour = ci.hour + ci.minute / 60
    co_hour = co.hour + co.minute / 60
    total = sum(
        max(0.0, min(item.end_hour, co_hour) - max(item.start_hour, ci_hour)) for item in leaves
    )
    return round(total, 2)


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
    hourly = list(
        db.scalars(
            select(HourlyLeaveRequest).where(
                HourlyLeaveRequest.user_id == user_id,
                HourlyLeaveRequest.status == STATUS_APPROVED,
                HourlyLeaveRequest.date >= start,
                HourlyLeaveRequest.date <= end,
            )
        )
    )
    absence_reasons = {
        row.date: row.reason
        for row in db.scalars(
            select(AbsenceReason).where(
                AbsenceReason.user_id == user_id,
                AbsenceReason.date >= start,
                AbsenceReason.date <= end,
            )
        )
    }
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
                hourly_leaves=[h for h in hourly if h.date == d],
                absence_reason=absence_reasons.get(d),
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
        "late_minutes": 0,
        "overtime_minutes": 0,
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
        totals["late_minutes"] += int(s.get("late_minutes") or 0)
        totals["overtime_minutes"] += int(s.get("overtime_minutes") or 0)
    return totals


def list_attendance(
    db: Session,
    from_date: date | None = None,
    to_date: date | None = None,
    user_id: int | None = None,
    branch_id: int | None = None,
) -> list[AttendanceOut]:
    """List attendance records with optional filters."""
    from app.schemas import attendance_out
    
    query = select(AttendanceRecord)
    if from_date is not None:
        query = query.where(AttendanceRecord.work_date >= from_date)
    if to_date is not None:
        query = query.where(AttendanceRecord.work_date <= to_date)
    if user_id is not None:
        query = query.where(AttendanceRecord.user_id == user_id)
    if branch_id is not None:
        query = query.where(AttendanceRecord.branch_id == branch_id)
    result = db.execute(query.order_by(AttendanceRecord.work_date.desc()))
    records = result.scalars().all()
    return [attendance_out(r) for r in records]


def admin_manual_record(
    db: Session,
    *,
    user_id: int,
    branch_id: int,
    work_date: date | None,
    check_in: str,
    check_out: str | None,
    work_description: str | None,
) -> AttendanceRecord:
    """Admin manually registers (or updates) an employee's attendance for a day."""
    from app.schemas import attendance_out

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")

    day = work_date or local_date(utcnow())

    from app.timeutil import at_local, parse_hhmm

    ci_local = at_local(day, check_in)
    co_local = at_local(day, check_out) if check_out else None
    if co_local is not None and co_local <= ci_local:
        raise HTTPException(status_code=422, detail="Check-out must be after check-in")

    ci_utc = as_utc(ci_local)
    co_utc = as_utc(co_local) if co_local else None

    rec = _today_record(db, user, day)
    if rec is not None:
        # Update existing record
        rec.branch_id = branch.id
        rec.check_in_at = ci_utc
        _mark_admin_edited(rec, "in")
        if co_utc is not None:
            rec.check_out_at = co_utc
            rec.check_out_source = "admin"
            _mark_admin_edited(rec, "out")
        if work_description is not None:
            rec.work_description = work_description.strip() or None
        rec.edited_by_admin = True
        rec.work_date = local_date(ci_utc)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Another record already exists for that day")
        db.refresh(rec)
        return rec

    # Create new record (no GPS data for admin manual entry)
    rec = AttendanceRecord(
        user_id=user.id,
        branch_id=branch.id,
        work_date=day,
        check_in_at=ci_utc,
        check_in_lat=0.0,
        check_in_lng=0.0,
        check_in_accuracy_m=0.0,
        check_in_distance_m=0.0,
        check_out_at=co_utc,
        check_out_lat=0.0 if co_utc else None,
        check_out_lng=0.0 if co_utc else None,
        check_out_accuracy_m=0.0 if co_utc else None,
        check_out_distance_m=0.0 if co_utc else None,
        check_out_source="admin" if co_utc else None,
        work_description=(work_description.strip() if work_description else None),
        edited_by_admin=True,
        admin_edited_fields="in,out" if co_utc else "in",
    )
    db.add(rec)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Another record already exists for that day")
    db.refresh(rec)
    return rec


def admin_dashboard(db: Session) -> "DashboardOut":
    from sqlalchemy import func
    from app.models import ROLE_EMPLOYEE, STATUS_APPROVED, STATUS_PENDING
    from app.services.schedule import get_schedule, schedule_out
    from app.schemas import DashboardOut

    refresh_expired_late_requests(db)
    today = local_date(utcnow())
    active = db.scalar(
        select(func.count()).select_from(User).where(
            User.role == ROLE_EMPLOYEE, User.is_active.is_(True)
        )
    ) or 0
    present = db.scalar(
        select(func.count()).select_from(AttendanceRecord).where(AttendanceRecord.work_date == today)
    ) or 0
    open_now = db.scalar(
        select(func.count()).select_from(AttendanceRecord).where(AttendanceRecord.check_out_at.is_(None))
    ) or 0
    leave_today = db.scalar(
        select(func.count()).select_from(LeaveRequest).where(
            LeaveRequest.status == STATUS_APPROVED,
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today,
        )
    ) or 0
    pending_leaves = db.scalar(
        select(func.count()).select_from(LeaveRequest).where(LeaveRequest.status == STATUS_PENDING)
    ) or 0
    pending_late = db.scalar(
        select(func.count()).select_from(LateCheckoutRequest).where(
            LateCheckoutRequest.status == STATUS_PENDING
        )
    ) or 0
    rejected_today = db.scalar(
        select(func.count()).select_from(AttendanceRecord).where(
            AttendanceRecord.work_date == today,
            AttendanceRecord.approval_status == "rejected",
        )
    ) or 0
    sched = get_schedule(db)
    return DashboardOut(
        date=today.isoformat(),
        active_employees=active,
        present_today=present,
        absent_today=max(active - present - leave_today, 0),
        leave_today=leave_today,
        rejected_today=rejected_today,
        open_check_ins=open_now,
        pending_leaves=pending_leaves,
        pending_late_checkouts=pending_late,
        schedule=schedule_out(sched),
    )


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
        _mark_admin_edited(rec, "in")
    if check_out_at is not None:
        rec.check_out_at = as_utc(check_out_at)
        rec.check_out_source = "admin"
        _mark_admin_edited(rec, "out")

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


# ---------- absence reasons (employee explains a missed working day) ----------


def save_absence_reason(db: Session, user: User, day: date, reason: str):
    """Creates or updates the employee's reason for being absent on one work day."""
    from app.schemas import absence_reason_out

    today = local_date(utcnow())
    if day > today:
        raise HTTPException(status_code=422, detail="Absence reason cannot be for a future day")
    if day < today - timedelta(days=365):
        raise HTTPException(status_code=422, detail="Absence reason is too far in the past")

    sched = get_schedule(db)
    if not is_work_day(sched, day):
        raise HTTPException(status_code=422, detail="That day is not a working day")

    rec = _today_record(db, user, day)
    if rec is not None and rec.check_out_at is not None:
        raise HTTPException(status_code=409, detail="This day already has recorded attendance")

    approved_leave = db.scalar(
        select(LeaveRequest).where(
            LeaveRequest.user_id == user.id,
            LeaveRequest.status == STATUS_APPROVED,
            LeaveRequest.start_date <= day,
            LeaveRequest.end_date >= day,
        )
    )
    if approved_leave is not None:
        raise HTTPException(status_code=409, detail="This day is covered by an approved leave")

    row = db.scalar(
        select(AbsenceReason).where(
            AbsenceReason.user_id == user.id, AbsenceReason.date == day
        )
    )
    if row is None:
        row = AbsenceReason(user_id=user.id, date=day, reason=reason)
        db.add(row)
    else:
        row.reason = reason
        row.created_at = utcnow()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Absence reason already exists for that day")
    db.refresh(row)
    return absence_reason_out(row)


def absence_reasons_between(
    db: Session, user_id: int, start: date, end: date
) -> list:
    return list(
        db.scalars(
            select(AbsenceReason).where(
                AbsenceReason.user_id == user_id,
                AbsenceReason.date >= start,
                AbsenceReason.date <= end,
            )
        )
    )


def current_week_start(today: date) -> date:
    """Weeks start on Saturday (Iranian week)."""
    return today - timedelta(days=(today.weekday() - 5) % 7)
