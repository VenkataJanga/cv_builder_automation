import logging
import json
from datetime import datetime
from pathlib import Path
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
def _ensure_log_path() -> Path:
    log_path = Path(settings.LOG_FILE_PATH)
    if not log_path.parent.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path.resolve()


def _configure_root_logger() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    if settings.ENV == "local":
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        )
    else:
        formatter = JsonFormatter()

    # Remove existing console/stream handlers so runtime noise does not go to stdout.
    for handler in list(root_logger.handlers):
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            root_logger.removeHandler(handler)

    if settings.LOG_TO_FILE:
        log_path = _ensure_log_path()
        file_handler_exists = any(
            isinstance(handler, logging.FileHandler) and Path(handler.baseFilename).resolve() == log_path
            for handler in root_logger.handlers
        )
        created_root_file_handler = False
        if not file_handler_exists:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            created_root_file_handler = True

        # Route uvicorn logs to the same file and suppress their console handlers.
        for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
            app_logger = logging.getLogger(logger_name)
            app_logger.setLevel(settings.LOG_LEVEL.upper())
            for handler in list(app_logger.handlers):
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    app_logger.removeHandler(handler)
            if not any(
                isinstance(handler, logging.FileHandler) and Path(handler.baseFilename).resolve() == log_path
                for handler in app_logger.handlers
            ):
                uvicorn_file_handler = logging.FileHandler(log_path, encoding="utf-8")
                uvicorn_file_handler.setFormatter(formatter)
                app_logger.addHandler(uvicorn_file_handler)
            app_logger.propagate = False

        if created_root_file_handler:
            root_logger.info(f"Logging to file: {log_path.resolve()}")


def get_logger(name: str) -> logging.Logger:
    """
    Returns configured logger instance.
    """
    _configure_root_logger()
    return logging.getLogger(name)


def get_print_logger(name: str):
    """Return a print-compatible callable that routes messages to the configured logger."""
    logger = get_logger(name)

    def _log_message(*args, **kwargs):
        message = " ".join(str(arg) for arg in args)
        if message.startswith("Error") or message.startswith("[ERROR]"):
            logger.error(message)
        elif message.startswith("Warning") or message.startswith("[WARNING]") or message.startswith("[WARN]"):
            logger.warning(message)
        else:
            logger.info(message)

    return _log_message


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