from fastapi import APIRouter

from src.application.services.conversation_service import ConversationService
from src.application.services.validation_service import ValidationService

router = APIRouter(prefix="/validation", tags=["validation"])

conversation_service = ConversationService()
validation_service = ValidationService()


@router.get("/{session_id}")
def get_validation(session_id: str):
    session = conversation_service.get_session(session_id)
    if "error" in session:
        return session
    return validation_service.validate(session["cv_data"])
