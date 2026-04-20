#!/usr/bin/env python3
"""
Check LangSmith Traces
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.observability.constants import (
    DEFAULT_LANGSMITH_PROJECT,
    LANGSMITH_PROJECT_ENV_VAR,
)
from src.observability.langsmith_tracer import get_langsmith_tracer

# Set environment variables
os.environ['LANGSMITH_ENABLED'] = 'true'
os.environ['LANGSMITH_API_KEY'] = os.getenv('LANGSMITH_API_KEY', '')
os.environ[LANGSMITH_PROJECT_ENV_VAR] = DEFAULT_LANGSMITH_PROJECT

def check_traces():
    print('🔍 Checking Stored Traces...')
    tracer = get_langsmith_tracer()

    # Check the demo trace we created
    session_id = 'live-demo-session-001'
    summary = tracer.get_trace_summary(session_id)

    if summary:
        print(f'✅ Found trace: {session_id}')
        print(f'   Status: {summary["status"]}')
        print(f'   Duration: {summary["duration_ms"]:.1f}ms')
        print(f'   Spans: {summary["span_count"]}')
        print(f'   LangSmith Export: {"Enabled" if tracer.langsmith_client else "Disabled"}')

        # Show detailed trace data
        full_trace = tracer.get_trace(session_id)
        if full_trace:
            print(f'\n📋 Trace Details:')
            print(f'   Name: {full_trace.name}')
            print(f'   User: {full_trace.user_id}')
            print(f'   Workflow: {full_trace.workflow_type}')
            print(f'   Start: {full_trace.start_time}')

            print(f'\n🔍 Span Breakdown:')
            for i, span in enumerate(full_trace.spans, 1):
                print(f'   {i}. {span.name} ({span.span_type.value}) - {span.duration_ms:.1f}ms')
    else:
        print(f'❌ No trace found for session: {session_id}')

    print(f'\n📊 LangSmith Dashboard: https://smith.langchain.com/')
    print(f'🔍 Project: {DEFAULT_LANGSMITH_PROJECT}')
    print(f'🆔 Look for trace: {session_id}')

if __name__ == "__main__":
    check_traces()