from __future__ import annotations

import json
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Callable, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.domain.session.models import CVSession


class SessionRepositoryError(Exception):
    """Base error for session repository failures."""


class SessionNotFoundError(SessionRepositoryError):
    """Raised when a session cannot be found by session_id."""


class SessionConflictError(SessionRepositoryError):
    """Raised when optimistic locking version checks fail."""


class SessionRepository(ABC):
    """Repository contract for session persistence backends."""

    @abstractmethod
    def create_session(self, session: CVSession) -> CVSession:
        raise NotImplementedError

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[CVSession]:
        raise NotImplementedError

    @abstractmethod
    def save_session(self, session: CVSession) -> CVSession:
        raise NotImplementedError

    @abstractmethod
    def update_session(self, session: CVSession, expected_version: Optional[int] = None) -> CVSession:
        raise NotImplementedError

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_expired_sessions(self, as_of: datetime) -> list[CVSession]:
        raise NotImplementedError


class InMemorySessionRepository(SessionRepository):
    """Fast in-memory repository for local development and unit tests."""

    def __init__(self) -> None:
        self._store: dict[str, CVSession] = {}
        self._lock = RLock()

    def create_session(self, session: CVSession) -> CVSession:
        with self._lock:
            if session.session_id in self._store:
                raise SessionConflictError(f"Session {session.session_id} already exists")
            self._store[session.session_id] = session.model_copy(deep=True)
            return session

    def get_session(self, session_id: str) -> Optional[CVSession]:
        with self._lock:
            found = self._store.get(session_id)
            return found.model_copy(deep=True) if found else None

    def save_session(self, session: CVSession) -> CVSession:
        with self._lock:
            self._store[session.session_id] = session.model_copy(deep=True)
            return session

    def update_session(self, session: CVSession, expected_version: Optional[int] = None) -> CVSession:
        with self._lock:
            existing = self._store.get(session.session_id)
            if not existing:
                raise SessionNotFoundError(f"Session {session.session_id} not found")
            if expected_version is not None and existing.version != expected_version:
                raise SessionConflictError(
                    f"Version mismatch for {session.session_id}: expected {expected_version}, got {existing.version}"
                )
            self._store[session.session_id] = session.model_copy(deep=True)
            return session

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)

    def find_expired_sessions(self, as_of: datetime) -> list[CVSession]:
        with self._lock:
            return [
                session.model_copy(deep=True)
                for session in self._store.values()
                if session.is_expired(as_of)
            ]


class FileSessionRepository(SessionRepository):
    """JSON-file persistence backend for development and debugging."""

    def __init__(self, root_dir: str) -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _path(self, session_id: str) -> Path:
        return self.root / f"{session_id}.json"

    def create_session(self, session: CVSession) -> CVSession:
        with self._lock:
            path = self._path(session.session_id)
            if path.exists():
                raise SessionConflictError(f"Session {session.session_id} already exists")
            self._write(path, session)
            return session

    def get_session(self, session_id: str) -> Optional[CVSession]:
        with self._lock:
            path = self._path(session_id)
            if not path.exists():
                return None
            return self._read(path)

    def save_session(self, session: CVSession) -> CVSession:
        with self._lock:
            self._write(self._path(session.session_id), session)
            return session

    def update_session(self, session: CVSession, expected_version: Optional[int] = None) -> CVSession:
        with self._lock:
            existing = self.get_session(session.session_id)
            if existing is None:
                raise SessionNotFoundError(f"Session {session.session_id} not found")
            if expected_version is not None and existing.version != expected_version:
                raise SessionConflictError(
                    f"Version mismatch for {session.session_id}: expected {expected_version}, got {existing.version}"
                )
            self._write(self._path(session.session_id), session)
            return session

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            path = self._path(session_id)
            if path.exists():
                path.unlink()

    def find_expired_sessions(self, as_of: datetime) -> list[CVSession]:
        with self._lock:
            results: list[CVSession] = []
            for path in self.root.glob("*.json"):
                session = self._read(path)
                if session.is_expired(as_of):
                    results.append(session)
            return results

    def _write(self, path: Path, session: CVSession) -> None:
        temp_path = path.with_suffix(".json.tmp")
        temp_path.write_text(session.model_dump_json(indent=2), encoding="utf-8")
        temp_path.replace(path)

    def _read(self, path: Path) -> CVSession:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CVSession.model_validate(payload)


