from __future__ import annotations

import logging
from typing import Any

from src.core.security.auth_context import get_auth_context
from src.infrastructure.persistence.mysql.database import SessionLocal
from src.infrastructure.persistence.mysql.repositories.audit_repository import (
    TransactionAuditRepository,
    TransactionAuditRepositoryError,
)

logger = logging.getLogger(__name__)


class TransactionLoggingService:
    """Best-effort service for persisting transaction events to DB."""

    def __init__(self) -> None:
        self._repository: TransactionAuditRepository | None = None
        self._disabled = False

    def _get_repository(self) -> TransactionAuditRepository | None:
        if self._disabled:
            return None
        if self._repository is not None:
            return self._repository

        try:
            self._repository = TransactionAuditRepository(connection_factory=SessionLocal)
            return self._repository
        except Exception as exc:
            self._disabled = True
            logger.warning("Transaction logging disabled because repository initialization failed: %s", exc)
            return None

    @staticmethod
    def _build_event_message(
        *,
        module_name: str,
        operation: str,
        status: str,
        error_message: str | None,
    ) -> str:
        if error_message:
            return f"{module_name}.{operation} {status}: {error_message}"
        return f"{module_name}.{operation} {status}"

    @staticmethod
    def _resolve_actor() -> tuple[int | None, str | None]:
        auth_user = get_auth_context()
        if auth_user is None:
            return None, None
        return auth_user.user_id, auth_user.username

    def log_transaction(
        self,
        *,
        module_name: str,
        operation: str,
        status: str,
        session_id: str | None = None,
        source_channel: str | None = None,
        export_format: str | None = None,
        http_status: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        repo = self._get_repository()
        if repo is None:
            return

        actor_user_id, actor_username = self._resolve_actor()
        event_message = self._build_event_message(
            module_name=module_name,
            operation=operation,
            status=status,
            error_message=error_message,
        )

        try:
            repo.log_event(
                module_name=module_name,
                operation=operation,
                status=status,
                session_id=session_id,
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                source_channel=source_channel,
                export_format=export_format,
                http_status=http_status,
                error_code=error_code,
                error_message=error_message,
                event_message=event_message,
                payload=payload,
            )
        except TransactionAuditRepositoryError as exc:
            logger.warning("Transaction logging write failed: %s", exc)
        except Exception as exc:
            logger.warning("Unexpected transaction logging failure: %s", exc)


_TRANSACTION_LOGGING_SERVICE = TransactionLoggingService()


def get_transaction_logging_service() -> TransactionLoggingService:
    return _TRANSACTION_LOGGING_SERVICE
