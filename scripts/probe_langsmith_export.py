from src.core.env_loader import load_environment_variables
load_environment_variables()

from src.ai.services.langsmith_service import LangSmithService
from src.observability.langsmith_tracer import get_langsmith_tracer

tracer = get_langsmith_tracer()
print("enabled", tracer.enabled)
print("has_client", tracer.langsmith_client is not None)
print("project", tracer.project)

service = LangSmithService(tracer=tracer)
result = service.trace(
    "conversation_submit_answer",
    {
        "session_id": "probe-session-001",
        "question": "What is your role?",
        "role": "Engineer",
        "analysis": {"intent": "probe"},
    },
)
print("trace_result", result)
