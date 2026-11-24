"""Excel (xlsx) exports.

The workbook mirrors the admin "گزارش و ساعات کاری" table: one row per day, with the
same columns the report page shows. A single-employee export is that table for one
person; the team export puts one such sheet per employee, each with the full daily
detail (no weekly or aggregated sheets).
"""

from datetime import date
from io import BytesIO

import jdatetime
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ROLE_EMPLOYEE, User
from app.services.attendance import day_states, refresh_expired_late_requests
from app.services.schedule import get_schedule
from app.timeutil import as_utc, local_tz

DAY_NAMES = {
    0: "دوشنبه",
    1: "سه‌شنبه",
    2: "چهارشنبه",
    3: "پنجشنبه",
    4: "جمعه",
    5: "شنبه",
    6: "یکشنبه",
}

STATUS_LABELS = {
    "present": "حاضر",
    "working": "در حال کار",
    "absent": "غایب",
    "incomplete": "غایب - خروج ثبت نشده",
    "rejected": "رد شده توسط مدیر",
    "leave": "مرخصی",
    "pending_checkout": "در انتظار تایید خروج",
    "non_working": "غیرکاری",
    "future": "پیش رو",
}

APPROVAL_LABELS = {"none": "-", "approved": "تایید شد", "rejected": "رد شد"}

# Same columns, in the same order, as the report table in the admin panel.
DETAIL_HEADERS = [
    "تاریخ شمسی",
    "روز",
    "وضعیت",
    "ورود",
    "خروج",
    "ساعت کاری",
    "تاخیر",
    "خروج زودتر",
    "شرح کار",
    "وضعیت تایید",
]

DETAIL_WIDTHS = [12, 11, 26, 10, 10, 11, 9, 12, 48, 26]

HEADER_FILL = PatternFill("solid", fgColor="7E22CE")
TITLE_FILL = PatternFill("solid", fgColor="4C1D95")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
TITLE_FONT = Font(bold=True, color="FFFFFF", size=12)
ALT_FILL = PatternFill("solid", fgColor="F5F1FF")
THIN = Side(style="thin", color="D8B4FE")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
INVALID_SHEET_CHARS = set('[]:*?/\\')


def _jalali_str(d: date) -> str:
    return jdatetime.date.fromgregorian(date=d).strftime("%Y/%m/%d")


def datetime_from_iso(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value)


def _local_hhmm(iso: str | None) -> str:
    if not iso:
        return "-"
    dt = as_utc(datetime_from_iso(iso)).astimezone(local_tz())
    return dt.strftime("%H:%M")


def _status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def _approval_label(state: dict) -> str:
    """Manager decision, plus their note when one was left (the table shows both)."""
    approved = APPROVAL_LABELS.get(state["approval_status"], state["approval_status"])
    note = state.get("approval_note")
    return f"{approved} — یادداشت: {note}" if note else approved


def _daily_rows(states: list[dict]) -> list[list]:
    rows = []
    for s in states:
        d = date.fromisoformat(s["date"])
        status = _status_label(s["status"])
        if s.get("pending_leave"):
            status += " (مرخصی در انتظار تایید)"
        rows.append(
            [
                _jalali_str(d),
                DAY_NAMES.get(d.weekday(), ""),
                status,
                _local_hhmm(s["check_in_at"]),
                _local_hhmm(s["check_out_at"]),
                s["hours_worked"] if s["hours_worked"] is not None else "-",
                "بله" if s["is_late"] else "-",
                "بله" if s["left_early"] else "-",
                s["work_description"] or "-",
                _approval_label(s),
            ]
        )
    return rows


def _sheet_name(text: str, used: set[str]) -> str:
    base = "".join(ch for ch in text if ch not in INVALID_SHEET_CHARS).strip() or "کارمند"
    name = base[:31]
    counter = 2
    while name in used:
        suffix = f" ({counter})"
        name = base[: 31 - len(suffix)] + suffix
        counter += 1
    used.add(name)
    return name


def _fill_detail_sheet(ws, title: str, rows: list[list]) -> None:
    ws.sheet_view.rightToLeft = True

    last_col = get_column_letter(len(DETAIL_HEADERS))
    ws.merge_cells(f"A1:{last_col}1")
    title_cell = ws["A1"]
    title_cell.value = title
    title_cell.font = TITLE_FONT
    title_cell.fill = TITLE_FILL
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24

    ws.append(DETAIL_HEADERS)
    for row in rows:
        ws.append(row)

    header_row = 2
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    ws.auto_filter.ref = f"A{header_row}:{last_col}{max(ws.max_row, header_row)}"

    for cell in ws[header_row]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER

    for i, width in enumerate(DETAIL_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    for r in range(header_row + 1, ws.max_row + 1):
        for cell in ws[r]:
            cell.border = BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        hours = ws.cell(row=r, column=6)
        hours.number_format = "0.00"
        hours.alignment = Alignment(horizontal="center", vertical="center")
        if r % 2 == 0:
            for cell in ws[r]:
                cell.fill = ALT_FILL


def build_workbook(
    db: Session,
    user_id: int | None,
    start: date,
    end: date,
) -> bytes:
    """Daily report for one employee, or one sheet per employee for the whole team."""
    refresh_expired_late_requests(db)
    sched = get_schedule(db)

    if user_id is not None:
        user = db.get(User, user_id)
        if user is None:
            raise LookupError("user not found")
        users = [user]
    else:
        users = list(
            db.scalars(
                select(User)
                .where(User.role == ROLE_EMPLOYEE, User.is_active.is_(True))
                .order_by(User.full_name)
            )
        )

    wb = Workbook()
    # The default empty sheet is not part of the report.
    wb.remove(wb.active)

    if not users:
        ws = wb.create_sheet("گزارش")
        ws.sheet_view.rightToLeft = True
        ws["A1"] = "در این بازه کارمندی برای گزارش وجود ندارد"
        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    range_text = f"{_jalali_str(start)} تا {_jalali_str(end)}"
    used_names: set[str] = set()

    for u in users:
        states = day_states(db, u.id, start, end, sched=sched, refresh=False)
        sheet_name = "گزارش روزانه" if user_id is not None else _sheet_name(u.full_name or u.username, used_names)
        ws = wb.create_sheet(sheet_name)
        _fill_detail_sheet(
            ws,
            f"{u.full_name} ({u.username}) — {range_text}",
            _daily_rows(states),
        )

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
