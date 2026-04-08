from fastapi import APIRouter

from src.application.services.conversation_service import ConversationService
from src.application.services.preview_service import PreviewService
from src.application.services.validation_service import ValidationService

router = APIRouter(prefix="/preview", tags=["preview"])

conversation_service = ConversationService()
preview_service = PreviewService()
validation_service = ValidationService()


@router.get("/{session_id}")
def get_preview(session_id: str):
    session = conversation_service.get_session(session_id)
    if "error" in session:
        return session

    print(f"DEBUG: Session cv_data: {session['cv_data']}")
    preview = preview_service.build_preview(session["cv_data"])
    print(f"DEBUG: Preview result: {preview}")
    validation = validation_service.validate(session["cv_data"])

    return {
        "preview": preview,
        "validation": validation,
    }
