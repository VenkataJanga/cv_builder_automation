"""
LangSmith Tracing Integration

Provides comprehensive tracing and observability for the CV processing workflow:
- Span tracking for each processing step
- Input/output capture
- Performance metrics
- Error tracking
- Custom metadata tags
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import logging
import json
import uuid
import requests

# Optional LangSmith import
try:
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    Client = None

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SpanType(str, Enum):
    """Types of spans for tracing"""
    WORKFLOW = "workflow"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    ENHANCEMENT = "enhancement"
    FOLLOWUP = "followup"
    RETRIEVAL = "retrieval"
    LLM_CALL = "llm_call"
    TOOL_USE = "tool_use"
    EXPORT = "export"


class SpanStatus(str, Enum):
    """Status of a span"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class Span:
    """Represents a traced operation"""
    span_id: str
    parent_span_id: Optional[str]
    name: str
    span_type: SpanType
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.PENDING
    
    # Data
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    # Metrics
    duration_ms: Optional[float] = None
    token_count: Optional[int] = None
    cost: Optional[float] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def end(self, status: SpanStatus = SpanStatus.SUCCESS, error: Optional[str] = None):
        """End the span"""
        self.end_time = _utc_now()
        self.status = status
        self.error = error
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "type": self.span_type.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "error": self.error,
            "token_count": self.token_count,
            "cost": self.cost,
            "tags": self.tags,
            "metadata": self.metadata
        }


