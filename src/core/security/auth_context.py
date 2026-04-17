from contextvars import ContextVar
from src.core.security.current_user import CurrentUser


# Request-scoped context variable holding the current authenticated user.
# Set by auth middleware; read by dependencies and services.
_current_user_var: ContextVar[CurrentUser | None] = ContextVar(
    "current_user", default=None
)


def set_auth_context(user: CurrentUser | None) -> None:
    _current_user_var.set(user)


def get_auth_context() -> CurrentUser | None:
    return _current_user_var.get()
