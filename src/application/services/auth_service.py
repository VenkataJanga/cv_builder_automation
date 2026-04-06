from src.core.security.policy_engine import PolicyEngine


class AuthService:
    def __init__(self) -> None:
        self.policy = PolicyEngine()

    def can(self, roles: list[str], permission: str) -> bool:
        return self.policy.has_permission(roles, permission)
