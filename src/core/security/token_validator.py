from datetime import datetime, timezone
from typing import Any

from jose import JWTError, jwt
from fastapi import HTTPException, status

from src.core.config.settings import settings
from src.core.constants import (
    ERR_COULD_NOT_VALIDATE_CREDENTIALS,
    JWT_EXP_CLAIM,
    JWT_SUB_CLAIM,
    WWW_AUTHENTICATE_BEARER,
    WWW_AUTHENTICATE_HEADER,
)


def create_access_token(payload: dict[str, Any]) -> str:
    """Encode a JWT access token with the given claims."""
    from datetime import timedelta
    data = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    data[JWT_EXP_CLAIM] = expire
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises HTTP 401 if the token is invalid or expired.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ERR_COULD_NOT_VALIDATE_CREDENTIALS,
        headers={WWW_AUTHENTICATE_HEADER: WWW_AUTHENTICATE_BEARER},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise credentials_exc

    if payload.get(JWT_SUB_CLAIM) is None:
        raise credentials_exc

    return payload
