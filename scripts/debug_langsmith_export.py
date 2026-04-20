from src.core.env_loader import load_environment_variables

load_environment_variables()

import logging
from src.observability.langsmith_tracer import get_langsmith_tracer, SpanType, SpanStatus

logging.basicConfig(level=logging.DEBUG)

tracer = get_langsmith_tracer()
print(
    "tracer",
    {
        "enabled": tracer.enabled,
        "client": bool(tracer.langsmith_client),
        "project": tracer.project,
        "endpoint": tracer.endpoint,
        "verify_ssl": tracer.verify_ssl,
    },
)

trace = tracer.start_trace(name="debug_trace_probe", metadata={"probe": True})

with tracer.span("debug_llm", SpanType.LLM_CALL, trace_id=trace.trace_id) as span:
    span.inputs = {"model": "gpt-4o", "prompt": "hi"}
    span.outputs = {"response": "hello"}
    span.token_count = 5
    span.cost = 0.0001
    span.metadata = {
        "prompt_tokens": 3,
        "completion_tokens": 2,
        "total_tokens": 5,
        "total_cost": 0.0001,
        "ls_provider": "openai",
        "ls_model_name": "gpt-4o",
    }

tracer.end_trace(trace.trace_id, status=SpanStatus.SUCCESS)

print("trace_id", trace.trace_id)
