from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.config import settings


def local_tz() -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def local_now() -> datetime:
    return utcnow().astimezone(local_tz())


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on read; treat naive values as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def local_date(dt: datetime) -> date:
    return as_utc(dt).astimezone(local_tz()).date()


def parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def at_local(d: date, hhmm: str) -> datetime:
    """Aware local datetime for a date + 'HH:MM' wall time."""
    return datetime.combine(d, parse_hhmm(hhmm), tzinfo=local_tz())


def end_of_local_day(d: date) -> datetime:
    return datetime.combine(d, time(23, 59, 59, 999999), tzinfo=local_tz())
