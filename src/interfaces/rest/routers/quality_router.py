from fastapi import APIRouter, Depends, HTTPException

from src.application.services.conversation_service import ConversationService
from src.application.services.quality_metrics_service import QualityMetricsService
from src.core.i18n import t
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user
from src.interfaces.rest.dependencies.locale_dependencies import get_request_locale

router = APIRouter(prefix="/quality", tags=["quality"], dependencies=[Depends(get_current_user)])

conversation_service = ConversationService()
quality_metrics_service = QualityMetricsService()


@router.get("/{session_id}")
def get_quality_report(session_id: str, locale: str = Depends(get_request_locale)):
    """Return latest quality report plus persisted quality history for a session."""
    session = conversation_service.get_session(session_id)
    if "error" in session:
        raise HTTPException(status_code=404, detail=t("api.preview.session_not_found", locale=locale))

    canonical_cv = session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(status_code=400, detail=t("api.preview.missing_canonical", locale=locale))

    validation_results = session.get("validation_results")
    latest_report = quality_metrics_service.evaluate(canonical_cv, validation_results)

    history = session.get("quality_audit", [])

    return {
        "session_id": session_id,
        "latest": latest_report,
        "history_count": len(history),
        "history": history,
    }
