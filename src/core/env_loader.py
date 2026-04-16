"""
Environment Variable Loader
Centralizes environment variable loading from .env file
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


def load_environment_variables(env_file: str = ".env") -> None:
    """
    Load environment variables from .env file
    
    Args:
        env_file: Name of the .env file (default: .env)
    """
    # Get project root directory (3 levels up from this file)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    
    # Construct path to .env file
    env_path = project_root / env_file
    
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        logger.info(f"Loaded environment variables from: {env_path}")
        
        # Verify critical variables
        critical_vars = ['OPENAI_API_KEY', 'OPENAI_MODEL']
        missing_vars = []
        
        for var in critical_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        else:
            logger.info("All critical environment variables loaded")
    else:
        logger.warning(f".env file not found at: {env_path}")
        logger.info(f"Please create a .env file with required variables (OPENAI_API_KEY, etc.)")


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
        'password': os.getenv('DB_PASSWORD', 'password')
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
