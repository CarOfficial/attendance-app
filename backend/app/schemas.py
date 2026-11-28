import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import AttendanceRecord, User
from app.timeutil import as_utc

USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,32}$")


def check_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("password must be at least 8 characters")
    # bcrypt only uses the first 72 bytes, so reject longer inputs explicitly.
    if len(v.encode("utf-8")) > 72:
        raise ValueError("password is too long (max 72 bytes)")
    return v


def normalize_username(v: str) -> str:
    v = v.strip().lower()
    if not USERNAME_PATTERN.fullmatch(v):
        raise ValueError("username must be 3-32 characters: a-z, 0-9, dot, underscore or dash")
    return v


# ---------- auth ----------

class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _valid_password(cls, v: str) -> str:
        return check_password(v)


# ---------- users ----------

class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool
    branch_ids: list[int]


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        branch_ids=[b.id for b in user.branches],
    )


class EmployeeCreate(BaseModel):
    username: str
    full_name: str = Field(min_length=2, max_length=120)
    password: str
    branch_ids: list[int] = Field(default_factory=list)

    @field_validator("username")
    @classmethod
    def _valid_username(cls, v: str) -> str:
        return normalize_username(v)

    @field_validator("password")
    @classmethod
    def _valid_password(cls, v: str) -> str:
        return check_password(v)


class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None
    branch_ids: list[int] | None = None


class ResetPasswordIn(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _valid_password(cls, v: str) -> str:
        return check_password(v)


# ---------- branches ----------

class BranchIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_m: float = Field(default=100, ge=20, le=1000)
    is_active: bool = True


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_m: float | None = Field(default=None, ge=20, le=1000)
    is_active: bool | None = None


class BranchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str | None
    latitude: float
    longitude: float
    radius_m: float
    is_active: bool


# ---------- attendance ----------

class LocationIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0, le=10_000)


class CheckoutIn(LocationIn):
    work_description: str = Field(min_length=3, max_length=1000)

    @field_validator("work_description")
    @classmethod
    def _strip_description(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("a short description of today's work is required")
        return v


class AttendanceAdminUpdate(BaseModel):
    branch_id: int | None = None
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None

    @field_validator("check_in_at", "check_out_at")
    @classmethod
    def _must_be_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("datetime must include a timezone offset")
        return v


class AttendanceManualIn(BaseModel):
    """Admin manually registers an employee's check-in (and optional check-out)."""
    user_id: int
    branch_id: int
    work_date: date | None = None
    check_in: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    check_out: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    work_description: str | None = Field(default=None, max_length=1000)


class AttendanceOut(BaseModel):
    id: int
    user_id: int
    user_full_name: str
    work_date: date
    branch_id: int
    branch_name: str
    check_in_at: datetime
    check_out_at: datetime | None
    edited_by_admin: bool
    work_description: str | None
    check_out_source: str | None
    approval_status: str
    approval_note: str | None
    hours_worked: float | None
    # Minutes late vs. the schedule (after the grace period) and overtime beyond the shift.
    late_minutes: int = 0
    overtime_minutes: int = 0
    # Approved hourly leave overlapping this record (already subtracted from hours_worked).
    hourly_leave_hours: float = 0.0
    # True when the manager recorded/changed that side of the record (used for highlighting).
    check_in_edited: bool = False
    check_out_edited: bool = False


def attendance_out(
    rec: AttendanceRecord,
    sched=None,
    hourly_leave_hours: float = 0.0,
    hourly_leaves=(),
) -> AttendanceOut:
    ci = as_utc(rec.check_in_at)
    co = as_utc(rec.check_out_at)
    hours = round((co - ci).total_seconds() / 3600, 2) if co else None
    if hours is not None and hourly_leave_hours:
        hours = round(max(0.0, hours - hourly_leave_hours), 2)
    late_minutes = 0
    overtime_minutes = 0
    if sched is not None:
        from app.services.attendance import record_metrics

        late_minutes, overtime_minutes = record_metrics(rec, sched, hourly_leaves)
    # Only the side the manager actually touched is highlighted; legacy rows fall
    # back to the old record-level flag.
    edited = {f for f in (rec.admin_edited_fields or "").split(",") if f}
    check_in_edited = ("in" in edited) if edited else rec.edited_by_admin
    check_out_edited = ("out" in edited) if edited else rec.check_out_source == "admin"
    return AttendanceOut(
        id=rec.id,
        user_id=rec.user_id,
        user_full_name=rec.user.full_name,
        work_date=rec.work_date,
        branch_id=rec.branch_id,
        branch_name=rec.branch.name,
        check_in_at=ci,
        check_out_at=co,
        edited_by_admin=rec.edited_by_admin,
        work_description=rec.work_description,
        check_out_source=rec.check_out_source,
        approval_status=rec.approval_status,
        approval_note=rec.approval_note,
        hours_worked=hours,
        late_minutes=late_minutes,
        overtime_minutes=overtime_minutes,
        hourly_leave_hours=hourly_leave_hours,
        check_in_edited=check_in_edited,
        check_out_edited=check_out_edited,
    )


class TodayOut(BaseModel):
    status: Literal["not_checked_in", "checked_in", "checked_out"]
    record: AttendanceOut | None


# ---------- leaves ----------

class LeaveIn(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=500)


class LeaveOut(BaseModel):
    id: int
    user_id: int
    user_full_name: str
    start_date: date
    end_date: date
    reason: str
    status: str
    created_at: datetime
    decided_at: datetime | None
    decision_note: str | None


def leave_out(leave) -> LeaveOut:
    return LeaveOut(
        id=leave.id,
        user_id=leave.user_id,
        user_full_name=leave.user.full_name,
        start_date=leave.start_date,
        end_date=leave.end_date,
        reason=leave.reason,
        status=leave.status,
        created_at=as_utc(leave.created_at),
        decided_at=as_utc(leave.decided_at),
        decision_note=leave.decision_note,
    )


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=255)


