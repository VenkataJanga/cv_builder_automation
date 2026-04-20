from fastapi import APIRouter, Depends, HTTPException
from src.core.i18n import t
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user
from src.interfaces.rest.dependencies.locale_dependencies import get_request_locale
from src.observability.langsmith_tracer import get_langsmith_tracer

router = APIRouter(prefix="/traces", tags=["traces"], dependencies=[Depends(get_current_user)])

@router.get("/{session_id}")
def get_trace(session_id: str, locale: str = Depends(get_request_locale)):
    """
    Get trace data for a session (optional observability endpoint).
    
    Returns trace summary and spans if tracing is enabled.
    """
    tracer = get_langsmith_tracer()
    if not tracer.enabled:
        return {"enabled": False, "message": "Tracing is not enabled"}
    
    trace = tracer.get_trace(session_id)
    if not trace:
        raise HTTPException(status_code=404, detail=t("trace.not_found", locale=locale))
    
    summary = tracer.get_trace_summary(session_id)
    return {
        "session_id": session_id,
        "enabled": True,
        "summary": summary,
        "trace": trace.dict() if trace else None
    }