from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_admin_user
from app.services.export import build_workbook
from app.timeutil import local_date, utcnow

router = APIRouter(
    prefix="/admin/export",
    tags=["export"],
    dependencies=[Depends(get_admin_user)],
)

MAX_RANGE_DAYS = 400
MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/excel")
def export_excel(
    user_id: int | None = Query(default=None, description="Export a single employee"),
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
) -> Response:
    today = local_date(utcnow())
    first = from_date or (today - timedelta(days=30))
    last = to_date or today
    if first > last:
        raise HTTPException(status_code=422, detail="from_date must be before to_date")
    if (last - first).days > MAX_RANGE_DAYS:
        raise HTTPException(status_code=422, detail=f"Date range too large (max {MAX_RANGE_DAYS} days)")

    try:
        data = build_workbook(db, user_id, first, last)
    except LookupError:
        raise HTTPException(status_code=404, detail="Employee not found")

    name = f"attendance-{user_id}" if user_id else "attendance-all"
    return Response(
        content=data,
        media_type=MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{name}-{first.isoformat()}-{last.isoformat()}.xlsx"'},
    )
