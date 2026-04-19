import os
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.application.services.conversation_service import ConversationService
from src.application.services.preview_service import PreviewService
from src.application.services.speech_service import SpeechService
from src.application.services.audio_cv_service import AudioCVService
from src.application.services.transaction_logging_service import get_transaction_logging_service
from src.core.config.settings import settings
from src.core.i18n import t
from src.domain.cv.enums import SourceType
from src.core.constants import MAX_AUDIO_FILE_SIZE_MB
from src.core.logging.logger import get_logger
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user
from src.interfaces.rest.dependencies.locale_dependencies import get_request_locale

logger = get_logger(__name__)

router = APIRouter(prefix="/speech", tags=["speech"], dependencies=[Depends(get_current_user)])

speech_service = SpeechService()
conversation_service = ConversationService()
audio_cv_service = AudioCVService()  # Phase 3: Canonical schema pipeline
preview_service = PreviewService()
transaction_logging_service = get_transaction_logging_service()


def _log_speech_event(
    operation: str,
    status: str,
    session_id: str | None = None,
    source_channel: str | None = None,
    http_status: int | None = None,
    error_message: str | None = None,
    payload: dict | None = None,
) -> None:
    transaction_logging_service.log_transaction(
        module_name="speech",
        operation=operation,
        status=status,
        session_id=session_id,
        source_channel=source_channel,
        http_status=http_status,
        error_message=error_message,
        payload=payload,
    )


def _ensure_file_size_limit(file_bytes: bytes, locale: str | None = None) -> None:
    max_bytes = MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=t("api.speech.file_too_large", locale=locale, max_mb=MAX_AUDIO_FILE_SIZE_MB),
        )


def _merge_legacy_cv_data(existing: dict, incoming: dict) -> dict:
    """Shallow-recursive merge for legacy cv_data compatibility."""
    base = dict(existing or {})
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _merge_legacy_cv_data(base[key], value)
        else:
            base[key] = value
    return base


def _build_preview_from_canonical(canonical_cv: dict) -> dict:
    """Build formatter-compatible preview data from canonical CV.

    This keeps legacy response compatibility without trusting a second extraction
    pipeline to produce display data.
    """
    if not canonical_cv:
        return {}

    try:
        return preview_service.build_preview_from_canonical(canonical_cv)
    except Exception:
        logger.exception("Failed to build preview from canonical CV")
        return {}

