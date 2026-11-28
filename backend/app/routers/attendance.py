from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_ready_user
from app.models import AttendanceRecord, LateCheckoutRequest, User
from app.schemas import (
    AbsenceReasonIn,
    AbsenceReasonOut,
    AttendanceOut,
    CheckoutIn,
    LateCheckoutIn,
    LateCheckoutOut,
    LocationIn,
    SummaryOut,
    TodayOut,
    WeekOut,
    absence_reason_out,
    attendance_out,
    late_checkout_out,
)
from app.services.attendance import (
    absence_reasons_between,
    check_in,
    check_out,
    current_week_start,
    day_states,
    default_history_range,
    get_today_status,
    save_absence_reason,
    submit_late_checkout,
    totals_for_states,
)
from app.services.schedule import get_schedule, schedule_out
from app.timeutil import local_date, utcnow

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/today", response_model=TodayOut)
def today(user: User = Depends(get_ready_user), db: Session = Depends(get_db)) -> TodayOut:
    status, rec = get_today_status(db, user)
    return TodayOut(
        status=status, record=attendance_out(rec, get_schedule(db)) if rec else None
    )


@router.post("/check-in", response_model=AttendanceOut, status_code=201)
def post_check_in(
    body: LocationIn,
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> AttendanceOut:
    rec = check_in(db, user, body.latitude, body.longitude, body.accuracy_m)
    return attendance_out(rec)


@router.post("/check-out", response_model=AttendanceOut)
def post_check_out(
    body: CheckoutIn,
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> AttendanceOut:
    rec = check_out(
        db, user, body.latitude, body.longitude, body.accuracy_m, body.work_description
    )
    return attendance_out(rec)


@router.get("/history", response_model=list[AttendanceOut])
def history(
    from_date: date | None = None,
    to_date: date | None = None,
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> list[AttendanceOut]:
    default_from, default_to = default_history_range(local_date(utcnow()))
    start = from_date or default_from
    end = to_date or default_to
    if start > end:
        raise HTTPException(status_code=422, detail="from_date must be before to_date")
    q = (
        select(AttendanceRecord)
        .where(
            AttendanceRecord.user_id == user.id,
            AttendanceRecord.work_date >= start,
            AttendanceRecord.work_date <= end,
        )
        .order_by(AttendanceRecord.work_date.desc())
    )
    sched = get_schedule(db)
    return [attendance_out(r, sched) for r in db.scalars(q)]


@router.get("/summary", response_model=SummaryOut)
def my_summary(
    from_date: date | None = None,
    to_date: date | None = None,
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> SummaryOut:
    """The signed-in employee's own day-by-day report and totals."""
    default_from, default_to = default_history_range(local_date(utcnow()))
    start = from_date or default_from
    end = to_date or default_to
    if start > end:
        raise HTTPException(status_code=422, detail="from_date must be before to_date")
    if (end - start).days > 400:
        raise HTTPException(status_code=422, detail="Date range is too large (max 400 days)")
    sched = get_schedule(db)
    states = day_states(db, user.id, start, end, sched=sched)
    return SummaryOut(
        user_id=user.id,
        user_full_name=user.full_name,
        from_date=start,
        to_date=end,
        days=states,
        totals=totals_for_states(states),
    )


# ---------- absence reasons ----------


@router.post("/absence-reason", response_model=AbsenceReasonOut, status_code=201)
def create_absence_reason(
    body: AbsenceReasonIn,
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> AbsenceReasonOut:
    """The employee explains why they were absent on one working day."""
    return save_absence_reason(db, user, body.date, body.reason)


@router.get("/absence-reasons", response_model=list[AbsenceReasonOut])
def my_absence_reasons(
    from_date: date | None = None,
    to_date: date | None = None,
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> list[AbsenceReasonOut]:
    default_from, default_to = default_history_range(local_date(utcnow()))
    start = from_date or default_from
    end = to_date or default_to
    return [absence_reason_out(r) for r in absence_reasons_between(db, user.id, start, end)]


@router.get("/week", response_model=WeekOut)
def week(
    start: date | None = None,
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> WeekOut:
    """Weekly view: present / absent / leave / pending check-out for each day."""
    today = local_date(utcnow())
    first = start or current_week_start(today)
    last = first + timedelta(days=6)
    sched = get_schedule(db)
    states = day_states(db, user.id, first, last, sched=sched)
    return WeekOut(start=first, end=last, days=states, schedule=schedule_out(sched))


@router.post("/late-checkout", response_model=LateCheckoutOut, status_code=201)
def post_late_checkout(
    body: LateCheckoutIn,
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> LateCheckoutOut:
    req = submit_late_checkout(
        db,
        user,
        body.work_date,
        body.check_out_time,
        body.latitude,
        body.longitude,
        body.accuracy_m,
        body.description,
    )
    return late_checkout_out(req)


@router.get("/late-checkouts", response_model=list[LateCheckoutOut])
def my_late_checkouts(
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> list[LateCheckoutOut]:
    from app.services.attendance import refresh_expired_late_requests

    refresh_expired_late_requests(db)
    reqs = db.scalars(
        select(LateCheckoutRequest)
        .where(LateCheckoutRequest.user_id == user.id)
        .order_by(LateCheckoutRequest.work_date.desc())
    )
    return [late_checkout_out(r) for r in reqs]
