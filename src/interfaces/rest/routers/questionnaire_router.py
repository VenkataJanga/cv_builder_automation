from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.application.services.conversation_service import ConversationService
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user
from src.interfaces.rest.dependencies.locale_dependencies import get_request_locale
from src.questionnaire.question_selector import select_initial_questions, select_questions


router = APIRouter(
	prefix="/questionnaire",
	tags=["questionnaire"],
	dependencies=[Depends(get_current_user)],
)
service = ConversationService()


class QuestionnaireAnswerRequest(BaseModel):
	session_id: str
	answer: str


@router.get("/initial-questions")
def initial_questions(locale: str = Depends(get_request_locale)) -> dict:
	return {"locale": locale, "questions": select_initial_questions(locale=locale)}


@router.get("/questions/{role}")
def role_questions(role: str, locale: str = Depends(get_request_locale)) -> dict:
	return {"locale": locale, "role": role, "questions": select_questions(role, locale=locale)}


@router.post("/answer")
def submit_answer(req: QuestionnaireAnswerRequest) -> dict:
	result = service.submit_answer(req.session_id, req.answer)
	if "error" in result:
		raise HTTPException(status_code=404, detail=result["error"])
	return result
