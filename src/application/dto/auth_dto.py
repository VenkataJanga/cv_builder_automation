from typing import List

from pydantic import BaseModel

from src.core.security.permissions import Permission
from src.core.security.roles import Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str | None = None
    role: Role
    permissions: List[Permission]
