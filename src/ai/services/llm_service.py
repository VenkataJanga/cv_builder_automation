"""
Base LLM Service Wrapper

Provides safe, provider-agnostic LLM access with graceful fallbacks.
Supports OpenAI (current) and Azure OpenAI (future) providers.
"""

import logging
from typing import Optional, Dict, Any
import httpx
from openai import OpenAI, AzureOpenAI

from src.core.config.settings import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Safe wrapper for LLM operations.
    
    Features:
    - Graceful fallback if API key missing
    - Provider abstraction (OpenAI/Azure)
    - Structured output support
    - Error handling
    """

    def __init__(self):
        """Initialize LLM client based on configuration."""
        self.client = self._initialize_client()
        self.enabled = self.client is not None

    def _initialize_client(self) -> Optional[Any]:
        """
        Initialize LLM client.
        
        Returns None if no provider is configured.
        Supports both OpenAI and Azure OpenAI.
        """
        # Try Azure OpenAI first if configured
        if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
            try:
                logger.info("Initializing Azure OpenAI client")
                return AzureOpenAI(
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version="2024-02-15-preview",
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Azure OpenAI: {e}. Falling back to standard OpenAI.")

        # Fall back to standard OpenAI
        if settings.OPENAI_API_KEY:
            try:
                logger.info("Initializing OpenAI client")
                verify_ssl = settings.OPENAI_VERIFY_SSL

                if verify_ssl:
                    return OpenAI(api_key=settings.OPENAI_API_KEY)
                else:
                    # DEVELOPMENT-ONLY: disable SSL verification
                    import warnings
                    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
                    httpx_client = httpx.Client(verify=False)
                    return OpenAI(api_key=settings.OPENAI_API_KEY, http_client=httpx_client)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")

        logger.warning("No LLM provider configured. LLM features will be disabled.")
        return None

    def call(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        json_mode: bool = False,
    ) -> Optional[str]:
        """
        Make an LLM call with fallback behavior.
        
        Args:
            prompt: User prompt/message
            system_message: Optional system context
            temperature: Sampling temperature
            max_tokens: Max output tokens
            json_mode: Request JSON-formatted output
            
        Returns:
            Response text or None if disabled/failed
        """
        if not self.enabled:
            logger.debug("LLM disabled. Skipping call.")
            return None

        try:
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            # Determine model and create request
            model = self._get_model()
            request_kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if json_mode:
                request_kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**request_kwargs)
            result = response.choices[0].message.content.strip()

            logger.debug(f"LLM call succeeded. Model: {model}")
            return result

        except Exception as e:
            logger.error(f"LLM call failed: {e}. Returning None.")
            return None

    def _get_model(self) -> str:
        """Get the appropriate model name for the current provider."""
        if settings.AZURE_OPENAI_DEPLOYMENT:
            return settings.AZURE_OPENAI_DEPLOYMENT
        return settings.LLM_ENHANCEMENT_MODEL

    def is_enabled(self) -> bool:
        """Check if LLM is enabled and configured."""
        return self.enabled


# Singleton instance
_llm_service_instance = None


def get_llm_service() -> LLMService:
    """Get or create singleton LLM service."""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance
