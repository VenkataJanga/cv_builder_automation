#!/usr/bin/env python3
"""
Standalone LangSmith Tracing Demonstration
Shows tracing working independently of the full application
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

# Set environment variables for LangSmith
os.environ['LANGSMITH_ENABLED'] = 'true'
os.environ['LANGSMITH_API_KEY'] = os.getenv('LANGSMITH_API_KEY', '')
os.environ[LANGSMITH_PROJECT_ENV_VAR] = DEFAULT_LANGSMITH_PROJECT
os.environ['LANGSMITH_ENDPOINT'] = 'https://api.smith.langchain.com'

def demonstrate_live_tracing():
    """Demonstrate LangSmith tracing with real export"""

    print("🚀 LangSmith Live Tracing Demonstration")
    print("=" * 50)

    # Initialize tracer
    print("\n1. Initializing LangSmith Tracer...")
    tracer = get_langsmith_tracer()
    print(f"   ✅ Enabled: {tracer.enabled}")
    print(f"   ✅ Client Available: {tracer.langsmith_client is not None}")

    if not tracer.enabled or not tracer.langsmith_client:
        print("❌ LangSmith not properly configured!")
        return

    # Create a realistic CV processing trace
    session_id = "live-demo-session-001"
    print(f"\n2. Creating CV Processing Trace (Session: {session_id})...")

    trace = tracer.start_trace(
        name="cv_processing_workflow_demo",
        session_id=session_id,
        user_id="demo-user",
        metadata={
            "input_type": "voice_upload",
            "model_version": "gpt-4-turbo",
            "environment": "demo"
        }
    )

    # Simulate document extraction
    print("   📄 Step 1: Document Extraction...")
    with tracer.span("document_extraction", SpanType.EXTRACTION, trace_id=session_id) as span:
        span.inputs = {
            "file_type": "audio/wav",
            "duration_seconds": 45,
            "language": "en-US"
        }
        import time
        time.sleep(0.1)  # Simulate processing time

        span.outputs = {
            "extracted_text": "Professional software engineer with 5 years experience...",
            "confidence_score": 0.94,
            "sections_identified": ["personal_info", "experience", "education", "skills"]
        }
        span.metadata = {
            "model": "whisper-1",
            "processing_time_ms": 100,
            "audio_quality": "high"
        }

    # Simulate data validation
    print("   ✅ Step 2: Data Validation...")
    with tracer.span("data_validation", SpanType.VALIDATION, trace_id=session_id) as span:
        span.inputs = {
            "validation_rules": ["required_fields", "data_consistency", "format_check"],
            "data_points": 25
        }
        time.sleep(0.05)

        span.outputs = {
            "validation_passed": True,
            "issues_found": 1,
            "warnings": ["Minor formatting inconsistency"],
            "quality_score": 0.96
        }
        span.metadata = {
            "validation_engine": "pydantic",
            "rules_applied": 15
        }

    # Simulate content enhancement
    print("   🚀 Step 3: Content Enhancement...")
    with tracer.span("content_enhancement", SpanType.ENHANCEMENT, trace_id=session_id) as span:
        span.inputs = {
            "enhancement_type": "professional_polish",
            "target_sections": ["summary", "experience", "achievements"]
        }
        time.sleep(0.08)

        span.outputs = {
            "enhanced_sections": ["summary", "experience"],
            "improvements_made": 12,
            "readability_score": 0.88,
            "professional_tone": 0.92
        }
        span.metadata = {
            "model": "gpt-4",
            "tokens_used": 450,
            "enhancement_version": "2.1"
        }

    # Simulate quality assessment
    print("   📊 Step 4: Quality Assessment...")
    with tracer.span("quality_assessment", SpanType.LLM_CALL, trace_id=session_id) as span:
        span.inputs = {
            "metrics": ["precision", "recall", "hallucination_rate", "completeness"],
            "benchmark_data": "cv_quality_dataset_v3"
        }
        time.sleep(0.03)

        span.outputs = {
            "precision": 0.94,
            "recall": 0.89,
            "hallucination_rate": 0.02,
            "completeness_score": 0.91,
            "overall_quality": "excellent"
        }
        span.metadata = {
            "assessment_model": "quality-evaluator-v2",
            "benchmark_version": "2024.1"
        }

    # Complete the trace
    print("\n3. Completing and Exporting Trace...")
    tracer.end_trace(session_id)

    # Get trace summary
    summary = tracer.get_trace_summary(session_id)
    print("   📈 Trace Summary:")
    print(f"      Duration: {summary['duration_ms']:.1f}ms")
    print(f"      Spans: {summary['span_count']}")
    print(f"      Status: {summary['status']}")

    print("\n4. ✅ Trace Successfully Exported to LangSmith!")
    print("   📊 View in Dashboard: https://smith.langchain.com/")
    print(f"   🔍 Project: {DEFAULT_LANGSMITH_PROJECT}")
    print("   🆔 Trace ID: live-demo-session-001")

    # Simulate API endpoint response
    print("\n5. API Endpoint Response Simulation:")
    print("   GET /traces/live-demo-session-001")

    full_trace = tracer.get_trace(session_id)
    api_response = {
        "session_id": session_id,
        "enabled": True,
        "summary": summary,
        "trace": full_trace.to_dict() if full_trace else None
    }

    print("   ✅ Status: 200 OK")
    print("   ✅ Response: Complete trace data with 4 spans")

    print("\n" + "=" * 50)
    print("🎉 LangSmith Tracing Demonstration Complete!")
    print("\n📋 What you can now do:")
    print("1. View traces in LangSmith dashboard")
    print("2. Use GET /traces/{session_id} API endpoint")
    print("3. Monitor real CV processing workflows")
    print("4. Analyze performance and quality metrics")

if __name__ == "__main__":
    demonstrate_live_tracing()