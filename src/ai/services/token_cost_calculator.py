"""
Token Cost Calculator

Calculates API costs based on token usage for different LLM models.
Supports OpenAI and Azure OpenAI pricing tiers.
"""

from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# OpenAI pricing as of April 2026 (in USD per 1K tokens)
# Update these values as pricing changes
PRICING_PER_1K_TOKENS = {
    # GPT-4 models
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo-2024-04-09": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-32k": {"input": 0.06, "output": 0.12},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-2024-05-13": {"input": 0.005, "output": 0.015},
    
    # GPT-3.5 models
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    "gpt-3.5-turbo-instruct": {"input": 0.0015, "output": 0.002},
    
    # Fallback for unknown models
    "default": {"input": 0.01, "output": 0.03},
}


def get_pricing_for_model(model: str) -> Dict[str, float]:
    """
    Get input/output pricing for a model.
    
    Args:
        model: Model name (e.g., "gpt-4-turbo", "gpt-3.5-turbo")
        
    Returns:
        Dictionary with "input" and "output" keys (prices per 1K tokens in USD)
    """
    # Try exact match first
    if model in PRICING_PER_1K_TOKENS:
        return PRICING_PER_1K_TOKENS[model]
    
    # Try prefix match for model variants
    model_lower = model.lower()
    for price_model in PRICING_PER_1K_TOKENS.keys():
        if model_lower.startswith(price_model.lower()):
            return PRICING_PER_1K_TOKENS[price_model]
    
    # Try contains match (e.g., "gpt-4" in "gpt-4-custom")
    for price_model in PRICING_PER_1K_TOKENS.keys():
        if price_model in model_lower:
            return PRICING_PER_1K_TOKENS[price_model]
    
    # Return default if no match
    logger.warning(f"Unknown model '{model}', using default pricing")
    return PRICING_PER_1K_TOKENS["default"]


def calculate_cost(
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0
) -> float:
    """
    Calculate API cost for an LLM call.
    
    Args:
        model: Model name
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        total_tokens: Total tokens (if prompt/completion not provided)
        
    Returns:
        Cost in USD (float)
    """
    try:
        pricing = get_pricing_for_model(model)
        
        # Use provided token counts, fallback to total_tokens if needed
        input_tokens = prompt_tokens
        output_tokens = completion_tokens
        
        if input_tokens == 0 and output_tokens == 0 and total_tokens > 0:
            # Estimate split (assume 90% input, 10% output as rough average)
            input_tokens = int(total_tokens * 0.9)
            output_tokens = total_tokens - input_tokens
        
        # Calculate cost
        input_cost = (input_tokens / 1000.0) * pricing["input"]
        output_cost = (output_tokens / 1000.0) * pricing["output"]
        
        total_cost = input_cost + output_cost
        
        logger.debug(
            f"Cost calculation: model={model}, input_tokens={input_tokens}, "
            f"output_tokens={output_tokens}, cost=${total_cost:.6f}"
        )
        
        return round(total_cost, 6)
    
    except Exception as e:
        logger.error(f"Failed to calculate cost: {e}")
        return 0.0


def format_cost(cost: float) -> str:
    """Format cost as human-readable string"""
    if cost < 0.0001:
        return f"${cost:.6f}"
    elif cost < 0.001:
        return f"${cost:.4f}"
    else:
        return f"${cost:.4f}"


# Example usage
if __name__ == "__main__":
    # Test cost calculations
    models = [
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "gpt-4o",
    ]
    
    for model in models:
        cost = calculate_cost(model, prompt_tokens=100, completion_tokens=50)
        print(f"{model}: {format_cost(cost)}")
