from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.application.services.conversation_service import ConversationService
from src.domain.cv.services.merge_cv import MergeCVService
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_user)])

conversation_service = ConversationService()
merge_service = MergeCVService()


class ChatRequest(BaseModel):
    message: str
    session_id: str = None


@router.post("")
async def chat(request: ChatRequest):
    """
    Chat endpoint for conversational CV building
    """
    try:
        # If no session_id provided, create a new session and return the first question
        if not request.session_id or request.session_id == "default-session":
            session = conversation_service.start_session()
            session_id = session.get("session_id")
            return {
                "bot": session.get("question"),
                "session_id": session_id,
                "cv_data": session.get("cv_data", {}),
                "status": "success"
            }

        session_id = request.session_id
        session = conversation_service.get_session(session_id)
        if "error" in session:
            session = conversation_service.start_session()
            session_id = session.get("session_id")
            return {
                "bot": session.get("question"),
                "session_id": session_id,
                "cv_data": session.get("cv_data", {}),
                "status": "success"
            }

        # Process the chat message using the conversation service
        result = conversation_service.submit_answer(session_id, request.message)
        
        bot_text = result.get("bot") or result.get("question") or result.get("followup_question") or result.get("message") or result.get("response")
        if not bot_text:
            bot_text = "I understand. Let me help you build your CV. Can you tell me more details?"

        updated_session = conversation_service.get_session(session_id)
        
        return {
            "bot": bot_text,
            "session_id": session_id,
            "cv_data": updated_session.get("cv_data", {}),
            "status": "success"
        }
        
    except Exception as e:
        return {
            "bot": f"I encountered an error: {str(e)}. Please try again.",
            "session_id": request.session_id,
            "cv_data": {},
            "status": "error"
        }


@router.post("/conversations/session")
async def create_conversation_session(request: dict = None):
    """
    Create a new conversation session - compatibility endpoint for the UI
    """
    try:
        session = conversation_service.start_session()
        return {
            "session_id": session.get("session_id"),
            "status": "success",
            "message": "Session created successfully",
            "question": session.get("question"),
            "cv_data": session.get("cv_data", {}),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create session: {str(e)}"
        }


@router.get("/conversations/{session_id}")
async def get_conversation_session(session_id: str):
    """
    Get conversation session data - compatibility endpoint for the UI
    """
    try:
        session = conversation_service.get_session(session_id)
        if "error" in session:
            return {
                "status": "error",
                "message": "Session not found"
            }
        
        return {
            "session_id": session_id,
            "cv_data": session.get("cv_data", {}),
            "status": "success"
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Failed to get session: {str(e)}"
        }
