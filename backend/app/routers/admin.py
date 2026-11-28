from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_admin_user
from app.models import (
    ROLE_EMPLOYEE,
    STATUS_APPROVED,
    AttendanceRecord,
    Branch,
    HourlyLeaveRequest,
    LateCheckoutRequest,
    LeaveRequest,
    User,
    employee_branches,
)
from app.schemas import (
    AttendanceAdminUpdate,
    AttendanceManualIn,
    AttendanceOut,
    BranchIn,
    BranchOut,
    BranchUpdate,
    DecisionLeaveIn,
    EmployeeCreate,
    EmployeeUpdate,
    HourlyLeaveIn,
    HourlyLeaveOut,
    ResetPasswordIn,
    UserOut,
    attendance_out,
    user_out,
)
from app.security import hash_password
from app.services.attendance import (
    admin_manual_record,
    admin_update_record,
    hourly_leave_hours_for_record,
)
from app.services.leave import create_hourly_leave, decide_hourly_leave, list_hourly_leaves
from app.services.schedule import get_schedule
from app.timeutil import local_date, utcnow

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_admin_user)])


# ---------- helpers ----------

def _get_employee(db: Session, user_id: int) -> User:
    user = db.scalar(select(User).where(User.id == user_id, User.role == ROLE_EMPLOYEE))
    if user is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return user


def _load_branches(db: Session, ids: list[int]) -> list[Branch]:
    ids = sorted(set(ids))
    if not ids:
        return []
    branches = list(db.scalars(select(Branch).where(Branch.id.in_(ids))))
    if len(branches) != len(ids):
        raise HTTPException(status_code=422, detail="One or more branch ids are invalid")
    return branches


# ---------- employees ----------

@router.get("/employees", response_model=list[UserOut])
def list_employees(
    include_inactive: bool = True,
    db: Session = Depends(get_db),
) -> list[UserOut]:
    q = select(User).where(User.role == ROLE_EMPLOYEE).order_by(User.full_name)
    if not include_inactive:
        q = q.where(User.is_active.is_(True))
    return [user_out(u) for u in db.scalars(q)]


@router.post("/employees", response_model=UserOut, status_code=201)
def create_employee(body: EmployeeCreate, db: Session = Depends(get_db)) -> UserOut:
    user = User(
        username=body.username,
        full_name=body.full_name,
        role=ROLE_EMPLOYEE,
        password_hash=hash_password(body.password),
        must_change_password=True,
    )
    user.branches = _load_branches(db, body.branch_ids)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")
    return user_out(user)


@router.get("/employees/{user_id}", response_model=UserOut)
def get_employee(user_id: int, db: Session = Depends(get_db)) -> UserOut:
    return user_out(_get_employee(db, user_id))


@router.patch("/employees/{user_id}", response_model=UserOut)
def update_employee(user_id: int, body: EmployeeUpdate, db: Session = Depends(get_db)) -> UserOut:
    user = _get_employee(db, user_id)
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        if not body.is_active and user.is_active:
            user.token_version += 1  # kick out existing sessions
        user.is_active = body.is_active
    if body.branch_ids is not None:
        user.branches = _load_branches(db, body.branch_ids)
    db.commit()
    return user_out(user)


