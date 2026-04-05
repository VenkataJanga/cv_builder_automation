import os
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form

from src.application.commands.upload_cv import UploadCVCommand
from src.application.services.conversation_service import ConversationService
from src.domain.cv.services.merge_cv import MergeCVService
from src.core.config.settings import settings

router = APIRouter(prefix="/cv", tags=["cv"])

upload_cmd = UploadCVCommand()
conversation_service = ConversationService()
merge_service = MergeCVService()


@router.post("/upload")
async def upload_cv(
    file: UploadFile = File(...),
    session_id: str = Form(None),
):
    if not file:
        return {"error": "No file provided"}

    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    save_path = os.path.join(
        settings.LOCAL_STORAGE_PATH,
        f"{uuid4()}_{file.filename}"
    )

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    parsed_data = upload_cmd.execute(save_path)

    if session_id:
        session = conversation_service.get_session(session_id)
        if "error" in session:
            return session

        merged = merge_service.merge(session["cv_data"], parsed_data)
        session["cv_data"] = merged

        return {
            "session_id": session_id,
            "parsed_data": parsed_data,
            "cv_data": merged,
        }

    return {"parsed_data": parsed_data}