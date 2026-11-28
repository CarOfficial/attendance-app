from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.timeutil import utcnow

ROLE_ADMIN = "admin"
ROLE_EMPLOYEE = "employee"

employee_branches = Table(
    "employee_branches",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("branch_id", ForeignKey("branches.id"), primary_key=True),
)


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    radius_m: Mapped[float] = mapped_column(Float, default=100.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Stored lowercase; unique index makes usernames unique case-insensitively.
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default=ROLE_EMPLOYEE)
    password_hash: Mapped[str] = mapped_column(String(255))
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Bumped on password change/reset or deactivation to revoke issued tokens.
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    branches: Mapped[list[Branch]] = relationship(secondary=employee_branches, lazy="selectin")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("user_id", "work_date", name="uq_attendance_user_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    work_date: Mapped[date] = mapped_column(Date, index=True)

    check_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    check_in_lat: Mapped[float] = mapped_column(Float)
    check_in_lng: Mapped[float] = mapped_column(Float)
    check_in_accuracy_m: Mapped[float] = mapped_column(Float)
    check_in_distance_m: Mapped[float] = mapped_column(Float)

    check_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_out_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_out_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_out_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Who recorded the check-out: "employee" | "late" (forgotten checkout) | "admin"
    check_out_source: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Daily report written by the employee when checking out.
    work_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # "none" = no decision needed (normal same-day record), "approved"/"rejected" = manager decision.
    approval_status: Mapped[str] = mapped_column(String(20), default="none")
    approval_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approval_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    edited_by_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    # Which sides the manager recorded/changed: "in", "out" or "in,out".
    admin_edited_fields: Mapped[str | None] = mapped_column(String(20), nullable=True)

    branch: Mapped[Branch] = relationship(lazy="joined")
    user: Mapped[User] = relationship(lazy="joined", foreign_keys=[user_id])


# Request statuses (leaves and forgotten check-outs share the same vocabulary).
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_EXPIRED = "expired"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(lazy="joined", foreign_keys=[user_id])


class LateCheckoutRequest(Base):
    """The employee forgot to check out: they come back to the location within 24h
    and request yesterday's check-out. The manager must approve it, otherwise the
    day is recorded as absent."""

    __tablename__ = "late_checkout_requests"
    __table_args__ = (UniqueConstraint("user_id", "work_date", name="uq_late_checkout_user_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("attendance_records.id"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))

    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Check-out time the employee claims for the previous day.
    check_out_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy_m: Mapped[float] = mapped_column(Float)
    distance_m: Mapped[float] = mapped_column(Float)

    description: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(lazy="joined", foreign_keys=[user_id])
    record: Mapped[AttendanceRecord] = relationship(lazy="joined")
    branch: Mapped[Branch] = relationship(lazy="joined")


class WorkSchedule(Base):
    """Company-wide official work days and hours (single row, id=1)."""

    __tablename__ = "work_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # JSON array of Python weekdays (0=Monday … 6=Sunday). Default: Saturday..Wednesday.
    work_days: Mapped[str] = mapped_column(String(128), default="[5,6,0,1,2]")
    start_time: Mapped[str] = mapped_column(String(5), default="08:00")  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5), default="17:00")  # HH:MM
    late_grace_minutes: Mapped[int] = mapped_column(Integer, default=15)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HourlyLeaveRequest(Base):
    """Hourly leave request for a specific date range (start_hour to end_hour)."""
    __tablename__ = "hourly_leaves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    start_hour: Mapped[float] = mapped_column(Float)
    end_hour: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(lazy="joined", foreign_keys=[user_id])


class AbsenceReason(Base):
    """The employee explains why they were absent on a working day."""

    __tablename__ = "absence_reasons"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_absence_user_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(lazy="joined", foreign_keys=[user_id])
