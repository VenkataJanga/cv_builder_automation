from fastapi import APIRouter
from pydantic import BaseModel

from src.application.services.conversation_service import ConversationService


router = APIRouter(prefix="/session", tags=["session"])
service = ConversationService()


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


@router.post("/start")
def start_session():
    return service.start_session()


@router.post("/answer")
def submit_answer(req: AnswerRequest):
    return service.submit_answer(req.session_id, req.answer)


@router.get("/{session_id}")
def get_session(session_id: str):
    return service.get_session(session_id)


@router.delete("/{session_id}")
def reset_session(session_id: str):
    return service.reset_session(session_id)
