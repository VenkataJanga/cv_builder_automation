from fastapi import APIRouter
from pydantic import BaseModel

from src.application.services.conversation_service import ConversationService
from src.domain.cv.services.merge_cv import MergeCVService

router = APIRouter(prefix="/chat", tags=["chat"])

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
        # If no session_id provided, create a new session
        if not request.session_id or request.session_id == "default-session":
            session = conversation_service.start_session()
            session_id = session.get("session_id")
        else:
            session_id = request.session_id
            session = conversation_service.get_session(session_id)
            if "error" in session:
                # Session doesn't exist, create a new one
                session = conversation_service.start_session()
                session_id = session.get("session_id")

        # Process the chat message using the conversation service
        # For now, we'll use the submit_answer method which should handle chat-like interactions
        result = conversation_service.submit_answer(session_id, request.message)
        
        # Get the updated session data
        updated_session = conversation_service.get_session(session_id)
        
        return {
            "bot": result.get("response", "I understand. Let me help you build your CV. Can you tell me more details?"),
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
            "message": "Session created successfully"
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
