import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (registers tables)
from app.config import settings, validate_settings
from app.db import Base, SessionLocal, engine
from app.migrate import upgrade_sqlite_schema
from app.models import ROLE_ADMIN, User
from app.routers import admin, admin_requests, attendance, auth, leaves
from app.routers import export as export_router
from app.security import hash_password
from app.services.schedule import get_schedule


def bootstrap_admin(db: Session) -> None:
    """Create the first admin from env vars if none exists. Forces a password change on first login."""
    if db.scalar(select(User.id).where(User.role == ROLE_ADMIN)) is not None:
        return
    if not settings.admin_bootstrap_password:
        return
    db.add(
        User(
            username=settings.admin_bootstrap_username.strip().lower(),
            full_name="Administrator",
            role=ROLE_ADMIN,
            password_hash=hash_password(settings.admin_bootstrap_password),
            must_change_password=True,
        )
    )
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_settings(settings)
    # For production, replace this with Alembic migrations.
    Base.metadata.create_all(bind=engine)
    upgrade_sqlite_schema(engine)
    with SessionLocal() as db:
        bootstrap_admin(db)
        get_schedule(db)  # ensure the default work schedule row exists
    yield


app = FastAPI(title="Attendance API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(admin_requests.router, prefix=API_PREFIX)
app.include_router(attendance.router, prefix=API_PREFIX)
app.include_router(leaves.router, prefix=API_PREFIX)
app.include_router(export_router.router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


# ---------- admin web panel (prebuilt static files) ----------
# Serving the built panel from the same origin as the API keeps the browser
# calls to /api/v1 same-origin, so no CORS or extra port is needed.
_web_dir = Path(os.getenv("WEB_DIR") or Path(__file__).resolve().parents[2] / "admin" / "dist")

if (_web_dir / "index.html").is_file():
    if (_web_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_web_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    def spa(full_path: str):
        # Never let the SPA answer for the API surface.
        if full_path == "api" or full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = (_web_dir / full_path).resolve()
        if full_path and candidate.is_file() and _web_dir.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_web_dir / "index.html")