@dataclass
class Trace:
    """Complete trace for a workflow execution"""
    trace_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.PENDING
    
    spans: List[Span] = field(default_factory=list)
    
    # Workflow metadata
    workflow_type: str = "cv_processing"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Metrics
    total_duration_ms: Optional[float] = None
    total_tokens: int = 0
    total_cost: float = 0.0
    
    # Tags
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def end(self, status: SpanStatus = SpanStatus.SUCCESS):
        """End the trace"""
        self.end_time = _utc_now()
        self.status = status
        if self.start_time and self.end_time:
            self.total_duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        
        # Calculate totals
        for span in self.spans:
            if span.token_count:
                self.total_tokens += span.token_count
            if span.cost:
                self.total_cost += span.cost
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary"""
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "workflow_type": self.workflow_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_ms": self.total_duration_ms,
            "status": self.status.value,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "tags": self.tags,
            "metadata": self.metadata,
            "spans": [span.to_dict() for span in self.spans]
        }


class LangSmithTracer:
    """
    LangSmith-compatible tracer for CV processing workflow
    
    Features:
    - Hierarchical span tracking
    - Automatic context propagation
    - Performance metrics collection
    - Error tracking and reporting
    - Integration with LangSmith API
    
    Usage:
        tracer = LangSmithTracer()
        
        # Start workflow trace
        trace = tracer.start_trace("cv_processing_workflow")
        
        # Track individual operations
        with tracer.span("extraction", SpanType.EXTRACTION, trace_id=trace.trace_id) as span:
            span.inputs = {"transcript": transcript}
            result = extract_cv_data(transcript)
            span.outputs = {"extracted_data": result}
        
        # End trace
        tracer.end_trace(trace.trace_id)
    """
    
    def __init__(
        self,
        project: Optional[str] = None,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        enabled: bool = True,
        verify_ssl: bool = True,
    ):
        from src.observability.constants import get_langsmith_project_name

        self.project = project or get_langsmith_project_name()
        self.api_key = api_key
        self.endpoint = endpoint or "https://api.smith.langchain.com"
        self.enabled = enabled
        self.verify_ssl = verify_ssl
        
        # LangSmith client
        self.langsmith_client = None
        if self.enabled and LANGSMITH_AVAILABLE and self.api_key:
            try:
                session = None
                if not self.verify_ssl:
                    session = requests.Session()
                    session.verify = False
                    logger.warning("LangSmith SSL verification is disabled for this runtime")

                self.langsmith_client = Client(
                    api_key=self.api_key,
                    api_url=self.endpoint,
                    session=session,
                )
                logger.info("LangSmith client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith client: {e}")
                self.langsmith_client = None
        
        # Active traces
        self.traces: Dict[str, Trace] = {}
        self.current_trace_id: Optional[str] = None
        self.span_stack: List[str] = []
        
        logger.info(f"LangSmith tracer initialized for project: {project}")
    
    def start_trace(
        self,
        name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Trace:
        """
        Start a new trace
        
        Args:
            name: Name of the trace
            user_id: User ID for the trace
            session_id: Session ID for the trace
            tags: Tags for categorization
            metadata: Additional metadata
            
        Returns:
            Created trace
        """
        trace_id = session_id or str(uuid.uuid4())
        
        trace = Trace(
            trace_id=trace_id,
            name=name,
            start_time=_utc_now(),
            user_id=user_id,
            session_id=session_id,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.traces[trace_id] = trace
        self.current_trace_id = trace_id
        
        logger.info(f"Started trace: {name} (ID: {trace_id})")
        
        if self.enabled:
            self._send_trace_start(trace)
        
        return trace
    
    def end_trace(
        self,
        trace_id: str,
        status: SpanStatus = SpanStatus.SUCCESS
    ) -> Trace:
        """
        End a trace
        
        Args:
            trace_id: ID of the trace to end
            status: Final status of the trace
            
        Returns:
            Ended trace
        """
        if trace_id not in self.traces:
            raise ValueError(f"Trace {trace_id} not found")
        
        trace = self.traces[trace_id]
        trace.end(status)
        
        logger.info(
            f"Ended trace: {trace.name} "
            f"(Duration: {trace.total_duration_ms:.2f}ms, "
            f"Tokens: {trace.total_tokens}, "
            f"Cost: ${trace.total_cost:.4f})"
        )
        
        if self.enabled:
            self._send_trace_end(trace)
        
        return trace
    
    def span(
        self,
        name: str,
        span_type: SpanType,
        trace_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "SpanContext":
        """
        Create a span context manager
        
        Args:
            name: Name of the span
            span_type: Type of span
            trace_id: Trace ID (uses current if not provided)
            tags: Tags for categorization
            metadata: Additional metadata
            
        Returns:
            Span context manager
        """
        trace_id = trace_id or self.current_trace_id
        if not trace_id:
            raise ValueError("No active trace. Call start_trace() first")
        
        return SpanContext(
            tracer=self,
            trace_id=trace_id,
            name=name,
            span_type=span_type,
            tags=tags or [],
            metadata=metadata or {}
        )
    
    def _create_span(
        self,
        trace_id: str,
        name: str,
        span_type: SpanType,
        tags: List[str],
        metadata: Dict[str, Any]
    ) -> Span:
        """Create and register a new span"""
        span_id = str(uuid.uuid4())
        parent_span_id = self.span_stack[-1] if self.span_stack else None
        
        span = Span(
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=name,
            span_type=span_type,
            start_time=_utc_now(),
            tags=tags,
            metadata=metadata
        )
        
        trace = self.traces[trace_id]
        trace.spans.append(span)
        
        self.span_stack.append(span_id)
        
        logger.debug(f"Started span: {name} (ID: {span_id})")
        
        if self.enabled:
            self._send_span_start(trace_id, span)
        
        return span
    
    def _end_span(
        self,
        trace_id: str,
        span_id: str,
        status: SpanStatus,
        error: Optional[str] = None
    ):
        """End a span"""
        trace = self.traces[trace_id]
        span = next((s for s in trace.spans if s.span_id == span_id), None)
        
        if span:
            span.end(status, error)
            
            logger.debug(
                f"Ended span: {span.name} "
                f"(Duration: {span.duration_ms:.2f}ms, Status: {status.value})"
            )
            
            if self.enabled:
                self._send_span_end(trace_id, span)
        
        if self.span_stack and self.span_stack[-1] == span_id:
            self.span_stack.pop()
    
    def track_llm_call(
        self,
        trace_id: str,
        model: str,
        prompt: str,
        response: str,
        tokens: int,
        cost: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track an LLM API call
        
        Args:
            trace_id: Trace ID
            model: Model name
            prompt: Input prompt
            response: Model response
            tokens: Token count
            cost: API cost
            metadata: Additional metadata
        """
        with self.span(
            name=f"llm_call_{model}",
            span_type=SpanType.LLM_CALL,
            trace_id=trace_id,
            metadata=metadata or {}
        ) as span:
            span.inputs = {
                "model": model,
                "prompt": prompt[:500]  # Truncate for storage
            }
            span.outputs = {
                "response": response[:500]  # Truncate for storage
            }
            span.token_count = tokens
            span.cost = cost
    
    def track_retrieval(
        self,
        trace_id: str,
        query: str,
        results: List[Dict[str, Any]],
        retrieval_time_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track a retrieval operation
        
        Args:
            trace_id: Trace ID
            query: Search query
            results: Retrieved results
            retrieval_time_ms: Time taken
            metadata: Additional metadata
        """
        with self.span(
            name="retrieval",
            span_type=SpanType.RETRIEVAL,
            trace_id=trace_id,
            metadata=metadata or {}
        ) as span:
            span.inputs = {"query": query}
            span.outputs = {
                "result_count": len(results),
                "top_scores": [r.get("score", 0) for r in results[:3]]
            }
            span.duration_ms = retrieval_time_ms
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID"""
        return self.traces.get(trace_id)
    
    def get_trace_summary(self, trace_id: str) -> Dict[str, Any]:
        """Get a summary of a trace"""
        trace = self.get_trace(trace_id)
        if not trace:
            return {}
        
        return {
            "trace_id": trace_id,
            "name": trace.name,
            "status": trace.status.value,
            "duration_ms": trace.total_duration_ms,
            "span_count": len(trace.spans),
            "total_tokens": trace.total_tokens,
            "total_cost": trace.total_cost,
            "error_count": sum(1 for s in trace.spans if s.status == SpanStatus.ERROR)
        }
    
    def export_trace(self, trace_id: str, format: str = "json") -> str:
        """Export a trace to file"""
        trace = self.get_trace(trace_id)
        if not trace:
            raise ValueError(f"Trace {trace_id} not found")
        
        if format == "json":
            return json.dumps(trace.to_dict(), indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    # Integration with LangSmith API (mock implementations)
    
    def _send_trace_start(self, trace: Trace):
        """Send trace start to LangSmith"""
        logger.debug(f"Sending trace start to LangSmith: {trace.trace_id}")
        # In production: POST to LangSmith API
    
    def _send_trace_end(self, trace: Trace):
        """Send trace end to LangSmith"""
        logger.debug(f"Sending trace end to LangSmith: {trace.trace_id}")
        if self.langsmith_client:
            try:
                logger.info(
                    "Attempting LangSmith export for trace %s to project %s",
                    trace.trace_id,
                    self.project,
                )
                # Convert trace to LangSmith format
                run_data = {
                    "name": trace.name,
                    "run_type": "chain",
                    "project_name": self.project,
                    "inputs": {"session_id": trace.session_id, "workflow_type": trace.workflow_type},
                    "outputs": {"status": trace.status.value, "total_tokens": trace.total_tokens},
                    "start_time": trace.start_time,
                    "end_time": trace.end_time,
                    "extra": {
                        "metadata": trace.metadata,
                        "tags": trace.tags,
                        "total_cost": trace.total_cost,
                        "total_duration_ms": trace.total_duration_ms
                    }
                }
                self.langsmith_client.create_run(**run_data)
                logger.info(f"Trace {trace.trace_id} sent to LangSmith")
            except Exception as e:
                logger.error(f"Failed to send trace to LangSmith: {e}")
        else:
            logger.debug("LangSmith client not available, skipping export")
    
    def _send_span_start(self, trace_id: str, span: Span):
        """Send span start to LangSmith"""
        logger.debug(f"Sending span start to LangSmith: {span.span_id}")
        # In production: POST to LangSmith API
    
    def _send_span_end(self, trace_id: str, span: Span):
        """Send span end to LangSmith"""
        logger.debug(f"Sending span end to LangSmith: {span.span_id}")
        # In production: POST to LangSmith API


class SpanContext:
    """Context manager for spans"""
    
    def __init__(
        self,
        tracer: LangSmithTracer,
        trace_id: str,
        name: str,
        span_type: SpanType,
        tags: List[str],
        metadata: Dict[str, Any]
    ):
        self.tracer = tracer
        self.trace_id = trace_id
        self.name = name
        self.span_type = span_type
        self.tags = tags
        self.metadata = metadata
        self.span: Optional[Span] = None
    
    def __enter__(self) -> Span:
        """Enter the span context"""
        self.span = self.tracer._create_span(
            self.trace_id,
            self.name,
            self.span_type,
            self.tags,
            self.metadata
        )
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the span context"""
        if self.span:
            if exc_type is not None:
                # Error occurred
                self.tracer._end_span(
                    self.trace_id,
                    self.span.span_id,
                    SpanStatus.ERROR,
                    str(exc_val)
                )
            else:
                # Success
                self.tracer._end_span(
                    self.trace_id,
                    self.span.span_id,
                    SpanStatus.SUCCESS
                )
        return False  # Don't suppress exceptions


# Global tracer instance
_tracer_instance: Optional[LangSmithTracer] = None


def get_langsmith_tracer() -> LangSmithTracer:
    """Get the global LangSmith tracer instance"""
    global _tracer_instance
    if _tracer_instance is None:
        import os
        enabled = os.getenv("LANGSMITH_ENABLED", "false").lower() == "true"
        api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
        verify_ssl = os.getenv("LANGSMITH_VERIFY_SSL", "true").lower() == "true"
        from src.observability.constants import get_langsmith_project_name

        project = get_langsmith_project_name()
        endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        
        _tracer_instance = LangSmithTracer(
            project=project,
            api_key=api_key,
            endpoint=endpoint,
            enabled=enabled,
            verify_ssl=verify_ssl,
        )
    return _tracer_instance
