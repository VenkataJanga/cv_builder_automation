from typing import Optional, Any


class AppException(Exception):
    """
    Base application exception.

    All custom exceptions should inherit from this.
    """

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


# ---------------------------------------------------------
# Common Exceptions
# ---------------------------------------------------------

class ValidationException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class NotFoundException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
        )


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
        )


class ConflictException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
        )


class InternalServerException(AppException):
    def __init__(self, message: str = "Internal Server Error"):
        super().__init__(
            message=message,
            code="INTERNAL_ERROR",
            status_code=500,
        )


# ---------------------------------------------------------
# AI / LLM Exceptions (MVP2 ready)
# ---------------------------------------------------------

class AIException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="AI_ERROR",
            status_code=500,
            details=details,
        )


class PromptInjectionException(AppException):
    def __init__(self, message: str = "Potential prompt injection detected"):
        super().__init__(
            message=message,
            code="PROMPT_INJECTION",
            status_code=400,
        )


# ---------------------------------------------------------
# Workflow Exceptions (LangGraph)
# ---------------------------------------------------------

class WorkflowException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="WORKFLOW_ERROR",
            status_code=500,
            details=details,
        )


class StateTransitionException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INVALID_STATE_TRANSITION",
            status_code=400,
        )


# ---------------------------------------------------------
# Storage / Infrastructure Exceptions
# ---------------------------------------------------------

class StorageException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="STORAGE_ERROR",
            status_code=500,
            details=details,
        )


class DatabaseException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            details=details,
        )