def _log_canonical_preview_details(session_data):
    canonical_cv = session_data.get("canonical_cv", {}) or {}
    candidate = canonical_cv.get("candidate", {}) or {}
    summary_text = candidate.get("summary") or canonical_cv.get("summary") or ""
    education_entries = canonical_cv.get("education") or []
    projects = (canonical_cv.get("experience") or {}).get("projects") or []

    logger.info(f"  - Candidate portalId: {candidate.get('portalId', 'NOT SET')}")
    logger.info(f"  - Candidate email: {candidate.get('email', 'NOT SET')}")
    logger.info(f"  - Candidate designation: {candidate.get('currentDesignation') or candidate.get('designation') or 'NOT SET'}")
    logger.info(f"  - Candidate summary length: {len(summary_text)}")
    logger.info(f"  - Education entries: {len(education_entries) if isinstance(education_entries, (list, tuple)) else 'unknown'}")
    logger.info(f"  - Project entries: {len(projects) if isinstance(projects, (list, tuple)) else 'unknown'}")
    if isinstance(education_entries, (list, tuple)) and education_entries:
        logger.info(f"  - First education keys: {list(education_entries[0].keys()) if isinstance(education_entries[0], dict) else 'not dict'}")
    if isinstance(projects, (list, tuple)) and projects:
        logger.info(f"  - First project keys: {list(projects[0].keys()) if isinstance(projects[0], dict) else 'not dict'}")


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    session_id: str | None = Form(None),
    locale: str = Depends(get_request_locale),
):
    """
    Phase 3: Audio transcription with canonical schema integration.
    
    Flow:
    1. Transcribe and enhance audio
    2. Process through canonical schema pipeline (AudioCVService)
    3. Update session's canonical_cv + cv_data (backward compatibility)
    4. Return transcript + validation + eligibility flags
    """
    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    file_path = os.path.join(settings.LOCAL_STORAGE_PATH, f"{uuid4()}_{file.filename}")

    file_content = await file.read()
    try:
        _ensure_file_size_limit(file_content, locale=locale)
    except HTTPException as exc:
        _log_speech_event(
            operation="audio_upload_transcribe",
            status="failed",
            session_id=session_id,
            source_channel="audio_upload",
            http_status=exc.status_code,
            error_message=str(exc.detail),
            payload={"filename": file.filename, "size_bytes": len(file_content)},
        )
        raise

    with open(file_path, "wb") as f:
        f.write(file_content)

    try:
        # Step 1: Transcribe and enhance
        transcription_result = speech_service.transcribe(file_path=file_path, language=language)
        enhanced_transcript = transcription_result["enhanced_transcript"]
    except Exception as exc:
        logger.exception("Speech transcription failed")
        _log_speech_event(
            operation="audio_upload_transcribe",
            status="failed",
            session_id=session_id,
            source_channel="audio_upload",
            http_status=502,
            error_message=str(exc),
            payload={"filename": file.filename},
        )
        raise HTTPException(status_code=502, detail=t("api.speech.transcribe_failed", locale=locale, error=str(exc)))
    finally:
        # Audio upload is temporary input; cleanup prevents storage bloat over time.
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            logger.warning(f"Failed to remove temporary audio file: {file_path}")

    # Handle session
    if session_id:
        session = conversation_service.get_session(session_id)
        if "error" in session:
            _log_speech_event(
                operation="audio_upload_transcribe",
                status="failed",
                session_id=session_id,
                source_channel="audio_upload",
                http_status=400,
                error_message="Invalid session_id",
            )
            return {"error": t("api.speech.invalid_session", locale=locale)}
    else:
        new_session = conversation_service.start_session(locale=locale)
        session_id = new_session["session_id"]
        session = conversation_service.get_session(session_id)
        transcription_result["question"] = new_session.get("question")

    # Step 2: Process through canonical schema pipeline
    audio_result = audio_cv_service.process_audio_transcript(
        enhanced_transcript=enhanced_transcript,
        existing_canonical_cv=session.get("canonical_cv", {}),
        source_type=SourceType.AUDIO_UPLOAD
    )

    # Step 3: Update session with canonical CV + validation
    logger.info("=" * 80)
    logger.info("SPEECH ROUTER - Updating session with audio results")
    logger.info(f"Session ID: {session_id}")
    
    session["canonical_cv"] = audio_result["canonical_cv"]
    session["validation"] = audio_result["validation"]
    session["validation_results"] = audio_result["validation"]
    
    logger.info("Session updated with canonical_cv")
    logger.info(f"  - canonical_cv keys: {list(session['canonical_cv'].keys())}")
    logger.info(f"  - Candidate name: {session['canonical_cv'].get('candidate', {}).get('fullName', 'NOT SET')}")
    _log_canonical_preview_details(session)
    
    # Backward compatibility: derive cv_data from canonical rather than trusting
    # a separate legacy extraction pipeline.
    preview_data = _build_preview_from_canonical(audio_result["canonical_cv"])
    session["cv_data"] = preview_data
    
    conversation_service.save_session(session_id, session)
    logger.info("Session saved to storage")
    logger.info("=" * 80)
    _log_speech_event(
        operation="audio_upload_transcribe",
        status="success",
        session_id=session_id,
        source_channel="audio_upload",
        http_status=200,
        payload={
            "can_save": audio_result.get("can_save"),
            "can_export": audio_result.get("can_export"),
            "filename": file.filename,
        },
    )

    # Step 4: Return complete result
    return {
        **transcription_result,
        "session_id": session_id,
        "preview": preview_data,
        "canonical_cv": audio_result["canonical_cv"],
        "validation": audio_result["validation"],
        "can_save": audio_result["can_save"],
        "can_export": audio_result["can_export"],
        "audio_quality_warning": audio_result.get("audio_quality_warning"),
        "cv_data": preview_data,  # Backward compatibility, derived from canonical
    }


