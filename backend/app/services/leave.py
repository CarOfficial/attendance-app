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
