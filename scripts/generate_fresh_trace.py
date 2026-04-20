#!/usr/bin/env python3
"""
Generate Fresh LangSmith Trace and Show Access
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
from src.observability.langsmith_tracer import get_langsmith_tracer, SpanType

# Set environment variables
os.environ['LANGSMITH_ENABLED'] = 'true'
os.environ['LANGSMITH_API_KEY'] = os.getenv('LANGSMITH_API_KEY', '')
os.environ[LANGSMITH_PROJECT_ENV_VAR] = DEFAULT_LANGSMITH_PROJECT

def generate_and_show_trace():
    print("🚀 Generating Fresh LangSmith Trace")
    print("=" * 50)

    # Initialize tracer
    tracer = get_langsmith_tracer()
    print(f"✅ LangSmith Client: {'Connected' if tracer.langsmith_client else 'Disconnected'}")

    # Create a fresh trace
    session_id = "fresh-trace-demo-002"
    print(f"\n📝 Creating trace: {session_id}")

    trace = tracer.start_trace(
        name="fresh_cv_processing_demo",
        session_id=session_id,
        user_id="demo-user-2",
        metadata={"demo": True, "fresh": True}
    )

    # Quick processing simulation
    print("⚡ Running quick processing simulation...")

    with tracer.span("quick_extraction", SpanType.EXTRACTION, trace_id=session_id) as span:
        span.inputs = {"source": "demo"}
        span.outputs = {"status": "success"}

    with tracer.span("quick_validation", SpanType.VALIDATION, trace_id=session_id) as span:
        span.inputs = {"checks": ["basic"]}
        span.outputs = {"passed": True}

    # Complete trace
    tracer.end_trace(session_id)

    # Show summary
    summary = tracer.get_trace_summary(session_id)
    print("\n📊 Trace Summary:")
    print(f"   Session ID: {session_id}")
    print(f"   Status: {summary['status']}")
    print(f"   Duration: {summary['duration_ms']:.1f}ms")
    print(f"   Spans: {summary['span_count']}")

    print("\n✅ Trace exported to LangSmith!")
    print("\n🔗 How to View Your Traces:")
    print("1. Go to: https://smith.langchain.com/")
    print("2. Sign in with your account")
    print(f"3. Select project: '{DEFAULT_LANGSMITH_PROJECT}'")
    print("4. Look for traces with session IDs like:")
    print(f"   - {session_id}")
    print("   - live-demo-session-001 (from previous demo)")

    print("\n📋 What You'll See:")
    print("- Real-time trace visualization")
    print("- Span-by-span breakdown")
    print("- Performance metrics")
    print("- Input/output data")
    print("- Quality scores")

    print("\n🎯 API Access:")
    print(f"GET /traces/{session_id} (when server is running)")

    print("\n" + "=" * 50)
    print("🎉 Fresh trace generated and exported!")
    print("Check your LangSmith dashboard now!")

if __name__ == "__main__":
    generate_and_show_trace()