from src.ai.services.llm_service import LLMService


class _FakeTracer:
    def __init__(self, enabled=True, current_trace_id="trace-1"):
        self.enabled = enabled
        self.current_trace_id = current_trace_id
        self.calls = []

    def track_llm_call(self, **kwargs):
        self.calls.append(kwargs)


class _FakeTracerFactory:
    def __init__(self, tracer):
        self._tracer = tracer

    def __call__(self):
        return self._tracer


def test_track_llm_call_with_tracer_emits_llm_span(monkeypatch):
    fake_tracer = _FakeTracer(enabled=True, current_trace_id="trace-123")

    from src.observability import langsmith_tracer as tracer_module

    monkeypatch.setattr(
        tracer_module,
        "get_langsmith_tracer",
        _FakeTracerFactory(fake_tracer),
    )

    service = object.__new__(LLMService)

    service._track_llm_call_with_tracer(
        model="gpt-4o",
        prompt="hello",
        response="world",
        usage_data={
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "cost": 0.0002,
        },
    )

    assert len(fake_tracer.calls) == 1
    call = fake_tracer.calls[0]
    assert call["trace_id"] == "trace-123"
    assert call["model"] == "gpt-4o"
    assert call["tokens"] == 15
    assert call["cost"] == 0.0002
    assert call["metadata"]["prompt_tokens"] == 10
    assert call["metadata"]["completion_tokens"] == 5
    assert call["metadata"]["total_tokens"] == 15


def test_track_llm_call_with_tracer_no_active_trace(monkeypatch):
    fake_tracer = _FakeTracer(enabled=True, current_trace_id=None)

    from src.observability import langsmith_tracer as tracer_module

    monkeypatch.setattr(
        tracer_module,
        "get_langsmith_tracer",
        _FakeTracerFactory(fake_tracer),
    )

    service = object.__new__(LLMService)

    service._track_llm_call_with_tracer(
        model="gpt-4o",
        prompt="hello",
        response="world",
        usage_data={"total_tokens": 1, "cost": 0.0},
    )

    assert fake_tracer.calls == []
