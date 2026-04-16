"""
Preview Router - Phase 4: Canonical CV Only

This router handles CV preview requests, reading exclusively from canonical_cv.
All repair functions and cv_data fallbacks have been removed.
"""

import logging

from fastapi import APIRouter, HTTPException

from src.application.services.conversation_service import ConversationService
from src.application.services.preview_service import PreviewService

router = APIRouter(prefix="/preview", tags=["preview"])

conversation_service = ConversationService()
preview_service = PreviewService()
logger = logging.getLogger(__name__)


@router.get("/{session_id}")
def get_preview(session_id: str):
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
        raise HTTPException(status_code=404, detail="Session not found")
    
    # DEBUG: Verify session state before preview
    logger.info(f"DEBUG: Preview request for session {session_id}")
    logger.info(f"  - Session exists: {bool(session and 'error' not in session)}")
    logger.info(f"  - canonical_cv exists: {bool(session.get('canonical_cv'))}")
    logger.info(f"  - canonical_cv top-level keys: {list(session.get('canonical_cv', {}).keys())}")
    logger.info(f"  - validation_results exists: {bool(session.get('validation_results'))}")
    
    # Get canonical CV from session
    canonical_cv = session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(
            status_code=400,
            detail="No canonical CV data found in session. Please complete CV creation first."
        )
    
    # Get validation results from session (stored during save/validate operations)
    validation_results = session.get("validation_results")

    # Use the preview service to convert canonical schema into the formatter-compatible preview structure.
    try:
        preview_data = preview_service.build_preview_from_canonical(canonical_cv)
    except Exception as e:
        logger.error(f"Failed to build preview from canonical_cv: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate preview from canonical CV data."
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
        "validation": validation_results,
        "validation_result": validation_results,
        "review_status": session.get("review_status", "pending"),
        "has_user_edits": session.get("has_user_edits", False),
        "source": "edited" if session.get("has_user_edits", False) else "generated"
    }

    return response
