from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import ChangePasswordIn, LoginIn, TokenOut, UserOut, user_out
from app.security import create_access_token, hash_password, verify_password
from app.timeutil import as_utc, utcnow

router = APIRouter(prefix="/auth", tags=["auth"])


def _register_failed_attempt(db: Session, user: User) -> None:
    user.failed_login_count += 1
    if user.failed_login_count >= settings.max_failed_logins:
        user.locked_until = utcnow() + timedelta(minutes=settings.lockout_minutes)
        user.failed_login_count = 0
    db.commit()


def _token_for(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id, user.role, user.token_version),
        must_change_password=user.must_change_password,
    )


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    username = body.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username))
    now = utcnow()

    if user is not None and as_utc(user.locked_until) and as_utc(user.locked_until) > now:
        raise HTTPException(status_code=429, detail="Account temporarily locked. Try again later.")

    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        if user is not None and user.is_active:
            _register_failed_attempt(db, user)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    return _token_for(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return user_out(user)


@router.post("/change-password", response_model=TokenOut)
def change_password(
    body: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenOut:
    # Allowed while must_change_password is True, so this is the only way out of that state.
    if not verify_password(body.current_password, user.password_hash):
        _register_failed_attempt(db, user)
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(body.new_password, user.password_hash):
        raise HTTPException(status_code=422, detail="New password must be different from the current one")

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.token_version += 1  # revoke all previously issued tokens
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    return _token_for(user)  # fresh token so the current session keeps working