@router.delete("/employees/{user_id}", status_code=204, response_class=Response)
def delete_employee(
    user_id: int, force: bool = False, db: Session = Depends(get_db)
) -> Response:
    """Deletes an employee account. With force=true their attendance/leave history goes too."""
    user = _get_employee(db, user_id)
    records = db.scalar(
        select(func.count()).select_from(AttendanceRecord).where(AttendanceRecord.user_id == user_id)
    ) or 0
    leaves = db.scalar(
        select(func.count()).select_from(LeaveRequest).where(LeaveRequest.user_id == user_id)
    ) or 0
    if (records or leaves) and not force:
        raise HTTPException(
            status_code=409,
            detail="Employee has attendance or leave history; pass force=true to delete it",
        )
    # Decisions this user made on other people's records must not keep a dangling reference.
    db.execute(update(AttendanceRecord).where(AttendanceRecord.approval_by == user_id).values(approval_by=None))
    db.execute(update(LeaveRequest).where(LeaveRequest.decided_by == user_id).values(decided_by=None))
    db.execute(
        update(LateCheckoutRequest).where(LateCheckoutRequest.decided_by == user_id).values(decided_by=None)
    )
    db.execute(delete(LateCheckoutRequest).where(LateCheckoutRequest.user_id == user_id))
    db.execute(delete(LeaveRequest).where(LeaveRequest.user_id == user_id))
    db.execute(delete(AttendanceRecord).where(AttendanceRecord.user_id == user_id))
    # The secondary (employee_branches) rows are deleted by the ORM together with the user.
    db.delete(user)
    db.commit()
    return Response(status_code=204)


@router.post("/employees/{user_id}/reset-password", status_code=204, response_class=Response)
def reset_employee_password(
    user_id: int, body: ResetPasswordIn, db: Session = Depends(get_db)
) -> Response:
    user = _get_employee(db, user_id)
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = True
    user.token_version += 1
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    return Response(status_code=204)


# ---------- branches ----------

@router.get("/branches", response_model=list[BranchOut])
def list_branches(db: Session = Depends(get_db)) -> list[Branch]:
    return list(db.scalars(select(Branch).order_by(Branch.name)))


@router.post("/branches", response_model=BranchOut, status_code=201)
def create_branch(body: BranchIn, db: Session = Depends(get_db)) -> Branch:
    branch = Branch(**body.model_dump())
    db.add(branch)
    db.commit()
    return branch


@router.delete("/branches/{branch_id}", status_code=204, response_class=Response)
def delete_branch(branch_id: int, force: bool = False, db: Session = Depends(get_db)) -> Response:
    """Deletes a branch. With force=true its attendance history is deleted too."""
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    records = db.scalar(
        select(func.count()).select_from(AttendanceRecord).where(AttendanceRecord.branch_id == branch_id)
    ) or 0
    if records and not force:
        raise HTTPException(
            status_code=409,
            detail="Branch has attendance records; pass force=true to delete them",
        )
    db.execute(delete(LateCheckoutRequest).where(LateCheckoutRequest.branch_id == branch_id))
    db.execute(delete(AttendanceRecord).where(AttendanceRecord.branch_id == branch_id))
    db.execute(delete(employee_branches).where(employee_branches.c.branch_id == branch_id))
    db.delete(branch)
    db.commit()
    return Response(status_code=204)


@router.patch("/branches/{branch_id}", response_model=BranchOut)
def update_branch(branch_id: int, body: BranchUpdate, db: Session = Depends(get_db)) -> Branch:
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(branch, field, value)
    db.commit()
    return branch


# ---------- attendance ----------

