from collections import defaultdict, deque
from threading import Lock
from time import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.constants import (
    AUTH_ME_PATH,
    AUTH_PREFIX,
    AUTH_TAG,
    AUTH_TOKEN_PATH,
    BEARER_TOKEN_TYPE,
    ERR_ACCOUNT_DISABLED,
    ERR_INCORRECT_USERNAME_OR_PASSWORD,
    JWT_ROLE_CLAIM,
    JWT_SUB_CLAIM,
    JWT_USER_ID_CLAIM,
    WWW_AUTHENTICATE_BEARER,
    WWW_AUTHENTICATE_HEADER,
)
from src.core.security.current_user import CurrentUser
from src.core.security.password_hashing import verify_password
from src.core.security.token_validator import create_access_token
from src.infrastructure.persistence.mysql.database import get_db
from src.infrastructure.persistence.mysql.repositories.auth_repository import AuthRepository
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user

router = APIRouter(prefix=AUTH_PREFIX, tags=[AUTH_TAG])

_AUTH_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)
_AUTH_LIMIT_LOCK = Lock()
_AUTH_WINDOW_SECONDS = 60
_AUTH_MAX_ATTEMPTS = 10


def _rate_limit_key(request: Request, username: str) -> str:
    return f"{request.client.host if request.client else 'unknown'}:{username.lower()}"


def _register_failed_attempt(key: str) -> None:
    now = time()
    with _AUTH_LIMIT_LOCK:
        attempts = _AUTH_ATTEMPTS[key]
        attempts.append(now)
        while attempts and now - attempts[0] > _AUTH_WINDOW_SECONDS:
            attempts.popleft()


def _is_rate_limited(key: str) -> bool:
    now = time()
    with _AUTH_LIMIT_LOCK:
        attempts = _AUTH_ATTEMPTS[key]
        while attempts and now - attempts[0] > _AUTH_WINDOW_SECONDS:
            attempts.popleft()
        return len(attempts) >= _AUTH_MAX_ATTEMPTS


def _reset_attempts(key: str) -> None:
    with _AUTH_LIMIT_LOCK:
        _AUTH_ATTEMPTS.pop(key, None)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = BEARER_TOKEN_TYPE


@router.post(AUTH_TOKEN_PATH, response_model=TokenResponse, summary="Obtain an access token")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    OAuth2 password flow — exchange username + password for a JWT access token.

    The token must be sent as ``Authorization: Bearer <token>`` on protected routes.
    """
    limit_key = _rate_limit_key(request, form.username)
    if _is_rate_limited(limit_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again after 60 seconds.",
        )

    repo = AuthRepository(db)
    user = repo.get_by_username(form.username)

    if user is None or not verify_password(form.password, user.hashed_password):
        _register_failed_attempt(limit_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERR_INCORRECT_USERNAME_OR_PASSWORD,
            headers={WWW_AUTHENTICATE_HEADER: WWW_AUTHENTICATE_BEARER},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_ACCOUNT_DISABLED,
        )

    token = create_access_token(
        payload={JWT_SUB_CLAIM: user.username, JWT_USER_ID_CLAIM: user.id, JWT_ROLE_CLAIM: user.role.value}
    )
    _reset_attempts(limit_key)
    return TokenResponse(access_token=token)


@router.get(AUTH_ME_PATH, summary="Current user info")
def current_user_info(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Returns profile and permissions of the currently authenticated user."""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "permissions": [p.value for p in current_user.permissions],
    }

