"""
Base LLM Service Wrapper

Provides safe, provider-agnostic LLM access with graceful fallbacks.
Supports OpenAI (current) and Azure OpenAI (future) providers.
Tracks token usage and cost for all API calls with LangSmith integration.
"""

import logging
from typing import Optional, Dict, Any, Tuple
import httpx
from openai import OpenAI, AzureOpenAI

from src.core.config.settings import settings
from src.ai.services.token_cost_calculator import calculate_cost

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
        result, usage = self.call_with_usage(
            prompt=prompt,
            system_message=system_message,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode
        )
        return result
    
    def call_with_usage(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        json_mode: bool = False,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Make an LLM call and return response with usage data.
        
        Automatically tracks the call with LangSmith tracer if available.
        
        Args:
            prompt: User prompt/message
            system_message: Optional system context
            temperature: Sampling temperature
            max_tokens: Max output tokens
            json_mode: Request JSON-formatted output
            
        Returns:
            Tuple of (response_text, usage_dict) where usage_dict contains:
            - prompt_tokens: Number of input tokens
            - completion_tokens: Number of output tokens
            - total_tokens: Total tokens used
            - cost: Estimated cost in USD
        """
        if not self.enabled:
            logger.debug("LLM disabled. Skipping call.")
            return None, {}

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

            # Extract usage data
            usage_data = self._extract_usage_data(response, model)

            # Track LLM call with tracer if available
            self._track_llm_call_with_tracer(
                model=model,
                prompt=prompt[:500],  # Truncate for tracer storage
                response=result[:500],  # Truncate for tracer storage
                usage_data=usage_data
            )

            logger.debug(
                f"LLM call succeeded. Model: {model}, "
                f"Tokens: {usage_data.get('total_tokens', 0)}, "
                f"Cost: ${usage_data.get('cost', 0):.6f}"
            )
            return result, usage_data

        except Exception as e:
            logger.error(f"LLM call failed: {e}. Returning None.")
            return None, {}
    
    def _track_llm_call_with_tracer(
        self,
        model: str,
        prompt: str,
        response: str,
        usage_data: Dict[str, Any]
    ):
        """
        Track LLM call with LangSmith tracer if available.
        
        This ensures token usage and cost metrics flow to the LangSmith dashboard.
        """
        try:
            # Import here to avoid circular dependency
            from src.observability.langsmith_tracer import get_langsmith_tracer

            tracer = get_langsmith_tracer()

            if not tracer.enabled:
                return

            prompt_tokens = int(usage_data.get("prompt_tokens", 0) or 0)
            completion_tokens = int(usage_data.get("completion_tokens", 0) or 0)
            total_tokens = int(usage_data.get("total_tokens", 0) or 0)
            total_cost = float(usage_data.get("cost", 0.0) or 0.0)

            active_trace_id = getattr(tracer, "current_trace_id", None)

            # If there is no active trace, create a lightweight standalone trace
            # so LLM metrics are still ingested by LangSmith dashboards.
            owns_trace = False
            traces = getattr(tracer, "traces", None)
            trace_missing = isinstance(traces, dict) and active_trace_id and active_trace_id not in traces

            if (not active_trace_id or trace_missing) and hasattr(tracer, "start_trace"):
                temp_trace = tracer.start_trace(
                    name="llm_call_standalone",
                    tags=["llm", "standalone"],
                    metadata={"source": "llm_service"},
                )
                active_trace_id = temp_trace.trace_id
                owns_trace = True

            if not active_trace_id:
                return

            tracer.track_llm_call(
                trace_id=active_trace_id,
                model=model,
                prompt=prompt,
                response=response,
                tokens=total_tokens,
                cost=total_cost,
                metadata={
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "total_cost": total_cost,
                    "ls_provider": "openai",
                    "ls_model_name": model,
                },
            )

            if owns_trace and hasattr(tracer, "end_trace"):
                from src.observability.langsmith_tracer import SpanStatus
                tracer.end_trace(active_trace_id, status=SpanStatus.SUCCESS)

            logger.debug(
                "LLM call tracked for model %s with %s tokens, cost: $%.6f",
                model,
                total_tokens,
                total_cost,
            )
        except Exception as e:
            # Silently fail - don't break LLM call if tracer integration fails
            logger.debug(f"Failed to track LLM call with tracer: {e}")

    def _get_model(self) -> str:
        """Get the appropriate model name for the current provider."""
        if settings.AZURE_OPENAI_DEPLOYMENT:
            return settings.AZURE_OPENAI_DEPLOYMENT
        return settings.LLM_ENHANCEMENT_MODEL

    def _extract_usage_data(self, response: Any, model: str) -> Dict[str, Any]:
        """
        Extract usage data from OpenAI response.
        
        Args:
            response: OpenAI API response object
            model: Model name used for cost calculation
            
        Returns:
            Dictionary with token and cost information
        """
        try:
            if hasattr(response, 'usage') and response.usage:
                prompt_tokens = response.usage.prompt_tokens or 0
                completion_tokens = response.usage.completion_tokens or 0
                total_tokens = response.usage.total_tokens or 0
                
                # Calculate cost
                cost = calculate_cost(
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )
                
                return {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost,
                    "model": model,
                }
            else:
                logger.warning("No usage data in response")
                return {"model": model}
        except Exception as e:
            logger.warning(f"Failed to extract usage data: {e}")
            return {"model": model}

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
