import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ROLE_ADMIN, User
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="Invalid or expired token",
                         headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Any authenticated, active user. Allowed even if a password change is pending."""
    if creds is None:
        raise _unauthorized()
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _unauthorized()

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.token_version != payload.get("tv"):
        raise _unauthorized()
    return user


def get_ready_user(user: User = Depends(get_current_user)) -> User:
    """Active user who has already replaced their initial password."""
    if user.must_change_password:
        raise HTTPException(
            status_code=403,
            detail="Password change required",
            headers={"X-Password-Change-Required": "1"},
        )
    return user


def get_admin_user(user: User = Depends(get_ready_user)) -> User:
    if user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    return user
