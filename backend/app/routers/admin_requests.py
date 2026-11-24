from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_admin_user
from app.models import (
    STATUS_PENDING,
    AttendanceRecord,
    LateCheckoutRequest,
    LeaveRequest,
    User,
)
from app.schemas import (
    DayStateOut,
    DecisionIn,
    LateCheckoutOut,
    LeaveOut,
    ScheduleIn,
    ScheduleOut,
    SummaryOut,
    WeekOut,
    leave_out,
    late_checkout_out,
)
from app.services.attendance import (
    current_week_start,
    day_states,
    decide_late_checkout,
    decide_record,
    refresh_expired_late_requests,
    totals_for_states,
)
from app.services.leave import decide_leave
from app.services.schedule import get_schedule, schedule_out
from app.timeutil import local_date, utcnow

router = APIRouter(prefix="/admin", tags=["admin-requests"], dependencies=[Depends(get_admin_user)])

MAX_RANGE_DAYS = 400


def _clamp_range(start: date | None, end: date | None) -> tuple[date, date]:
    today = local_date(utcnow())
    first = start or (today - timedelta(days=30))
    last = end or today
    if first > last:
        raise HTTPException(status_code=422, detail="from_date must be before to_date")
    if (last - first).days > MAX_RANGE_DAYS:
        raise HTTPException(status_code=422, detail=f"Date range too large (max {MAX_RANGE_DAYS} days)")
    return first, last


# ---------- leaves ----------

@router.get("/leaves", response_model=list[LeaveOut])
def list_leaves(
    status: str | None = None,
    user_id: int | None = None,
    limit: int = Query(300, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[LeaveOut]:
    q = select(LeaveRequest).order_by(LeaveRequest.created_at.desc()).limit(limit)
    if status:
        q = q.where(LeaveRequest.status == status)
    if user_id:
        q = q.where(LeaveRequest.user_id == user_id)
    return [leave_out(l) for l in db.scalars(q)]


@router.patch("/leaves/{leave_id}", response_model=LeaveOut)
def decide_leave_request(
    leave_id: int,
    body: DecisionIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> LeaveOut:
    leave = decide_leave(db, admin, leave_id, body.decision, body.note)
    return leave_out(leave)


# ---------- forgotten check-outs ----------

@router.get("/late-checkouts", response_model=list[LateCheckoutOut])
def list_late_checkouts(
    status: str | None = None,
    user_id: int | None = None,
    limit: int = Query(300, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[LateCheckoutOut]:
    refresh_expired_late_requests(db)
    q = select(LateCheckoutRequest).order_by(LateCheckoutRequest.work_date.desc()).limit(limit)
    if status:
        q = q.where(LateCheckoutRequest.status == status)
    if user_id:
        q = q.where(LateCheckoutRequest.user_id == user_id)
    return [late_checkout_out(r) for r in db.scalars(q)]


@router.patch("/late-checkouts/{request_id}", response_model=LateCheckoutOut)
def decide_late_checkout_request(
    request_id: int,
    body: DecisionIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> LateCheckoutOut:
    req = decide_late_checkout(db, admin, request_id, body.decision, body.note)
    return late_checkout_out(req)


# ---------- daily record decision ----------

@router.patch("/attendance/{record_id}/decision")
def decide_attendance(
    record_id: int,
    body: DecisionIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    rec = decide_record(db, admin, record_id, body.decision, body.note)
    return {"id": rec.id, "approval_status": rec.approval_status, "approval_note": rec.approval_note}


# ---------- work schedule ----------

@router.get("/schedule", response_model=ScheduleOut)
def get_work_schedule(db: Session = Depends(get_db)) -> ScheduleOut:
    return schedule_out(get_schedule(db))


@router.patch("/schedule", response_model=ScheduleOut)
def update_work_schedule(
    body: ScheduleIn,
    db: Session = Depends(get_db),
) -> ScheduleOut:
    import json

    from app.timeutil import utcnow as _utcnow

    sched = get_schedule(db)
    sched.work_days = json.dumps(body.work_days)
    sched.start_time = body.start_time
    sched.end_time = body.end_time
    sched.late_grace_minutes = body.late_grace_minutes
    sched.updated_at = _utcnow()
    db.commit()
    db.refresh(sched)
    return schedule_out(sched)


# ---------- weekly view / summary ----------

@router.get("/week", response_model=WeekOut)
def employee_week(
    user_id: int,
    start: date | None = None,
    db: Session = Depends(get_db),
) -> WeekOut:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    today = local_date(utcnow())
    first = start or current_week_start(today)
    last = first + timedelta(days=6)
    sched = get_schedule(db)
    states = day_states(db, user.id, first, last, sched=sched)
    return WeekOut(start=first, end=last, days=states, schedule=schedule_out(sched))


@router.get("/summary", response_model=SummaryOut)
def employee_summary(
    user_id: int,
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
) -> SummaryOut:
    """Day-by-day states plus totals (hours, late, early) for one employee."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    first, last = _clamp_range(from_date, to_date)
    sched = get_schedule(db)
    states = day_states(db, user.id, first, last, sched=sched)
    return SummaryOut(
        user_id=user.id,
        user_full_name=user.full_name,
        from_date=first,
        to_date=last,
        days=[DayStateOut(**s) for s in states],
        totals=totals_for_states(states),
    )
