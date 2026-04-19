"""
Validation Router - Phase 5: Canonical CV Only

This router handles CV validation requests, reading exclusively from canonical_cv.
Validation results are stored in session for export gates.
"""

from fastapi import APIRouter, Depends, HTTPException

from src.application.services.conversation_service import ConversationService
from src.application.services.schema_validation_service import SchemaValidationService
from src.core.i18n import t
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user
from src.interfaces.rest.dependencies.locale_dependencies import get_request_locale

router = APIRouter(prefix="/validation", tags=["validation"], dependencies=[Depends(get_current_user)])

conversation_service = ConversationService()
validation_service = SchemaValidationService()


@router.get("/{session_id}")
def get_validation(session_id: str, locale: str = Depends(get_request_locale)):
    """
    Validate canonical CV and store results in session
    
    Phase 5: Reads from canonical_cv only, no cv_data fallback.
    Stores validation results in session["validation_results"].
    """
    session = conversation_service.get_session(session_id)
    if "error" in session:
        return session
    
    # Phase 5: Read from canonical_cv only
    canonical_cv = session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(
            status_code=400,
            detail=t("api.validation.missing_canonical", locale=locale)
        )
    
    # Validate canonical CV
    validation_result = validation_service.validate(canonical_cv, locale=locale)
    
    # Store validation results in session for export gates
    session["validation_results"] = validation_result.to_dict()
    conversation_service.save_session(session_id, session)
    
    return validation_result.to_dict()
