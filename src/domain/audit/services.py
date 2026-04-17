import logging
from typing import Any


logger = logging.getLogger(__name__)


class AuditService:
    def log_event(self, event_name: str, **payload: Any) -> None:
        logger.info("audit_event=%s payload=%s", event_name, payload)