@router.get("/attendance", response_model=list[AttendanceOut])
def list_attendance(
    from_date: date | None = None,
    to_date: date | None = None,
    user_id: int | None = None,
    branch_id: int | None = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[AttendanceOut]:
    q = select(AttendanceRecord).order_by(AttendanceRecord.work_date.desc(), AttendanceRecord.id.desc())
    if from_date:
        q = q.where(AttendanceRecord.work_date >= from_date)
    if to_date:
        q = q.where(AttendanceRecord.work_date <= to_date)
    if user_id:
        q = q.where(AttendanceRecord.user_id == user_id)
    if branch_id:
        q = q.where(AttendanceRecord.branch_id == branch_id)
    records = list(db.scalars(q.limit(limit).offset(offset)))
    sched = get_schedule(db)
    grouped: dict[tuple[int, date], list] = {}
    if records:
        days = [r.work_date for r in records]
        leaves = db.scalars(
            select(HourlyLeaveRequest).where(
                HourlyLeaveRequest.user_id.in_({r.user_id for r in records}),
                HourlyLeaveRequest.status == STATUS_APPROVED,
                HourlyLeaveRequest.date >= min(days),
                HourlyLeaveRequest.date <= max(days),
            )
        )
        for leave in leaves:
            grouped.setdefault((leave.user_id, leave.date), []).append(leave)
    return [
        attendance_out(
            r,
            sched,
            hourly_leave_hours_for_record(r, grouped.get((r.user_id, r.work_date), [])),
            grouped.get((r.user_id, r.work_date), []),
        )
        for r in records
    ]


@router.patch("/attendance/{record_id}", response_model=AttendanceOut)
def update_attendance(
    record_id: int, body: AttendanceAdminUpdate, db: Session = Depends(get_db)
) -> AttendanceOut:
    rec = db.get(AttendanceRecord, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    rec = admin_update_record(
        db,
        rec,
        branch_id=body.branch_id,
        check_in_at=body.check_in_at,
        check_out_at=body.check_out_at,
    )
    return attendance_out(rec, get_schedule(db))


@router.delete("/attendance/{record_id}", status_code=204, response_class=Response)
def delete_attendance(record_id: int, db: Session = Depends(get_db)) -> Response:
    rec = db.get(AttendanceRecord, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    db.execute(delete(LateCheckoutRequest).where(LateCheckoutRequest.record_id == record_id))
    db.delete(rec)
    db.commit()
    return Response(status_code=204)


# ---------- manual attendance (admin records check-in/check-out for an employee) ----------

@router.post("/attendance/manual", response_model=AttendanceOut)
def admin_manual_attendance(
    body: AttendanceManualIn, db: Session = Depends(get_db)
) -> AttendanceOut:
    """Admin registers (or updates) an employee's check-in and optional check-out."""
    rec = admin_manual_record(
        db,
        user_id=body.user_id,
        branch_id=body.branch_id,
        work_date=body.work_date,
        check_in=body.check_in,
        check_out=body.check_out,
        work_description=body.work_description,
    )
    return attendance_out(rec, get_schedule(db))


# ---------- hourly leaves ----------

@router.post("/hourly-leaves", response_model=HourlyLeaveOut, status_code=201)
def create_hourly_leave_request(
    body: HourlyLeaveIn, db: Session = Depends(get_db)
) -> HourlyLeaveOut:
    """The manager files an hourly leave on behalf of an employee."""
    if body.user_id is None:
        raise HTTPException(status_code=422, detail="user_id is required")
    return create_hourly_leave(
        db,
        user_id=body.user_id,
        day=body.date,
        start_hour=body.start_hour,
        end_hour=body.end_hour,
        reason=body.reason,
    )


@router.get("/hourly-leaves", response_model=list[HourlyLeaveOut])
def list_hourly_leave_requests(
    user_id: int | None = Query(default=None),
    date: date | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[HourlyLeaveOut]:
    return list_hourly_leaves(db, user_id, date, status)


@router.patch("/hourly-leaves/{leave_id}", response_model=HourlyLeaveOut)
def decide_hourly_leave_request(
    leave_id: int,
    body: DecisionLeaveIn,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> HourlyLeaveOut:
    return decide_hourly_leave(db, admin, leave_id, body.decision, body.note)


# ---------- dashboard ----------

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict:
    from app.models import (
        STATUS_APPROVED,
        STATUS_PENDING,
        LateCheckoutRequest,
        LeaveRequest,
    )
    from app.services.attendance import refresh_expired_late_requests

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
    from app.models import HourlyLeaveRequest

    pending_hourly = db.scalar(
        select(func.count()).select_from(HourlyLeaveRequest).where(
            HourlyLeaveRequest.status == STATUS_PENDING
        )
    ) or 0
    return {
        "date": today.isoformat(),
        "active_employees": active,
        "present_today": present,
        "absent_today": max(active - present - leave_today, 0),
        "leave_today": leave_today,
        "rejected_today": rejected_today,
        "open_check_ins": open_now,
        "pending_leaves": pending_leaves,
        "pending_late_checkouts": pending_late,
        "pending_hourly_leaves": pending_hourly,
    }
