from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_ready_user
from app.models import LeaveRequest, User
from app.schemas import LeaveIn, LeaveOut, leave_out
from app.services.leave import create_leave

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
