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


class ReverseChronologicalFileHandler(logging.Handler):
    """File handler that writes newest entries at the top of the file."""

    def __init__(self, filename: Path, encoding: str = "utf-8"):
        super().__init__()
        self.baseFilename = str(Path(filename).resolve())
        self.encoding = encoding

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            if not message.endswith("\n"):
                message += "\n"

            self.acquire()
            try:
                file_path = Path(self.baseFilename)
                existing = ""
                if file_path.exists():
                    existing = file_path.read_text(encoding=self.encoding, errors="ignore")
                file_path.write_text(message + existing, encoding=self.encoding)
            finally:
                self.release()
        except Exception:
            self.handleError(record)


# ---------------------------------------------------------
# Logger Factory
# ---------------------------------------------------------
def _ensure_log_path() -> Path:
    log_path = Path(settings.LOG_FILE_PATH)
    if not log_path.parent.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path.resolve()


def _handler_targets_log_path(handler: logging.Handler, log_path: Path) -> bool:
    base_filename = getattr(handler, "baseFilename", None)
    if not base_filename:
        return False
    try:
        return Path(base_filename).resolve() == log_path
    except Exception:
        return False


def _create_file_handler(log_path: Path, formatter: logging.Formatter) -> logging.Handler:
    if settings.LOG_NEWEST_FIRST:
        handler = ReverseChronologicalFileHandler(log_path)
    else:
        handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(formatter)
    return handler


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

    # Also strip stream handlers from any already-instantiated non-root loggers.
    # Some third-party libraries attach their own StreamHandler instances.
    logger_dict = logging.Logger.manager.loggerDict
    for logger_name, logger_obj in logger_dict.items():
        if not isinstance(logger_obj, logging.Logger):
            continue
        for handler in list(logger_obj.handlers):
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                logger_obj.removeHandler(handler)

    if settings.LOG_TO_FILE:
        log_path = _ensure_log_path()
        file_handler_exists = any(_handler_targets_log_path(handler, log_path) for handler in root_logger.handlers)
        created_root_file_handler = False
        if not file_handler_exists:
            file_handler = _create_file_handler(log_path, formatter)
            root_logger.addHandler(file_handler)
            created_root_file_handler = True

        # Route uvicorn logs to the same file and suppress their console handlers.
        for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
            app_logger = logging.getLogger(logger_name)
            app_logger.setLevel(settings.LOG_LEVEL.upper())
            for handler in list(app_logger.handlers):
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    app_logger.removeHandler(handler)
            if not any(_handler_targets_log_path(handler, log_path) for handler in app_logger.handlers):
                uvicorn_file_handler = _create_file_handler(log_path, formatter)
                app_logger.addHandler(uvicorn_file_handler)
            app_logger.propagate = False

        # Keep file useful by reducing noisy framework internals while preserving app-level info.
        noisy_logger_levels = {
            "sqlalchemy.engine": logging.WARNING,
            "watchfiles.main": logging.WARNING,
            "watchgod.main": logging.WARNING,
            "asyncio": logging.WARNING,
        }
        for logger_name, level in noisy_logger_levels.items():
            noisy_logger = logging.getLogger(logger_name)
            noisy_logger.setLevel(level)

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