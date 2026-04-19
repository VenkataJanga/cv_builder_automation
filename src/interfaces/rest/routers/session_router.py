from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.application.services.conversation_service import ConversationService
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user
from src.interfaces.rest.dependencies.locale_dependencies import get_request_locale


router = APIRouter(prefix="/session", tags=["session"], dependencies=[Depends(get_current_user)])
service = ConversationService()


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


@router.post("/start")
def start_session(locale: str = Depends(get_request_locale)):
    return service.start_session(locale=locale)


@router.post("/answer")
def submit_answer(req: AnswerRequest):
    return service.submit_answer(req.session_id, req.answer)


@router.get("/{session_id}")
def get_session(session_id: str):
    return service.get_session(session_id)


@router.delete("/{session_id}")
def reset_session(session_id: str):
    return service.reset_session(session_id)
