#!/usr/bin/env python3
"""
Test LangSmith Integration
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.observability.langsmith_tracer import get_langsmith_tracer, SpanType

def test_langsmith_integration():
    print('🚀 Testing Complete Tracing Workflow...')

    # Get tracer
    tracer = get_langsmith_tracer()
    print(f'✅ Tracer enabled: {tracer.enabled}')
    print(f'✅ LangSmith client available: {tracer.langsmith_client is not None}')

    # Create a test trace
    session_id = 'test-session-langsmith-integration'
    trace = tracer.start_trace(
        name='test_cv_processing_workflow',
        session_id=session_id,
        user_id='test-user',
        metadata={'test': True, 'integration': 'langsmith'}
    )
    print(f'✅ Trace created: {trace.trace_id}')

    # Add some spans
    with tracer.span('test_extraction', SpanType.EXTRACTION, trace_id=session_id) as span:
        span.inputs = {'test_data': 'sample cv text'}
        span.outputs = {'extracted': ['name', 'email', 'experience']}
        span.metadata = {'model': 'gpt-4', 'tokens': 150}

    with tracer.span('test_validation', SpanType.VALIDATION, trace_id=session_id) as span:
        span.inputs = {'rules': ['required_fields']}
        span.outputs = {'valid': True, 'score': 0.95}

    # End trace
    tracer.end_trace(session_id)
    print('✅ Trace completed and exported to LangSmith!')

    # Verify trace data
    summary = tracer.get_trace_summary(session_id)
    print(f'📊 Trace Summary: {summary["span_count"]} spans, {summary["duration_ms"]:.1f}ms total')

    print('🎉 LangSmith integration test successful!')
    print('📈 Check your LangSmith dashboard at https://smith.langchain.com/')

if __name__ == "__main__":
    test_langsmith_integration()