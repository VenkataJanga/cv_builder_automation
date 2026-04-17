from src.domain.session.repositories import DatabaseSessionRepository


class MySQLSessionRepository(DatabaseSessionRepository):
	"""Concrete MySQL session repository backed by SQLAlchemy session factory."""

	pass
