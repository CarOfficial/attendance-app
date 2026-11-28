from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    LeaveRequest,
    User,
)
from app.schemas import HourlyLeaveIn, HourlyLeaveOut
from app.timeutil import local_date, utcnow

# Employees may file a leave for today or up to N days back (retroactive correction).
RETRO_DAYS = 3
MAX_LEAVE_DAYS = 400


def _overlaps(db: Session, user_id: int, start: date, end: date) -> LeaveRequest | None:
    return db.scalar(
        select(LeaveRequest).where(
            LeaveRequest.user_id == user_id,
            LeaveRequest.status.in_([STATUS_PENDING, STATUS_APPROVED]),
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        )
    )


def create_leave(db: Session, user: User, start: date, end: date, reason: str) -> LeaveRequest:
    reason = reason.strip()
    if len(reason) < 3:
        raise HTTPException(status_code=422, detail="Reason is too short")
    if start > end:
        raise HTTPException(status_code=422, detail="start_date must not be after end_date")
    today = local_date(utcnow())
    if start < today - timedelta(days=RETRO_DAYS):
        raise HTTPException(status_code=422, detail=f"Leave cannot start more than {RETRO_DAYS} days in the past")
    if end - start > timedelta(days=MAX_LEAVE_DAYS):
        raise HTTPException(status_code=422, detail="Leave range is too long")

    existing = _overlaps(db, user.id, start, end)
    if existing is not None:
        raise HTTPException(status_code=409, detail="You already have a pending or approved leave for these dates")

    leave = LeaveRequest(user_id=user.id, start_date=start, end_date=end, reason=reason)
    db.add(leave)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Leave request already exists")
    db.refresh(leave)
    return leave


def decide_leave(
    db: Session, admin: User, leave_id: int, decision: str, note: str | None
) -> LeaveRequest:
    leave = db.get(LeaveRequest, leave_id)
    if leave is None:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if leave.status != STATUS_PENDING:
        raise HTTPException(status_code=409, detail=f"Leave request is already {leave.status}")

    leave.status = STATUS_APPROVED if decision == "approve" else STATUS_REJECTED
    leave.decided_at = utcnow()
    leave.decided_by = admin.id
    leave.decision_note = note
    db.commit()
    db.refresh(leave)
    return leave


def approved_leaves_between(db: Session, user_id: int, start: date, end: date) -> list[LeaveRequest]:
    return list(
        db.scalars(
            select(LeaveRequest).where(
                LeaveRequest.user_id == user_id,
                LeaveRequest.status == STATUS_APPROVED,
                LeaveRequest.start_date <= end,
                LeaveRequest.end_date >= start,
            )
        )
    )


# ---- Hourly leave (a few hours off on one day) ----

HOURLY_RETRO_DAYS = 3
HOURLY_FUTURE_DAYS = 60


def _hourly_overlap(
    db: Session, user_id: int, day: date, start_hour: float, end_hour: float
):
    """A pending or approved hourly leave that shares hours on the same day."""
    from app.models import HourlyLeaveRequest

    return db.scalar(
        select(HourlyLeaveRequest).where(
            HourlyLeaveRequest.user_id == user_id,
            HourlyLeaveRequest.date == day,
            HourlyLeaveRequest.status.in_([STATUS_PENDING, STATUS_APPROVED]),
            HourlyLeaveRequest.start_hour < end_hour,
            HourlyLeaveRequest.end_hour > start_hour,
        )
    )


def create_hourly_leave(
    db: Session,
    *,
    user_id: int,
    day: date,
    start_hour: float,
    end_hour: float,
    reason: str,
) -> HourlyLeaveOut:
    """Files an hourly leave for one employee. Used by both the app and the admin panel."""
    from app.models import HourlyLeaveRequest
    from app.schemas import hourly_leave_out

    reason = (reason or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=422, detail="Reason is too short")
    if not (0 <= start_hour < end_hour <= 24):
        raise HTTPException(status_code=422, detail="Hours must satisfy 0 <= start < end <= 24")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    today = local_date(utcnow())
    if day < today - timedelta(days=HOURLY_RETRO_DAYS):
        raise HTTPException(
            status_code=422,
            detail=f"Hourly leave cannot be for more than {HOURLY_RETRO_DAYS} days in the past",
        )
    if day > today + timedelta(days=HOURLY_FUTURE_DAYS):
        raise HTTPException(status_code=422, detail="Hourly leave is too far in the future")

    if _hourly_overlap(db, user.id, day, start_hour, end_hour) is not None:
        raise HTTPException(
            status_code=409, detail="You already have a pending or approved hourly leave at that time"
        )

    leave = HourlyLeaveRequest(
        user_id=user.id,
        date=day,
        start_hour=start_hour,
        end_hour=end_hour,
        reason=reason,
        status=STATUS_PENDING,
    )
    db.add(leave)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Hourly leave request already exists")
    db.refresh(leave)
    return hourly_leave_out(leave)


def decide_hourly_leave(
    db: Session, admin: User, leave_id: int, decision: str, note: str | None = None
) -> HourlyLeaveOut:
    """The manager approves or rejects one hourly leave request."""
    from app.models import HourlyLeaveRequest
    from app.schemas import hourly_leave_out

    leave = db.get(HourlyLeaveRequest, leave_id)
    if leave is None:
        raise HTTPException(status_code=404, detail="Hourly leave request not found")
    if leave.status != STATUS_PENDING:
        raise HTTPException(status_code=409, detail=f"Request is already {leave.status}")

    leave.status = STATUS_APPROVED if decision == "approve" else STATUS_REJECTED
    leave.decided_at = utcnow()
    leave.decided_by = admin.id
    leave.decision_note = note
    db.commit()
    db.refresh(leave)
    return hourly_leave_out(leave)


def list_hourly_leaves(
    db: Session,
    user_id: int | None = None,
    day: date | None = None,
    status: str | None = None,
) -> list[HourlyLeaveOut]:
    """Lists hourly leave requests, optionally filtered by employee, day or status."""
    from app.models import HourlyLeaveRequest
    from app.schemas import hourly_leave_out

    query = select(HourlyLeaveRequest)
    if user_id is not None:
        query = query.where(HourlyLeaveRequest.user_id == user_id)
    if day is not None:
        query = query.where(HourlyLeaveRequest.date == day)
    if status is not None:
        query = query.where(HourlyLeaveRequest.status == status)

    leaves = db.scalars(query.order_by(HourlyLeaveRequest.date.desc(), HourlyLeaveRequest.id.desc())).all()
    return [hourly_leave_out(l) for l in leaves]
