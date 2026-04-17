from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.mysql.base import Base


class CVSessionORM(Base):
	__tablename__ = "cv_sessions"

	session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
	canonical_cv: Mapped[str] = mapped_column(Text, nullable=False)
	validation_results: Mapped[str] = mapped_column(Text, nullable=False)
	status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
	last_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
	exported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
	expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
	source_history: Mapped[str] = mapped_column(Text, nullable=False)
	uploaded_artifacts: Mapped[str] = mapped_column(Text, nullable=False)
	metadata_json: Mapped[str] = mapped_column("metadata", Text, nullable=False)
	workflow_state: Mapped[str] = mapped_column(Text, nullable=False)
	version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
