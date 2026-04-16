from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Callable, Optional

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

    def create_session(self, session: CVSession) -> CVSession:
        raise NotImplementedError("Implement INSERT into cv_sessions and source events")

    def get_session(self, session_id: str) -> Optional[CVSession]:
        raise NotImplementedError("Implement SELECT by session_id and hydrate CVSession")

    def save_session(self, session: CVSession) -> CVSession:
        raise NotImplementedError("Implement upsert save semantics")

    def update_session(self, session: CVSession, expected_version: Optional[int] = None) -> CVSession:
        raise NotImplementedError("Implement optimistic update WHERE version = expected_version")

    def delete_session(self, session_id: str) -> None:
        raise NotImplementedError("Implement delete/soft-delete strategy")

    def find_expired_sessions(self, as_of: datetime) -> list[CVSession]:
        raise NotImplementedError("Implement SELECT by expires_at <= as_of")
