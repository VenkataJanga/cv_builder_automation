import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

from src.core.config.settings import settings


# ---------------------------------------------------------
# JSON Formatter (Production Ready)
# ---------------------------------------------------------
class JsonFormatter(logging.Formatter):
    """
    Structured JSON logging formatter.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add optional fields
        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id

        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


# ---------------------------------------------------------
# Logger Factory
# ---------------------------------------------------------
def get_logger(name: str) -> logging.Logger:
    """
    Returns configured logger instance.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # prevent duplicate handlers

    logger.setLevel(settings.LOG_LEVEL.upper())

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)

    if settings.ENV == "local":
        # Simple readable logs for dev
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        )
    else:
        # JSON logs for prod
        formatter = JsonFormatter()

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# ---------------------------------------------------------
# Helper Logging Functions
# ---------------------------------------------------------
def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    correlation_id: str = None,
    user_id: str = None,
    extra: Dict[str, Any] = None,
):
    """
    Log with additional context fields.
    """
    extra_fields = extra or {}

    if correlation_id:
        extra_fields["correlation_id"] = correlation_id

    if user_id:
        extra_fields["user_id"] = user_id

    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message, extra=extra_fields)