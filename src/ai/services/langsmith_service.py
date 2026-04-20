from __future__ import annotations

import logging
from typing import Any

from src.observability.langsmith_tracer import SpanStatus, SpanType, get_langsmith_tracer


logger = logging.getLogger(__name__)


class LangSmithService:
    def __init__(self, tracer=None) -> None:
        self.tracer = tracer or get_langsmith_tracer()

    def trace(self, run_name: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload_dict = payload if isinstance(payload, dict) else {}
        payload_keys = list(payload_dict.keys())
        trace = None

        try:
            trace = self.tracer.start_trace(
                name=run_name,
                tags=["conversation"],
                metadata={
                    "source": "conversation_service",
                    "session_id": payload_dict.get("session_id"),
                },
            )

            with self.tracer.span(
                "conversation_submit_answer",
                SpanType.WORKFLOW,
                trace_id=trace.trace_id,
                metadata={"run_name": run_name},
            ) as span:
                span.inputs = payload_dict
                span.outputs = {"payload_keys": payload_keys}

            self.tracer.end_trace(trace.trace_id, status=SpanStatus.SUCCESS)

            return {
                "langsmith_enabled": bool(self.tracer.enabled and self.tracer.langsmith_client),
                "run_name": run_name,
                "payload_keys": payload_keys,
                "trace_id": trace.trace_id,
                "project": self.tracer.project,
                "exported": bool(self.tracer.enabled and self.tracer.langsmith_client),
            }
        except Exception as exc:
            logger.warning("LangSmith trace capture failed for %s: %s", run_name, exc)
            if trace is not None:
                try:
                    self.tracer.end_trace(trace.trace_id, status=SpanStatus.ERROR)
                except Exception:
                    logger.debug("Failed to close errored LangSmith trace", exc_info=True)

            return {
                "langsmith_enabled": False,
                "run_name": run_name,
                "payload_keys": payload_keys,
                "error": str(exc),
            }
