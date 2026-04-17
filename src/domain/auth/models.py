from dataclasses import dataclass, field
from datetime import datetime
from src.core.security.roles import Role


@dataclass
class User:
    """Domain entity representing an authenticated user."""

    id: int
    username: str
    email: str
    hashed_password: str
    role: Role = Role.USER
    full_name: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
