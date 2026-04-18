from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.constants import (
    AUTH_HEADER_NAME,
    AUTH_HEADER_PREFIX,
    JWT_EMAIL_CLAIM,
    JWT_FULL_NAME_CLAIM,
    JWT_ROLE_CLAIM,
    JWT_SUB_CLAIM,
    JWT_USER_ID_CLAIM,
    PUBLIC_PATHS,
)
from src.core.security.auth_context import set_auth_context
from src.core.security.current_user import CurrentUser
from src.core.security.roles import Role
from src.core.security.token_validator import decode_access_token


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Extracts the bearer token from every incoming request, validates it,
    and stores the resulting ``CurrentUser`` in the request context variable.

    - Public routes (listed in ``_PUBLIC_PREFIXES``) are allowed through
      unconditionally; their handlers simply receive ``None`` context.
    - Protected routes that carry a valid token have the user object set in
      ``auth_context`` so that ``get_current_user()`` dependencies can read it
      without hitting the database a second time.
    - If the token is present but invalid the middleware sets context to ``None``;
      the dependency layer will then raise HTTP 401 when the route requires auth.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        set_auth_context(None)  # reset per-request

        if any(
            request.url.path == public_path
            or request.url.path.startswith(f"{public_path}/")
            for public_path in PUBLIC_PATHS
        ):
            return await call_next(request)

        auth_header: str = request.headers.get(AUTH_HEADER_NAME, "")
        if auth_header.startswith(AUTH_HEADER_PREFIX):
            token = auth_header.removeprefix(AUTH_HEADER_PREFIX).strip()
            try:
                payload = decode_access_token(token)
                user = CurrentUser(
                    user_id=payload[JWT_USER_ID_CLAIM],
                    username=payload[JWT_SUB_CLAIM],
                    email=payload.get(JWT_EMAIL_CLAIM, ""),
                    full_name=payload.get(JWT_FULL_NAME_CLAIM),
                    role=Role(payload.get(JWT_ROLE_CLAIM, Role.USER.value)),
                )
                set_auth_context(user)
            except Exception:
                # Invalid / expired token — context stays None
                pass

        return await call_next(request)

