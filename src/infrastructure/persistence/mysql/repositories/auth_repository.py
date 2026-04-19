from sqlalchemy.orm import Session

from src.domain.auth.models import User
from src.core.security.roles import Role
from src.infrastructure.persistence.mysql.auth_models import UserORM


class AuthRepository:
    """Handles all database operations for user authentication."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_by_username(self, username: str) -> User | None:
        row = self._db.query(UserORM).filter(UserORM.username == username).first()
        return self._to_domain(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        row = self._db.query(UserORM).filter(UserORM.email == email).first()
        return self._to_domain(row) if row else None

    def get_by_id(self, user_id: int) -> User | None:
        row = self._db.query(UserORM).filter(UserORM.id == user_id).first()
        return self._to_domain(row) if row else None

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create(self, username: str, email: str, hashed_password: str,
               full_name: str | None = None, role: Role = Role.USER, preferred_locale: str = "en") -> User:
        row = UserORM(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role.value,
            preferred_locale=preferred_locale,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return self._to_domain(row)

    def deactivate(self, user_id: int) -> None:
        self._db.query(UserORM).filter(UserORM.id == user_id).update({"is_active": False})
        self._db.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(row: UserORM) -> User:
        return User(
            id=row.id,
            username=row.username,
            email=row.email,
            hashed_password=row.hashed_password,
            full_name=row.full_name,
            role=Role(row.role),
            preferred_locale=row.preferred_locale,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