class DecisionLeaveIn(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=255)

class HourlyLeaveIn(BaseModel):
    """Hourly leave for one day, e.g. 10:00 to 12:30 (start_hour/end_hour are decimal hours)."""

    # Required only when an admin files the request for someone else.
    user_id: int | None = None
    date: date
    start_hour: float = Field(ge=0, le=24)
    end_hour: float = Field(ge=0, le=24)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("end_hour")
    @classmethod
    def _end_after_start(cls, v: float, info) -> float:
        start = info.data.get("start_hour")
        if start is not None and v <= start:
            raise ValueError("end_hour must be after start_hour")
        return v

    model_config = {"from_attributes": True}

class HourlyLeaveOut(BaseModel):
    id: int
    user_id: int
    user_full_name: str
    date: date
    start_hour: float
    end_hour: float
    reason: str
    status: str
    created_at: datetime
    decided_at: datetime | None
    decided_by: int | None
    decision_note: str | None

    model_config = {"from_attributes": True}

def hourly_leave_out(leave) -> HourlyLeaveOut:
    return HourlyLeaveOut(
        id=leave.id,
        user_id=leave.user_id,
        user_full_name=leave.user.full_name,
        date=leave.date,
        start_hour=leave.start_hour,
        end_hour=leave.end_hour,
        reason=leave.reason,
        status=leave.status,
        created_at=as_utc(leave.created_at),
        decided_at=as_utc(leave.decided_at),
        decided_by=leave.decided_by,
        decision_note=leave.decision_note,
    )


# ---------- forgotten check-out ----------

class LateCheckoutIn(BaseModel):
    work_date: date
    check_out_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0, le=10_000)
    description: str = Field(min_length=3, max_length=1000)


class LateCheckoutOut(BaseModel):
    id: int
    user_id: int
    user_full_name: str
    work_date: date
    record_id: int
    requested_at: datetime
    check_out_at: datetime
    description: str
    status: str
    branch_name: str
    distance_m: float
    decided_at: datetime | None
    decision_note: str | None
    submission_deadline: datetime
    decision_deadline: datetime


def late_checkout_out(req) -> LateCheckoutOut:
    from app.services.attendance import late_decision_deadline, late_submission_deadline

    return LateCheckoutOut(
        id=req.id,
        user_id=req.user_id,
        user_full_name=req.user.full_name,
        work_date=req.work_date,
        record_id=req.record_id,
        requested_at=as_utc(req.requested_at),
        check_out_at=as_utc(req.check_out_at),
        description=req.description,
        status=req.status,
        branch_name=req.branch.name,
        distance_m=req.distance_m,
        decided_at=as_utc(req.decided_at),
        decision_note=req.decision_note,
        submission_deadline=late_submission_deadline(req.work_date),
        decision_deadline=late_decision_deadline(req),
    )


# ---------- work schedule / weekly view ----------

class ScheduleIn(BaseModel):
    work_days: list[int]
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    late_grace_minutes: int = Field(default=15, ge=0, le=180)

    @field_validator("work_days")
    @classmethod
    def _valid_days(cls, v: list[int]) -> list[int]:
        days = sorted(set(v))
        if not days or any(d < 0 or d > 6 for d in days):
            raise ValueError("work_days must contain weekday numbers 0-6 (0=Monday)")
        if days == [4]:
            raise ValueError("at least one working day other than Friday is required")
        return days

    @field_validator("end_time")
    @classmethod
    def _after_start(cls, v: str, info) -> str:
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v


class ScheduleOut(BaseModel):
    work_days: list[int]
    start_time: str
    end_time: str
    late_grace_minutes: int
    updated_at: datetime | None


class DayStateOut(BaseModel):
    date: date
    is_work_day: bool
    status: str
    check_in_at: datetime | None
    check_out_at: datetime | None
    hours_worked: float | None
    branch_name: str | None
    work_description: str | None
    approval_status: str
    approval_note: str | None
    late_request_status: str | None
    pending_leave: bool
    is_late: bool
    left_early: bool
    # Approved hourly leave on this day and the minutes of overtime / lateness.
    hourly_leave_hours: float = 0.0
    late_minutes: int = 0
    overtime_minutes: int = 0
    # The employee's explanation for an absent day, when they filed one.
    absence_reason: str | None = None


class WeekOut(BaseModel):
    start: date
    end: date
    days: list[DayStateOut]
    schedule: ScheduleOut


class DashboardOut(BaseModel):
    date: str
    active_employees: int = 0
    present_today: int = 0
    absent_today: int = 0
    leave_today: int = 0
    rejected_today: int = 0
    open_check_ins: int = 0
    pending_leaves: int = 0
    pending_late_checkouts: int = 0
    pending_hourly_leaves: int = 0
    schedule: ScheduleOut


class SummaryOut(BaseModel):
    user_id: int
    user_full_name: str
    from_date: date
    to_date: date
    days: list[DayStateOut]
    totals: dict


# ---------- absence reasons ----------

class AbsenceReasonIn(BaseModel):
    date: date
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("reason is too short")
        return v


class AbsenceReasonOut(BaseModel):
    id: int
    user_id: int
    date: date
    reason: str
    created_at: datetime


def absence_reason_out(row) -> AbsenceReasonOut:
    return AbsenceReasonOut(
        id=row.id,
        user_id=row.user_id,
        date=row.date,
        reason=row.reason,
        created_at=as_utc(row.created_at),
    )