@router.post("/correct")
def correct_transcript(
    transcript: str = Form(...),
    corrected_text: str | None = Form(None),
    session_id: str | None = Form(None),
    locale: str = Depends(get_request_locale),
):
    """
    Phase 3: Manual transcript correction with canonical schema integration.
    
    Flow:
    1. Correct and enhance transcript
    2. Process through canonical schema pipeline (AudioCVService)
    3. Update session's canonical_cv + cv_data (backward compatibility)
    4. Return corrected transcript + validation + eligibility flags
    """
    try:
        # Step 1: Correct and enhance
        correction_result = speech_service.correct_transcript(transcript=transcript, corrected_text=corrected_text)
        enhanced_transcript = correction_result["enhanced_transcript"]
    except Exception as exc:
        logger.exception("Transcript correction failed")
        _log_speech_event(
            operation="start_recording_correct_transcript",
            status="failed",
            session_id=session_id,
            source_channel="start_recording",
            http_status=502,
            error_message=str(exc),
        )
        raise HTTPException(status_code=502, detail=t("api.speech.correction_failed", locale=locale, error=str(exc)))

    # Handle session
    if session_id:
        session = conversation_service.get_session(session_id)
        if "error" in session:
            _log_speech_event(
                operation="start_recording_correct_transcript",
                status="failed",
                session_id=session_id,
                source_channel="start_recording",
                http_status=400,
                error_message="Invalid session_id",
            )
            return {"error": t("api.speech.invalid_session", locale=locale)}
    else:
        new_session = conversation_service.start_session(locale=locale)
        session_id = new_session["session_id"]
        session = conversation_service.get_session(session_id)
        correction_result["question"] = new_session.get("question")

    # Step 2: Process through canonical schema pipeline
    audio_result = audio_cv_service.process_audio_transcript(
        enhanced_transcript=enhanced_transcript,
        existing_canonical_cv=session.get("canonical_cv", {}),
        source_type=SourceType.AUDIO_RECORDING  # Corrected transcript treated as recording
    )

    # Step 3: Update session with canonical CV + validation
    logger.info("=" * 80)
    logger.info("SPEECH ROUTER - Updating session with correction results")
    logger.info(f"Session ID: {session_id}")
    
    session["canonical_cv"] = audio_result["canonical_cv"]
    session["validation"] = audio_result["validation"]
    session["validation_results"] = audio_result["validation"]
    
    logger.info("Session updated with canonical_cv")
    logger.info(f"  - canonical_cv keys: {list(session['canonical_cv'].keys())}")
    logger.info(f"  - Candidate name: {session['canonical_cv'].get('candidate', {}).get('fullName', 'NOT SET')}")
    _log_canonical_preview_details(session)
    
    # Backward compatibility: derive cv_data from canonical rather than trusting
    # a separate legacy extraction pipeline.
    preview_data = _build_preview_from_canonical(audio_result["canonical_cv"])
    session["cv_data"] = preview_data
    
    conversation_service.save_session(session_id, session)
    logger.info("Session saved to storage")
    logger.info("=" * 80)
    _log_speech_event(
        operation="start_recording_correct_transcript",
        status="success",
        session_id=session_id,
        source_channel="start_recording",
        http_status=200,
        payload={
            "can_save": audio_result.get("can_save"),
            "can_export": audio_result.get("can_export"),
        },
    )

    # Step 4: Return complete result
    return {
        **correction_result,
        "session_id": session_id,
        "preview": preview_data,
        "canonical_cv": audio_result["canonical_cv"],
        "validation": audio_result["validation"],
        "can_save": audio_result["can_save"],
        "can_export": audio_result["can_export"],
        "audio_quality_warning": audio_result.get("audio_quality_warning"),
        "cv_data": preview_data,  # Backward compatibility, derived from canonical
    }
