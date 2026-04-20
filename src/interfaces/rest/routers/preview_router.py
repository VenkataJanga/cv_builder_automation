"""
Preview Router - Phase 4: Canonical CV Only

This router handles CV preview requests, reading exclusively from canonical_cv.
All repair functions and cv_data fallbacks have been removed.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from src.application.services.conversation_service import ConversationService
from src.application.services.preview_service import PreviewService
from src.application.services.quality_metrics_service import QualityMetricsService
from src.core.i18n import t
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user
from src.interfaces.rest.dependencies.locale_dependencies import get_request_locale

router = APIRouter(prefix="/preview", tags=["preview"], dependencies=[Depends(get_current_user)])

conversation_service = ConversationService()
preview_service = PreviewService()
quality_metrics_service = QualityMetricsService()
logger = logging.getLogger(__name__)


@router.get("/{session_id}")
def get_preview(session_id: str, locale: str = Depends(get_request_locale)):
    """
    Get CV preview for a session (Phase 4: Canonical-only)
    
    Args:
        session_id: Session identifier
        
    Returns:
        Preview data with validation results and metadata
        
    Phase 4 Changes:
    - Reads from canonical_cv only
    - No repair functions or fallbacks
    - Validation results from session (not inline)
    """
    # Get session
    session = conversation_service.get_session(session_id)
    if "error" in session:
        raise HTTPException(status_code=404, detail=t("api.preview.session_not_found", locale=locale))
    
    # DEBUG: Verify session state before preview
    logger.info(f"DEBUG: Preview request for session {session_id}")
    logger.info(f"  - Session exists: {bool(session and 'error' not in session)}")
    logger.info(f"  - canonical_cv exists: {bool(session.get('canonical_cv'))}")
    logger.info(f"  - canonical_cv top-level keys: {list(session.get('canonical_cv', {}).keys())}")
    logger.info(f"  - validation_results exists: {bool(session.get('validation_results'))}")
    
    # Get canonical CV from session.
    # Prefer resolved_canonical (frozen at Save & Validate) — it is the single agreed
    # source of truth for all downstream reads.  Fall back to live canonical_cv for
    # sessions that have not yet gone through Save & Validate (e.g. immediately after
    # audio upload before any user review action).
    canonical_cv = session.get("resolved_canonical") or session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(
            status_code=400,
            detail=t("api.preview.missing_canonical", locale=locale)
        )
    
    # Get validation results from session (stored during save/validate operations)
    validation_results = session.get("validation_results")

    # Compute quality metrics and source-to-output traceability from canonical + snapshots.
    quality_report = quality_metrics_service.evaluate(canonical_cv, validation_results)

    # Persist quality report snapshots for longitudinal monitoring and auditability.
    quality_snapshot = {
        "captured_at": datetime.utcnow().isoformat(),
        "metrics": quality_report.get("metrics", {}),
        "counts": quality_report.get("counts", {}),
        "definitions": quality_report.get("definitions", {}),
        "field_traceability": quality_report.get("field_traceability", []),
    }
    session.setdefault("quality_audit", []).append(quality_snapshot)
    # Keep bounded history to avoid unbounded session growth.
    if len(session["quality_audit"]) > 50:
        session["quality_audit"] = session["quality_audit"][-50:]
    conversation_service.save_session(session_id, session)

    # Use the preview service to convert canonical schema into the formatter-compatible preview structure.
    try:
        preview_data = preview_service.build_preview_from_canonical(canonical_cv)
    except Exception as e:
        logger.error(f"Failed to build preview from canonical_cv: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("api.preview.preview_build_failed", locale=locale)
        )

    logger.info("Preview generated from canonical_cv")
    candidate = canonical_cv.get("candidate", {}) or {}
    preview_fields = {
        "portal_id": candidate.get("portalId") or "NOT SET",
        "current_designation": candidate.get("currentDesignation") or candidate.get("designation") or "NOT SET",
        "email": candidate.get("email") or "NOT SET",
        "summary_length": len(candidate.get("summary") or canonical_cv.get("summary") or ""),
        "education_count": len(canonical_cv.get("education") or []),
        "project_count": len((canonical_cv.get("experience") or {}).get("projects") or []),
        "preview_keys": list(preview_data.keys()),
    }
    logger.info(f"  - Preview details: {preview_fields}")

    response = {
        "cv_data": preview_data,
        "preview": preview_data,
        "unmapped_attributes": ((canonical_cv.get("unmappedData") or {}).get("attributes") or []),
        "unmapped_attributes_count": len(((canonical_cv.get("unmappedData") or {}).get("attributes") or [])),
        "validation": validation_results,
        "validation_result": validation_results,
        "quality_metrics": quality_report.get("metrics", {}),
        "quality_counts": quality_report.get("counts", {}),
        "quality_definitions": quality_report.get("definitions", {}),
        "field_traceability": quality_report.get("field_traceability", []),
        "review_status": session.get("review_status", "pending"),
        "has_user_edits": session.get("has_user_edits", False),
        "source": "edited" if session.get("has_user_edits", False) else "generated"
    }

    return response
