import json

from sqlalchemy.orm import Session

from app.models import WorkSchedule
from app.timeutil import as_utc

# Saturday..Wednesday (Python weekdays: Mon=0 .. Sun=6; Saturday=5).
DEFAULT_WORK_DAYS = [5, 6, 0, 1, 2]


def get_schedule(db: Session) -> WorkSchedule:
    """Return the single company-wide schedule row, creating it with defaults if missing."""
    sched = db.get(WorkSchedule, 1)
    if sched is None:
        sched = WorkSchedule(id=1)
        db.add(sched)
        db.commit()
        db.refresh(sched)
    return sched


def work_days(sched: WorkSchedule) -> set[int]:
    try:
        days = {int(x) for x in json.loads(sched.work_days)}
    except (ValueError, TypeError, json.JSONDecodeError):
        days = set(DEFAULT_WORK_DAYS)
    days &= set(range(7))
    return days or set(DEFAULT_WORK_DAYS)


def is_work_day(sched: WorkSchedule, d) -> bool:
    return d.weekday() in work_days(sched)


def schedule_out(sched: WorkSchedule) -> dict:
    updated = as_utc(sched.updated_at)
    return {
        "work_days": sorted(work_days(sched)),
        "start_time": sched.start_time,
        "end_time": sched.end_time,
        "late_grace_minutes": sched.late_grace_minutes,
        "updated_at": updated.isoformat() if updated else None,
    }
