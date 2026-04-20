from src.ai.services.langsmith_service import LangSmithService
from src.observability.langsmith_tracer import SpanStatus


class _FakeSpanContext:
    def __init__(self) -> None:
        self.inputs = {}
        self.outputs = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class _FakeTracer:
    def __init__(self, enabled=True, client=True) -> None:
        self.enabled = enabled
        self.langsmith_client = object() if client else None
        self.project = "cv_builder_automation"
        self.started = []
        self.ended = []

    def start_trace(self, name, tags=None, metadata=None):
        trace = type("Trace", (), {"trace_id": "trace-123"})()
        self.started.append({"name": name, "tags": tags or [], "metadata": metadata or {}})
        return trace

    def span(self, name, span_type, trace_id=None, metadata=None):
        self.last_span = {
            "name": name,
            "span_type": span_type,
            "trace_id": trace_id,
            "metadata": metadata or {},
        }
        return _FakeSpanContext()

    def end_trace(self, trace_id, status=SpanStatus.SUCCESS):
        self.ended.append({"trace_id": trace_id, "status": status})


class _FailingTracer(_FakeTracer):
    def start_trace(self, name, tags=None, metadata=None):
        raise RuntimeError("boom")


def test_langsmith_service_exports_trace_metadata_without_breaking_flow():
    service = LangSmithService(tracer=_FakeTracer(enabled=True, client=True))

    result = service.trace(
        "conversation_submit_answer",
        {"session_id": "session-1", "question": "What is your role?"},
    )

    assert result["langsmith_enabled"] is True
    assert result["run_name"] == "conversation_submit_answer"
    assert result["trace_id"] == "trace-123"
    assert result["project"] == "cv_builder_automation"
    assert result["exported"] is True
    assert result["payload_keys"] == ["session_id", "question"]


def test_langsmith_service_falls_back_safely_on_tracing_error():
    service = LangSmithService(tracer=_FailingTracer())

    result = service.trace("conversation_submit_answer", {"session_id": "session-1"})

    assert result["langsmith_enabled"] is False
    assert result["run_name"] == "conversation_submit_answer"
    assert result["payload_keys"] == ["session_id"]
    assert "error" in result