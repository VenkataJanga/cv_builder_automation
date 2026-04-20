from __future__ import annotations

import logging
from typing import Any
from datetime import datetime

from src.core.security.auth_context import get_auth_context
from src.observability.langsmith_tracer import SpanStatus, SpanType, get_langsmith_tracer
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
        self._tracer = None
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

    def _get_tracer(self):
        if self._tracer is not None:
            return self._tracer
        try:
            self._tracer = get_langsmith_tracer()
            return self._tracer
        except Exception as exc:
            logger.debug("LangSmith tracer unavailable for transaction logging: %s", exc)
            return None

    def _trace_transaction(
        self,
        *,
        module_name: str,
        operation: str,
        status: str,
        session_id: str | None,
        source_channel: str | None,
        export_format: str | None,
        http_status: int | None,
        error_code: str | None,
        error_message: str | None,
        payload: dict[str, Any] | None,
        actor_username: str | None,
    ) -> None:
        tracer = self._get_tracer()
        if tracer is None:
            return

        trace = None
        try:
            trace = tracer.start_trace(
                name=f"{module_name}_{operation}",
                tags=["transaction", module_name, status],
                metadata={
                    "module": module_name,
                    "operation": operation,
                    "session_id": session_id,
                    "source_channel": source_channel,
                    "export_format": export_format,
                    "http_status": http_status,
                    "actor_username": actor_username,
                },
            )
            with tracer.span(
                operation,
                SpanType.WORKFLOW,
                trace_id=trace.trace_id,
                metadata={"module": module_name},
            ) as span:
                span.inputs = payload or {}
                span.outputs = {
                    "status": status,
                    "http_status": http_status,
                    "error_code": error_code,
                    "error_message": error_message,
                }

            end_status = SpanStatus.SUCCESS if status.lower() == "success" else SpanStatus.ERROR
            tracer.end_trace(trace.trace_id, status=end_status)
        except Exception as exc:
            logger.debug("Transaction trace emission failed: %s", exc)
            if trace is not None:
                try:
                    tracer.end_trace(trace.trace_id, status=SpanStatus.ERROR)
                except Exception:
                    logger.debug("Failed to close transaction trace after error", exc_info=True)

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
        actor_user_id: int | None = None,
        actor_username: str | None = None,
    ) -> None:
        repo = self._get_repository()
        if repo is None:
            return

        resolved_actor_user_id, resolved_actor_username = self._resolve_actor()
        if actor_user_id is None:
            actor_user_id = resolved_actor_user_id
        if actor_username is None:
            actor_username = resolved_actor_username

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

        self._trace_transaction(
            module_name=module_name,
            operation=operation,
            status=status,
            session_id=session_id,
            source_channel=source_channel,
            export_format=export_format,
            http_status=http_status,
            error_code=error_code,
            error_message=error_message,
            payload=payload,
            actor_username=actor_username,
        )

    def list_transactions(
        self,
        *,
        limit: int = 100,
        module_name: str | None = None,
        operation: str | None = None,
        status: str | None = None,
        session_id: str | None = None,
        actor_username: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> list[dict[str, Any]]:
        repo = self._get_repository()
        if repo is None:
            return []

        try:
            return repo.list_events(
                limit=limit,
                module_name=module_name,
                operation=operation,
                status=status,
                session_id=session_id,
                actor_username=actor_username,
                created_from=created_from,
                created_to=created_to,
            )
        except TransactionAuditRepositoryError as exc:
            logger.warning("Transaction log query failed: %s", exc)
            return []


_TRANSACTION_LOGGING_SERVICE = TransactionLoggingService()


def get_transaction_logging_service() -> TransactionLoggingService:
    return _TRANSACTION_LOGGING_SERVICE
