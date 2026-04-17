from pydantic import BaseModel
from src.core.security.roles import Role
from src.core.security.permissions import Permission, get_permissions_for_role


class CurrentUser(BaseModel):
    """Represents the authenticated user attached to each request."""

    user_id: int
    username: str
    email: str
    full_name: str | None = None
    role: Role = Role.USER
    is_active: bool = True

    @property
    def permissions(self) -> set[Permission]:
        return get_permissions_for_role(self.role)

    def has_role(self, *roles: Role) -> bool:
        return self.role in roles

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions
