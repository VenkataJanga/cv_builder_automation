"""
LangSmith Tracing Hook - Observability and Debugging
Provides comprehensive tracing for LLM calls, workflow execution, and system performance
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import json
import uuid


class TraceLevel(str, Enum):
    """Trace level"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SpanType(str, Enum):
    """Types of trace spans"""
    LLM = "llm"
    CHAIN = "chain"
    TOOL = "tool"
    RETRIEVAL = "retrieval"
    WORKFLOW = "workflow"
    VALIDATION = "validation"
    EXTRACTION = "extraction"


class TraceSpan(BaseModel):
    """Individual trace span"""
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    trace_id: str
    name: str
    span_type: SpanType
    start_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    
    # Input/Output
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    
    # Status
    status: str = "running"  # running, success, error
    error: Optional[str] = None
    
    # Metrics
    token_usage: Optional[Dict[str, int]] = None
    model_name: Optional[str] = None
    
    # Feedback
    feedback_score: Optional[float] = None
    feedback_comment: Optional[str] = None


class TraceSession(BaseModel):
    """Trace session containing multiple spans"""
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_name: str
    user_id: Optional[str] = None
    start_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None
    spans: List[TraceSpan] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class LangSmithTracer:
    """LangSmith tracing implementation"""
    
    def __init__(
        self,
        project_name: str = "cv-builder-automation",
        api_key: Optional[str] = None,
        enabled: bool = True
    ):
        self.project_name = project_name
        self.api_key = api_key
        self.enabled = enabled
        self.active_sessions: Dict[str, TraceSession] = {}
        self.active_spans: Dict[str, TraceSpan] = {}
    
    def start_session(
        self,
        session_name: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Start a new trace session"""
        
        if not self.enabled:
            return "disabled"
        
        session = TraceSession(
            session_name=session_name,
            user_id=user_id,
            metadata=metadata or {},
            tags=tags or []
        )
        
        self.active_sessions[session.trace_id] = session
        
        return session.trace_id
    
    def end_session(self, trace_id: str):
        """End a trace session"""
        
        if not self.enabled or trace_id not in self.active_sessions:
            return
        
        session = self.active_sessions[trace_id]
        session.end_time = datetime.utcnow().isoformat()
        
        # Export to LangSmith
        self._export_session(session)
    
    def start_span(
        self,
        trace_id: str,
        name: str,
        span_type: SpanType,
        inputs: Optional[Dict[str, Any]] = None,
        parent_span_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Start a new span"""
        
        if not self.enabled or trace_id not in self.active_sessions:
            return "disabled"
        
        span = TraceSpan(
            trace_id=trace_id,
            name=name,
            span_type=span_type,
            parent_span_id=parent_span_id,
            inputs=inputs or {},
            metadata=metadata or {},
            tags=tags or []
        )
        
        self.active_spans[span.span_id] = span
        self.active_sessions[trace_id].spans.append(span)
        
        return span.span_id
    
    def end_span(
        self,
        span_id: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        token_usage: Optional[Dict[str, int]] = None
    ):
        """End a span"""
        
        if not self.enabled or span_id not in self.active_spans:
            return
        
        span = self.active_spans[span_id]
        span.end_time = datetime.utcnow().isoformat()
        
        # Calculate duration
        start = datetime.fromisoformat(span.start_time)
        end = datetime.fromisoformat(span.end_time)
        span.duration_ms = (end - start).total_seconds() * 1000
        
        # Set outputs and status
        span.outputs = outputs or {}
        span.status = "error" if error else "success"
        span.error = error
        span.token_usage = token_usage
        
        # Remove from active spans
        del self.active_spans[span_id]
    
    def add_feedback(
        self,
        span_id: str,
        score: float,
        comment: Optional[str] = None
    ):
        """Add feedback to a span"""
        
        if not self.enabled:
            return
        
        # Find span in all sessions
        for session in self.active_sessions.values():
            for span in session.spans:
                if span.span_id == span_id:
                    span.feedback_score = score
                    span.feedback_comment = comment
                    return
    
    def trace_llm_call(
        self,
        trace_id: str,
        model: str,
        messages: List[Dict[str, str]],
        response: str,
        token_usage: Dict[str, int],
        parent_span_id: Optional[str] = None
    ) -> str:
        """Trace an LLM call"""
        
        span_id = self.start_span(
            trace_id=trace_id,
            name=f"llm_call_{model}",
            span_type=SpanType.LLM,
            inputs={"messages": messages, "model": model},
            parent_span_id=parent_span_id,
            metadata={"model": model}
        )
        
        self.end_span(
            span_id=span_id,
            outputs={"response": response},
            token_usage=token_usage
        )
        
        return span_id
    
    def trace_retrieval(
        self,
        trace_id: str,
        query: str,
        results: List[Dict[str, Any]],
        retrieval_time_ms: float,
        parent_span_id: Optional[str] = None
    ) -> str:
        """Trace a retrieval operation"""
        
        span_id = self.start_span(
            trace_id=trace_id,
            name="retrieval",
            span_type=SpanType.RETRIEVAL,
            inputs={"query": query},
            parent_span_id=parent_span_id
        )
        
        self.end_span(
            span_id=span_id,
            outputs={
                "num_results": len(results),
                "results": results[:3]  # Only log top 3
            }
        )
        
        return span_id
    
    def trace_extraction(
        self,
        trace_id: str,
        input_text: str,
        extracted_data: Dict[str, Any],
        confidence_scores: Dict[str, float],
        parent_span_id: Optional[str] = None
    ) -> str:
        """Trace an extraction operation"""
        
        span_id = self.start_span(
            trace_id=trace_id,
            name="extraction",
            span_type=SpanType.EXTRACTION,
            inputs={"text_length": len(input_text)},
            parent_span_id=parent_span_id,
            metadata={"num_fields": len(extracted_data)}
        )
        
        # Calculate average confidence
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0
        
        self.end_span(
            span_id=span_id,
            outputs={
                "extracted_fields": list(extracted_data.keys()),
                "average_confidence": avg_confidence,
                "low_confidence_fields": [k for k, v in confidence_scores.items() if v < 0.7]
            }
        )
        
        return span_id
    
    def trace_validation(
        self,
        trace_id: str,
        data: Dict[str, Any],
        validation_results: Dict[str, Any],
        parent_span_id: Optional[str] = None
    ) -> str:
        """Trace a validation operation"""
        
        span_id = self.start_span(
            trace_id=trace_id,
            name="validation",
            span_type=SpanType.VALIDATION,
            inputs={"fields_validated": list(data.keys())},
            parent_span_id=parent_span_id
        )
        
        self.end_span(
            span_id=span_id,
            outputs={
                "overall_valid": validation_results.get("overall_valid"),
                "num_issues": len(validation_results.get("issues", [])),
                "critical_issues": [
                    i for i in validation_results.get("issues", [])
                    if i.get("severity") == "critical"
                ]
            }
        )
        
        return span_id
    
    def trace_workflow_node(
        self,
        trace_id: str,
        node_name: str,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        parent_span_id: Optional[str] = None
    ) -> str:
        """Trace a workflow node execution"""
        
        span_id = self.start_span(
            trace_id=trace_id,
            name=f"workflow_node_{node_name}",
            span_type=SpanType.WORKFLOW,
            inputs={"node_name": node_name},
            parent_span_id=parent_span_id,
            tags=["workflow", node_name]
        )
        
        # Calculate state changes
        state_changes = self._calculate_state_changes(state_before, state_after)
        
        self.end_span(
            span_id=span_id,
            outputs={
                "state_changes": state_changes,
                "errors": state_after.get("errors", []),
                "warnings": state_after.get("warnings", [])
            }
        )
        
        return span_id
    
    def get_session_summary(self, trace_id: str) -> Dict[str, Any]:
        """Get summary of a trace session"""
        
        if trace_id not in self.active_sessions:
            return {}
        
        session = self.active_sessions[trace_id]
        
        # Calculate statistics
        total_spans = len(session.spans)
        llm_calls = len([s for s in session.spans if s.span_type == SpanType.LLM])
        total_tokens = sum(
            s.token_usage.get("total_tokens", 0)
            for s in session.spans
            if s.token_usage
        )
        
        error_count = len([s for s in session.spans if s.status == "error"])
        avg_duration = sum(
            s.duration_ms for s in session.spans if s.duration_ms
        ) / total_spans if total_spans > 0 else 0
        
        return {
            "trace_id": trace_id,
            "session_name": session.session_name,
            "total_spans": total_spans,
            "llm_calls": llm_calls,
            "total_tokens": total_tokens,
            "error_count": error_count,
            "average_duration_ms": avg_duration,
            "tags": session.tags,
            "start_time": session.start_time,
            "end_time": session.end_time
        }
    
    def _calculate_state_changes(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any]
    ) -> List[str]:
        """Calculate what changed in state"""
        
        changes = []
        
        # Find new keys
        new_keys = set(after.keys()) - set(before.keys())
        if new_keys:
            changes.extend([f"added_{k}" for k in new_keys])
        
        # Find changed values
        for key in set(before.keys()) & set(after.keys()):
            if before[key] != after[key]:
                changes.append(f"modified_{key}")
        
        return changes
    
    def _export_session(self, session: TraceSession):
        """Export session to LangSmith"""
        
        # In production, would send to actual LangSmith API
        # For now, just log to console or file
        
        session_data = {
            "project": self.project_name,
            "trace_id": session.trace_id,
            "session_name": session.session_name,
            "user_id": session.user_id,
            "spans": [s.dict() for s in session.spans],
            "metadata": session.metadata,
            "tags": session.tags,
            "start_time": session.start_time,
            "end_time": session.end_time
        }
        
        # Log or save
        print(f"[LangSmith] Exported trace: {session.trace_id}")
        
        # Optionally save to file
        # with open(f"traces/{session.trace_id}.json", "w") as f:
        #     json.dump(session_data, f, indent=2)


# Context manager for easier tracing
class traced_span:
    """Context manager for automatic span tracking"""
    
    def __init__(
        self,
        tracer: LangSmithTracer,
        trace_id: str,
        name: str,
        span_type: SpanType,
        inputs: Optional[Dict[str, Any]] = None,
        parent_span_id: Optional[str] = None
    ):
        self.tracer = tracer
        self.trace_id = trace_id
        self.name = name
        self.span_type = span_type
        self.inputs = inputs
        self.parent_span_id = parent_span_id
        self.span_id = None
        self.outputs = None
        self.error = None
    
    def __enter__(self):
        self.span_id = self.tracer.start_span(
            trace_id=self.trace_id,
            name=self.name,
            span_type=self.span_type,
            inputs=self.inputs,
            parent_span_id=self.parent_span_id
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        error = str(exc_val) if exc_val else None
        self.tracer.end_span(
            span_id=self.span_id,
            outputs=self.outputs,
            error=error
        )
        return False  # Don't suppress exceptions
    
    def set_outputs(self, outputs: Dict[str, Any]):
        """Set outputs for the span"""
        self.outputs = outputs
