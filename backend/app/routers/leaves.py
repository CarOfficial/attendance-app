from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_ready_user
from app.models import LeaveRequest, User
from app.schemas import HourlyLeaveIn, HourlyLeaveOut, LeaveIn, LeaveOut, leave_out
from app.services.leave import create_hourly_leave, create_leave, list_hourly_leaves

router = APIRouter(prefix="/leaves", tags=["leaves"])


@router.post("", response_model=LeaveOut, status_code=201)
def request_leave(
    body: LeaveIn,
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> LeaveOut:
    leave = create_leave(db, user, body.start_date, body.end_date, body.reason)
    return leave_out(leave)


@router.get("/mine", response_model=list[LeaveOut])
def my_leaves(
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> list[LeaveOut]:
    leaves = db.scalars(
        select(LeaveRequest)
        .where(LeaveRequest.user_id == user.id)
        .order_by(LeaveRequest.start_date.desc(), LeaveRequest.id.desc())
    )
    return [leave_out(l) for l in leaves]


# ---------- hourly leave (a few hours off, needs the manager's approval) ----------


@router.post("/hourly", response_model=HourlyLeaveOut, status_code=201)
def request_hourly_leave(
    body: HourlyLeaveIn,
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> HourlyLeaveOut:
    """Files an hourly leave for the signed-in employee (any user_id in the body is ignored)."""
    return create_hourly_leave(
        db,
        user_id=user.id,
        day=body.date,
        start_hour=body.start_hour,
        end_hour=body.end_hour,
        reason=body.reason,
    )


@router.get("/hourly/mine", response_model=list[HourlyLeaveOut])
def my_hourly_leaves(
    user: User = Depends(get_ready_user),
    db: Session = Depends(get_db),
) -> list[HourlyLeaveOut]:
    return list_hourly_leaves(db, user_id=user.id)
