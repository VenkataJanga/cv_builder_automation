import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import requests

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.core.env_loader import load_environment_variables
from src.observability.langsmith_tracer import get_langsmith_tracer, SpanStatus
from src.ai.services.llm_service import get_llm_service
from langsmith import Client


def main() -> int:
    load_environment_variables()

    tracer = get_langsmith_tracer()
    if not tracer.enabled or not tracer.langsmith_client:
        print("langsmith_ready false")
        return 1

    llm = get_llm_service()
    if not llm.is_enabled():
        print("llm_ready false")
        return 1

    session_id = f"verify-metrics-{int(datetime.now(tz=timezone.utc).timestamp())}"
    trace = tracer.start_trace(
        name="verify_llm_metrics_trace",
        user_id="local-verifier",
        tags=["verification", "llm", "metrics"],
        metadata={"source": "verify_langsmith_llm_metrics.py", "session_id": session_id},
    )

    result, usage = llm.call_with_usage(
        prompt="Return only this JSON: {\"status\":\"ok\"}",
        system_message="You are a strict JSON responder.",
        temperature=0.0,
        max_tokens=50,
        json_mode=True,
    )

    tracer.end_trace(trace.trace_id, status=SpanStatus.SUCCESS)
    try:
        tracer.langsmith_client.flush()
    except Exception:
        pass

    print("trace_id", trace.trace_id)
    print("session_id", session_id)
    print("usage_prompt_tokens", usage.get("prompt_tokens"))
    print("usage_completion_tokens", usage.get("completion_tokens"))
    print("usage_total_tokens", usage.get("total_tokens"))
    print("usage_cost", usage.get("cost"))
    print("llm_result", result)

    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    api_url = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    project_name = tracer.project

    verify_ssl = os.getenv("LANGSMITH_VERIFY_SSL", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    session = requests.Session()
    session.verify = verify_ssl

    client = Client(api_key=api_key, api_url=api_url, session=session)
    runs = list(client.list_runs(project_name=project_name, trace_id=trace.trace_id, limit=50))

    llm_runs = [r for r in runs if getattr(r, "run_type", None) == "llm"]
    print("runs_total", len(runs))
    print("runs_llm", len(llm_runs))

    if llm_runs:
        run = llm_runs[0]
        print("llm_run_id", getattr(run, "id", None))
        print("llm_prompt_tokens", getattr(run, "prompt_tokens", None))
        print("llm_completion_tokens", getattr(run, "completion_tokens", None))
        print("llm_total_tokens", getattr(run, "total_tokens", None))
        print("llm_total_cost", getattr(run, "total_cost", None))
        outputs = getattr(run, "outputs", {}) or {}
        usage_meta = outputs.get("usage_metadata") if isinstance(outputs, dict) else None
        print("llm_usage_metadata", usage_meta)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
