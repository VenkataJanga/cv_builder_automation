"""Shared constants for observability configuration."""

import os


LANGSMITH_PROJECT_ENV_VAR = "LANGCHAIN_PROJECT"
DEFAULT_LANGSMITH_PROJECT = "cv_builder_automation"


def get_langsmith_project_name() -> str:
    """Resolve the LangSmith project name from environment with a single fallback."""
    return os.getenv(LANGSMITH_PROJECT_ENV_VAR, DEFAULT_LANGSMITH_PROJECT)
