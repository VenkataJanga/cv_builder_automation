# LangSmith Metrics Integration Fix

## Problem Summary
LangSmith dashboard showed Traces data but missing metrics in:
- LLM Calls (count)
- Cost & Tokens (total cost and tokens)
- Input/Output Tokens (prompt and completion tokens)

## Root Causes Identified
1. **Span Export Stub**: `_send_span_end()` was incomplete - only logged, didn't actually send spans to LangSmith API
2. **Missing Token Capture**: LLM calls didn't capture OpenAI `response.usage` data (prompt_tokens, completion_tokens)
3. **No Cost Calculation**: No mechanism to convert tokens to estimated USD cost
4. **Missing Tracer Integration**: LLMService and EnhancementAgent didn't integrate with tracer to track metrics
5. **No Span Recursion**: Parent traces weren't sending child spans to LangSmith

## Solutions Implemented

### 1. Implemented Span Export (langsmith_tracer.py)
- **File**: `src/observability/langsmith_tracer.py`
- **Change**: Replaced `_send_span_end()` stub with full implementation
- **What it does**:
  - Maps span types to LangSmith run_type (e.g., LLM_CALL → "llm", EXTRACTION → "tool")
  - Builds span data structure with inputs, outputs, token_count, cost
  - Sends individual spans to LangSmith as separate runs
  - Links child spans to parent trace via parent_run_id
  - Includes metadata with duration, tags, and metrics

### 2. Fixed Trace End Handling (langsmith_tracer.py)
- **File**: `src/observability/langsmith_tracer.py`
- **Change**: Updated `_send_trace_end()` to recursively send child spans
- **What it does**:
  - Iterates through all spans in trace before sending parent
  - Each span sent via `_send_span_end()` with metrics
  - Parent trace sent last to establish hierarchy
  - Includes aggregated metrics (total_tokens, total_cost) at trace level

### 3. Created Token Cost Calculator (NEW FILE)
- **File**: `src/ai/services/token_cost_calculator.py`
- **What it does**:
  - Calculates API costs based on token count and model
  - Supports GPT-4, GPT-3.5, GPT-4o models with current pricing
  - Function: `calculate_cost(model, prompt_tokens, completion_tokens)` → cost in USD
  - Gracefully falls back to default pricing for unknown models

### 4. Extended LLMService with Usage Tracking (llm_service.py)
- **File**: `src/ai/services/llm_service.py`
- **Changes**:
  - Added `call_with_usage()` method that returns (response, usage_data)
  - Extracts OpenAI response.usage data: prompt_tokens, completion_tokens, total_tokens
  - Calculates cost using token_cost_calculator
  - Added `_extract_usage_data()` to parse response.usage safely
  - Added `_track_llm_call_with_tracer()` to automatically track metrics if tracer is active

### 5. Automatic Tracer Integration (llm_service.py)
- **File**: `src/ai/services/llm_service.py`
- **What it does**:
  - When LLMService.call_with_usage() executes, it:
    1. Gets global tracer instance
    2. Checks if tracer is enabled and active trace exists
    3. Creates LLM_CALL span with metrics (token_count, cost)
    4. Adds span to current trace
    5. Updates trace-level totals (total_tokens, total_cost)
  - Fails gracefully if tracer not available
  - No changes needed to calling code - automatic integration!

### 6. Updated EnhancementAgent (enhancement_agent.py)
- **File**: `src/ai/agents/enhancement_agent.py`
- **Changes**:
  - Switched from direct OpenAI calls to LLMService
  - Methods now use `llm_service.call_with_usage()`
  - Automatic token tracking for all enhancement operations
  - All methods (professionalize_transcript, structure_cv_transcript, enhance_summary_text, enhance_achievement_text)

## Data Flow with Fixes

```
LLM Call occurs
    ↓
LLMService.call_with_usage()
    ↓
[Makes OpenAI API call]
    ↓
[Extracts response.usage → tokens & cost]
    ↓
[Auto-creates LLM_CALL span in active trace]
    ↓
Span has:
  - token_count: prompt_tokens + completion_tokens
  - cost: calculated in USD
  - inputs: model, prompt (truncated)
  - outputs: response (truncated)
    ↓
[Trace ends or metrics aggregated]
    ↓
_send_trace_end() sends all spans + parent trace
    ↓
Each span sent to LangSmith with proper run_type
    ↓
LangSmith Dashboard Populates:
  ✅ LLM Calls: Count of LLM_CALL spans
  ✅ Tokens: total_tokens from span.token_count
  ✅ Cost: total_cost summed across spans
  ✅ Input/Output Tokens: prompt/completion_tokens in span
```

## Testing the Fix

To verify the fix works:

1. **Enable LangSmith**:
   ```
   LANGSMITH_ENABLED=true
   LANGSMITH_API_KEY=<your-key>
   ```

2. **Run a CV workflow** that triggers LLM calls (normalization, enhancement, etc.)

3. **Check LangSmith Dashboard**:
   - Go to Traces tab - should see trace with LLM_CALL spans
   - Check individual span details - should see token_count and cost
   - Dashboard metrics panels should now populate:
     - LLM Calls: [count of spans with SpanType.LLM_CALL]
     - Input Tokens: [sum of prompt_tokens]
     - Output Tokens: [sum of completion_tokens]
     - Cost & Tokens: [total_tokens and cost]

## Files Modified

1. ✅ `src/observability/langsmith_tracer.py`
   - `_send_span_end()`: Full implementation with LangSmith API calls
   - `_send_trace_end()`: Recursive span sending

2. ✅ `src/ai/services/llm_service.py`
   - Added `call_with_usage()` method
   - Added `_extract_usage_data()` helper
   - Added `_track_llm_call_with_tracer()` for automatic integration

3. ✅ `src/ai/services/token_cost_calculator.py` (NEW)
   - Cost calculation utilities

4. ✅ `src/ai/agents/enhancement_agent.py`
   - Switched to LLMService for automatic tracking

## Backward Compatibility

- `LLMService.call()` still works unchanged (calls `call_with_usage()` internally)
- Old code that calls `llm_service.call()` continues to work
- Tracer integration is automatic and transparent
- No breaking changes to any APIs

## Performance Impact

- Minimal: Token counting happens at response time (negligible)
- Cost calculation is O(1) lookup and arithmetic
- Span tracking adds metrics to in-memory Span objects
- No additional API calls until trace end

## Future Enhancements

1. Add support for other LLM providers (Claude, Gemini, etc.)
2. Track token usage per model for reporting
3. Add cost budgeting/alerting
4. Cache cost calculations per model/endpoint
5. Support batch token usage analysis
