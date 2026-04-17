from enum import Enum
from src.core.security.roles import Role


class Permission(str, Enum):
    CREATE_CV = "create_cv"
    EDIT_CV = "edit_cv"
    REVIEW_CV = "review_cv"
    APPROVE_CV = "approve_cv"
    EXPORT_CV = "export_cv"
    MANAGE_TEMPLATES = "manage_templates"


# Maps each role to its allowed permissions
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    Role.ADMIN: {
        Permission.CREATE_CV,
        Permission.EDIT_CV,
        Permission.REVIEW_CV,
        Permission.APPROVE_CV,
        Permission.EXPORT_CV,
        Permission.MANAGE_TEMPLATES,
    },
    Role.DELIVERY_MANAGER: {
        Permission.CREATE_CV,
        Permission.EDIT_CV,
        Permission.REVIEW_CV,
        Permission.APPROVE_CV,
        Permission.EXPORT_CV,
    },
    Role.REVIEWER: {
        Permission.REVIEW_CV,
        Permission.EXPORT_CV,
    },
    Role.CV_EDITOR: {
        Permission.CREATE_CV,
        Permission.EDIT_CV,
        Permission.EXPORT_CV,
    },
    Role.USER: {
        Permission.CREATE_CV,
        Permission.EDIT_CV,
        Permission.EXPORT_CV,
    },
}


def get_permissions_for_role(role: str) -> set[Permission]:
    """Return the set of permissions granted to a role."""
    try:
        return ROLE_PERMISSIONS.get(Role(role), set())
    except ValueError:
        return set()
