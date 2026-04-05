import os
from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile

from src.application.services.conversation_service import ConversationService
from src.application.services.speech_service import SpeechService
from src.core.config.settings import settings
from src.domain.cv.services.merge_cv import MergeCVService

router = APIRouter(prefix="/speech", tags=["speech"])

speech_service = SpeechService()
conversation_service = ConversationService()
merge_service = MergeCVService()


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    session_id: str | None = Form(None),
):
    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    file_path = os.path.join(settings.LOCAL_STORAGE_PATH, f"{uuid4()}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(await file.read())

    result = speech_service.transcribe(file_path=file_path, language=language)

    if session_id:
        session = conversation_service.get_session(session_id)
        if "error" not in session:
            merged = merge_service.merge(session["cv_data"], result.get("extracted_cv_data", {}))
            session["cv_data"] = merged
            result["session_id"] = session_id
            result["cv_data"] = merged

    return result


@router.post("/correct")
def correct_transcript(
    transcript: str = Form(...),
    corrected_text: str | None = Form(None),
    session_id: str | None = Form(None),
):
    result = speech_service.correct_transcript(transcript=transcript, corrected_text=corrected_text)

    if session_id:
        session = conversation_service.get_session(session_id)
        if "error" not in session:
            merged = merge_service.merge(session["cv_data"], result.get("extracted_cv_data", {}))
            session["cv_data"] = merged
            result["session_id"] = session_id
            result["cv_data"] = merged

    return result
