"""
LangSmith Tracing Integration.

Provides comprehensive tracing for CV processing workflows with:
- Automatic span creation
- Metadata tracking
- Error logging
- Performance metrics
"""

import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import json

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """A trace span representing an operation"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    parent_id: Optional[str] = None
    span_id: str = field(default_factory=lambda: str(time.time_ns()))
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export"""
        return {
            'name': self.name,
            'span_id': self.span_id,
            'parent_id': self.parent_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'metadata': self.metadata,
            'error': self.error
        }


class LangSmithTracer:
    """
    LangSmith-compatible tracer for CV processing workflows.
    
    Provides:
    - Hierarchical span tracking
    - Automatic performance monitoring
    - Error capture
    - Export to LangSmith format
    """
    
    def __init__(
        self,
        project_name: str = "cv-builder-automation",
        api_key: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Initialize tracer.
        
        Args:
            project_name: LangSmith project name
            api_key: LangSmith API key
            enabled: Whether tracing is enabled
        """
        self.project_name = project_name
        self.api_key = api_key
        self.enabled = enabled
        
        self.spans: Dict[str, TraceSpan] = {}
        self.current_span_id: Optional[str] = None
        self.root_spans: List[str] = []
        
        logger.info(f"LangSmithTracer initialized (enabled={enabled})")
    
    @contextmanager
    def trace(
        self,
        name: str,
        inputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracing an operation.
        
        Usage:
            with tracer.trace("extraction", inputs={"text": text}):
                result = extract_data(text)
        
        Args:
            name: Name of the operation
            inputs: Input parameters
            metadata: Additional metadata
        """
        if not self.enabled:
            yield None
            return
        
        # Create span
        span = TraceSpan(
            name=name,
            start_time=time.time(),
            inputs=inputs or {},
            metadata=metadata or {},
            parent_id=self.current_span_id
        )
        
        # Store span
        self.spans[span.span_id] = span
        
        # Track root spans
        if not span.parent_id:
            self.root_spans.append(span.span_id)
        
        # Set as current
        previous_span_id = self.current_span_id
        self.current_span_id = span.span_id
        
        try:
            yield span
        except Exception as e:
            # Capture error
            span.error = str(e)
            logger.error(f"Error in traced operation '{name}': {e}")
            raise
        finally:
            # Complete span
            span.end_time = time.time()
            
            # Restore previous span
            self.current_span_id = previous_span_id
            
            # Log span completion
            logger.debug(
                f"Span '{name}' completed in {span.duration:.3f}s "
                f"(span_id={span.span_id})"
            )
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to current span"""
        if self.current_span_id and self.current_span_id in self.spans:
            self.spans[self.current_span_id].metadata[key] = value
    
    def set_output(self, outputs: Dict[str, Any]):
        """Set output for current span"""
        if self.current_span_id and self.current_span_id in self.spans:
            self.spans[self.current_span_id].outputs = outputs
    
    def log_event(self, event_name: str, data: Optional[Dict[str, Any]] = None):
        """Log an event in the current span"""
        if self.current_span_id and self.current_span_id in self.spans:
            span = self.spans[self.current_span_id]
            if 'events' not in span.metadata:
                span.metadata['events'] = []
            
            span.metadata['events'].append({
                'name': event_name,
                'timestamp': time.time(),
                'data': data or {}
            })
    
    def get_trace_tree(self, root_span_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get hierarchical trace tree.
        
        Args:
            root_span_id: Root span ID (None = all roots)
        
        Returns:
            Nested dictionary representing trace tree
        """
        if root_span_id:
            roots = [root_span_id]
        else:
            roots = self.root_spans
        
        def build_tree(span_id: str) -> Dict[str, Any]:
            span = self.spans[span_id]
            children = [
                build_tree(sid)
                for sid, s in self.spans.items()
                if s.parent_id == span_id
            ]
            
            tree = span.to_dict()
            if children:
                tree['children'] = children
            
            return tree
        
        if len(roots) == 1:
            return build_tree(roots[0])
        else:
            return {
                'roots': [build_tree(root_id) for root_id in roots]
            }
    
    def export_to_langsmith_format(self) -> List[Dict[str, Any]]:
        """
        Export traces in LangSmith-compatible format.
        
        Returns:
            List of trace records
        """
        records = []
        
        for span in self.spans.values():
            record = {
                'id': span.span_id,
                'parent_id': span.parent_id,
                'name': span.name,
                'start_time': datetime.fromtimestamp(span.start_time).isoformat(),
                'end_time': datetime.fromtimestamp(span.end_time).isoformat() if span.end_time else None,
                'duration_ms': span.duration * 1000 if span.duration else None,
                'inputs': span.inputs,
                'outputs': span.outputs,
                'metadata': span.metadata,
                'error': span.error,
                'project_name': self.project_name
            }
            records.append(record)
        
        return records
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get aggregate metrics from traces.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.spans:
            return {}
        
        total_spans = len(self.spans)
        completed_spans = [s for s in self.spans.values() if s.end_time]
        error_spans = [s for s in self.spans.values() if s.error]
        
        durations = [s.duration for s in completed_spans if s.duration]
        
        metrics = {
            'total_spans': total_spans,
            'completed_spans': len(completed_spans),
            'error_spans': len(error_spans),
            'error_rate': len(error_spans) / total_spans if total_spans > 0 else 0,
        }
        
        if durations:
            metrics.update({
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'total_duration': sum(durations)
            })
        
        # Per-operation metrics
        operations = {}
        for span in self.spans.values():
            if span.name not in operations:
                operations[span.name] = {
                    'count': 0,
                    'errors': 0,
                    'durations': []
                }
            
            operations[span.name]['count'] += 1
            if span.error:
                operations[span.name]['errors'] += 1
            if span.duration:
                operations[span.name]['durations'].append(span.duration)
        
        for op_name, op_data in operations.items():
            if op_data['durations']:
                op_data['avg_duration'] = sum(op_data['durations']) / len(op_data['durations'])
            del op_data['durations']  # Remove raw durations
        
        metrics['by_operation'] = operations
        
        return metrics
    
    def clear(self):
        """Clear all traces"""
        self.spans.clear()
        self.root_spans.clear()
        self.current_span_id = None
        logger.info("Traces cleared")
    
    def save_to_file(self, filepath: str):
        """Save traces to JSON file"""
        trace_data = {
            'project_name': self.project_name,
            'timestamp': datetime.utcnow().isoformat(),
            'traces': self.export_to_langsmith_format(),
            'metrics': self.get_metrics(),
            'trace_tree': self.get_trace_tree()
        }
        
        with open(filepath, 'w') as f:
            json.dump(trace_data, f, indent=2)
        
        logger.info(f"Traces saved to {filepath}")
    
    async def send_to_langsmith(self):
        """
        Send traces to LangSmith API.
        
        Note: This is a placeholder. Real implementation would use
        the LangSmith SDK to send traces.
        """
        if not self.api_key:
            logger.warning("LangSmith API key not configured, skipping upload")
            return
        
        try:
            traces = self.export_to_langsmith_format()
            
            # TODO: Use actual LangSmith SDK
            # from langsmith import Client
            # client = Client(api_key=self.api_key)
            # for trace in traces:
            #     client.create_run(**trace)
            
            logger.info(f"Would send {len(traces)} traces to LangSmith")
            
        except Exception as e:
            logger.error(f"Failed to send traces to LangSmith: {e}")


class TracingMiddleware:
    """
    Middleware for automatic tracing of service calls.
    
    Usage:
        middleware = TracingMiddleware(tracer)
        service = middleware.wrap(MyService(...), "my_service")
    """
    
    def __init__(self, tracer: LangSmithTracer):
        """
        Initialize middleware.
        
        Args:
            tracer: Tracer instance
        """
        self.tracer = tracer
    
    def wrap(self, service: Any, service_name: str) -> Any:
        """
        Wrap a service with automatic tracing.
        
        Args:
            service: Service instance to wrap
            service_name: Name for tracing
        
        Returns:
            Wrapped service with tracing
        """
        class TracedService:
            def __init__(self, svc, tracer, name):
                self._service = svc
                self._tracer = tracer
                self._name = name
            
            def __getattr__(self, attr):
                original_method = getattr(self._service, attr)
                
                if not callable(original_method):
                    return original_method
                
                async def traced_method(*args, **kwargs):
                    with self._tracer.trace(
                        f"{self._name}.{attr}",
                        inputs={'args': str(args)[:100], 'kwargs': str(kwargs)[:100]}
                    ):
                        result = await original_method(*args, **kwargs)
                        self._tracer.set_output({'result': str(result)[:100]})
                        return result
                
                return traced_method
        
        return TracedService(service, self.tracer, service_name)
