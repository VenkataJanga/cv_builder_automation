from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


class TransactionAuditRepositoryError(Exception):
	"""Raised when transaction audit persistence fails."""


class TransactionAuditRepository:
	"""Repository for durable transaction event logging."""

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
	def _dump_payload(payload: dict[str, Any] | None) -> str:
		return json.dumps(payload or {}, ensure_ascii=False, default=str)

	@staticmethod
	def _utc_naive_now() -> datetime:
		return datetime.now(timezone.utc).replace(tzinfo=None)

	def _ensure_table(self) -> None:
		ddl = text(
			"""
			CREATE TABLE IF NOT EXISTS transaction_event_logs (
				id BIGINT AUTO_INCREMENT PRIMARY KEY,
				session_id VARCHAR(64) NULL,
				actor_user_id BIGINT NULL,
				actor_username VARCHAR(128) NULL,
				module_name VARCHAR(64) NOT NULL,
				operation VARCHAR(128) NOT NULL,
				status VARCHAR(16) NOT NULL,
				event_message TEXT NULL,
				source_channel VARCHAR(64) NULL,
				export_format VARCHAR(16) NULL,
				http_status INT NULL,
				error_code VARCHAR(64) NULL,
				error_message TEXT NULL,
				payload LONGTEXT NOT NULL,
				created_at DATETIME NOT NULL,
				INDEX ix_transaction_event_logs_session_id (session_id),
				INDEX ix_transaction_event_logs_module_name (module_name),
				INDEX ix_transaction_event_logs_status (status),
				INDEX ix_transaction_event_logs_actor_user_id (actor_user_id),
				INDEX ix_transaction_event_logs_actor_username (actor_username),
				INDEX ix_transaction_event_logs_created_at (created_at)
			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
			"""
		)
		column_query = text(
			"""
			SELECT COUNT(*) AS cnt
			FROM INFORMATION_SCHEMA.COLUMNS
			WHERE TABLE_SCHEMA = DATABASE()
			  AND TABLE_NAME = 'transaction_event_logs'
			  AND COLUMN_NAME = :column_name
			"""
		)
		index_query = text(
			"""
			SELECT COUNT(*) AS cnt
			FROM INFORMATION_SCHEMA.STATISTICS
			WHERE TABLE_SCHEMA = DATABASE()
			  AND TABLE_NAME = 'transaction_event_logs'
			  AND INDEX_NAME = :index_name
			"""
		)
		add_column_actor_user_id = text(
			"ALTER TABLE transaction_event_logs ADD COLUMN actor_user_id BIGINT NULL AFTER session_id"
		)
		add_column_actor_username = text(
			"ALTER TABLE transaction_event_logs ADD COLUMN actor_username VARCHAR(128) NULL AFTER actor_user_id"
		)
		add_column_event_message = text(
			"ALTER TABLE transaction_event_logs ADD COLUMN event_message TEXT NULL AFTER status"
		)
		add_index_actor_user_id = text(
			"CREATE INDEX ix_transaction_event_logs_actor_user_id ON transaction_event_logs (actor_user_id)"
		)
		add_index_actor_username = text(
			"CREATE INDEX ix_transaction_event_logs_actor_username ON transaction_event_logs (actor_username)"
		)
		try:
			with self._db() as db:
				db.execute(ddl)

				actor_user_id_exists = db.execute(
					column_query,
					{"column_name": "actor_user_id"},
				).scalar_one() > 0
				if not actor_user_id_exists:
					db.execute(add_column_actor_user_id)

				actor_username_exists = db.execute(
					column_query,
					{"column_name": "actor_username"},
				).scalar_one() > 0
				if not actor_username_exists:
					db.execute(add_column_actor_username)

				event_message_exists = db.execute(
					column_query,
					{"column_name": "event_message"},
				).scalar_one() > 0
				if not event_message_exists:
					db.execute(add_column_event_message)

				actor_user_id_index_exists = db.execute(
					index_query,
					{"index_name": "ix_transaction_event_logs_actor_user_id"},
				).scalar_one() > 0
				if not actor_user_id_index_exists:
					db.execute(add_index_actor_user_id)

				actor_username_index_exists = db.execute(
					index_query,
					{"index_name": "ix_transaction_event_logs_actor_username"},
				).scalar_one() > 0
				if not actor_username_index_exists:
					db.execute(add_index_actor_username)
		except SQLAlchemyError as exc:
			raise TransactionAuditRepositoryError(f"Failed to initialize transaction_event_logs table: {exc}") from exc

	def log_event(
		self,
		*,
		module_name: str,
		operation: str,
		status: str,
		session_id: str | None = None,
		actor_user_id: int | None = None,
		actor_username: str | None = None,
		source_channel: str | None = None,
		export_format: str | None = None,
		http_status: int | None = None,
		error_code: str | None = None,
		error_message: str | None = None,
		event_message: str | None = None,
		payload: dict[str, Any] | None = None,
	) -> None:
		stmt = text(
			"""
			INSERT INTO transaction_event_logs (
				session_id,
				actor_user_id,
				actor_username,
				module_name,
				operation,
				status,
				event_message,
				source_channel,
				export_format,
				http_status,
				error_code,
				error_message,
				payload,
				created_at
			) VALUES (
				:session_id,
				:actor_user_id,
				:actor_username,
				:module_name,
				:operation,
				:status,
				:event_message,
				:source_channel,
				:export_format,
				:http_status,
				:error_code,
				:error_message,
				:payload,
				:created_at
			)
			"""
		)
		params = {
			"session_id": session_id,
			"actor_user_id": actor_user_id,
			"actor_username": actor_username,
			"module_name": module_name,
			"operation": operation,
			"status": status,
			"event_message": event_message,
			"source_channel": source_channel,
			"export_format": export_format,
			"http_status": http_status,
			"error_code": error_code,
			"error_message": error_message,
			"payload": self._dump_payload(payload),
			"created_at": self._utc_naive_now(),
		}

		try:
			with self._db() as db:
				db.execute(stmt, params)
		except SQLAlchemyError as exc:
			raise TransactionAuditRepositoryError(f"Failed to write transaction log: {exc}") from exc
