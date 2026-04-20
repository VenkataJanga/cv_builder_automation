#!/usr/bin/env python3
"""
LangSmith Tracing Demonstration Script

This script demonstrates the complete LangSmith tracing implementation:
1. Environment setup
2. Tracer initialization
3. Trace creation with session correlation
4. Span tracking for different operations
5. Trace export and retrieval
6. API endpoint simulation
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.observability.constants import (
    DEFAULT_LANGSMITH_PROJECT,
    LANGSMITH_PROJECT_ENV_VAR,
)
from src.observability.langsmith_tracer import get_langsmith_tracer, SpanType

def demonstrate_tracing():
    """Demonstrate the complete tracing workflow"""

    print("🔍 LangSmith Tracing Demonstration")
    print("=" * 50)

    # 1. Environment Setup
    print("\n1. Environment Configuration:")
    print(f"   LANGSMITH_ENABLED: {os.getenv('LANGSMITH_ENABLED', 'false')}")
    print(f"   LANGSMITH_API_KEY: {'***' if os.getenv('LANGSMITH_API_KEY') else 'Not set'}")
    print(
        f"   {LANGSMITH_PROJECT_ENV_VAR}: "
        f"{os.getenv(LANGSMITH_PROJECT_ENV_VAR, DEFAULT_LANGSMITH_PROJECT)}"
    )

    # 2. Tracer Initialization
    print("\n2. Tracer Initialization:")
    tracer = get_langsmith_tracer()
    print(f"   Tracer enabled: {tracer.enabled}")
    print(f"   LangSmith client available: {tracer.langsmith_client is not None}")

    # 3. Create a workflow trace with session correlation
    session_id = "demo-session-12345"
    print(f"\n3. Creating workflow trace for session: {session_id}")

    trace = tracer.start_trace(
        name="cv_processing_workflow",
        session_id=session_id,
        user_id="demo-user",
        metadata={"input_type": "voice", "model": "gpt-4"}
    )
    print(f"   Trace created: {trace.trace_id}")
    print(f"   Workflow type: {trace.workflow_type}")

    # 4. Simulate different processing steps
    print("\n4. Simulating CV processing workflow:")

    # Extraction step
    print("   📝 Extraction step...")
    with tracer.span("document_extraction", SpanType.EXTRACTION, trace_id=session_id) as span:
        span.inputs = {
            "input_type": "voice",
            "document_length": 1500,
            "source": "audio_transcript"
        }
        # Simulate processing
        import time
        time.sleep(0.1)
        span.outputs = {
            "extracted_fields": ["personal_details", "education", "experience"],
            "confidence_score": 0.92
        }
        span.metadata = {"model": "gpt-4", "tokens_used": 1250}

    # Validation step
    print("   ✅ Validation step...")
    with tracer.span("data_validation", SpanType.VALIDATION, trace_id=session_id) as span:
        span.inputs = {"validation_rules": ["required_fields", "data_consistency"]}
        time.sleep(0.05)
        span.outputs = {
            "validation_passed": True,
            "issues_found": 0,
            "quality_score": 0.95
        }
        span.metadata = {"validation_time_ms": 50}

    # Enhancement step
    print("   🚀 Enhancement step...")
    with tracer.span("content_enhancement", SpanType.ENHANCEMENT, trace_id=session_id) as span:
        span.inputs = {"enhancement_type": "professional_polish"}
        time.sleep(0.08)
        span.outputs = {
            "enhanced_sections": ["summary", "experience"],
            "improvement_score": 0.88
        }
        span.metadata = {"model": "gpt-4", "enhancement_tokens": 800}

    # Quality metrics
    print("   📊 Quality metrics...")
    with tracer.span("quality_assessment", SpanType.LLM_CALL, trace_id=session_id) as span:
        span.inputs = {"metrics": ["precision", "recall", "hallucination_rate"]}
        time.sleep(0.03)
        span.outputs = {
            "precision": 0.94,
            "recall": 0.89,
            "hallucination_rate": 0.03,
            "completeness_score": 0.91
        }
        span.metadata = {"quality_check_time_ms": 30}

    # 5. End the trace
    print("\n5. Completing workflow trace...")
    tracer.end_trace(session_id)
    print("   Trace completed and exported")

    # 6. Retrieve and display trace data
    print("\n6. Trace Retrieval and Analysis:")

    # Get trace summary
    summary = tracer.get_trace_summary(session_id)
    print("   📈 Trace Summary:")
    print(f"      Trace ID: {summary['trace_id']}")
    print(f"      Name: {summary['name']}")
    print(f"      Status: {summary['status']}")
    print(".2f")
    print(f"      Span Count: {summary['span_count']}")
    print(f"      Total Tokens: {summary['total_tokens']}")
    print(f"      Total Cost: ${summary['total_cost']:.4f}")
    print(f"      Error Count: {summary['error_count']}")

    # Get full trace
    full_trace = tracer.get_trace(session_id)
    if full_trace:
        print("\n   📋 Full Trace Details:")
        print(f"      User ID: {full_trace.user_id}")
        print(f"      Session ID: {full_trace.session_id}")
        print(f"      Workflow Type: {full_trace.workflow_type}")
        print(f"      Tags: {full_trace.tags}")
        print(f"      Metadata: {full_trace.metadata}")

        print("\n   🔍 Span Details:")
        for i, span in enumerate(full_trace.spans, 1):
            print(f"      {i}. {span.name} ({span.span_type.value})")
            print(f"         Duration: {span.duration_ms:.1f}ms")
            print(f"         Status: {span.status.value}")
            if span.token_count:
                print(f"         Tokens: {span.token_count}")
            if span.inputs:
                print(f"         Inputs: {span.inputs}")
            if span.outputs:
                print(f"         Outputs: {span.outputs}")

    # 7. Simulate API endpoint response
    print("\n7. API Endpoint Simulation:")
    print("   GET /traces/demo-session-12345")
    print("   Response:")

    # Simulate the API response
    api_response = {
        "session_id": session_id,
        "enabled": tracer.enabled,
        "summary": summary,
        "trace": full_trace.to_dict() if full_trace else None
    }

    print(json.dumps(api_response, indent=2, default=str))

    print("\n" + "=" * 50)
    print("✅ LangSmith Tracing Demonstration Complete!")
    print("\nTo enable real LangSmith export:")
    print("   export LANGSMITH_ENABLED=true")
    print("   export LANGSMITH_API_KEY=your_api_key")
    print(f"   export {LANGSMITH_PROJECT_ENV_VAR}={DEFAULT_LANGSMITH_PROJECT}")
    print("\nTraces will then appear in your LangSmith dashboard!")

if __name__ == "__main__":
    demonstrate_tracing()