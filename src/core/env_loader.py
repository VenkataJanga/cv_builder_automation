"""
Environment Variable Loader
Centralizes environment variable loading from .env file
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _candidate_env_files(env_file: str | None = None) -> list[str]:
    """Return env files in load order from lowest to highest precedence."""
    if env_file:
        return [env_file]

    env_name = os.getenv("ENV", "local").strip().lower() or "local"
    if env_name == "local":
        return [".env"]
    return [".env", f".env.{env_name}"]


def load_environment_variables(env_file: str | None = None) -> None:
    """
    Load environment variables from one or more env files.
    
    Args:
        env_file: Optional explicit env filename. If omitted, uses ENV-aware
            resolution (.env and .env.<ENV> when ENV is set).
    """
    # Get project root directory (3 levels up from this file)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    
    loaded_paths: list[Path] = []
    for candidate in _candidate_env_files(env_file=env_file):
        env_path = project_root / candidate
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
            loaded_paths.append(env_path)

    if loaded_paths:
        for path in loaded_paths:
            logger.info(f"Loaded environment variables from: {path}")

        # Verify critical variables
        critical_vars = ["OPENAI_API_KEY", "OPENAI_MODEL"]
        missing_vars = [var for var in critical_vars if not os.getenv(var)]

        if missing_vars:
            logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        else:
            logger.info("All critical environment variables loaded")
    else:
        logger.warning(
            "No env file found. Expected one of: %s",
            ", ".join(_candidate_env_files(env_file=env_file)),
        )
        logger.info(
            "Create .env for local defaults or .env.<env> and set ENV (for example ENV=dev)."
        )


def get_openai_config() -> dict:
    """
    Get OpenAI configuration from environment variables
    
    Returns:
        Dictionary with OpenAI configuration
    """
    return {
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        'temperature': float(os.getenv('OPENAI_TEMPERATURE', '0.1')),
        'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '4000')),
        'verify_ssl': os.getenv('OPENAI_VERIFY_SSL', 'true').lower() == 'true'
    }


def get_db_config() -> dict:
    """
    Get database configuration from environment variables
    
    Returns:
        Dictionary with database configuration
    """
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'name': os.getenv('DB_NAME', 'cv_builder'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', '')
    }


def get_storage_config() -> dict:
    """
    Get storage configuration from environment variables
    
    Returns:
        Dictionary with storage configuration
    """
    return {
        'local_path': os.getenv('LOCAL_STORAGE_PATH', './data/storage')
    }


# Auto-load environment variables when this module is imported
load_environment_variables()
