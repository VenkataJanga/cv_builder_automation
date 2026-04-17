from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.config.settings import settings
from src.core.constants import (
    DEV_EMAIL,
    DEV_FULL_NAME,
    DEV_USER_ID,
    DEV_USERNAME,
    ERR_INVALID_TOKEN_PAYLOAD,
    ERR_NOT_AUTHENTICATED,
    ERR_USER_NOT_FOUND_OR_INACTIVE,
    JWT_USER_ID_CLAIM,
    WWW_AUTHENTICATE_BEARER,
    WWW_AUTHENTICATE_HEADER,
)
from src.core.security.current_user import CurrentUser
from src.core.security.oauth2 import oauth2_scheme
from src.core.security.permissions import Permission
from src.core.security.roles import Role
from src.core.security.token_validator import decode_access_token
from src.infrastructure.persistence.mysql.database import get_db
from src.infrastructure.persistence.mysql.repositories.auth_repository import AuthRepository


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """
    Core FastAPI dependency — extracts and validates the bearer token,
    loads the user from the database, and returns a `CurrentUser`.

    When ENABLE_RBAC is False the check is bypassed and an anonymous
    user is returned so the application works without auth in dev mode.
    """
    if not settings.ENABLE_RBAC:
        # Dev / local mode: return a synthetic admin user
        return CurrentUser(
            user_id=DEV_USER_ID,
            username=DEV_USERNAME,
            email=DEV_EMAIL,
            full_name=DEV_FULL_NAME,
            role=Role.ADMIN,
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERR_NOT_AUTHENTICATED,
            headers={WWW_AUTHENTICATE_HEADER: WWW_AUTHENTICATE_BEARER},
        )

    payload = decode_access_token(token)
    user_id: int | None = payload.get(JWT_USER_ID_CLAIM)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERR_INVALID_TOKEN_PAYLOAD,
            headers={WWW_AUTHENTICATE_HEADER: WWW_AUTHENTICATE_BEARER},
        )

    repo = AuthRepository(db)
    user = repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERR_USER_NOT_FOUND_OR_INACTIVE,
            headers={WWW_AUTHENTICATE_HEADER: WWW_AUTHENTICATE_BEARER},
        )

    return CurrentUser(
        user_id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


def require_role(*roles: Role) -> Callable:
    """
    Dependency factory — raises HTTP 403 if the current user's role
    is not in the given list.

    Usage::

        @router.get("/admin", dependencies=[Depends(require_role(Role.ADMIN))])
    """
    def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role(s): {[r.value for r in roles]}",
            )
        return current_user

    return _check


def require_permission(permission: Permission) -> Callable:
    """
    Dependency factory — raises HTTP 403 if the current user does not
    have the requested permission.

    Usage::

        @router.post("/cv", dependencies=[Depends(require_permission(Permission.CREATE_CV))])
    """
    def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission.value}",
            )
        return current_user

    return _check
