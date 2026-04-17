# Re-export the canonical dependency from the interfaces layer so that
# existing router imports (`from apps.api.dependencies import get_current_user`)
# continue to work without changes.
from src.interfaces.rest.dependencies.auth_dependencies import (
    get_current_user,
    require_role,
    require_permission,
)

__all__ = ["get_current_user", "require_role", "require_permission"]