class DatabaseSessionRepository(SessionRepository):
    """
    Production repository skeleton.

    Back this implementation with MySQL/PostgreSQL via your preferred DB layer
    (SQLAlchemy, psycopg, mysqlclient, etc). This class intentionally defines
    operation contracts and version checks while keeping DB choice pluggable.
    """

    def __init__(self, connection_factory: Callable[[], object]) -> None:
        self.connection_factory = connection_factory
        self._ensure_table()

    @contextmanager
    def _db(self):
        db = self.connection_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _dump(value: object) -> str:
        return json.dumps(value or {}, ensure_ascii=True)

    @staticmethod
    def _dump_list(value: object) -> str:
        return json.dumps(value or [], ensure_ascii=True)

    @staticmethod
    def _parse(value: object, default):
        if value is None or value == "":
            return default
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)

    @staticmethod
    def _naive(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        return dt.replace(tzinfo=None)

    def _to_payload(self, session: CVSession) -> dict:
        metadata_dict = session.metadata.model_dump(mode="json") if hasattr(session.metadata, "model_dump") else session.metadata
        return {
            "session_id": session.session_id,
            "canonical_cv": self._dump(session.canonical_cv),
            "validation_results": self._dump(session.validation_results),
            "status": session.status.value,
            "created_at": self._naive(session.created_at),
            "last_updated_at": self._naive(session.last_updated_at),
            "exported_at": self._naive(session.exported_at),
            "expires_at": self._naive(session.expires_at),
            "source_history": self._dump_list([item.model_dump(mode="json") for item in session.source_history]),
            "uploaded_artifacts": self._dump_list([item.model_dump(mode="json") for item in session.uploaded_artifacts]),
            "metadata": self._dump(metadata_dict),
            "workflow_state": self._dump(session.workflow_state),
            "version": session.version,
        }

    def _to_domain(self, row: dict) -> CVSession:
        payload = {
            "session_id": row["session_id"],
            "canonical_cv": self._parse(row.get("canonical_cv"), {}),
            "validation_results": self._parse(row.get("validation_results"), {}),
            "status": row.get("status", "active"),
            "created_at": row.get("created_at"),
            "last_updated_at": row.get("last_updated_at"),
            "exported_at": row.get("exported_at"),
            "expires_at": row.get("expires_at"),
            "source_history": self._parse(row.get("source_history"), []),
            "uploaded_artifacts": self._parse(row.get("uploaded_artifacts"), []),
            "metadata": self._parse(row.get("metadata"), {}),
            "workflow_state": self._parse(row.get("workflow_state"), {}),
            "version": row.get("version", 1),
        }
        return CVSession.model_validate(payload)

    def _ensure_table(self) -> None:
        ddl = text(
            """
            CREATE TABLE IF NOT EXISTS cv_sessions (
                session_id VARCHAR(64) PRIMARY KEY,
                canonical_cv LONGTEXT NOT NULL,
                validation_results LONGTEXT NOT NULL,
                status VARCHAR(32) NOT NULL,
                created_at DATETIME NOT NULL,
                last_updated_at DATETIME NOT NULL,
                exported_at DATETIME NULL,
                expires_at DATETIME NOT NULL,
                source_history LONGTEXT NOT NULL,
                uploaded_artifacts LONGTEXT NOT NULL,
                metadata LONGTEXT NOT NULL,
                workflow_state LONGTEXT NOT NULL,
                version INT NOT NULL DEFAULT 1,
                INDEX ix_cv_sessions_expires_at (expires_at),
                INDEX ix_cv_sessions_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        try:
            with self._db() as db:
                db.execute(ddl)
        except SQLAlchemyError as exc:
            raise SessionRepositoryError(f"Failed to initialize cv_sessions table: {exc}") from exc

    def create_session(self, session: CVSession) -> CVSession:
        payload = self._to_payload(session)
        stmt = text(
            """
            INSERT INTO cv_sessions (
                session_id, canonical_cv, validation_results, status,
                created_at, last_updated_at, exported_at, expires_at,
                source_history, uploaded_artifacts, metadata, workflow_state, version
            ) VALUES (
                :session_id, :canonical_cv, :validation_results, :status,
                :created_at, :last_updated_at, :exported_at, :expires_at,
                :source_history, :uploaded_artifacts, :metadata, :workflow_state, :version
            )
            """
        )
        try:
            with self._db() as db:
                db.execute(stmt, payload)
            return session
        except SQLAlchemyError as exc:
            raise SessionConflictError(f"Failed to create session {session.session_id}: {exc}") from exc

    def get_session(self, session_id: str) -> Optional[CVSession]:
        stmt = text("SELECT * FROM cv_sessions WHERE session_id = :session_id")
        try:
            with self._db() as db:
                row = db.execute(stmt, {"session_id": session_id}).mappings().first()
                return self._to_domain(dict(row)) if row else None
        except SQLAlchemyError as exc:
            raise SessionRepositoryError(f"Failed to get session {session_id}: {exc}") from exc

    def save_session(self, session: CVSession) -> CVSession:
        payload = self._to_payload(session)
        stmt = text(
            """
            INSERT INTO cv_sessions (
                session_id, canonical_cv, validation_results, status,
                created_at, last_updated_at, exported_at, expires_at,
                source_history, uploaded_artifacts, metadata, workflow_state, version
            ) VALUES (
                :session_id, :canonical_cv, :validation_results, :status,
                :created_at, :last_updated_at, :exported_at, :expires_at,
                :source_history, :uploaded_artifacts, :metadata, :workflow_state, :version
            )
            ON DUPLICATE KEY UPDATE
                canonical_cv = VALUES(canonical_cv),
                validation_results = VALUES(validation_results),
                status = VALUES(status),
                created_at = VALUES(created_at),
                last_updated_at = VALUES(last_updated_at),
                exported_at = VALUES(exported_at),
                expires_at = VALUES(expires_at),
                source_history = VALUES(source_history),
                uploaded_artifacts = VALUES(uploaded_artifacts),
                metadata = VALUES(metadata),
                workflow_state = VALUES(workflow_state),
                version = VALUES(version)
            """
        )
        try:
            with self._db() as db:
                db.execute(stmt, payload)
            return session
        except SQLAlchemyError as exc:
            raise SessionRepositoryError(f"Failed to save session {session.session_id}: {exc}") from exc

    def update_session(self, session: CVSession, expected_version: Optional[int] = None) -> CVSession:
        payload = self._to_payload(session)
        if expected_version is None:
            return self.save_session(session)

        stmt = text(
            """
            UPDATE cv_sessions
            SET
                canonical_cv = :canonical_cv,
                validation_results = :validation_results,
                status = :status,
                created_at = :created_at,
                last_updated_at = :last_updated_at,
                exported_at = :exported_at,
                expires_at = :expires_at,
                source_history = :source_history,
                uploaded_artifacts = :uploaded_artifacts,
                metadata = :metadata,
                workflow_state = :workflow_state,
                version = :version
            WHERE session_id = :session_id AND version = :expected_version
            """
        )

        try:
            with self._db() as db:
                result = db.execute(stmt, {**payload, "expected_version": expected_version})
                if result.rowcount == 0:
                    exists = db.execute(
                        text("SELECT session_id, version FROM cv_sessions WHERE session_id = :session_id"),
                        {"session_id": session.session_id},
                    ).mappings().first()
                    if not exists:
                        raise SessionNotFoundError(f"Session {session.session_id} not found")
                    raise SessionConflictError(
                        f"Version mismatch for {session.session_id}: expected {expected_version}, got {exists['version']}"
                    )
            return session
        except SessionRepositoryError:
            raise
        except SQLAlchemyError as exc:
            raise SessionRepositoryError(f"Failed to update session {session.session_id}: {exc}") from exc

    def delete_session(self, session_id: str) -> None:
        stmt = text("DELETE FROM cv_sessions WHERE session_id = :session_id")
        try:
            with self._db() as db:
                db.execute(stmt, {"session_id": session_id})
        except SQLAlchemyError as exc:
            raise SessionRepositoryError(f"Failed to delete session {session_id}: {exc}") from exc

    def find_expired_sessions(self, as_of: datetime) -> list[CVSession]:
        stmt = text(
            "SELECT * FROM cv_sessions WHERE expires_at <= :as_of AND status != 'deleted'"
        )
        try:
            with self._db() as db:
                rows = db.execute(stmt, {"as_of": self._naive(as_of)}).mappings().all()
                return [self._to_domain(dict(row)) for row in rows]
        except SQLAlchemyError as exc:
            raise SessionRepositoryError(f"Failed to query expired sessions: {exc}") from exc
