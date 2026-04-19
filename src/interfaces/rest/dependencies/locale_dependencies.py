from fastapi import Depends, Header, Query

from src.core.i18n import resolve_locale
from src.core.security.auth_context import get_auth_context


def get_request_locale(
    locale: str | None = Query(default=None),
    x_locale: str | None = Header(default=None, alias="X-Locale"),
) -> str:
    """Resolve the request locale without requiring authentication.

    Reads an explicit locale from the query string or ``X-Locale`` header,
    then falls back to the authenticated user's preferred locale (if any),
    and finally to the application default.  This dependency is intentionally
    auth-free so it can be used on public endpoints such as ``/auth/token``.
    """
    auth_user = get_auth_context()
    user_preferred = getattr(auth_user, "preferred_locale", None) if auth_user else None
    return resolve_locale(
        explicit_locale=locale or x_locale,
        user_preferred_locale=user_preferred,
    )
